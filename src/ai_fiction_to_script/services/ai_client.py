from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

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
        act_templates = [
            ("a1", "开端", "建立人物关系与触发事件"),
            ("a2", "发展", "升级冲突并推进调查"),
            ("a3", "结局", "收束核心矛盾并给出阶段答案"),
        ]
        total_scenes = len(analyses)
        act_scene_buckets: dict[str, list[ScenePlan]] = defaultdict(list)
        scene_plans: list[ScenePlan] = []

        for index, analysis in enumerate(analyses, start=1):
            if total_scenes == 1:
                act_id = "a1"
            elif index == 1:
                act_id = "a1"
            elif index == total_scenes:
                act_id = "a3"
            else:
                act_id = "a2"
            scene_plan = ScenePlan(
                scene_id=make_id("s", index),
                act_id=act_id,
                title=analysis.title.replace("第", "场 "),
                objective=analysis.conflicts[0] if analysis.conflicts else "推进核心冲突",
                chapter_refs=[analysis.chapter_id],
                conflict=analysis.conflicts[0] if analysis.conflicts else "",
                notes=analysis.summary,
            )
            scene_plans.append(scene_plan)
            act_scene_buckets[act_id].append(scene_plan)

        acts = []
        for act_id, name, purpose in act_templates:
            acts.append(
                {
                    "act_id": act_id,
                    "name": name,
                    "purpose": purpose,
                    "scene_count": len(act_scene_buckets[act_id]),
                }
            )
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
        beat_texts = sentences[:3] or [chapter.raw_text[:80]]
        for index, text in enumerate(beat_texts, start=1):
            beat_type = "action"
            speaker_ref = None
            if index == 2 and primary_character:
                beat_type = "dialogue"
                speaker_ref = primary_character
                text = f"{story_bible.characters[0].name}说：{scene_plan.objective}"
            beats.append(
                Beat(
                    beat_id=make_id("b", index),
                    type=beat_type,
                    text=text,
                    speaker_ref=speaker_ref,
                    emotion="紧张" if "紧张" in text or "秘密" in text else "",
                )
            )

        location_ref = story_bible.locations[0].location_id if story_bible.locations else None
        source_refs = [SourceRef(chapter_id=chapter.chapter_id, excerpt_id=excerpt.excerpt_id) for excerpt in chapter.excerpts[:2]]
        time_of_day = "night" if any(token in chapter.raw_text for token in ("夜", "深夜", "晚上")) else "day"
        return Scene(
            scene_id=scene_plan.scene_id,
            title=scene_plan.title,
            chapter_refs=scene_plan.chapter_refs,
            location_ref=location_ref,
            time_of_day=time_of_day,
            objective=scene_plan.objective,
            summary=summarize_text(chapter.raw_text),
            beats=beats,
            transitions=SceneTransition(next_scene_hint=scene_plan.conflict or "进入下一场戏", transition_type="cut"),
            source_refs=source_refs,
        )

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

    def _format_dashscope_error(self, response: httpx.Response, model: str, url: str) -> str:
        detail = response.text.strip()
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
                    "act_id": _normalize_text_field(act.get("act_id")) or make_id("a", index, width=1),
                    "name": _normalize_text_field(act.get("name")) or f"第{index}幕",
                    "purpose": _normalize_text_field(act.get("purpose")),
                    "scene_count": _normalize_int(act.get("scene_count"), 0),
                }
            )
        for index, scene in enumerate(_normalize_named_mapping_list(payload.get("scene_plans"), fallback_key="title"), start=1):
            fallback_act_id = normalized["acts"][min(index - 1, len(normalized["acts"]) - 1)]["act_id"] if normalized["acts"] else "a1"
            normalized["scene_plans"].append(
                {
                    "scene_id": _normalize_text_field(scene.get("scene_id")) or make_id("s", index),
                    "act_id": _normalize_text_field(scene.get("act_id")) or fallback_act_id,
                    "title": _normalize_text_field(scene.get("title")) or f"场景{index}",
                    "objective": _normalize_text_field(scene.get("objective")) or "推进核心冲突",
                    "chapter_refs": _ensure_str_list(scene.get("chapter_refs")),
                    "conflict": _normalize_text_field(scene.get("conflict")),
                    "notes": _normalize_text_field(scene.get("notes")),
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
                    text=payload.get("summary") or scene_plan.objective,
                )
            )
        source_refs = [
            SourceRef(
                chapter_id=_normalize_text_field(item.get("chapter_id")) or chapter.chapter_id,
                excerpt_id=_normalize_text_field(item.get("excerpt_id")) or "p001",
            )
            for item in _normalize_named_mapping_list(payload.get("source_refs"), fallback_key="excerpt_id")
        ]
        return Scene(
            scene_id=scene_plan.scene_id,
            title=_normalize_text_field(payload.get("title")) or scene_plan.title,
            chapter_refs=scene_plan.chapter_refs,
            location_ref=_normalize_optional_str(payload.get("location_ref")),
            time_of_day=_normalize_text_field(payload.get("time_of_day")),
            objective=_normalize_text_field(payload.get("objective")) or scene_plan.objective,
            summary=_normalize_text_field(payload.get("summary")),
            beats=beats,
            transitions=SceneTransition.model_validate(_normalize_mapping(payload.get("transitions"))) if payload.get("transitions") else None,
            source_refs=source_refs,
        )

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


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item and item not in output:
            output.append(item)
    return output
