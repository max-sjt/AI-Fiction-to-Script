from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ai_fiction_to_script.models.runtime import AdaptationRequest, ModelRouting, ParsedChapter
from ai_fiction_to_script.models.schema import Outline, Scene, ScenePlan, ScreenplayDocument, Script, ScriptAct
from ai_fiction_to_script.pipeline.engine import AdaptationEngine
from ai_fiction_to_script.services.ai_client import HybridAIClient, MockAIClient, QwenAIClient
from ai_fiction_to_script.services.cache_store import CacheStore, NullCacheStore
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.presets import SCRIPT_TYPE_PRESETS, TONE_PRESETS, build_adaptation_goal, build_style_guide_for_tone
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore
from ai_fiction_to_script.services.yaml_service import dump_yaml
from ai_fiction_to_script.settings import QwenSettings, WebCacheSettings


class WorkbenchService:
    def __init__(
        self,
        version_root: str | Path = ".novel2script",
        cache_store: CacheStore | None = None,
        cache_settings: WebCacheSettings | None = None,
    ) -> None:
        self.version_store = VersionStore(version_root)
        self.quality_checker = QualityChecker()
        self.cache_settings = cache_settings or WebCacheSettings()
        self.cache_store = cache_store or NullCacheStore()

    def list_projects(self) -> list[dict]:
        key = "projects"
        cached = self.cache_store.get_json(key)
        if cached is not None:
            return cached
        payload = [project.model_dump(mode="json") for project in self.version_store.list_projects()]
        self.cache_store.set_json(key, payload, self.cache_settings.ttl_seconds)
        return payload

    def list_versions(self, project_id: str) -> list[dict]:
        key = f"projects:{project_id}:versions"
        cached = self.cache_store.get_json(key)
        if cached is not None:
            return cached
        payload = [version.model_dump(mode="json") for version in self.version_store.list_versions(project_id)]
        self.cache_store.set_json(key, payload, self.cache_settings.ttl_seconds)
        return payload

    def get_version_payload(self, project_id: str, version_id: str) -> dict:
        key = f"projects:{project_id}:versions:{version_id}:payload"
        cached = self.cache_store.get_json(key)
        if cached is not None:
            return cached
        record = self.version_store.get_record(project_id, version_id)
        document = self.version_store.load_document(project_id, version_id)
        yaml_text = Path(record.script_yaml_path).read_text(encoding="utf-8")
        payload = {
            "project_id": project_id,
            "version": record.model_dump(mode="json"),
            "document": document.model_dump(mode="json"),
            "yaml_text": yaml_text,
            "rendered_script": self._render_screenplay(document),
            "scene_options": self._scene_options(document),
        }
        self.cache_store.set_json(key, payload, self.cache_settings.ttl_seconds)
        return payload

    def diff_versions(self, project_id: str, version_a: str, version_b: str) -> dict:
        key = f"projects:{project_id}:diff:{version_a}:{version_b}"
        cached = self.cache_store.get_json(key)
        if cached is not None:
            return cached
        payload = {
            "project_id": project_id,
            "version_a": version_a,
            "version_b": version_b,
            "diff": self.version_store.diff(project_id, version_a, version_b),
        }
        self.cache_store.set_json(key, payload, self.cache_settings.ttl_seconds)
        return payload

    def adapt(self, payload: dict) -> dict:
        title = payload.get("title") or "未命名剧本"
        tone = payload.get("tone") or "balanced"
        target_format = payload.get("script_type") or "tv_drama"
        request = AdaptationRequest(
            project_id=self._slugify(title),
            title=title,
            original_novel_title=payload.get("original_title") or title,
            original_author=payload.get("original_author") or "未知作者",
            target_format=target_format,
            genre=self._normalize_genre(payload.get("genre")),
            tone=tone,
            adaptation_goal=build_adaptation_goal(target_format),
            style_guide=build_style_guide_for_tone(tone),
            provider=payload.get("provider") or "qwen",
            model_routing=self._web_model_routing(payload.get("provider") or "qwen"),
        )
        input_path = self._resolve_input_path(request.project_id, payload)
        engine = AdaptationEngine(
            parser=ChapterParser(),
            ai_client=self._build_ai_client(request.provider, payload.get("api_key", "")),
            quality_checker=self.quality_checker,
            version_store=self.version_store,
        )
        result = engine.run(input_path=input_path, request=request, note=payload.get("note", ""))
        if result.version is None:
            raise RuntimeError("Adaptation completed without a saved version.")
        self._invalidate_project_cache(request.project_id)
        return self.get_version_payload(request.project_id, result.version.version_id)

    def save_edited_yaml(self, project_id: str, version_id: str, yaml_text: str, note: str = "") -> dict:
        payload = yaml.safe_load(yaml_text)
        if not isinstance(payload, dict):
            raise ValueError("YAML must deserialize into an object.")
        document = ScreenplayDocument.model_validate(payload)
        quality = self.quality_checker.review(document)
        document = document.model_copy(update={"quality": quality})

        request = self._load_request(project_id, version_id, document)
        intermediates = self._build_intermediates_from_document(project_id, version_id, document, request)
        saved = self.version_store.save(
            project_id,
            document,
            intermediates=intermediates,
            note=note or f"manual edit from {version_id}",
        )
        self._invalidate_project_cache(project_id)
        return self.get_version_payload(project_id, saved.version_id)

    def regenerate_scene(
        self,
        project_id: str,
        version_id: str,
        scene_id: str,
        instruction: str = "",
        provider_override: str = "",
        api_key: str = "",
        tone_override: str = "",
        note: str = "",
    ) -> dict:
        document = self.version_store.load_document(project_id, version_id)
        request = self._load_request(project_id, version_id, document)
        if provider_override:
            request = request.model_copy(update={"provider": provider_override})
        if tone_override:
            request = request.model_copy(
                update={
                    "tone": tone_override,
                    "style_guide": build_style_guide_for_tone(tone_override),
                }
            )
        if request.provider == "qwen":
            request = request.model_copy(update={"model_routing": self._web_model_routing(request.provider)})

        chapters = self._load_chapters(project_id, version_id)
        outline = document.outline
        scene_plan = self._find_scene_plan(outline.scene_plans, scene_id)
        previous_scene = self._find_scene(document.script, scene_id)
        if instruction:
            scene_plan = scene_plan.model_copy(
                update={
                    "objective": f"{scene_plan.objective}；修改要求：{instruction}",
                    "notes": f"{scene_plan.notes} | 本次重生成必须执行：{instruction}".strip(" |"),
                }
            )
        chapter = self._resolve_scene_source(scene_plan, chapters)
        ai_client = self._build_ai_client(request.provider, api_key)
        scene = ai_client.generate_scene(scene_plan, document.story_bible, chapter, request)
        updated_script = self._replace_scene(document.script, scene_plan.act_id, scene_id, scene)
        updated_document = document.model_copy(
            update={
                "meta": document.meta.model_copy(
                    update={
                        "tone": request.tone,
                        "model_provider": request.provider,
                        "model_name": self._resolve_model_name(request),
                    }
                ),
                "adaptation": document.adaptation.model_copy(
                    update={
                        "adaptation_goal": request.adaptation_goal,
                        "style_guide": request.style_guide,
                    }
                ),
                "script": updated_script,
            }
        )
        quality = self.quality_checker.review(updated_document)
        ai_warnings, ai_suggestions = ai_client.review_document(updated_document, request)
        quality.warnings = self._merge_unique(quality.warnings, ai_warnings)
        quality.revision_suggestions = self._merge_unique(quality.revision_suggestions, ai_suggestions)
        updated_document = updated_document.model_copy(update={"quality": quality})

        saved = self.version_store.save(
            project_id,
            updated_document,
            intermediates=self._build_intermediates_from_document(project_id, version_id, updated_document, request),
            note=note or f"regenerate {scene_id}",
        )
        self._invalidate_project_cache(project_id)
        payload = self.get_version_payload(project_id, saved.version_id)
        payload["scene_comparison"] = self._build_scene_comparison(
            document=document,
            previous_scene=previous_scene,
            updated_document=updated_document,
            updated_scene=scene,
            instruction=instruction,
        )
        return payload

    def export_version_yaml(self, project_id: str, version_id: str) -> str:
        document = self.version_store.load_document(project_id, version_id)
        return dump_yaml(document)

    def _build_ai_client(self, provider: str, api_key: str = ""):
        if provider == "mock":
            return MockAIClient()
        if provider == "qwen":
            qwen_client = QwenAIClient(QwenSettings.from_env(api_key_override=api_key or None))
            planner_client = MockAIClient()
            return HybridAIClient(planner_client=planner_client, generator_client=qwen_client, reviewer_client=planner_client)
        raise ValueError(f"Unsupported provider: {provider}")

    def _web_model_routing(self, provider: str) -> ModelRouting:
        if provider != "qwen":
            return ModelRouting()
        return ModelRouting(
            summary_model="qwen3.6-flash",
            planning_model="qwen3.6-flash",
            generation_model="qwen3.6-flash",
            validation_model="qwen3.6-flash",
        )

    def _resolve_input_path(self, project_id: str, payload: dict) -> Path:
        input_path = payload.get("input_path")
        novel_text = payload.get("novel_text", "")
        upload_name = payload.get("upload_name", "")
        upload_base64 = payload.get("upload_base64", "")
        if input_path:
            return Path(str(input_path))
        if upload_name and upload_base64:
            uploads_dir = self.version_store.root / "_uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            suffix = Path(upload_name).suffix or ".txt"
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            target = uploads_dir / f"{project_id}_{timestamp}{suffix}"
            target.write_bytes(base64.b64decode(upload_base64))
            return target
        if not novel_text.strip():
            raise ValueError("Provide a file upload, an input path, or pasted novel text.")
        uploads_dir = self.version_store.root / "_uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        target = uploads_dir / f"{project_id}_{timestamp}.txt"
        target.write_text(novel_text, encoding="utf-8")
        return target

    def _load_request(self, project_id: str, version_id: str, document: ScreenplayDocument) -> AdaptationRequest:
        try:
            payload = self.version_store.load_intermediate(project_id, version_id, "request")
            return AdaptationRequest.model_validate(payload)
        except FileNotFoundError:
            return AdaptationRequest(
                project_id=document.meta.project_id,
                title=document.meta.title,
                original_novel_title=document.meta.original_novel_title,
                original_author=document.meta.original_author,
                target_format=document.meta.target_format,
                language=document.meta.language,
                genre=document.meta.genre,
                tone=document.meta.tone,
                provider=document.meta.model_provider if document.meta.model_provider in {"mock", "qwen"} else "qwen",
                adaptation_goal=build_adaptation_goal(document.meta.target_format),
                style_guide=build_style_guide_for_tone(document.meta.tone),
            )

    def _load_chapters(self, project_id: str, version_id: str) -> list[ParsedChapter]:
        payload = self.version_store.load_intermediate(project_id, version_id, "chapters")
        return [ParsedChapter.model_validate(item) for item in payload]

    def _build_intermediates_from_document(
        self,
        project_id: str,
        version_id: str,
        document: ScreenplayDocument,
        request: AdaptationRequest,
    ) -> dict:
        intermediates: dict = {
            "request": request.model_dump(mode="json"),
            "story_bible": document.story_bible.model_dump(mode="json"),
            "outline": document.outline.model_dump(mode="json"),
            "document_snapshot": document.model_dump(mode="json"),
            "edit_context": {
                "source_project_id": project_id,
                "source_version_id": version_id,
            },
        }
        try:
            intermediates["chapters"] = self.version_store.load_intermediate(project_id, version_id, "chapters")
        except FileNotFoundError:
            intermediates["chapters"] = []
        try:
            intermediates["chapter_analyses"] = self.version_store.load_intermediate(project_id, version_id, "chapter_analyses")
        except FileNotFoundError:
            pass
        return intermediates

    def _scene_options(self, document: ScreenplayDocument) -> list[dict]:
        options: list[dict] = []
        for act in document.script.acts:
            for scene in act.scenes:
                options.append(
                    {
                        "scene_id": scene.scene_id,
                        "act_id": act.act_id,
                        "label": f"{scene.scene_id} · {scene.title}",
                        "title": scene.title,
                    }
                )
        return options

    def _find_scene_plan(self, scene_plans: list[ScenePlan], scene_id: str) -> ScenePlan:
        for scene_plan in scene_plans:
            if scene_plan.scene_id == scene_id:
                return scene_plan
        raise ValueError(f"Scene plan not found: {scene_id}")

    def _resolve_scene_source(self, scene_plan: ScenePlan, chapters: list[ParsedChapter]) -> ParsedChapter:
        chapter_map = {chapter.chapter_id: chapter for chapter in chapters}
        for chapter_id in scene_plan.chapter_refs:
            if chapter_id in chapter_map:
                return chapter_map[chapter_id]
        return chapters[0]

    def _replace_scene(self, script: Script, act_id: str, scene_id: str, replacement) -> Script:
        acts: list[ScriptAct] = []
        replaced = False
        for act in script.acts:
            scenes = []
            for scene in act.scenes:
                if act.act_id == act_id and scene.scene_id == scene_id:
                    scenes.append(replacement)
                    replaced = True
                else:
                    scenes.append(scene)
            acts.append(ScriptAct(act_id=act.act_id, title=act.title, scenes=scenes))
        if not replaced:
            raise ValueError(f"Scene not found in script: {scene_id}")
        return Script(acts=acts)

    def _find_scene(self, script: Script, scene_id: str) -> Scene:
        for act in script.acts:
            for scene in act.scenes:
                if scene.scene_id == scene_id:
                    return scene
        raise ValueError(f"Scene not found in script: {scene_id}")

    def _normalize_genre(self, genre) -> list[str]:
        if genre is None:
            return []
        if isinstance(genre, list):
            return [str(item).strip() for item in genre if str(item).strip()]
        if isinstance(genre, str):
            return [item.strip() for item in genre.split(",") if item.strip()]
        return [str(genre).strip()]

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^\w-]+", "-", value, flags=re.UNICODE).strip("-_")
        return slug or "novel-project"

    def _merge_unique(self, base: list[str], new_items: list[str]) -> list[str]:
        output = list(base)
        for item in new_items:
            if item and item not in output:
                output.append(item)
        return output

    def _build_scene_comparison(
        self,
        document: ScreenplayDocument,
        previous_scene: Scene,
        updated_document: ScreenplayDocument,
        updated_scene: Scene,
        instruction: str,
    ) -> dict:
        before_rendered = self._render_scene(document, previous_scene)
        after_rendered = self._render_scene(updated_document, updated_scene)
        return {
            "scene_id": updated_scene.scene_id,
            "instruction": instruction,
            "before": {
                "scene": previous_scene.model_dump(mode="json"),
                "rendered": before_rendered,
            },
            "after": {
                "scene": updated_scene.model_dump(mode="json"),
                "rendered": after_rendered,
            },
        }

    def _render_screenplay(self, document: ScreenplayDocument) -> str:
        lines: list[str] = [document.meta.title, "=" * len(document.meta.title), ""]
        lines.append(f"剧本类型：{SCRIPT_TYPE_PRESETS.get(document.meta.target_format, {}).get('label_zh', document.meta.target_format)}")
        lines.append(f"题材：{', '.join(document.meta.genre) if document.meta.genre else '未设置'}")
        lines.append(f"语气：{TONE_PRESETS.get(document.meta.tone, {}).get('label_zh', document.meta.tone)}")
        lines.append("")
        for act in document.script.acts:
            lines.append(f"{act.act_id.upper()} {act.title}")
            lines.append("-" * max(12, len(act.title) + 4))
            for scene in act.scenes:
                lines.append(f"[{scene.scene_id}] {scene.title}")
                if scene.summary:
                    lines.append(f"场景摘要：{scene.summary}")
                if scene.objective:
                    lines.append(f"戏剧目标：{scene.objective}")
                for beat in scene.beats:
                    if beat.type == "dialogue" and beat.speaker_ref:
                        speaker_name = self._speaker_name(document, beat.speaker_ref)
                        lines.append(f"{speaker_name}：{beat.text}")
                    else:
                        lines.append(beat.text)
                lines.append("")
            lines.append("")
        return "\n".join(lines).strip()

    def _render_scene(self, document: ScreenplayDocument, scene: Scene) -> str:
        lines = [f"[{scene.scene_id}] {scene.title}"]
        if scene.summary:
            lines.append(f"场景摘要：{scene.summary}")
        if scene.objective:
            lines.append(f"戏剧目标：{scene.objective}")
        for beat in scene.beats:
            if beat.type == "dialogue" and beat.speaker_ref:
                speaker_name = self._speaker_name(document, beat.speaker_ref)
                lines.append(f"{speaker_name}：{beat.text}")
            else:
                lines.append(beat.text)
        return "\n".join(lines).strip()

    def _speaker_name(self, document: ScreenplayDocument, speaker_ref: str) -> str:
        for character in document.story_bible.characters:
            if character.character_id == speaker_ref:
                return character.name
        return speaker_ref

    def _resolve_model_name(self, request: AdaptationRequest) -> str:
        if request.provider == "mock":
            return "mock-qwen-planner"
        return request.model_routing.generation_model

    def _invalidate_project_cache(self, project_id: str) -> None:
        self.cache_store.delete_prefix("projects")
        self.cache_store.delete_prefix(f"projects:{project_id}")
