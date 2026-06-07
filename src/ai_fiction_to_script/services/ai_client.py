from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Callable

import httpx

from ai_fiction_to_script.models.runtime import AdaptationRequest, ChapterAnalysis, ParsedChapter
from ai_fiction_to_script.models.schema import (
    Beat,
    CharacterCard,
    CharacterRelation,
    LocationCard,
    Outline,
    QualityReport,
    ScreenplayDocument,
    Scene,
    ScenePlan,
    SceneTransition,
    Script,
    ScriptAct,
    SourceRef,
    StoryBible,
    TimelineEvent,
)
from ai_fiction_to_script.services.prompt_builder import PromptBuilder
from ai_fiction_to_script.settings import QwenSettings
from ai_fiction_to_script.utils.ids import make_id, next_available_id
from ai_fiction_to_script.utils.text import (
    extract_candidate_terms,
    extract_character_candidates,
    extract_location_candidates,
    parse_json_object,
    split_sentences,
    summarize_text,
)


class BaseAIClient(ABC):
    @abstractmethod
    def analyze_chapter(self, chapter: ParsedChapter, request: AdaptationRequest) -> ChapterAnalysis:
        raise NotImplementedError

    @abstractmethod
    def build_story_bible(
        self,
        analyses: list[ChapterAnalysis],
        request: AdaptationRequest,
    ) -> StoryBible:
        raise NotImplementedError

    @abstractmethod
    def plan_outline(
        self,
        analyses: list[ChapterAnalysis],
        story_bible: StoryBible,
        request: AdaptationRequest,
    ) -> Outline:
        raise NotImplementedError

    @abstractmethod
    def generate_scene(
        self,
        scene_plan: ScenePlan,
        story_bible: StoryBible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
    ) -> Scene:
        raise NotImplementedError

    @abstractmethod
    def review_document(
        self,
        document: ScreenplayDocument,
        request: AdaptationRequest,
    ) -> tuple[list[str], list[str]]:
        raise NotImplementedError


