from __future__ import annotations

import base64
import json
import re
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ai_fiction_to_script.models.runtime import AdaptationRequest, ChapterAnalysis, ModelRouting, ParsedChapter
from ai_fiction_to_script.models.schema import Beat, ActOutline, Outline, Scene, ScenePlan, ScreenplayDocument, Script, ScriptAct, SourceRef
from ai_fiction_to_script.pipeline.engine import AdaptationEngine, AdaptationResult, synchronize_outline_with_script
from ai_fiction_to_script.services.ai_client import HybridAIClient, MockAIClient, QwenAIClient, _normalize_scene_refs
from ai_fiction_to_script.services.cache_store import CacheStore, NullCacheStore
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.presets import SCRIPT_TYPE_PRESETS, TONE_PRESETS, build_adaptation_goal, build_style_guide_for_tone
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore
from ai_fiction_to_script.services.yaml_service import dump_public_yaml, dump_yaml
from ai_fiction_to_script.settings import QwenSettings, WebCacheSettings


@dataclass(slots=True)
class AsyncTaskRecord:
    task_id: str
    kind: str
    project_id: str
    preview_version_id: str
    preview_document: ScreenplayDocument | None = None
    preview_chapters: list[ParsedChapter] | None = None
    preview_analyses: list[ChapterAnalysis] | None = None
    request: AdaptationRequest | None = None
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
        payload = []
        for project in self.version_store.list_projects():
            project_payload = project.model_dump(mode="json")
            project_payload["versions"] = [
                self._version_record_with_generation_summary(project.project_id, version_payload)
                for version_payload in project_payload.get("versions", [])
            ]
            payload.append(project_payload)
        self.cache_store.set_json(key, payload, self.cache_settings.ttl_seconds)
        return payload

    def _version_record_with_generation_summary(self, project_id: str, version_payload: dict) -> dict:
        version_id = str(version_payload.get("version_id") or "")
        if not version_id:
            return version_payload
        try:
            document = self.version_store.load_document(project_id, version_id)
        except Exception:
            return version_payload
        settings = document.extensions.get("generation_settings", {}) if isinstance(document.extensions, dict) else {}
        request_payload = self._safe_load_request_payload(project_id, version_id)
        script_type = str(settings.get("script_type") or request_payload.get("target_format") or document.meta.target_format or "")
        tone = str(settings.get("tone") or request_payload.get("tone") or document.meta.tone or "")
        detail_level = str(settings.get("detail_level") or request_payload.get("detail_level") or "")
        version_payload["generation_summary"] = {
            "script_type": script_type,
            "script_type_label": SCRIPT_TYPE_PRESETS.get(script_type, {}).get("label_zh", script_type or "未设置"),
            "tone": tone,
            "tone_label": TONE_PRESETS.get(tone, {}).get("label_zh", tone or "未设置"),
            "detail_level": detail_level,
            "detail_label": {"fast": "快速", "standard": "标准", "detailed": "详写"}.get(detail_level, detail_level or "未设置"),
        }
        return version_payload

    def _safe_load_request_payload(self, project_id: str, version_id: str) -> dict:
        try:
            payload = self.version_store.load_intermediate(project_id, version_id, "request")
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

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
        preview_result = self._build_preview_adaptation(input_path, preview_request)
        preview_payload = self._build_preview_payload(request.project_id, preview_result.document)
        task = self._create_task(
            kind="adapt",
            project_id=request.project_id,
            preview_version_id=preview_payload["version"]["version_id"],
        )
        self._update_task(
            task.task_id,
            preview_document=preview_result.document,
            preview_chapters=preview_result.chapters,
            preview_analyses=preview_result.analyses,
            request=request,
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
                payload.get("api_key", ""),
                payload.get("note", ""),
            ),
            daemon=True,
        )
        thread.start()
        return {
            "preview": preview_payload,
            "task": self._serialize_task(task),
        }

    def start_regenerate_from_yaml_async(self, payload: dict) -> dict:
        yaml_text = self._read_yaml_bundle_text(payload)
        bundle_payload = self._build_payload_from_yaml_bundle(yaml_text, payload)
        return self.start_adapt_async(bundle_payload)

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
        model_name: str = "",
        tone_override: str = "",
        detail_level: str = "",
        note: str = "",
    ) -> dict:
        document = self.version_store.load_document(project_id, version_id)
        request = self._load_request(project_id, version_id, document)
        if provider_override:
            request = request.model_copy(update={"provider": provider_override})
        if model_name:
            request = request.model_copy(update={"model_name": model_name})
        request = self._apply_detail_level_to_request(request, detail_level)
        if tone_override:
            request = request.model_copy(
                update={
                    "tone": tone_override,
                    "style_guide": build_style_guide_for_tone(tone_override),
                }
            )
        if request.provider == "qwen":
            request = request.model_copy(update={"model_routing": self._web_model_routing(request.provider, request.model_name)})

        chapters = self._load_chapters(project_id, version_id)
        outline = document.outline
        scene_plan = self._find_scene_plan(outline.scene_plans, scene_id)
        previous_scene = self._find_scene(document.script, scene_id)
        scene_plan = self._apply_scene_instruction(scene_plan, instruction)
        chapter = self._resolve_scene_source(scene_plan, chapters)
        ai_client = self._build_ai_client(request.provider, api_key)
        scene, length_warning = self._generate_scene_with_length_warning(
            ai_client,
            scene_plan,
            document.story_bible,
            chapter,
            request,
        )
        scene = _normalize_scene_refs(scene, document.story_bible)
        updated_script = self._replace_scene(document.script, scene_plan.act_id, scene_id, scene)
        updated_outline = synchronize_outline_with_script(document.outline, updated_script)
        updated_document = self._document_with_generation_settings(
            document,
            request,
            outline=updated_outline,
            script=updated_script,
        )
        quality = self.quality_checker.review(updated_document)
        ai_warnings, ai_suggestions = ai_client.review_document(updated_document, request)
        quality.warnings = self._merge_unique(quality.warnings, [self._generation_settings_warning(request)])
        quality.warnings = self._merge_unique(quality.warnings, [length_warning])
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
        model_name: str = "",
        tone_override: str = "",
        detail_level: str = "",
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
                model_name,
                tone_override,
                detail_level,
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
        chapters = self._load_chapters(project_id, version_id)
        return dump_public_yaml(document, chapters)

    def list_qwen_models(self, api_key: str = "", base_url: str = "") -> list[dict[str, str]]:
        settings = QwenSettings.from_env(api_key_override=api_key or None)
        if base_url:
            settings = QwenSettings(
                api_key=settings.api_key,
                base_url=base_url,
                timeout_seconds=settings.timeout_seconds,
            )
        if not settings.api_key:
            raise ValueError("Qwen API key is required to list models.")
        return QwenAIClient(settings).list_models()

    def _build_preview_adaptation(self, input_path: str | Path, request: AdaptationRequest) -> AdaptationResult:
        engine = AdaptationEngine(
            parser=ChapterParser(),
            ai_client=MockAIClient(),
            quality_checker=self.quality_checker,
            version_store=None,
        )
        return engine.run(input_path=input_path, request=request, note="preview")

    def _build_preview_payload(self, project_id: str, document: ScreenplayDocument) -> dict:
        return {
            "project_id": project_id,
            "version": {"version_id": "preview"},
            "document": document.model_dump(mode="json"),
            "yaml_text": dump_yaml(document),
            "rendered_script": self._render_screenplay(document),
            "scene_options": self._scene_options(document),
        }

    def _build_ai_client(self, provider: str, api_key: str = ""):
        if provider == "mock":
            return MockAIClient()
        if provider == "qwen":
            qwen_client = QwenAIClient(QwenSettings.from_env(api_key_override=api_key or None))
            planner_client = MockAIClient()
            return HybridAIClient(planner_client=planner_client, generator_client=qwen_client, reviewer_client=qwen_client)
        raise ValueError(f"Unsupported provider: {provider}")

    def _build_request_from_payload(self, payload: dict) -> AdaptationRequest:
        title = payload.get("title") or "未命名剧本"
        tone = payload.get("tone") or "balanced"
        target_format = payload.get("script_type") or "tv_drama"
        provider = payload.get("provider") or "qwen"
        model_name = str(payload.get("model_name") or "").strip()
        speed_mode = self._resolve_speed_mode(provider, payload)
        detail_level = self._resolve_detail_level(payload, speed_mode)
        detail_config = self._detail_config(detail_level)
        model_routing = self._web_model_routing(provider, model_name)
        genre = self._normalize_genre(payload.get("genre"))
        if not genre:
            genre = self._infer_genre_from_payload(payload)
        return AdaptationRequest(
            project_id=self._slugify(title),
            title=title,
            original_novel_title=payload.get("original_title") or title,
            original_author=payload.get("original_author") or "未知作者",
            target_format=target_format,
            genre=genre,
            tone=tone,
            adaptation_goal=build_adaptation_goal(target_format),
            style_guide=build_style_guide_for_tone(tone),
            provider=provider,
            model_name=model_name,
            model_routing=model_routing,
            temperature=0.2 if detail_level == "fast" else 0.3,
            max_scenes_per_chapter=detail_config["max_scenes_per_chapter"],
            detail_level=detail_level,
            max_beats_per_scene=detail_config["max_beats_per_scene"],
            chapter_context_chars=detail_config["chapter_context_chars"],
        )

    def _resolve_detail_level(self, payload: dict, speed_mode: str) -> str:
        raw = str(payload.get("detail_level") or payload.get("generation_detail") or "").strip().lower()
        aliases = {
            "quick": "fast",
            "speed": "fast",
            "fast": "fast",
            "standard": "standard",
            "normal": "standard",
            "balanced": "standard",
            "detail": "detailed",
            "detailed": "detailed",
            "rich": "detailed",
            "full": "detailed",
        }
        if raw in aliases:
            return aliases[raw]
        if speed_mode == "fast":
            return "fast"
        return "standard"

    def _detail_config(self, detail_level: str) -> dict[str, int]:
        if detail_level == "fast":
            return {"max_scenes_per_chapter": 1, "max_beats_per_scene": 6, "chapter_context_chars": 600}
        if detail_level == "detailed":
            return {"max_scenes_per_chapter": 1, "max_beats_per_scene": 12, "chapter_context_chars": 1600}
        return {"max_scenes_per_chapter": 1, "max_beats_per_scene": 10, "chapter_context_chars": 1200}

    def _apply_detail_level_to_request(self, request: AdaptationRequest, detail_level: str) -> AdaptationRequest:
        resolved_detail_level = self._resolve_detail_level({"detail_level": detail_level or request.detail_level}, "balanced")
        detail_config = self._detail_config(resolved_detail_level)
        return request.model_copy(
            update={
                "detail_level": resolved_detail_level,
                "temperature": 0.2 if resolved_detail_level == "fast" else 0.3,
                "max_scenes_per_chapter": detail_config["max_scenes_per_chapter"],
                "max_beats_per_scene": detail_config["max_beats_per_scene"],
                "chapter_context_chars": detail_config["chapter_context_chars"],
            }
        )

    def _web_model_routing(self, provider: str, model_name: str = "") -> ModelRouting:
        if provider != "qwen":
            return ModelRouting()
        selected_model = model_name or "qwen3.6-flash"
        return ModelRouting(
            summary_model=selected_model,
            planning_model=selected_model,
            generation_model=selected_model,
            validation_model=selected_model,
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
                model_name=document.meta.model_name or "",
                adaptation_goal=build_adaptation_goal(document.meta.target_format),
                style_guide=build_style_guide_for_tone(document.meta.tone),
            )

    def _load_chapters(self, project_id: str, version_id: str) -> list[ParsedChapter]:
        payload = self.version_store.load_intermediate(project_id, version_id, "chapters")
        return [ParsedChapter.model_validate(item) for item in payload]

    def _load_analyses(self, project_id: str, version_id: str) -> list[ChapterAnalysis]:
        try:
            payload = self.version_store.load_intermediate(project_id, version_id, "chapter_analyses")
        except FileNotFoundError:
            return []
        return [ChapterAnalysis.model_validate(item) for item in payload]

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

    def _build_generation_intermediates(
        self,
        request: AdaptationRequest,
        chapters: list[ParsedChapter],
        analyses: list[ChapterAnalysis],
        document: ScreenplayDocument,
    ) -> dict:
        return {
            "request": request.model_dump(mode="json"),
            "chapters": [chapter.model_dump(mode="json") for chapter in chapters],
            "chapter_analyses": [analysis.model_dump(mode="json") for analysis in analyses],
            "story_bible": document.story_bible.model_dump(mode="json"),
            "outline": document.outline.model_dump(mode="json"),
            "document_snapshot": document.model_dump(mode="json"),
        }

    def _document_with_generation_settings(self, document: ScreenplayDocument, request: AdaptationRequest, **updates) -> ScreenplayDocument:
        extension_updates = dict(document.extensions)
        extension_updates["generation_settings"] = {
            "script_type": request.target_format,
            "tone": request.tone,
            "detail_level": request.detail_level,
            "max_beats_per_scene": request.max_beats_per_scene,
            "chapter_context_chars": request.chapter_context_chars,
        }
        merged_updates = {
            "meta": document.meta.model_copy(
                update={
                    "target_format": request.target_format,
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
            "extensions": extension_updates,
            **updates,
        }
        return document.model_copy(update=merged_updates)

    def _read_yaml_bundle_text(self, payload: dict) -> str:
        yaml_text = str(payload.get("yaml_text") or "").strip()
        upload_base64 = str(payload.get("upload_base64") or "").strip()
        if yaml_text:
            return yaml_text
        if upload_base64:
            return base64.b64decode(upload_base64).decode("utf-8")
        raise ValueError("Provide yaml_text or upload_base64 for YAML regeneration.")

    def _build_payload_from_yaml_bundle(self, yaml_text: str, payload: dict) -> dict:
        raw_payload = yaml.safe_load(yaml_text)
        if not isinstance(raw_payload, dict):
            raise ValueError("YAML bundle must deserialize into an object.")

        meta = raw_payload.get("meta")
        if not isinstance(meta, dict):
            raise ValueError("YAML bundle must contain a meta section.")

        chapter_blocks = self._extract_yaml_bundle_chapter_blocks(raw_payload)

        if len(chapter_blocks) < 3:
            raise ValueError("YAML bundle must contain at least 3 source chapters or 3 screenplay scenes.")

        return {
            "title": payload.get("title") or meta.get("title") or "未命名剧本",
            "original_author": payload.get("original_author") or meta.get("original_author") or "未知作者",
            "original_title": payload.get("original_title") or meta.get("original_novel_title") or meta.get("title") or "未命名剧本",
            "script_type": payload.get("script_type") or meta.get("target_format") or "tv_drama",
            "genre": payload.get("genre") or meta.get("genre") or [],
            "tone": payload.get("tone") or meta.get("tone") or "balanced",
            "provider": payload.get("provider") or "qwen",
            "api_key": payload.get("api_key") or "",
            "model_name": payload.get("model_name") or meta.get("model_name") or meta.get("model") or "",
            "speed_mode": payload.get("speed_mode") or "balanced",
            "detail_level": payload.get("detail_level") or payload.get("generation_detail") or "",
            "novel_text": "\n\n".join(chapter_blocks),
            "note": payload.get("note") or "regenerated from yaml bundle",
        }

    def _extract_yaml_bundle_chapter_blocks(self, raw_payload: dict) -> list[str]:
        extensions = raw_payload.get("extensions")
        if isinstance(extensions, dict):
            regeneration_bundle = extensions.get("regeneration_bundle")
            if isinstance(regeneration_bundle, dict):
                chapter_blocks = self._chapter_blocks_from_yaml_chapters(regeneration_bundle.get("source_chapters"))
                if chapter_blocks:
                    return chapter_blocks

        source = raw_payload.get("source")
        if isinstance(source, dict):
            chapters = source.get("chapters")
            chapter_blocks = self._chapter_blocks_from_yaml_chapters(chapters)
            if chapter_blocks:
                return chapter_blocks

        appendix = raw_payload.get("appendix")
        if isinstance(appendix, dict):
            chapter_blocks = self._chapter_blocks_from_yaml_chapters(appendix.get("source_chapters"))
            if chapter_blocks:
                return chapter_blocks

        return self._chapter_blocks_from_screenplay_scenes(raw_payload.get("scenes"))

    def _chapter_blocks_from_yaml_chapters(self, chapters) -> list[str]:
        if not isinstance(chapters, list) or not chapters:
            return []
        chapter_blocks: list[str] = []
        for index, chapter in enumerate(chapters, start=1):
            if not isinstance(chapter, dict):
                continue
            title = str(chapter.get("title") or f"Chapter {index}").strip()
            text = str(chapter.get("text") or "").strip()
            if not text:
                summary = str(chapter.get("summary") or "").strip()
                if not summary:
                    raise ValueError("Every source chapter in the YAML bundle must include text or summary.")
                text = summary
            chapter_blocks.append(f"{title}\n\n{text}")
        return chapter_blocks

    def _chapter_blocks_from_screenplay_scenes(self, scenes) -> list[str]:
        if not isinstance(scenes, list) or not scenes:
            raise ValueError("YAML bundle must contain appendix.source_chapters, source.chapters, or scenes[].")

        chapter_blocks: list[str] = []
        for index, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                continue
            title = str(scene.get("title") or scene.get("scene_id") or f"Scene {index}").strip()
            setting = scene.get("setting") if isinstance(scene.get("setting"), dict) else {}
            summary = str(scene.get("summary") or "").strip()
            objective = str(scene.get("objective") or "").strip()
            location = str(setting.get("location") or "").strip()
            time_of_day = str(setting.get("time_of_day") or "").strip()
            lines = scene.get("lines")
            scene_lines: list[str] = []
            if isinstance(lines, list):
                for line in lines:
                    if not isinstance(line, dict):
                        continue
                    kind = str(line.get("kind") or "").strip()
                    speaker = str(line.get("speaker") or "").strip()
                    text = str(line.get("text") or "").strip()
                    if not text:
                        continue
                    if kind == "dialogue" and speaker:
                        scene_lines.append(f"{speaker}：{text}")
                    else:
                        scene_lines.append(text)
            chapter_text_parts = [item for item in [summary, objective, f"时间：{time_of_day}" if time_of_day else "", f"地点：{location}" if location else ""] if item]
            chapter_text_parts.extend(scene_lines)
            chapter_text = "\n".join(part for part in chapter_text_parts if part).strip()
            if not chapter_text:
                raise ValueError("Every screenplay scene in the YAML bundle must include summary, objective, or lines.")
            chapter_blocks.append(f"{title}\n\n{chapter_text}")
        return chapter_blocks

    def _scene_options(self, document: ScreenplayDocument) -> list[dict]:
        options: list[dict] = []
        for act in document.script.acts:
            for scene in act.scenes:
                options.append(
                    {
                        "scene_id": scene.scene_id,
                        "act_id": act.act_id,
                        "label": f"{scene.scene_id} · 章节剧本：{scene.title}",
                        "title": scene.title,
                    }
                )
        return options

    def _collapse_document_to_chapter_units(self, document: ScreenplayDocument) -> ScreenplayDocument:
        source_chapters = document.source.chapters
        if not source_chapters:
            return document

        scenes_by_chapter: dict[str, list[Scene]] = {chapter.chapter_id: [] for chapter in source_chapters}
        for scene in self._iter_script_scenes(document.script):
            chapter_id = scene.chapter_refs[0] if scene.chapter_refs else ""
            if chapter_id in scenes_by_chapter:
                scenes_by_chapter[chapter_id].append(scene)

        collapsed_scenes: list[Scene] = []
        collapsed_plans: list[ScenePlan] = []
        for index, source_chapter in enumerate(source_chapters, start=1):
            scene_id = f"s{index:03d}"
            chapter_scenes = scenes_by_chapter.get(source_chapter.chapter_id) or []
            collapsed_scene = self._collapse_chapter_scenes(scene_id, source_chapter.chapter_id, source_chapter.title, chapter_scenes)
            collapsed_scenes.append(collapsed_scene)
            collapsed_plans.append(
                ScenePlan(
                    scene_id=scene_id,
                    act_id="main",
                    title=collapsed_scene.title,
                    objective=collapsed_scene.objective,
                    chapter_refs=[source_chapter.chapter_id],
                    conflict=collapsed_scene.summary,
                    notes=collapsed_scene.summary or source_chapter.summary,
                    focus_event=collapsed_scene.beats[0].text if collapsed_scene.beats else source_chapter.summary,
                )
            )

        script = Script(acts=[ScriptAct(act_id="main", title="正文", scenes=collapsed_scenes)])
        outline = Outline(
            structure_type=document.outline.structure_type,
            acts=[
                ActOutline(
                    act_id="main",
                    name="正文",
                    purpose="按小说章节逐章输出剧本单元，每章只保留一个完整章节剧本。",
                    scene_count=len(collapsed_scenes),
                )
            ],
            scene_plans=collapsed_plans,
        )
        return document.model_copy(update={"outline": outline, "script": script})

    def _collapse_chapter_scenes(
        self,
        scene_id: str,
        chapter_id: str,
        chapter_title: str,
        scenes: list[Scene],
    ) -> Scene:
        if not scenes:
            return Scene(
                scene_id=scene_id,
                title=chapter_title,
                chapter_refs=[chapter_id],
                objective=chapter_title,
                summary="",
                beats=[Beat(beat_id="b001", type="action", text=chapter_title)],
                source_refs=[SourceRef(chapter_id=chapter_id, excerpt_id="p001")],
            )

        first_scene = scenes[0]
        summaries = self._merge_unique([], [scene.summary for scene in scenes if scene.summary])
        beats: list[Beat] = []
        seen_beat_texts: set[str] = set()
        for scene in scenes:
            for beat in scene.beats:
                text = beat.text.strip()
                if not text or text in seen_beat_texts:
                    continue
                seen_beat_texts.add(text)
                beats.append(
                    beat.model_copy(update={"beat_id": f"b{len(beats) + 1:03d}"})
                )
        if not beats:
            beats = [Beat(beat_id="b001", type="action", text=first_scene.objective)]

        source_refs: list[SourceRef] = []
        seen_refs: set[tuple[str, str]] = set()
        for scene in scenes:
            for source_ref in scene.source_refs:
                ref_key = (source_ref.chapter_id, source_ref.excerpt_id)
                if ref_key in seen_refs:
                    continue
                seen_refs.add(ref_key)
                source_refs.append(source_ref)
        if not source_refs:
            source_refs = [SourceRef(chapter_id=chapter_id, excerpt_id="p001")]

        return first_scene.model_copy(
            update={
                "scene_id": scene_id,
                "title": first_scene.title or chapter_title,
                "chapter_refs": [chapter_id],
                "objective": first_scene.objective or chapter_title,
                "summary": " / ".join(summaries),
                "beats": beats,
                "source_refs": source_refs,
            }
        )

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

    def _infer_genre_from_payload(self, payload: dict) -> list[str]:
        text = str(payload.get("novel_text") or "")
        if not text and payload.get("upload_base64"):
            try:
                raw = base64.b64decode(str(payload.get("upload_base64")), validate=False)
                text = raw.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
        return infer_genres_from_text(text)

    def _resolve_speed_mode(self, provider: str, payload: dict) -> str:
        raw_mode = str(payload.get("speed_mode") or "").strip().lower()
        if raw_mode in {"fast", "balanced"}:
            return raw_mode
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
        body = self._render_scene_body(document, scene)
        if body:
            lines.append(body)
        if scene.transitions and scene.transitions.next_scene_hint:
            lines.append(f"转场：{scene.transitions.next_scene_hint}")
        return "\n".join(lines).strip()

    def _render_scene_body(self, document: ScreenplayDocument, scene: Scene) -> str:
        paragraphs: list[str] = []
        for beat in scene.beats:
            rendered = self._render_beat(document, beat).strip()
            if not rendered:
                continue
            if beat.type == "dialogue":
                paragraphs.append(rendered)
            else:
                paragraphs.extend(line.strip() for line in rendered.splitlines() if line.strip())
        return "\n".join(paragraph for paragraph in paragraphs if paragraph).strip()

    def _render_streaming_scene(self, scene_plan: ScenePlan, streamed_text: str) -> str:
        lines = [
            f"[{scene_plan.scene_id}] {scene_plan.title}",
            "Qwen 正在生成当前章节剧本...",
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
            is_target_override = scene.scene_id == target_scene_id and bool(override_text)
            if scene.scene_id not in visible_scene_ids and not is_target_override:
                continue
            if is_target_override:
                lines.append(override_text)
            else:
                lines.append(self._render_scene(document, scene))
            lines.append("")
        return "\n".join(lines).strip()

    def _screenplay_header_lines(self, document: ScreenplayDocument) -> list[str]:
        script_type_label = SCRIPT_TYPE_PRESETS.get(document.meta.target_format, dict()).get("label_zh", document.meta.target_format)
        tone_label = TONE_PRESETS.get(document.meta.tone, dict()).get("label_zh", document.meta.tone)
        detail_level = str(document.extensions.get("generation_settings", {}).get("detail_level") or "")
        detail_label = {"fast": "快速", "standard": "标准", "detailed": "详写"}.get(detail_level, detail_level or "未设置")
        genre_label = ", ".join(document.meta.genre) if document.meta.genre else "未设置"
        lines: list[str] = [document.meta.title, "=" * len(document.meta.title), ""]
        lines.append(f"剧本类型：{script_type_label}")
        lines.append(f"题材：{genre_label}")
        lines.append(f"语气：{tone_label}")
        lines.append(f"详细度：{detail_label}")
        lines.append("")
        return lines

    def _iter_script_scenes(self, script: Script):
        for act in script.acts:
            for scene in act.scenes:
                yield scene

    def _render_beat(self, document: ScreenplayDocument, beat) -> str:
        text = self._clean_rendered_beat_text(beat.text)
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

    def _clean_rendered_beat_text(self, text: str) -> str:
        lines: list[str] = []
        for raw_line in str(text or "").splitlines():
            line = raw_line.strip()
            if re.match(r"^[Ee]\d{1,5}\s*[:：]\s*[\u4e00-\u9fffA-Za-z_][\w\u4e00-\u9fff·]{0,16}\s*$", line):
                continue
            line = re.sub(r"^[Ee]\d{1,5}\s*[:：]\s*", "", line).strip()
            if line:
                lines.append(line)
        return "\n".join(lines).strip()

    def _speaker_name(self, document: ScreenplayDocument, speaker_ref: str) -> str:
        for character in document.story_bible.characters:
            if character.character_id == speaker_ref:
                return character.name
        return speaker_ref

    def _resolve_model_name(self, request: AdaptationRequest) -> str:
        if request.provider == "mock":
            return "mock-qwen-planner"
        return request.model_name or request.model_routing.generation_model

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

    def _generate_scene_with_length_warning(
        self,
        ai_client,
        scene_plan: ScenePlan,
        story_bible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
        on_delta=None,
    ) -> tuple[Scene, str]:
        scene = self._generate_scene_with_optional_stream(
            ai_client,
            scene_plan,
            story_bible,
            chapter,
            request,
            on_delta=on_delta,
        )
        original_chars = self._scene_body_char_count(scene)
        if request.provider == "qwen":
            scene = self._apply_detail_length_floor(scene, chapter, request)
        if request.provider != "qwen":
            return scene, ""
        warning = self._length_budget_warning(scene_plan, chapter, request, scene, original_chars=original_chars)
        return scene, warning

    def _generate_scene_enforcing_length(
        self,
        ai_client,
        scene_plan: ScenePlan,
        story_bible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
        on_delta=None,
    ) -> Scene:
        scene, _warning = self._generate_scene_with_length_warning(
            ai_client,
            scene_plan,
            story_bible,
            chapter,
            request,
            on_delta=on_delta,
        )
        return scene

    def _length_budget_warning(
        self,
        scene_plan: ScenePlan,
        chapter: ParsedChapter,
        request: AdaptationRequest,
        scene: Scene,
        original_chars: int | None = None,
    ) -> str:
        if request.provider != "qwen":
            return ""
        min_chars, max_chars = self._target_scene_body_chars(chapter, request)
        actual_chars = self._scene_body_char_count(scene)
        if min_chars <= actual_chars <= max_chars:
            return ""
        return (
            f"{scene_plan.scene_id} 生成正文 {actual_chars} 字，未达到目标字数范围 {min_chars}-{max_chars} 字；"
            "已保留本次生成结果。"
        )

    def _generation_settings_warning(self, request: AdaptationRequest) -> str:
        return (
            "生成设置已应用："
            f"剧本类型={request.target_format}，"
            f"语气={request.tone}，"
            f"详细度={request.detail_level}，"
            f"模型={self._resolve_model_name(request)}。"
        )

    def _generate_scene_retrying_length(
        self,
        ai_client,
        scene_plan: ScenePlan,
        story_bible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
        on_delta=None,
        max_attempts: int = 1,
    ) -> tuple[Scene, str]:
        if max_attempts <= 1:
            return self._generate_scene_with_length_warning(
                ai_client,
                scene_plan,
                story_bible,
                chapter,
                request,
                on_delta=on_delta,
            )
        active_plan = scene_plan
        min_chars, max_chars = self._target_scene_body_chars(chapter, request)
        last_count = 0
        last_scene: Scene | None = None
        for attempt in range(1, max_attempts + 1):
            scene = self._generate_scene_with_optional_stream(
                ai_client,
                active_plan,
                story_bible,
                chapter,
                request,
                on_delta=on_delta if attempt == 1 else None,
            )
            last_scene = scene
            last_count = self._scene_body_char_count(scene)
            if min_chars <= last_count <= max_chars:
                return scene, ""
            if attempt < max_attempts:
                active_plan = self._apply_scene_instruction(
                    scene_plan,
                    self._length_retry_instruction(chapter, request, last_count),
                )
        if last_scene is None:
            raise RuntimeError("Scene generation did not return a scene.")
        return last_scene, (
            f"{scene_plan.scene_id} 生成正文 {last_count} 字，未达到目标字数范围 {min_chars}-{max_chars} 字；"
            "已保留本次生成结果。"
        )

    def _target_scene_body_chars(self, chapter: ParsedChapter, request: AdaptationRequest) -> tuple[int, int]:
        source_chars = self._compact_char_count(chapter.raw_text)
        if request.detail_level == "fast":
            return max(1, round(source_chars * 0.6)), max(1, round(source_chars * 0.8))
        if request.detail_level == "detailed":
            return max(1, round(source_chars * 1.5)), max(1, round(source_chars * 2.5))
        return max(1, round(source_chars * 0.8)), max(1, round(source_chars * 1.5))

    def _length_retry_instruction(self, chapter: ParsedChapter, request: AdaptationRequest, actual_chars: int) -> str:
        min_chars, max_chars = self._target_scene_body_chars(chapter, request)
        source_chars = self._compact_char_count(chapter.raw_text)
        direction = "明显偏短，必须扩写" if actual_chars < min_chars else "明显偏长，必须压缩"
        return (
            f"严格字数重写：来源章节约 {source_chars} 字，本次生成正文为 {actual_chars} 字，{direction}。"
            f"重写后 ACTION / 台词 / NARRATION 主体正文合计必须在 {min_chars}-{max_chars} 字之间；"
            "不要改变章节核心事件，不要拆成多个场景。"
        )

    def _scene_body_char_count(self, scene: Scene) -> int:
        return sum(self._compact_char_count(beat.text) for beat in scene.beats)

    def _compact_char_count(self, text: str) -> int:
        return len("".join(str(text or "").split()))

    def _apply_detail_length_floor(self, scene: Scene, chapter: ParsedChapter, request: AdaptationRequest) -> Scene:
        return scene

    def _generate_script_with_optional_stream(
        self,
        ai_client,
        outline: Outline,
        story_bible,
        chapters: list[ParsedChapter],
        request: AdaptationRequest,
        on_delta=None,
    ):
        if hasattr(ai_client, "generate_script_stream"):
            return ai_client.generate_script_stream(outline, story_bible, chapters, request, on_delta=on_delta)
        nested_generator = getattr(ai_client, "_generator_client", None)
        if nested_generator is not None and hasattr(nested_generator, "generate_script_stream"):
            return nested_generator.generate_script_stream(outline, story_bible, chapters, request, on_delta=on_delta)
        if hasattr(ai_client, "generate_script"):
            return ai_client.generate_script(outline, story_bible, chapters, request)
        if nested_generator is not None and hasattr(nested_generator, "generate_script"):
            return nested_generator.generate_script(outline, story_bible, chapters, request)
        raise AttributeError("AI client does not support full-script generation.")

    def _should_use_full_script_fast_path(self, request: AdaptationRequest, ai_client) -> bool:
        # Strict per-chapter length budgets require validating each chapter unit independently.
        return False
        if request.provider != "qwen":
            return False
        if request.detail_level != "fast":
            return False
        if request.max_scenes_per_chapter != 1:
            return False
        return hasattr(ai_client, "generate_script_stream") or hasattr(getattr(ai_client, "_generator_client", None), "generate_script_stream")

    def _chapter_generation_workers(self, request: AdaptationRequest, total_scenes: int) -> int:
        if request.provider != "qwen":
            return min(6, max(1, total_scenes))
        if request.detail_level == "detailed":
            return min(2, max(1, total_scenes))
        return min(3, max(1, total_scenes))

    def _run_adaptation_progressive_full_script(
        self,
        task_id: str,
        ai_client,
        note: str,
        preview_document: ScreenplayDocument,
        chapters: list[ParsedChapter],
        analyses: list[ChapterAnalysis],
        request: AdaptationRequest,
    ) -> dict:
        total_scenes = max(1, len(preview_document.outline.scene_plans))

        def on_script_delta(accumulated_text: str, _delta_text: str) -> None:
            rendered_script = "\n".join(
                self._screenplay_header_lines(preview_document)
                + ["Qwen 正在生成整篇剧本...", "", accumulated_text.rstrip()]
            ).strip()
            self._update_task(
                task_id,
                result=self._task_snapshot_payload(
                    project_id=request.project_id,
                    version_id="preview",
                    rendered_script=rendered_script,
                    completed_scenes=0,
                    total_scenes=total_scenes,
                    mode="streaming",
                    stream_source="model_chunk",
                ),
            )

        generated_script = self._generate_script_with_optional_stream(
            ai_client,
            preview_document.outline,
            preview_document.story_bible,
            chapters,
            request,
            on_delta=on_script_delta,
        )
        updated_outline = synchronize_outline_with_script(preview_document.outline, generated_script)
        updated_document = self._document_with_generation_settings(
            preview_document,
            request,
            outline=updated_outline,
            script=generated_script,
        )
        updated_document = self._collapse_document_to_chapter_units(updated_document)
        self._update_task(
            task_id,
            result=self._task_snapshot_payload(
                project_id=request.project_id,
                version_id="preview",
                rendered_script=self._render_screenplay(updated_document),
                completed_scenes=total_scenes,
                total_scenes=total_scenes,
                mode="streaming",
                stream_source="scene_snapshot",
            ),
        )

        quality = self.quality_checker.review(updated_document)
        ai_warnings, ai_suggestions = ai_client.review_document(updated_document, request)
        quality.warnings = self._merge_unique(quality.warnings, [self._generation_settings_warning(request)])
        quality.warnings = self._merge_unique(quality.warnings, ai_warnings)
        quality.revision_suggestions = self._merge_unique(quality.revision_suggestions, ai_suggestions)
        updated_document = updated_document.model_copy(update={"quality": quality})

        saved = self.version_store.save(
            request.project_id,
            updated_document,
            intermediates=self._build_generation_intermediates(
                request=request,
                chapters=chapters,
                analyses=analyses,
                document=updated_document,
            ),
            note=note,
        )
        self._invalidate_project_cache(request.project_id)
        return self.get_version_payload(request.project_id, saved.version_id)

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
        ai_client,
        note: str,
        preview_document: ScreenplayDocument,
        chapters: list[ParsedChapter],
        analyses: list[ChapterAnalysis],
        request: AdaptationRequest,
    ) -> dict:
        outline = preview_document.outline
        current_script = preview_document.script
        total_scenes = max(1, len(outline.scene_plans))
        completed_scenes = 0
        visible_scene_ids: set[str] = set()

        if self._should_use_full_script_fast_path(request, ai_client):
            try:
                return self._run_adaptation_progressive_full_script(
                    task_id=task_id,
                    ai_client=ai_client,
                    note=note,
                    preview_document=preview_document,
                    chapters=chapters,
                    analyses=analyses,
                    request=request,
                )
            except Exception as exc:
                fallback_config = self._detail_config("standard")
                request = request.model_copy(
                    update={
                        "detail_level": "standard",
                        "max_beats_per_scene": fallback_config["max_beats_per_scene"],
                        "chapter_context_chars": fallback_config["chapter_context_chars"],
                    }
                )
                self._update_task(
                    task_id,
                    result=self._task_snapshot_payload(
                        project_id=request.project_id,
                        version_id="preview",
                        rendered_script="\n".join(
                            self._screenplay_header_lines(preview_document)
                            + [
                                "整篇快速生成超时，正在自动切换为逐章节并发生成...",
                                "",
                                str(exc),
                            ]
                        ).strip(),
                        completed_scenes=0,
                        total_scenes=total_scenes,
                        mode="streaming",
                        stream_source="fallback_notice",
                    ),
                )

        generation_warnings: list[str] = []
        scene_plan_lookup = {scene_plan.scene_id: scene_plan for scene_plan in outline.scene_plans}
        progress_lock = threading.Lock()
        stream_probe_lock = threading.Lock()
        stream_probe_claimed = False

        def push_progress_notice(scene_plan: ScenePlan, text: str, stream_source: str = "scene_progress") -> None:
            with progress_lock:
                snapshot_script = current_script
                snapshot_visible_scene_ids = set(visible_scene_ids)
                snapshot_completed_scenes = completed_scenes
            partial_document = preview_document.model_copy(update={"script": snapshot_script})
            self._update_task(
                task_id,
                result=self._task_snapshot_payload(
                    project_id=request.project_id,
                    version_id="preview",
                    rendered_script=self._render_screenplay_progress(
                        partial_document,
                        snapshot_script,
                        snapshot_visible_scene_ids,
                        target_scene_id=scene_plan.scene_id,
                        override_text=text,
                    ),
                    completed_scenes=snapshot_completed_scenes,
                    total_scenes=total_scenes,
                    mode="streaming",
                    stream_source=stream_source,
                    active_scene_id=scene_plan.scene_id,
                ),
            )

        def generate_scene_job(scene_plan: ScenePlan) -> tuple[str, Scene, str]:
            nonlocal stream_probe_claimed
            chapter = self._resolve_scene_source(scene_plan, chapters)
            initial_notice = self._render_streaming_scene(scene_plan, "正在连接模型并生成当前章节剧本...")
            push_progress_notice(scene_plan, initial_notice)
            with stream_probe_lock:
                should_stream_probe = not stream_probe_claimed
                stream_probe_claimed = True

            def on_scene_delta(accumulated_text: str, _delta_text: str) -> None:
                if not should_stream_probe:
                    return
                streaming_scene = self._render_streaming_scene(scene_plan, accumulated_text)
                push_progress_notice(scene_plan, streaming_scene, stream_source="model_chunk")

            try:
                scene, length_warning = self._generate_scene_with_length_warning(
                    ai_client,
                    scene_plan,
                    preview_document.story_bible,
                    chapter,
                    request,
                    on_delta=on_scene_delta if should_stream_probe else None,
                )
                return scene_plan.scene_id, _normalize_scene_refs(scene, preview_document.story_bible), length_warning
            except Exception as exc:
                fallback_scene = self._find_scene(preview_document.script, scene_plan.scene_id)
                warning = f"{scene_plan.scene_id} 章节剧本生成失败，已保留本地预览草稿：{exc}"
                return scene_plan.scene_id, fallback_scene, warning

        workers = self._chapter_generation_workers(request, total_scenes)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {executor.submit(generate_scene_job, scene_plan): scene_plan.scene_id for scene_plan in outline.scene_plans}
            for future in as_completed(future_map):
                scene_id, scene, warning = future.result()
                scene_plan = scene_plan_lookup[scene_id]
                with progress_lock:
                    current_script = self._replace_scene(current_script, scene_plan.act_id, scene_id, scene)
                    completed_scenes += 1
                    visible_scene_ids.add(scene_id)
                    snapshot_script = current_script
                    snapshot_visible_scene_ids = set(visible_scene_ids)
                    snapshot_completed_scenes = completed_scenes
                if warning:
                    generation_warnings.append(warning)
                partial_document = self._document_with_generation_settings(
                    preview_document,
                    request,
                    script=snapshot_script,
                )
                self._update_task(
                    task_id,
                    result=self._task_snapshot_payload(
                        project_id=request.project_id,
                        version_id="preview",
                        rendered_script=self._render_screenplay_progress(
                            partial_document,
                            snapshot_script,
                            snapshot_visible_scene_ids,
                        ),
                        completed_scenes=snapshot_completed_scenes,
                        total_scenes=total_scenes,
                        mode="streaming",
                        stream_source="scene_snapshot",
                        active_scene_id=scene_id,
                    ),
                )

        updated_document = self._document_with_generation_settings(
            preview_document,
            request,
            script=current_script,
        )
        updated_document = self._collapse_document_to_chapter_units(updated_document)
        quality = self.quality_checker.review(updated_document)
        ai_warnings, ai_suggestions = ai_client.review_document(updated_document, request)
        quality.warnings = self._merge_unique(quality.warnings, [self._generation_settings_warning(request)])
        quality.warnings = self._merge_unique(quality.warnings, generation_warnings)
        quality.warnings = self._merge_unique(quality.warnings, ai_warnings)
        quality.revision_suggestions = self._merge_unique(quality.revision_suggestions, ai_suggestions)
        updated_document = updated_document.model_copy(update={"quality": quality})

        saved = self.version_store.save(
            request.project_id,
            updated_document,
            intermediates=self._build_generation_intermediates(
                request=request,
                chapters=chapters,
                analyses=analyses,
                document=updated_document,
            ),
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
        api_key: str,
        note: str,
    ) -> None:
        try:
            with self._task_lock:
                task = self._tasks[task_id]
            if task.preview_document is None or task.preview_chapters is None or task.preview_analyses is None or task.request is None:
                raise RuntimeError("Async adaptation task is missing preview context.")
            payload = self._run_adaptation_progressive(
                task_id=task_id,
                ai_client=self._build_ai_client(task.request.provider, api_key),
                note=note or "qwen final draft",
                preview_document=task.preview_document,
                chapters=task.preview_chapters,
                analyses=task.preview_analyses,
                request=task.request,
            )
            self._update_task(
                task_id,
                status="completed",
                final_version_id=payload["version"]["version_id"],
                result=payload,
            )
        except Exception as exc:
            self._fail_task(task_id, exc)

    def _finish_regenerate_scene_async(
        self,
        task_id: str,
        project_id: str,
        version_id: str,
        preview_version_id: str,
        scene_id: str,
        provider_override: str,
        api_key: str,
        model_name: str,
        tone_override: str,
        detail_level: str,
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
                model_name=model_name,
                tone_override=tone_override,
                detail_level=detail_level,
                note=note or f"qwen final regenerate {scene_id}",
            )
            self._update_task(
                task_id,
                status="completed",
                final_version_id=payload["version"]["version_id"],
                result=payload,
            )
        except Exception as exc:
            self._fail_task(task_id, exc)

    def _fail_task(self, task_id: str, exc: Exception) -> None:
        trace = traceback.format_exc()
        self._write_task_error_log(task_id, trace)
        self._update_task(task_id, status="failed", error=str(exc) or exc.__class__.__name__)

    def _write_task_error_log(self, task_id: str, trace: str) -> None:
        try:
            log_path = self.version_store.root.parent / "runtime" / "task_errors.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"[{datetime.now(timezone.utc).isoformat()}] task={task_id}\n{trace}\n")
        except OSError:
            return

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
        model_name: str,
        tone_override: str,
        detail_level: str,
        note: str,
    ) -> dict:
        document = self.version_store.load_document(project_id, version_id)
        request = self._load_request(project_id, version_id, document)
        if provider_override:
            request = request.model_copy(update={"provider": provider_override})
        if model_name:
            request = request.model_copy(update={"model_name": model_name})
        request = self._apply_detail_level_to_request(request, detail_level)
        if tone_override:
            request = request.model_copy(
                update={
                    "tone": tone_override,
                    "style_guide": build_style_guide_for_tone(tone_override),
                }
            )
        if request.provider == "qwen":
            request = request.model_copy(update={"model_routing": self._web_model_routing(request.provider, request.model_name)})

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

        scene, length_warning = self._generate_scene_with_length_warning(
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
        updated_document = self._document_with_generation_settings(
            document,
            request,
            outline=updated_outline,
            script=updated_script,
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
        quality.warnings = self._merge_unique(quality.warnings, [self._generation_settings_warning(request)])
        quality.warnings = self._merge_unique(quality.warnings, [length_warning])
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


GENRE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("悬疑", ("悬疑", "谜", "线索", "真相", "调查", "侦探", "案件", "失踪", "秘密", "嫌疑")),
    ("惊悚", ("惊悚", "恐惧", "尖叫", "血", "尸", "鬼", "诅咒", "噩梦", "恐怖")),
    ("科幻", ("科幻", "星舰", "宇宙", "机器人", "人工智能", "时间线", "穿越", "实验舱", "量子", "未来")),
    ("奇幻", ("奇幻", "魔法", "精灵", "龙", "神殿", "法阵", "巫师", "灵力", "异界")),
    ("玄幻", ("玄幻", "修炼", "灵气", "宗门", "丹田", "渡劫", "仙门", "剑气", "妖兽")),
    ("武侠", ("武侠", "江湖", "剑客", "门派", "掌门", "轻功", "侠", "刀光", "客栈")),
    ("言情", ("言情", "爱情", "喜欢", "恋人", "婚约", "心动", "拥抱", "告白", "分手")),
    ("都市", ("都市", "公司", "办公室", "咖啡", "地铁", "小区", "老板", "项目", "合同")),
    ("历史", ("历史", "皇帝", "朝廷", "将军", "宫", "王爷", "边关", "战马", "臣")),
    ("校园", ("校园", "学校", "教室", "同桌", "老师", "考试", "社团", "操场")),
)


def infer_genres_from_text(text: str, limit: int = 2) -> list[str]:
    compact = text.strip()
    if not compact:
        return []
    scores: list[tuple[int, str]] = []
    for genre, keywords in GENRE_KEYWORDS:
        score = sum(compact.count(keyword) for keyword in keywords)
        if score:
            scores.append((score, genre))
    scores.sort(key=lambda item: (-item[0], item[1]))
    return [genre for _, genre in scores[:limit]]
