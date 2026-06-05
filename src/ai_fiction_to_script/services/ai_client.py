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
        response = httpx.post(url, headers=headers, json=payload, timeout=self._settings.timeout_seconds)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, list):
            text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        else:
            text = str(content)
        return parse_json_object(text)

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
        for index, item in enumerate(payload.get("characters", []), start=1):
            characters.append(
                CharacterCard(
                    character_id=item.get("character_id") or make_id("c", index),
                    name=item.get("name", f"角色{index}"),
                    role=item.get("role", "supporting"),
                    traits=_ensure_str_list(item.get("traits")),
                    goal=item.get("goal", ""),
                    conflict=item.get("conflict", ""),
                    arc=item.get("arc", ""),
                    voice=item.get("voice", ""),
                    relations=[
                        CharacterRelation(
                            target_character_id=relation.get("target_character_id", ""),
                            relation=relation.get("relation", "关联"),
                            notes=relation.get("notes", ""),
                        )
                        for relation in item.get("relations", [])
                        if relation.get("target_character_id")
                    ],
                )
            )
        locations = [
            LocationCard(
                location_id=item.get("location_id") or make_id("l", index),
                name=item.get("name", f"地点{index}"),
                description=item.get("description", ""),
                mood=item.get("mood", ""),
            )
            for index, item in enumerate(payload.get("locations", []), start=1)
        ]
        timeline = [
            TimelineEvent(
                event_id=item.get("event_id") or make_id("e", index),
                time_order=int(item.get("time_order", index)),
                summary=item.get("summary", ""),
                chapter_refs=_ensure_str_list(item.get("chapter_refs")),
            )
            for index, item in enumerate(payload.get("timeline", []), start=1)
        ]
        return StoryBible(
            logline=payload.get("logline", ""),
            synopsis=payload.get("synopsis", ""),
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
        for index, act in enumerate(payload.get("acts", []), start=1):
            normalized["acts"].append(
                {
                    "act_id": act.get("act_id") or make_id("a", index, width=1),
                    "name": act.get("name", f"第{index}幕"),
                    "purpose": act.get("purpose", ""),
                    "scene_count": int(act.get("scene_count", 0)),
                }
            )
        for index, scene in enumerate(payload.get("scene_plans", []), start=1):
            fallback_act_id = normalized["acts"][min(index - 1, len(normalized["acts"]) - 1)]["act_id"] if normalized["acts"] else "a1"
            normalized["scene_plans"].append(
                {
                    "scene_id": scene.get("scene_id") or make_id("s", index),
                    "act_id": scene.get("act_id") or fallback_act_id,
                    "title": scene.get("title", f"场景{index}"),
                    "objective": scene.get("objective", "推进核心冲突"),
                    "chapter_refs": _ensure_str_list(scene.get("chapter_refs")),
                    "conflict": scene.get("conflict", ""),
                    "notes": scene.get("notes", ""),
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
        for index, beat in enumerate(payload.get("beats", []), start=1):
            beats.append(
                Beat(
                    beat_id=beat.get("beat_id") or make_id("b", index),
                    type=beat.get("type", "action"),
                    text=beat.get("text", ""),
                    speaker_ref=beat.get("speaker_ref"),
                    emotion=beat.get("emotion", ""),
                )
            )
        source_refs = [
            SourceRef(chapter_id=item.get("chapter_id", chapter.chapter_id), excerpt_id=item.get("excerpt_id", "p001"))
            for item in payload.get("source_refs", [])
        ]
        return Scene(
            scene_id=scene_plan.scene_id,
            title=payload.get("title", scene_plan.title),
            chapter_refs=scene_plan.chapter_refs,
            location_ref=payload.get("location_ref"),
            time_of_day=payload.get("time_of_day", ""),
            objective=payload.get("objective", scene_plan.objective),
            summary=payload.get("summary", ""),
            beats=beats,
            transitions=SceneTransition.model_validate(payload.get("transitions", {})) if payload.get("transitions") else None,
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


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item and item not in output:
            output.append(item)
    return output