class MockAIClient(BaseAIClient):
    def analyze_chapter(self, chapter: ParsedChapter, request: AdaptationRequest) -> ChapterAnalysis:
        sentences = split_sentences(chapter.raw_text)
        summary = summarize_text(chapter.raw_text)
        key_events = sentences[:3] or [summary]
        conflicts = [item for item in sentences if any(token in item for token in ("但", "却", "然而", "冲突", "争执", "秘密"))]
        if not conflicts:
            conflicts = [key_events[min(1, len(key_events) - 1)]]
        emotions = [item for item in ("紧张", "压抑", "犹豫", "期待", "愤怒") if item in chapter.raw_text]
        if not emotions:
            emotions = ["克制"]
        props = [term for term in extract_candidate_terms(chapter.raw_text, limit=5) if term not in chapter.title][:3]
        return ChapterAnalysis(
            chapter_id=chapter.chapter_id,
            title=chapter.title,
            summary=summary,
            characters=extract_character_candidates(chapter.raw_text),
            key_events=key_events,
            conflicts=conflicts,
            emotions=emotions,
            locations=extract_location_candidates(chapter.raw_text),
            props=props,
        )

    def build_story_bible(
        self,
        analyses: list[ChapterAnalysis],
        request: AdaptationRequest,
    ) -> StoryBible:
        all_characters: list[str] = []
        all_locations: list[str] = []
        all_props: list[str] = []
        for analysis in analyses:
            for item in analysis.characters:
                if item not in all_characters:
                    all_characters.append(item)
            for item in analysis.locations:
                if item not in all_locations:
                    all_locations.append(item)
            for item in analysis.props:
                if item not in all_props:
                    all_props.append(item)

        character_cards: list[CharacterCard] = []
        existing_ids: list[str] = []
        for index, name in enumerate(all_characters[:6], start=1):
            character_id = next_available_id("c", existing_ids)
            existing_ids.append(character_id)
            relations: list[CharacterRelation] = []
            if index > 1 and character_cards:
                relations.append(CharacterRelation(target_character_id=character_cards[0].character_id, relation="关联角色"))
            character_cards.append(
                CharacterCard(
                    character_id=character_id,
                    name=name,
                    role="protagonist" if index == 1 else "supporting",
                    traits=["克制", "有目标"],
                    goal="推动主线发展",
                    conflict="在追求目标时遭遇阻力",
                    arc="从被动进入主动",
                    voice="简洁直接",
                    relations=relations,
                )
            )

        location_cards = [
            LocationCard(location_id=make_id("l", index), name=name, description="与关键事件相关的地点", mood="悬而未决")
            for index, name in enumerate(all_locations[:5], start=1)
        ]

        timeline = [
            TimelineEvent(
                event_id=make_id("e", index),
                time_order=index,
                summary=analysis.summary,
                chapter_refs=[analysis.chapter_id],
            )
            for index, analysis in enumerate(analyses, start=1)
        ]

        themes = []
        if any("秘密" in analysis.summary or "真相" in analysis.summary for analysis in analyses):
            themes.append("真相")
        if any("家庭" in analysis.summary or "亲人" in analysis.summary for analysis in analyses):
            themes.append("亲情")
        if not themes:
            themes = ["成长", "选择"]

        return StoryBible(
            logline=f"{request.title}围绕主要人物逐步揭开核心冲突并推动故事升级。",
            synopsis=" ".join(analysis.summary for analysis in analyses),
            theme=themes,
            characters=character_cards,
            locations=location_cards,
            timeline=timeline,
            props=all_props[:5],
        )

    def plan_outline(
        self,
        analyses: list[ChapterAnalysis],
        story_bible: StoryBible,
        request: AdaptationRequest,
    ) -> Outline:
        scene_plans = _build_continuous_scene_plans(analyses, request)
        acts = [
            {
                "act_id": "main",
                "name": "正文",
                "purpose": "按小说内容连续推进剧情，而不是套用机械三幕标签。",
                "scene_count": len(scene_plans),
            }
        ]
        return Outline.model_validate({"structure_type": request.structure_type, "acts": acts, "scene_plans": scene_plans})

    def generate_scene(
        self,
        scene_plan: ScenePlan,
        story_bible: StoryBible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
    ) -> Scene:
        sentences = split_sentences(chapter.raw_text)
        primary_character = story_bible.characters[0].character_id if story_bible.characters else None
        beats: list[Beat] = []
        beat_specs = _build_mock_beat_specs(scene_plan, chapter, primary_character)
        for index, (beat_type, text, speaker_ref) in enumerate(beat_specs, start=1):
            beats.append(
                Beat(
                    beat_id=make_id("b", index),
                    type=beat_type,
                    text=text,
                    speaker_ref=speaker_ref,
                    emotion=_infer_beat_emotion(text),
                )
            )

        location_ref = story_bible.locations[0].location_id if story_bible.locations else None
        source_refs = [SourceRef(chapter_id=chapter.chapter_id, excerpt_id=excerpt.excerpt_id) for excerpt in chapter.excerpts[:2]]
        if not source_refs:
            source_refs = [SourceRef(chapter_id=chapter.chapter_id, excerpt_id="p001")]
        time_of_day = "night" if any(token in chapter.raw_text for token in ("夜", "深夜", "晚上")) else "day"
        return Scene(
            scene_id=scene_plan.scene_id,
            title=scene_plan.title,
            chapter_refs=scene_plan.chapter_refs,
            location_ref=location_ref,
            time_of_day=time_of_day,
            objective=scene_plan.objective,
            summary=_build_scene_summary(scene_plan, chapter),
            beats=beats,
            transitions=SceneTransition(
                next_scene_hint=scene_plan.bridge_out or scene_plan.conflict or "切入下一场戏",
                transition_type="cut",
            ),
            source_refs=source_refs,
        )

    def generate_script(
        self,
        outline: Outline,
        story_bible: StoryBible,
        chapters: list[ParsedChapter],
        request: AdaptationRequest,
    ) -> Script:
        chapter_map = {chapter.chapter_id: chapter for chapter in chapters}
        scenes_by_act: dict[str, list[Scene]] = {}
        for scene_plan in outline.scene_plans:
            chapter = next((chapter_map[item] for item in scene_plan.chapter_refs if item in chapter_map), chapters[0])
            scenes_by_act.setdefault(scene_plan.act_id, []).append(
                self.generate_scene(scene_plan, story_bible, chapter, request)
            )
        return Script(
            acts=[
                ScriptAct(act_id=act.act_id, title=act.name, scenes=scenes_by_act.get(act.act_id, []))
                for act in outline.acts
            ]
        )

    def generate_script_stream(
        self,
        outline: Outline,
        story_bible: StoryBible,
        chapters: list[ParsedChapter],
        request: AdaptationRequest,
        on_delta: Callable[[str, str], None] | None = None,
    ) -> Script:
        if on_delta is not None:
            on_delta("正在生成整篇剧本预览...", "正在生成整篇剧本预览...")
        return self.generate_script(outline, story_bible, chapters, request)

    def review_document(
        self,
        document: ScreenplayDocument,
        request: AdaptationRequest,
    ) -> tuple[list[str], list[str]]:
        warnings = list(document.quality.warnings)
        revision_suggestions = list(document.quality.revision_suggestions)
        if not revision_suggestions:
            revision_suggestions.append("建议人工复核关键对白，使角色口吻更鲜明。")
        return warnings, revision_suggestions


class HybridAIClient(BaseAIClient):
    """Use local heuristics for planning and a remote model only for scene text."""

    def __init__(
        self,
        planner_client: BaseAIClient,
        generator_client: BaseAIClient,
        reviewer_client: BaseAIClient | None = None,
    ) -> None:
        self._planner_client = planner_client
        self._generator_client = generator_client
        self._reviewer_client = reviewer_client or planner_client

    def analyze_chapter(self, chapter: ParsedChapter, request: AdaptationRequest) -> ChapterAnalysis:
        return self._planner_client.analyze_chapter(chapter, request)

    def build_story_bible(
        self,
        analyses: list[ChapterAnalysis],
        request: AdaptationRequest,
    ) -> StoryBible:
        return self._planner_client.build_story_bible(analyses, request)

    def plan_outline(
        self,
        analyses: list[ChapterAnalysis],
        story_bible: StoryBible,
        request: AdaptationRequest,
    ) -> Outline:
        return self._planner_client.plan_outline(analyses, story_bible, request)

    def generate_scene(
        self,
        scene_plan: ScenePlan,
        story_bible: StoryBible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
    ) -> Scene:
        return self._generator_client.generate_scene(scene_plan, story_bible, chapter, request)

    def review_document(
        self,
        document: ScreenplayDocument,
        request: AdaptationRequest,
    ) -> tuple[list[str], list[str]]:
        return self._reviewer_client.review_document(document, request)

    def generate_script(
        self,
        outline: Outline,
        story_bible: StoryBible,
        chapters: list[ParsedChapter],
        request: AdaptationRequest,
    ) -> Script:
        generator = self._generator_client
        if hasattr(generator, "generate_script"):
            return generator.generate_script(outline, story_bible, chapters, request)
        raise AttributeError("Generator client does not support generate_script.")

    def generate_script_stream(
        self,
        outline: Outline,
        story_bible: StoryBible,
        chapters: list[ParsedChapter],
        request: AdaptationRequest,
        on_delta: Callable[[str, str], None] | None = None,
    ) -> Script:
        generator = self._generator_client
        if hasattr(generator, "generate_script_stream"):
            return generator.generate_script_stream(outline, story_bible, chapters, request, on_delta=on_delta)
        if hasattr(generator, "generate_script"):
            return generator.generate_script(outline, story_bible, chapters, request)
        raise AttributeError("Generator client does not support generate_script_stream.")


