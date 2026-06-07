from __future__ import annotations

import base64
import json
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ai_fiction_to_script.models.runtime import AdaptationRequest, ModelRouting, ParsedChapter
from ai_fiction_to_script.models.schema import Outline, Scene, ScenePlan, ScreenplayDocument, Script, ScriptAct
from ai_fiction_to_script.pipeline.engine import AdaptationEngine, synchronize_outline_with_script
from ai_fiction_to_script.services.ai_client import HybridAIClient, MockAIClient, QwenAIClient, _normalize_scene_refs
from ai_fiction_to_script.services.cache_store import CacheStore, NullCacheStore
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.presets import SCRIPT_TYPE_PRESETS, TONE_PRESETS, build_adaptation_goal, build_style_guide_for_tone
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore
from ai_fiction_to_script.services.yaml_service import dump_yaml
from ai_fiction_to_script.settings import QwenSettings, WebCacheSettings


@dataclass(slots=True)
class AsyncTaskRecord:
    task_id: str
    kind: str
    project_id: str
    preview_version_id: str
    status: str = "running"
    final_version_id: str = ""
    error: str = ""
    result: dict | None = None
    created_at: str = ""
    updated_at: str = ""


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
        self._tasks: dict[str, AsyncTaskRecord] = {}
        self._task_lock = threading.Lock()

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
        if cached is not None and not self._is_stale_version_payload(cached):
            return cached
        record = self.version_store.get_record(project_id, version_id)
        document = self.version_store.load_document(project_id, version_id)
        yaml_text = dump_yaml(document)
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

    def delete_version(self, project_id: str, version_id: str) -> dict:
        self.version_store.delete_version(project_id, version_id)
        self._invalidate_project_cache(project_id)
        project_exists = any(project["project_id"] == project_id for project in self.list_projects())
        return {
            "project_id": project_id,
            "version_id": version_id,
            "project_exists": project_exists,
            "versions": self.list_versions(project_id) if project_exists else [],
        }

    def adapt(self, payload: dict) -> dict:
        request = self._build_request_from_payload(payload)
        input_path = self._resolve_input_path(request.project_id, payload)
        return self._run_adaptation(
            input_path=input_path,
            request=request,
            ai_client=self._build_ai_client(request.provider, payload.get("api_key", "")),
            note=payload.get("note", ""),
        )

    def start_adapt_async(self, payload: dict) -> dict:
        request = self._build_request_from_payload(payload)
        input_path = self._resolve_input_path(request.project_id, payload)
        preview_request = request.model_copy(update={"provider": "mock"})
        preview_payload = self._run_adaptation(
            input_path=input_path,
            request=preview_request,
            ai_client=MockAIClient(),
            note=payload.get("note") or "local preview draft",
        )
        task = self._create_task(
            kind="adapt",
            project_id=request.project_id,
            preview_version_id=preview_payload["version"]["version_id"],
        )
        self._update_task(
            task.task_id,
            result=self._task_snapshot_payload(
                project_id=request.project_id,
                version_id=preview_payload["version"]["version_id"],
                rendered_script=preview_payload["rendered_script"],
                completed_scenes=0,
                total_scenes=len(preview_payload["scene_options"]),
                mode="preview",
            ),
        )
        thread = threading.Thread(
            target=self._finish_adapt_async,
            args=(
                task.task_id,
                input_path,
                request,
                payload.get("api_key", ""),
                payload.get("note", ""),
                preview_payload["version"]["version_id"],
            ),
            daemon=True,
        )
        thread.start()
        return {
            "preview": preview_payload,
            "task": self._serialize_task(task),
        }

    def save_edited_yaml(self, project_id: str, version_id: str, yaml_text: str, note: str = "") -> dict:
        payload = yaml.safe_load(yaml_text)
        if not isinstance(payload, dict):
            raise ValueError("YAML must deserialize into an object.")
        document = ScreenplayDocument.model_validate(payload)
        document = document.model_copy(update={"outline": synchronize_outline_with_script(document.outline, document.script)})
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
        scene_plan = self._apply_scene_instruction(scene_plan, instruction)
        chapter = self._resolve_scene_source(scene_plan, chapters)
        ai_client = self._build_ai_client(request.provider, api_key)
        scene = ai_client.generate_scene(scene_plan, document.story_bible, chapter, request)
        scene = _normalize_scene_refs(scene, document.story_bible)
        updated_script = self._replace_scene(document.script, scene_plan.act_id, scene_id, scene)
        updated_outline = synchronize_outline_with_script(document.outline, updated_script)
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
                "outline": updated_outline,
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

    def start_regenerate_scene_async(
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
        preview_comparison = self._build_pending_scene_comparison(document, scene_id, instruction)
        task = self._create_task(
            kind="regenerate_scene",
            project_id=project_id,
            preview_version_id=version_id,
        )
        self._update_task(
            task.task_id,
            result=self._task_snapshot_payload(
                project_id=project_id,
                version_id=version_id,
                rendered_script="",
                completed_scenes=0,
                total_scenes=1,
                mode="streaming",
                scene_comparison=preview_comparison,
                active_scene_id=scene_id,
            ),
        )
        thread = threading.Thread(
            target=self._finish_regenerate_scene_async,
            args=(
                task.task_id,
                project_id,
                version_id,
                version_id,
                scene_id,
                provider_override or "qwen",
                api_key,
                tone_override,
                instruction,
                note,
            ),
            daemon=True,
        )
        thread.start()
        return {
            "preview": {
                "project_id": project_id,
                "version": {"version_id": version_id},
                "scene_comparison": preview_comparison,
            },
            "task": self._serialize_task(task),
        }

    def get_task_status(self, task_id: str) -> dict:
        with self._task_lock:
            task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return self._serialize_task(task)

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

    def _build_request_from_payload(self, payload: dict) -> AdaptationRequest:
        title = payload.get("title") or "未命名剧本"
        tone = payload.get("tone") or "balanced"
        target_format = payload.get("script_type") or "tv_drama"
        provider = payload.get("provider") or "qwen"
        speed_mode = self._resolve_speed_mode(provider, payload)
        return AdaptationRequest(
            project_id=self._slugify(title),
            title=title,
            original_novel_title=payload.get("original_title") or title,
            original_author=payload.get("original_author") or "未知作者",
            target_format=target_format,
            genre=self._normalize_genre(payload.get("genre")),
            tone=tone,
            adaptation_goal=build_adaptation_goal(target_format),
            style_guide=build_style_guide_for_tone(tone),
            provider=provider,
            model_routing=self._web_model_routing(provider),
            temperature=0.2 if speed_mode == "fast" else 0.3,
            max_scenes_per_chapter=1 if speed_mode == "fast" else 2,
        )

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

    def _resolve_speed_mode(self, provider: str, payload: dict) -> str:
        raw_mode = str(payload.get("speed_mode") or "").strip().lower()
        if raw_mode in {"fast", "balanced"}:
            return raw_mode
        if provider == "qwen":
            return "fast"
        return "balanced"

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^\w-]+", "-", value, flags=re.UNICODE).strip("-_")
        return slug or "novel-project"

    def _merge_unique(self, base: list[str], new_items: list[str]) -> list[str]:
        output = list(base)
        for item in new_items:
            if item and item not in output:
                output.append(item)
        return output

    def _apply_scene_instruction(self, scene_plan: ScenePlan, instruction: str) -> ScenePlan:
        if not instruction:
            return scene_plan
        objective = (scene_plan.objective or "").strip()
        notes = (scene_plan.notes or "").strip()
        updated_objective = f"{objective}；修改要求：{instruction}".strip("；")
        updated_notes = f"{notes} | 本次重生成必须执行：{instruction}".strip(" |")
        return scene_plan.model_copy(
            update={
                "objective": updated_objective,
                "notes": updated_notes,
            }
        )

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

    def _build_pending_scene_comparison(
        self,
        document: ScreenplayDocument,
        scene_id: str,
        instruction: str,
    ) -> dict:
        previous_scene = self._find_scene(document.script, scene_id)
        return {
            "scene_id": scene_id,
            "instruction": instruction,
            "before": {
                "scene": previous_scene.model_dump(mode="json"),
                "rendered": self._render_scene(document, previous_scene),
            },
            "after": {
                "scene": None,
                "rendered": "",
            },
        }

    def _render_screenplay(self, document: ScreenplayDocument) -> str:
        lines = self._screenplay_header_lines(document)
        for scene in self._iter_script_scenes(document.script):
            lines.append(self._render_scene(document, scene))
            lines.append("")
        return "\n".join(lines).strip()

    def _render_scene(self, document: ScreenplayDocument, scene: Scene) -> str:
        lines = [f"[{scene.scene_id}] {scene.title}"]
        if scene.summary:
            lines.append(f"场景摘要：{scene.summary}")
        for beat in scene.beats:
            lines.append(self._render_beat(document, beat))
        if scene.transitions and scene.transitions.next_scene_hint:
            lines.append(f"转场：{scene.transitions.next_scene_hint}")
        return "\n".join(lines).strip()

    def _render_streaming_scene(self, scene_plan: ScenePlan, streamed_text: str) -> str:
        lines = [
            f"[{scene_plan.scene_id}] {scene_plan.title}",
            "Qwen 正在生成当前场景...",
        ]
        if streamed_text.strip():
            lines.append("")
            lines.append(streamed_text.rstrip())
        return "\n".join(lines).strip()

    def _render_screenplay_with_scene_override(
        self,
        document: ScreenplayDocument,
        script: Script,
        target_scene_id: str,
        override_text: str,
    ) -> str:
        lines = self._screenplay_header_lines(document)
        for scene in self._iter_script_scenes(script):
            if scene.scene_id == target_scene_id:
                lines.append(override_text)
            else:
                lines.append(self._render_scene(document, scene))
            lines.append("")
        return "\n".join(lines).strip()

    def _render_screenplay_progress(
        self,
        document: ScreenplayDocument,
        script: Script,
        visible_scene_ids: set[str],
        target_scene_id: str = "",
        override_text: str = "",
    ) -> str:
        lines = self._screenplay_header_lines(document)
        for scene in self._iter_script_scenes(script):
            if scene.scene_id not in visible_scene_ids:
                continue
            if scene.scene_id == target_scene_id and override_text:
                lines.append(override_text)
            else:
                lines.append(self._render_scene(document, scene))
            lines.append("")
        return "\n".join(lines).strip()

    def _screenplay_header_lines(self, document: ScreenplayDocument) -> list[str]:
        script_type_label = SCRIPT_TYPE_PRESETS.get(document.meta.target_format, dict()).get("label_zh", document.meta.target_format)
        tone_label = TONE_PRESETS.get(document.meta.tone, dict()).get("label_zh", document.meta.tone)
        genre_label = ", ".join(document.meta.genre) if document.meta.genre else "未设置"
        lines: list[str] = [document.meta.title, "=" * len(document.meta.title), ""]
        lines.append(f"剧本类型：{script_type_label}")
        lines.append(f"题材：{genre_label}")
        lines.append(f"语气：{tone_label}")
        lines.append("")
        return lines

    def _iter_script_scenes(self, script: Script):
        for act in script.acts:
            for scene in act.scenes:
                yield scene

    def _render_beat(self, document: ScreenplayDocument, beat) -> str:
        text = beat.text.strip()
        if beat.type != "dialogue" or not beat.speaker_ref:
            return text
        speaker_name = self._speaker_name(document, beat.speaker_ref)
        duplicate_prefixes = (
            f"{speaker_name}：",
            f"{speaker_name}:",
            f"{speaker_name}说",
            f"{speaker_name}问",
            f"{speaker_name}喊",
            f"{speaker_name}答",
            f"{speaker_name}道",
        )
        if any(text.startswith(prefix) for prefix in duplicate_prefixes):
            return text
        return f"{speaker_name}：{text}"

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

    def _is_stale_version_payload(self, payload: dict) -> bool:
        if not isinstance(payload, dict):
            return True

        document = payload.get("document")
        if not isinstance(document, dict):
            return True

        if document.get("schema_version") != "2.0":
            return True

        yaml_text = payload.get("yaml_text")
        if not isinstance(yaml_text, str):
            return True

        if "schema_version: '1.0'" in yaml_text or 'schema_version: "1.0"' in yaml_text:
            return True

        return False

    def _generate_scene_with_optional_stream(
        self,
        ai_client,
        scene_plan: ScenePlan,
        story_bible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
        on_delta=None,
    ) -> Scene:
        generator = ai_client
        if hasattr(generator, "generate_scene_stream"):
            return generator.generate_scene_stream(scene_plan, story_bible, chapter, request, on_delta=on_delta)
        nested_generator = getattr(generator, "_generator_client", None)
        if nested_generator is not None and hasattr(nested_generator, "generate_scene_stream"):
            return nested_generator.generate_scene_stream(scene_plan, story_bible, chapter, request, on_delta=on_delta)
        return ai_client.generate_scene(scene_plan, story_bible, chapter, request)

    def _run_adaptation(
        self,
        input_path: str | Path,
        request: AdaptationRequest,
        ai_client,
        note: str,
    ) -> dict:
        engine = AdaptationEngine(
            parser=ChapterParser(),
            ai_client=ai_client,
            quality_checker=self.quality_checker,
            version_store=self.version_store,
        )
        result = engine.run(input_path=input_path, request=request, note=note)
        if result.version is None:
            raise RuntimeError("Adaptation completed without a saved version.")
        self._invalidate_project_cache(request.project_id)
        return self.get_version_payload(request.project_id, result.version.version_id)

    def _run_adaptation_progressive(
        self,
        task_id: str,
        input_path: str | Path,
        request: AdaptationRequest,
        ai_client,
        note: str,
        preview_version_id: str,
    ) -> dict:
        chapters = ChapterParser().parse(input_path)
        if not chapters or not any(chapter.raw_text.strip() for chapter in chapters):
            raise ValueError("输入小说正文为空，无法生成剧本。")
        if len(chapters) < 3:
            raise ValueError("输入小说章节数不足 3 章，无法生成符合 Schema 2.0 的结构化剧本。")

        preview_document = self.version_store.load_document(request.project_id, preview_version_id)
        outline = preview_document.outline
        current_script = preview_document.script
        total_scenes = max(1, len(outline.scene_plans))
        completed_scenes = 0
        visible_scene_ids: set[str] = set()

        for scene_plan in outline.scene_plans:
            chapter = self._resolve_scene_source(scene_plan, chapters)

            def on_scene_delta(accumulated_text: str, _delta_text: str) -> None:
                streaming_scene = self._render_streaming_scene(scene_plan, accumulated_text)
                self._update_task(
                    task_id,
                    result=self._task_snapshot_payload(
                        project_id=request.project_id,
                        version_id=preview_version_id,
                        rendered_script=self._render_screenplay_progress(
                            preview_document,
                            current_script,
                            visible_scene_ids | {scene_plan.scene_id},
                            target_scene_id=scene_plan.scene_id,
                            override_text=streaming_scene,
                        ),
                        completed_scenes=completed_scenes,
                        total_scenes=total_scenes,
                        mode="streaming",
                        stream_source="model_chunk",
                        active_scene_id=scene_plan.scene_id,
                    ),
                )

            scene = self._generate_scene_with_optional_stream(
                ai_client,
                scene_plan,
                preview_document.story_bible,
                chapter,
                request,
                on_delta=on_scene_delta,
            )
            scene = _normalize_scene_refs(scene, preview_document.story_bible)
            current_script = self._replace_scene(current_script, scene_plan.act_id, scene_plan.scene_id, scene)
            completed_scenes += 1
            visible_scene_ids.add(scene_plan.scene_id)
            partial_document = preview_document.model_copy(
                update={
                    "meta": preview_document.meta.model_copy(
                        update={
                            "tone": request.tone,
                            "model_provider": request.provider,
                            "model_name": self._resolve_model_name(request),
                        }
                    ),
                    "adaptation": preview_document.adaptation.model_copy(
                        update={
                            "adaptation_goal": request.adaptation_goal,
                            "style_guide": request.style_guide,
                        }
                    ),
                    "script": current_script,
                }
            )
            self._update_task(
                task_id,
                result=self._task_snapshot_payload(
                    project_id=request.project_id,
                    version_id=preview_version_id,
                    rendered_script=self._render_screenplay_progress(
                        partial_document,
                        current_script,
                        visible_scene_ids,
                    ),
                    completed_scenes=completed_scenes,
                    total_scenes=total_scenes,
                    mode="streaming",
                    stream_source="scene_snapshot",
                    active_scene_id=scene_plan.scene_id,
                ),
            )

        updated_document = preview_document.model_copy(
            update={
                "meta": preview_document.meta.model_copy(
                    update={
                        "tone": request.tone,
                        "model_provider": request.provider,
                        "model_name": self._resolve_model_name(request),
                    }
                ),
                "adaptation": preview_document.adaptation.model_copy(
                    update={
                        "adaptation_goal": request.adaptation_goal,
                        "style_guide": request.style_guide,
                    }
                ),
                "script": current_script,
            }
        )
        quality = self.quality_checker.review(updated_document)
        ai_warnings, ai_suggestions = ai_client.review_document(updated_document, request)
        quality.warnings = self._merge_unique(quality.warnings, ai_warnings)
        quality.revision_suggestions = self._merge_unique(quality.revision_suggestions, ai_suggestions)
        updated_document = updated_document.model_copy(update={"quality": quality})

        saved = self.version_store.save(
            request.project_id,
            updated_document,
            intermediates=self._build_intermediates_from_document(request.project_id, preview_version_id, updated_document, request),
            note=note,
        )
        self._invalidate_project_cache(request.project_id)
        return self.get_version_payload(request.project_id, saved.version_id)

    def _create_task(self, kind: str, project_id: str, preview_version_id: str) -> AsyncTaskRecord:
        now = datetime.now(timezone.utc).isoformat()
        task = AsyncTaskRecord(
            task_id=uuid.uuid4().hex,
            kind=kind,
            project_id=project_id,
            preview_version_id=preview_version_id,
            created_at=now,
            updated_at=now,
        )
        with self._task_lock:
            self._tasks[task.task_id] = task
        return task

    def _update_task(self, task_id: str, **updates) -> None:
        with self._task_lock:
            task = self._tasks[task_id]
            for key, value in updates.items():
                setattr(task, key, value)
            task.updated_at = datetime.now(timezone.utc).isoformat()

    def _serialize_task(self, task: AsyncTaskRecord) -> dict:
        return {
            "task_id": task.task_id,
            "kind": task.kind,
            "project_id": task.project_id,
            "preview_version_id": task.preview_version_id,
            "status": task.status,
            "final_version_id": task.final_version_id,
            "error": task.error,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "result": task.result,
        }

    def _task_snapshot_payload(
        self,
        project_id: str,
        version_id: str,
        rendered_script: str,
        completed_scenes: int,
        total_scenes: int,
        mode: str,
        scene_comparison: dict | None = None,
        stream_source: str = "scene_snapshot",
        active_scene_id: str = "",
    ) -> dict:
        payload = {
            "project_id": project_id,
            "version": {"version_id": version_id},
            "rendered_script": rendered_script,
            "completed_scenes": completed_scenes,
            "total_scenes": total_scenes,
            "mode": mode,
            "stream_source": stream_source,
            "active_scene_id": active_scene_id,
        }
        if scene_comparison is not None:
            payload["scene_comparison"] = scene_comparison
        return payload

    def _finish_adapt_async(
        self,
        task_id: str,
        input_path: Path,
        request: AdaptationRequest,
        api_key: str,
        note: str,
        preview_version_id: str,
    ) -> None:
        try:
            payload = self._run_adaptation_progressive(
                task_id=task_id,
                input_path=input_path,
                request=request,
                ai_client=self._build_ai_client(request.provider, api_key),
                note=note or "qwen final draft",
                preview_version_id=preview_version_id,
            )
            self._update_task(
                task_id,
                status="completed",
                final_version_id=payload["version"]["version_id"],
                result=payload,
            )
        except Exception as exc:
            self._update_task(task_id, status="failed", error=str(exc))

    def _finish_regenerate_scene_async(
        self,
        task_id: str,
        project_id: str,
        version_id: str,
        preview_version_id: str,
        scene_id: str,
        provider_override: str,
        api_key: str,
        tone_override: str,
        instruction: str,
        note: str,
    ) -> None:
        try:
            payload = self._run_regenerate_scene_progressive(
                task_id=task_id,
                project_id=project_id,
                version_id=version_id,
                preview_version_id=preview_version_id,
                scene_id=scene_id,
                instruction=instruction,
                provider_override=provider_override,
                api_key=api_key,
                tone_override=tone_override,
                note=note or f"qwen final regenerate {scene_id}",
            )
            self._update_task(
                task_id,
                status="completed",
                final_version_id=payload["version"]["version_id"],
                result=payload,
            )
        except Exception as exc:
            self._update_task(task_id, status="failed", error=str(exc))

    def _run_regenerate_scene_progressive(
        self,
        task_id: str,
        project_id: str,
        version_id: str,
        preview_version_id: str,
        scene_id: str,
        instruction: str,
        provider_override: str,
        api_key: str,
        tone_override: str,
        note: str,
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
        scene_plan = self._apply_scene_instruction(scene_plan, instruction)
        chapter = self._resolve_scene_source(scene_plan, chapters)
        ai_client = self._build_ai_client(request.provider, api_key)
        pending_comparison = self._build_pending_scene_comparison(document, scene_id, instruction)

        def on_scene_delta(accumulated_text: str, _delta_text: str) -> None:
            streaming_scene = self._render_streaming_scene(scene_plan, accumulated_text)
            streaming_comparison = {
                **pending_comparison,
                "after": {
                    "scene": None,
                    "rendered": streaming_scene,
                },
            }
            self._update_task(
                task_id,
                result=self._task_snapshot_payload(
                    project_id=project_id,
                    version_id=preview_version_id,
                    rendered_script=self._render_screenplay_with_scene_override(
                        document,
                        document.script,
                        scene_id,
                        streaming_scene,
                    ),
                    completed_scenes=0,
                    total_scenes=1,
                    mode="streaming",
                    scene_comparison=streaming_comparison,
                    stream_source="model_chunk",
                    active_scene_id=scene_id,
                ),
            )

        scene = self._generate_scene_with_optional_stream(
            ai_client,
            scene_plan,
            document.story_bible,
            chapter,
            request,
            on_delta=on_scene_delta,
        )
        scene = _normalize_scene_refs(scene, document.story_bible)
        updated_script = self._replace_scene(document.script, scene_plan.act_id, scene_id, scene)
        updated_outline = synchronize_outline_with_script(document.outline, updated_script)
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
                "outline": updated_outline,
                "script": updated_script,
            }
        )
        scene_comparison = self._build_scene_comparison(
            document=document,
            previous_scene=previous_scene,
            updated_document=updated_document,
            updated_scene=scene,
            instruction=instruction,
        )
        self._update_task(
            task_id,
            result=self._task_snapshot_payload(
                project_id=project_id,
                version_id=preview_version_id,
                rendered_script=self._render_screenplay(updated_document),
                completed_scenes=1,
                total_scenes=1,
                mode="streaming",
                scene_comparison=scene_comparison,
                stream_source="scene_snapshot",
                active_scene_id=scene_id,
            ),
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
            note=note or f"qwen final regenerate {scene_id}",
        )
        self._invalidate_project_cache(project_id)
        payload = self.get_version_payload(project_id, saved.version_id)
        payload["scene_comparison"] = scene_comparison
        return payload
