from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ai_fiction_to_script.models.runtime import AdaptationRequest, ParsedChapter
from ai_fiction_to_script.models.schema import Outline, ScenePlan, ScreenplayDocument, Script, ScriptAct
from ai_fiction_to_script.pipeline.engine import AdaptationEngine
from ai_fiction_to_script.services.ai_client import MockAIClient, QwenAIClient
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore
from ai_fiction_to_script.services.yaml_service import dump_yaml
from ai_fiction_to_script.settings import QwenSettings


class WorkbenchService:
    def __init__(self, version_root: str | Path = ".novel2script") -> None:
        self.version_store = VersionStore(version_root)
        self.quality_checker = QualityChecker()

    def list_projects(self) -> list[dict]:
        return [project.model_dump(mode="json") for project in self.version_store.list_projects()]

    def list_versions(self, project_id: str) -> list[dict]:
        return [version.model_dump(mode="json") for version in self.version_store.list_versions(project_id)]

    def get_version_payload(self, project_id: str, version_id: str) -> dict:
        record = self.version_store.get_record(project_id, version_id)
        document = self.version_store.load_document(project_id, version_id)
        yaml_text = Path(record.script_yaml_path).read_text(encoding="utf-8")
        return {
            "project_id": project_id,
            "version": record.model_dump(mode="json"),
            "document": document.model_dump(mode="json"),
            "yaml_text": yaml_text,
            "scene_options": self._scene_options(document),
        }

    def diff_versions(self, project_id: str, version_a: str, version_b: str) -> dict:
        return {
            "project_id": project_id,
            "version_a": version_a,
            "version_b": version_b,
            "diff": self.version_store.diff(project_id, version_a, version_b),
        }

    def adapt(self, payload: dict) -> dict:
        request = AdaptationRequest(
            project_id=payload.get("project_id") or self._slugify(payload.get("title") or "novel-project"),
            title=payload.get("title") or "未命名项目",
            original_novel_title=payload.get("original_title") or payload.get("title") or "未命名项目",
            original_author=payload.get("original_author") or "未知作者",
            target_format=payload.get("target_format") or "tv_drama",
            genre=self._normalize_genre(payload.get("genre")),
            tone=payload.get("tone") or "balanced",
            provider=payload.get("provider") or "mock",
        )
        input_path = self._resolve_input_path(request.project_id, payload)
        engine = AdaptationEngine(
            parser=ChapterParser(),
            ai_client=self._build_ai_client(request.provider),
            quality_checker=self.quality_checker,
            version_store=self.version_store,
        )
        result = engine.run(input_path=input_path, request=request, note=payload.get("note", ""))
        if result.version is None:
            raise RuntimeError("Adaptation completed without a saved version.")
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
        return self.get_version_payload(project_id, saved.version_id)

    def regenerate_scene(
        self,
        project_id: str,
        version_id: str,
        scene_id: str,
        instruction: str = "",
        provider_override: str = "",
        note: str = "",
    ) -> dict:
        document = self.version_store.load_document(project_id, version_id)
        request = self._load_request(project_id, version_id, document)
        if provider_override:
            request = request.model_copy(update={"provider": provider_override})

        chapters = self._load_chapters(project_id, version_id)
        outline = document.outline
        scene_plan = self._find_scene_plan(outline.scene_plans, scene_id)
        if instruction:
            scene_plan = scene_plan.model_copy(
                update={
                    "objective": f"{scene_plan.objective}; additional instruction: {instruction}",
                    "notes": f"{scene_plan.notes} | {instruction}".strip(),
                }
            )
        chapter = self._resolve_scene_source(scene_plan, chapters)
        scene = self._build_ai_client(request.provider).generate_scene(scene_plan, document.story_bible, chapter, request)
        updated_script = self._replace_scene(document.script, scene_plan.act_id, scene_id, scene)
        updated_document = document.model_copy(update={"script": updated_script})
        quality = self.quality_checker.review(updated_document)
        ai_warnings, ai_suggestions = self._build_ai_client(request.provider).review_document(updated_document, request)
        quality.warnings = self._merge_unique(quality.warnings, ai_warnings)
        quality.revision_suggestions = self._merge_unique(quality.revision_suggestions, ai_suggestions)
        updated_document = updated_document.model_copy(update={"quality": quality})

        saved = self.version_store.save(
            project_id,
            updated_document,
            intermediates=self._build_intermediates_from_document(project_id, version_id, updated_document, request),
            note=note or f"regenerate {scene_id}",
        )
        return self.get_version_payload(project_id, saved.version_id)

    def export_version_yaml(self, project_id: str, version_id: str) -> str:
        document = self.version_store.load_document(project_id, version_id)
        return dump_yaml(document)

    def _build_ai_client(self, provider: str):
        if provider == "mock":
            return MockAIClient()
        if provider == "qwen":
            return QwenAIClient(QwenSettings.from_env())
        raise ValueError(f"Unsupported provider: {provider}")

    def _resolve_input_path(self, project_id: str, payload: dict) -> Path:
        input_path = payload.get("input_path")
        novel_text = payload.get("novel_text", "")
        if input_path:
            return Path(str(input_path))
        if not novel_text.strip():
            raise ValueError("Either input_path or novel_text must be provided.")
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
                provider=document.meta.model_provider if document.meta.model_provider in {"mock", "qwen"} else "mock",
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

    def _normalize_genre(self, genre) -> list[str]:
        if genre is None:
            return []
        if isinstance(genre, list):
            return [str(item).strip() for item in genre if str(item).strip()]
        if isinstance(genre, str):
            return [item.strip() for item in genre.split(",") if item.strip()]
        return [str(genre).strip()]

    def _slugify(self, value: str) -> str:
        return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-") or "novel-project"

    def _merge_unique(self, base: list[str], new_items: list[str]) -> list[str]:
        output = list(base)
        for item in new_items:
            if item and item not in output:
                output.append(item)
        return output