class QwenAIClient(BaseAIClient):
    def __init__(self, settings: QwenSettings) -> None:
        if not settings.api_key:
            raise ValueError("Qwen API key is missing. Set DASHSCOPE_API_KEY or QWEN_API_KEY.")
        self._settings = settings

    def _chat_json(self, model: str, system: str, user: str, temperature: float) -> dict[str, Any]:
        url = f"{self._settings.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=httpx.Timeout(self._settings.timeout_seconds, connect=15.0),
            )
        except httpx.ReadTimeout as exc:
            raise ValueError(
                f"DashScope request timed out after {self._settings.timeout_seconds} seconds for model `{model}`。"
                "当前已启用极速草稿模式；如果仍超时，通常说明当前模型响应过慢、网络不稳定，或账号所在地域与 Base URL 不匹配。"
            ) from exc
        except httpx.HTTPError as exc:
            raise ValueError(f"DashScope request failed for model `{model}`: {exc}") from exc
        if response.is_error:
            raise ValueError(self._format_dashscope_error(response, model, url))
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, list):
            text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        else:
            text = str(content)
        return parse_json_object(text)

    def _chat_json_stream(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float,
        on_delta: Callable[[str, str], None] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._settings.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }
        chunks: list[str] = []
        try:
            with httpx.stream(
                "POST",
                url,
                headers=headers,
                json=payload,
                timeout=httpx.Timeout(self._settings.timeout_seconds, connect=15.0),
            ) as response:
                if response.is_error:
                    raise ValueError(self._format_dashscope_error(response, model, url))
                for raw_line in response.iter_lines():
                    line = raw_line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        chunk_payload = json.loads(data)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"DashScope streaming chunk was not valid JSON for model `{model}`: {data[:200]}") from exc
                    choices = chunk_payload.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if isinstance(content, list):
                        text_delta = "".join(part.get("text", "") for part in content if isinstance(part, dict))
                    elif content is None:
                        text_delta = ""
                    else:
                        text_delta = str(content)
                    if not text_delta:
                        continue
                    chunks.append(text_delta)
                    if on_delta is not None:
                        on_delta("".join(chunks), text_delta)
        except httpx.ReadTimeout as exc:
            raise ValueError(
                f"DashScope request timed out after {self._settings.timeout_seconds} seconds for model `{model}`。"
                "当前已启用流式模式；如果仍然超时，通常说明当前模型响应过慢、网络不稳定，或账号所在地域与 Base URL 不匹配。"
            ) from exc
        except httpx.HTTPError as exc:
            raise ValueError(f"DashScope request failed for model `{model}`: {exc}") from exc
        return parse_json_object("".join(chunks))

    def _format_dashscope_error(self, response: httpx.Response, model: str, url: str) -> str:
        try:
            detail = response.text.strip()
        except httpx.ResponseNotRead:
            detail = response.read().decode("utf-8", errors="ignore").strip()
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            detail = str(
                payload.get("message")
                or payload.get("error")
                or payload.get("msg")
                or payload.get("detail")
                or detail
            ).strip()

        if not detail:
            detail = f"HTTP {response.status_code}"

        message = f"DashScope request failed ({response.status_code}) for model `{model}`: {detail}"
        if response.status_code == 400:
            message += (
                "。请重点检查模型名是否受支持、API Key 与 Base URL 是否是同一区域，以及当前账号是否支持该模型。"
            )
        return message

    def analyze_chapter(self, chapter: ParsedChapter, request: AdaptationRequest) -> ChapterAnalysis:
        system, user = PromptBuilder.chapter_analysis(chapter, request)
        payload = self._chat_json(request.model_routing.summary_model, system, user, request.temperature)
        return ChapterAnalysis(
            chapter_id=chapter.chapter_id,
            title=chapter.title,
            summary=payload.get("summary", summarize_text(chapter.raw_text)),
            characters=_ensure_str_list(payload.get("characters")),
            key_events=_ensure_str_list(payload.get("key_events")),
            conflicts=_ensure_str_list(payload.get("conflicts")),
            emotions=_ensure_str_list(payload.get("emotions")),
            locations=_ensure_str_list(payload.get("locations")),
            props=_ensure_str_list(payload.get("props")),
        )

    def build_story_bible(
        self,
        analyses: list[ChapterAnalysis],
        request: AdaptationRequest,
    ) -> StoryBible:
        system, user = PromptBuilder.story_bible(analyses, request)
        payload = self._chat_json(request.model_routing.planning_model, system, user, request.temperature)
        characters = []
        for index, raw_item in enumerate(_ensure_list(payload.get("characters")), start=1):
            item = _normalize_named_mapping(raw_item, fallback_key="name")
            characters.append(
                CharacterCard(
                    character_id=_normalize_text_field(item.get("character_id")) or make_id("c", index),
                    name=_normalize_text_field(item.get("name")) or f"角色{index}",
                    role=_normalize_text_field(item.get("role")) or "supporting",
                    traits=_ensure_str_list(item.get("traits")),
                    goal=_normalize_text_field(item.get("goal")),
                    conflict=_normalize_text_field(item.get("conflict")),
                    arc=_normalize_text_field(item.get("arc")),
                    voice=_normalize_text_field(item.get("voice")),
                    relations=[
                        CharacterRelation(
                            target_character_id=_normalize_text_field(relation.get("target_character_id")),
                            relation=_normalize_text_field(relation.get("relation")) or "关联",
                            notes=_normalize_text_field(relation.get("notes")),
                        )
                        for relation in _normalize_relation_list(item.get("relations"))
                        if _normalize_text_field(relation.get("target_character_id"))
                    ],
                )
            )
        locations = [
            LocationCard(
                location_id=_normalize_text_field(item.get("location_id")) or make_id("l", index),
                name=_normalize_text_field(item.get("name")) or f"地点{index}",
                description=_normalize_text_field(item.get("description")),
                mood=_normalize_text_field(item.get("mood")),
            )
            for index, item in enumerate(_normalize_named_mapping_list(payload.get("locations"), fallback_key="name"), start=1)
        ]
        timeline = [
            TimelineEvent(
                event_id=_normalize_text_field(item.get("event_id")) or make_id("e", index),
                time_order=_normalize_int(item.get("time_order"), index),
                summary=_normalize_text_field(item.get("summary")) or f"事件{index}",
                chapter_refs=_ensure_str_list(item.get("chapter_refs")),
            )
            for index, item in enumerate(_normalize_named_mapping_list(payload.get("timeline"), fallback_key="summary"), start=1)
        ]
        return StoryBible(
            logline=_normalize_text_field(payload.get("logline")),
            synopsis=_normalize_text_field(payload.get("synopsis")),
            theme=_ensure_str_list(payload.get("theme")),
            characters=characters,
            locations=locations,
            timeline=timeline,
            props=_ensure_str_list(payload.get("props")),
        )

    def plan_outline(
        self,
        analyses: list[ChapterAnalysis],
        story_bible: StoryBible,
        request: AdaptationRequest,
    ) -> Outline:
        system, user = PromptBuilder.outline(analyses, story_bible, request)
        payload = self._chat_json(request.model_routing.planning_model, system, user, request.temperature)
        normalized = {
            "structure_type": request.structure_type,
            "acts": [],
            "scene_plans": [],
        }
        for index, act in enumerate(_normalize_named_mapping_list(payload.get("acts"), fallback_key="name"), start=1):
            normalized["acts"].append(
                {
                    "act_id": _normalize_text_field(act.get("act_id")) or ("main" if index == 1 else make_id("a", index, width=1)),
                    "name": _normalize_text_field(act.get("name")) or ("正文" if index == 1 else f"第{index}幕"),
                    "purpose": _normalize_text_field(act.get("purpose")),
                    "scene_count": _normalize_int(act.get("scene_count"), 0),
                }
            )
        for index, scene in enumerate(_normalize_named_mapping_list(payload.get("scene_plans"), fallback_key="title"), start=1):
            fallback_act_id = normalized["acts"][min(index - 1, len(normalized["acts"]) - 1)]["act_id"] if normalized["acts"] else "main"
            normalized["scene_plans"].append(
                {
                    "scene_id": _normalize_text_field(scene.get("scene_id")) or make_id("s", index),
                    "act_id": _normalize_text_field(scene.get("act_id")) or fallback_act_id,
                    "title": _normalize_scene_title(_normalize_text_field(scene.get("title")), index),
                    "objective": _normalize_text_field(scene.get("objective")) or "推进核心冲突",
                    "chapter_refs": _ensure_str_list(scene.get("chapter_refs")),
                    "conflict": _normalize_text_field(scene.get("conflict")),
                    "notes": _normalize_text_field(scene.get("notes")),
                    "focus_event": _normalize_text_field(scene.get("focus_event")),
                    "bridge_in": _normalize_text_field(scene.get("bridge_in")),
                    "bridge_out": _normalize_text_field(scene.get("bridge_out")),
                }
            )
        return Outline.model_validate(normalized)

    def generate_scene(
        self,
        scene_plan: ScenePlan,
        story_bible: StoryBible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
    ) -> Scene:
        system, user = PromptBuilder.scene(scene_plan, story_bible, chapter, request)
        payload = self._chat_json(request.model_routing.generation_model, system, user, request.temperature)
        return _build_scene_from_payload(payload, scene_plan, chapter, story_bible)

    def generate_scene_stream(
        self,
        scene_plan: ScenePlan,
        story_bible: StoryBible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
        on_delta: Callable[[str, str], None] | None = None,
    ) -> Scene:
        system, user = PromptBuilder.scene(scene_plan, story_bible, chapter, request)
        payload = self._chat_json_stream(
            request.model_routing.generation_model,
            system,
            user,
            request.temperature,
            on_delta=on_delta,
        )
        return _build_scene_from_payload(payload, scene_plan, chapter, story_bible)

    def generate_script(
        self,
        outline: Outline,
        story_bible: StoryBible,
        chapters: list[ParsedChapter],
        request: AdaptationRequest,
    ) -> Script:
        system, user = PromptBuilder.full_script(outline, story_bible, chapters, request)
        payload = self._chat_json(request.model_routing.generation_model, system, user, request.temperature)
        return _build_script_from_payload(payload, outline, chapters, story_bible)

    def generate_script_stream(
        self,
        outline: Outline,
        story_bible: StoryBible,
        chapters: list[ParsedChapter],
        request: AdaptationRequest,
        on_delta: Callable[[str, str], None] | None = None,
    ) -> Script:
        system, user = PromptBuilder.full_script(outline, story_bible, chapters, request)
        payload = self._chat_json_stream(
            request.model_routing.generation_model,
            system,
            user,
            request.temperature,
            on_delta=on_delta,
        )
        return _build_script_from_payload(payload, outline, chapters, story_bible)

    def review_document(
        self,
        document: ScreenplayDocument,
        request: AdaptationRequest,
    ) -> tuple[list[str], list[str]]:
        warnings = list(document.quality.warnings)
        revision_suggestions = list(document.quality.revision_suggestions)
        system, user = PromptBuilder.quality(document)
        payload = self._chat_json(request.model_routing.validation_model, system, user, request.temperature)
        warnings.extend(_ensure_str_list(payload.get("warnings")))
        revision_suggestions.extend(_ensure_str_list(payload.get("revision_suggestions")))
        return _dedupe(warnings), _dedupe(revision_suggestions)


def _ensure_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _normalize_named_mapping(value: Any, fallback_key: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    return {fallback_key: str(value)}


def _normalize_named_mapping_list(value: Any, fallback_key: str) -> list[dict[str, Any]]:
    return [_normalize_named_mapping(item, fallback_key) for item in _ensure_list(value)]


def _normalize_relation_list(value: Any) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for item in _ensure_list(value):
        if isinstance(item, dict):
            relations.append(item)
        elif item is not None:
            relations.append({"target_character_id": str(item), "relation": "关联"})
    return relations


def _normalize_transition(value: Any) -> SceneTransition | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return SceneTransition(next_scene_hint=text, transition_type="cut")

    payload = _normalize_mapping(value)
    if not payload:
        return None

    next_scene_hint = _normalize_text_field(
        payload.get("next_scene_hint")
        or payload.get("entry")
        or payload.get("exit")
        or payload.get("transition")
        or payload.get("text")
    )
    transition_type = _normalize_text_field(payload.get("transition_type")) or "cut"
    return SceneTransition(next_scene_hint=next_scene_hint, transition_type=transition_type)


def _build_scene_from_payload(
    payload: dict[str, Any],
    scene_plan: ScenePlan,
    chapter: ParsedChapter,
    story_bible: StoryBible,
) -> Scene:
    beats = []
    for index, beat in enumerate(_normalize_named_mapping_list(payload.get("beats"), fallback_key="text"), start=1):
        beats.append(
            Beat(
                beat_id=_normalize_beat_id(beat.get("beat_id"), index),
                type=_normalize_beat_type(beat.get("type")),
                text=_normalize_text_field(beat.get("text")) or scene_plan.objective,
                speaker_ref=_normalize_optional_str(beat.get("speaker_ref")),
                emotion=_normalize_text_field(beat.get("emotion")),
            )
        )
    if not beats:
        beats.append(
            Beat(
                beat_id=make_id("b", 1),
                type="action",
                text=_normalize_text_field(payload.get("summary")) or scene_plan.objective,
            )
        )
    source_refs = [
        SourceRef(
            chapter_id=_normalize_text_field(item.get("chapter_id")) or chapter.chapter_id,
            excerpt_id=_normalize_text_field(item.get("excerpt_id")) or "p001",
        )
        for item in _normalize_named_mapping_list(payload.get("source_refs"), fallback_key="excerpt_id")
    ]
    if not source_refs:
        source_refs = [SourceRef(chapter_id=chapter.chapter_id, excerpt_id="p001")]
    scene = Scene(
        scene_id=scene_plan.scene_id,
        title=_normalize_text_field(payload.get("title")) or scene_plan.title,
        chapter_refs=scene_plan.chapter_refs,
        location_ref=_normalize_optional_str(payload.get("location_ref")),
        time_of_day=_normalize_text_field(payload.get("time_of_day")),
        objective=_normalize_text_field(payload.get("objective")) or scene_plan.objective,
        summary=_normalize_text_field(payload.get("summary")),
        beats=beats,
        transitions=_normalize_transition(payload.get("transitions")),
        source_refs=source_refs,
    )
    return _normalize_scene_refs(scene, story_bible)


def _build_script_from_payload(
    payload: dict[str, Any],
    outline: Outline,
    chapters: list[ParsedChapter],
    story_bible: StoryBible,
) -> Script:
    chapter_map = {chapter.chapter_id: chapter for chapter in chapters}
    scene_plan_lookup = {scene_plan.scene_id: scene_plan for scene_plan in outline.scene_plans}
    act_scene_buckets: dict[str, list[Scene]] = {act.act_id: [] for act in outline.acts}

    for index, scene_payload in enumerate(_normalize_named_mapping_list(payload.get("scenes"), fallback_key="title"), start=1):
        scene_id = _normalize_text_field(scene_payload.get("scene_id"))
        scene_plan = scene_plan_lookup.get(scene_id or "")
        if scene_plan is None:
            scene_plan = outline.scene_plans[min(index - 1, len(outline.scene_plans) - 1)]
        chapter = next((chapter_map[item] for item in scene_plan.chapter_refs if item in chapter_map), chapters[0])
        scene = _build_scene_from_payload(scene_payload, scene_plan, chapter, story_bible)
        act_scene_buckets.setdefault(scene_plan.act_id, []).append(scene)

    if not any(act_scene_buckets.values()):
        raise ValueError("Qwen did not return any scenes for the full-script generation path.")

    return Script(
        acts=[
            ScriptAct(act_id=act.act_id, title=act.name, scenes=act_scene_buckets.get(act.act_id, []))
            for act in outline.acts
        ]
    )


def _normalize_text_field(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_optional_str(value: Any) -> str | None:
    normalized = _normalize_text_field(value)
    return normalized or None


def _normalize_beat_id(value: Any, index: int) -> str:
    normalized = _normalize_text_field(value)
    return normalized or make_id("b", index)


def _normalize_beat_type(value: Any) -> str:
    normalized = _normalize_text_field(value).lower()
    if normalized in {"dialogue", "line", "speech", "conversation"}:
        return "dialogue"
    if normalized in {"transition", "cut", "fade", "wipe"}:
        return "transition"
    if normalized in {"narration", "voiceover", "voice_over", "vo", "setup", "intro", "exposition"}:
        return "narration"
    if normalized in {"action", "beat", "description", "scene", "movement"}:
        return "action"
    return "action"


def _normalize_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _compact_text(value: Any, limit: int = 32) -> str:
    text = _normalize_text_field(value)
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip("，。！？；：:,. ")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("，。！？；：:,. ") + "…"


def _build_segment_title(base_title: str, focus_event: str, segment_index: int) -> str:
    if segment_index == 0:
        return base_title
    event_label = _compact_text(focus_event, limit=10)
    if not event_label or event_label in base_title:
        return f"{base_title}（续）"
    return f"{base_title}·{event_label}"


def _plan_analysis_segments(analysis: ChapterAnalysis, max_scenes_per_chapter: int) -> list[dict[str, str]]:
    base_title = _normalize_scene_title(analysis.title, 1)
    candidate_events = _dedupe(
        [item for item in analysis.key_events if _normalize_text_field(item)]
        + [item for item in analysis.conflicts if _normalize_text_field(item)]
    )
    if not candidate_events:
        candidate_events = [analysis.summary or base_title]

    scene_count = min(max_scenes_per_chapter, 2 if len(candidate_events) >= 2 else 1)
    segments: list[dict[str, str]] = []
    for segment_index in range(scene_count):
        focus_event = candidate_events[min(segment_index, len(candidate_events) - 1)]
        conflict = analysis.conflicts[min(segment_index, len(analysis.conflicts) - 1)] if analysis.conflicts else focus_event
        segments.append(
            {
                "title": _build_segment_title(base_title, focus_event, segment_index),
                "objective": _compact_text(conflict or focus_event, limit=24) or "推进当前冲突",
                "focus_event": _compact_text(focus_event, limit=64),
                "conflict": _compact_text(conflict, limit=48),
                "notes": _compact_text(analysis.summary, limit=120),
            }
        )
    return segments


def _build_continuous_scene_plans(analyses: list[ChapterAnalysis], request: AdaptationRequest) -> list[ScenePlan]:
    scene_plans: list[ScenePlan] = []
    for chapter_index, analysis in enumerate(analyses):
        segments = _plan_analysis_segments(analysis, request.max_scenes_per_chapter)
        previous_summary = analyses[chapter_index - 1].summary if chapter_index > 0 else ""
        next_summary = analyses[chapter_index + 1].summary if chapter_index + 1 < len(analyses) else ""
        for segment_index, segment in enumerate(segments):
            prior_focus = segments[segment_index - 1]["focus_event"] if segment_index > 0 else _compact_text(previous_summary, limit=48)
            next_focus = (
                segments[segment_index + 1]["focus_event"]
                if segment_index + 1 < len(segments)
                else _compact_text(next_summary, limit=48)
            )
            scene_plans.append(
                ScenePlan(
                    scene_id=make_id("s", len(scene_plans) + 1),
                    act_id="main",
                    title=segment["title"],
                    objective=segment["objective"],
                    chapter_refs=[analysis.chapter_id],
                    conflict=segment["conflict"],
                    notes=segment["notes"],
                    focus_event=segment["focus_event"],
                    bridge_in=prior_focus,
                    bridge_out=next_focus,
                )
            )
    return scene_plans


def _build_mock_beat_specs(
    scene_plan: ScenePlan,
    chapter: ParsedChapter,
    primary_character: str | None,
) -> list[tuple[str, str, str | None]]:
    sentences = split_sentences(chapter.raw_text)
    beat_specs: list[tuple[str, str, str | None]] = []

    if scene_plan.bridge_in:
        beat_specs.append(("narration", scene_plan.bridge_in, None))
    if scene_plan.focus_event:
        beat_specs.append(("action", scene_plan.focus_event, None))
    if primary_character and scene_plan.objective:
        beat_specs.append(("dialogue", scene_plan.objective, primary_character))

    for sentence in sentences:
        beat_specs.append(("action", _compact_text(sentence, limit=72), None))

    normalized_specs: list[tuple[str, str, str | None]] = []
    seen_texts: set[str] = set()
    for beat_type, text, speaker_ref in beat_specs:
        cleaned = _compact_text(text, limit=96)
        if not cleaned or cleaned in seen_texts:
            continue
        seen_texts.add(cleaned)
        normalized_specs.append((beat_type, cleaned, speaker_ref))
        if len(normalized_specs) >= 4:
            break

    if not normalized_specs:
        fallback_text = _compact_text(chapter.raw_text[:96], limit=96) or "场景开始。"
        normalized_specs.append(("action", fallback_text, None))
    return normalized_specs


def _build_scene_summary(scene_plan: ScenePlan, chapter: ParsedChapter) -> str:
    summary_parts = [
        _compact_text(scene_plan.notes, limit=72),
        _compact_text(scene_plan.focus_event, limit=48),
    ]
    summary = " ".join(part for part in summary_parts if part).strip()
    return summary or summarize_text(chapter.raw_text)


def _infer_beat_emotion(text: str) -> str:
    if any(token in text for token in ("紧张", "追", "逼", "惊", "突", "危", "险")):
        return "紧张"
    if any(token in text for token in ("哭", "痛", "失", "伤", "泪")):
        return "伤感"
    if any(token in text for token in ("怒", "吼", "喝", "质问")):
        return "激烈"
    return ""


def _normalize_scene_title(value: Any, index: int) -> str:
    title = _normalize_text_field(value)
    if not title:
        return f"场景{index}"
    title = title.strip()
    title = re.sub(r"^第[一二三四五六七八九十百千0-9零两]+[章节幕回集卷篇]\s*[:：]?\s*", "", title)
    title = re.sub(r"^场(?:景)?\s*[一二三四五六七八九十百千0-9零两]+\s*[章节幕回集卷篇]\s*[:：]?\s*", "", title)
    title = re.sub(r"^A[1-9][0-9]*\s*(?:开端|发展|结局)?\s*[:：-]?\s*", "", title, flags=re.IGNORECASE)
    title = title.strip("：: ").strip()
    return title or f"场景{index}"


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item and item not in output:
            output.append(item)
    return output


def _normalize_lookup_key(value: Any) -> str:
    return str(value or "").strip().casefold()


def _build_entity_lookup(items: list[Any], id_attr: str, name_attr: str) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for item in items:
        entity_id = _normalize_text_field(getattr(item, id_attr, ""))
        entity_name = _normalize_text_field(getattr(item, name_attr, ""))
        for raw_key in (entity_id, entity_name):
            key = _normalize_lookup_key(raw_key)
            if key:
                lookup[key] = entity_id
    return lookup


def _character_aliases(character: CharacterCard) -> set[str]:
    name = _normalize_text_field(character.name)
    role = _normalize_text_field(character.role)
    aliases: set[str] = {name, role}

    male_aliases = {
        "来客",
        "客人",
        "男人",
        "男子",
        "黑衣人",
        "黑衣男人",
        "黑衣男子",
        "神秘人",
        "神秘来客",
    }
    female_aliases = {
        "女人",
        "女子",
        "女士",
        "夫人",
        "女孩",
        "少女",
        "守钟人之女",
    }
    elder_female_aliases = {
        "老妇人",
        "老夫人",
        "老太太",
        "老人",
        "女士",
    }

    if any(token in name for token in male_aliases):
        aliases.update(male_aliases)
    if any(token in name for token in female_aliases):
        aliases.update(female_aliases)
    if any(token in name for token in elder_female_aliases):
        aliases.update(elder_female_aliases)

    aliases.discard("")
    return aliases


def _build_character_lookup(story_bible: StoryBible) -> dict[str, str]:
    lookup = _build_entity_lookup(story_bible.characters, "character_id", "name")
    alias_map: dict[str, set[str]] = {}
    for character in story_bible.characters:
        for alias in _character_aliases(character):
            key = _normalize_lookup_key(alias)
            if key:
                alias_map.setdefault(key, set()).add(character.character_id)
    for key, ids in alias_map.items():
        if len(ids) == 1 and key not in lookup:
            lookup[key] = next(iter(ids))
    return lookup


def _resolve_lookup_ref(value: str | None, lookup: dict[str, str]) -> str | None:
    key = _normalize_lookup_key(value)
    if not key:
        return None
    return lookup.get(key)


def _resolve_unique_partial_ref(value: str | None, items: list[Any], id_attr: str, name_attr: str) -> str | None:
    key = _normalize_lookup_key(value)
    if not key:
        return None
    matches: list[str] = []
    for item in items:
        entity_id = _normalize_text_field(getattr(item, id_attr, ""))
        entity_name = _normalize_text_field(getattr(item, name_attr, ""))
        name_key = _normalize_lookup_key(entity_name)
        if name_key and (key in name_key or name_key in key):
            matches.append(entity_id)
    unique = list(dict.fromkeys(matches))
    if len(unique) == 1:
        return unique[0]
    return None


def _infer_speaker_ref_from_text(text: str, story_bible: StoryBible) -> str | None:
    content = _normalize_text_field(text)
    if not content:
        return None
    sorted_characters = sorted(story_bible.characters, key=lambda item: len(item.name), reverse=True)
    for character in sorted_characters:
        name = _normalize_text_field(character.name)
        if not name:
            continue
        if any(content.startswith(f"{name}{marker}") for marker in ("：", ":", "说", "问", "喊", "答", "道")):
            return character.character_id
    return None


def _strip_audio_markup(text: str) -> tuple[str, str, str]:
    content = _normalize_text_field(text)
    match = re.match(r"^\[(?P<tag>[A-Za-z]+|旁白)(?:[\/|／｜](?P<speaker>[^\]]+))?\]\s*(?P<text>.+)$", content)
    if not match:
        return "", "", content
    tag = match.group("tag").strip().upper() if match.group("tag") != "旁白" else "旁白"
    speaker = _normalize_text_field(match.group("speaker"))
    cleaned_text = _normalize_text_field(match.group("text"))
    return tag, speaker, cleaned_text


def _speaker_name_from_ref(story_bible: StoryBible, speaker_ref: str | None) -> str:
    if not speaker_ref:
        return ""
    for character in story_bible.characters:
        if character.character_id == speaker_ref:
            return _normalize_text_field(character.name)
    return _normalize_text_field(speaker_ref)


def _looks_like_narrative_dialogue_text(text: str, speaker_name: str) -> bool:
    content = _normalize_text_field(text)
    if not content:
        return True
    if speaker_name:
        dialogue_prefixes = (
            f"{speaker_name}：",
            f"{speaker_name}:",
            f"{speaker_name}说",
            f"{speaker_name}问",
            f"{speaker_name}喊",
            f"{speaker_name}答",
            f"{speaker_name}道",
        )
        if any(content.startswith(prefix) for prefix in dialogue_prefixes):
            return False
        if content.startswith(speaker_name):
            narrative_prefixes = (
                "没有",
                "未",
                "只是",
                "看",
                "盯",
                "望",
                "转",
                "抬",
                "低",
                "走",
                "站",
                "坐",
                "拿",
                "放",
                "沉默",
                "点头",
                "摇头",
                "皱",
            )
            suffix = content[len(speaker_name) :]
            if any(suffix.startswith(prefix) for prefix in narrative_prefixes):
                return True
    narrative_markers = ("镜头", "画面", "特写", "动作", "转身", "走入", "放在", "抬眼", "盯着", "看着", "没有回答")
    return any(marker in content for marker in narrative_markers)


def _resolve_speaker_ref_from_name(speaker_name: str, story_bible: StoryBible) -> str | None:
    if not speaker_name:
        return None
    character_lookup = _build_character_lookup(story_bible)
    resolved = _resolve_lookup_ref(speaker_name, character_lookup)
    if resolved is not None:
        return resolved
    return _resolve_unique_partial_ref(speaker_name, story_bible.characters, "character_id", "name")


def _normalize_scene_refs(scene: Scene, story_bible: StoryBible) -> Scene:
    character_lookup = _build_character_lookup(story_bible)
    location_lookup = _build_entity_lookup(story_bible.locations, "location_id", "name")

    normalized_beats: list[Beat] = []
    beats_changed = False
    for beat in scene.beats:
        audio_tag, audio_speaker, cleaned_text = _strip_audio_markup(beat.text)
        resolved_speaker_ref = _resolve_lookup_ref(beat.speaker_ref, character_lookup)
        if resolved_speaker_ref is None:
            resolved_speaker_ref = _resolve_unique_partial_ref(
                beat.speaker_ref,
                story_bible.characters,
                "character_id",
                "name",
            )
        if resolved_speaker_ref is None and audio_speaker:
            resolved_speaker_ref = _resolve_speaker_ref_from_name(audio_speaker, story_bible)
        if resolved_speaker_ref is None and beat.type == "dialogue":
            resolved_speaker_ref = _infer_speaker_ref_from_text(cleaned_text, story_bible)
        beat_updates: dict[str, Any] = {}
        speaker_name = _speaker_name_from_ref(story_bible, resolved_speaker_ref or beat.speaker_ref)
        normalized_type = beat.type
        if audio_tag in {"SFX", "BGM", "FX"}:
            normalized_type = "action"
            resolved_speaker_ref = None
        elif audio_tag in {"VO", "OS", "旁白"} and normalized_type == "dialogue" and not resolved_speaker_ref and audio_speaker:
            resolved_speaker_ref = _resolve_speaker_ref_from_name(audio_speaker, story_bible)
            if resolved_speaker_ref is None:
                cleaned_text = f"{audio_speaker}：{cleaned_text}"

        if cleaned_text != beat.text:
            beat_updates["text"] = cleaned_text
        if normalized_type != beat.type:
            beat_updates["type"] = normalized_type
        if normalized_type == "dialogue" and _looks_like_narrative_dialogue_text(cleaned_text, speaker_name):
            beat_updates["type"] = "action"
            beat_updates["speaker_ref"] = None
        elif resolved_speaker_ref != beat.speaker_ref:
            beat_updates["speaker_ref"] = resolved_speaker_ref
        if beat_updates:
            normalized_beats.append(beat.model_copy(update=beat_updates))
            beats_changed = True
        else:
            normalized_beats.append(beat)

    resolved_location_ref = _resolve_lookup_ref(scene.location_ref, location_lookup)
    if resolved_location_ref is None:
        resolved_location_ref = _resolve_unique_partial_ref(
            scene.location_ref,
            story_bible.locations,
            "location_id",
            "name",
        )

    update_payload: dict[str, Any] = {}
    if beats_changed:
        update_payload["beats"] = normalized_beats
    if resolved_location_ref != scene.location_ref:
        update_payload["location_ref"] = resolved_location_ref

    if not update_payload:
        return scene
    return scene.model_copy(update=update_payload)
