from __future__ import annotations

import json
from typing import Any

from ai_fiction_to_script.models.runtime import AdaptationRequest, ChapterAnalysis, ParsedChapter
from ai_fiction_to_script.models.schema import ScenePlan, ScreenplayDocument, StoryBible


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


class PromptBuilder:
    @staticmethod
    def chapter_analysis(chapter: ParsedChapter, request: AdaptationRequest) -> tuple[str, str]:
        system = (
            "你是专业小说改编分析师。"
            "请先理解小说章节，再输出严格 JSON，不要输出额外解释。"
        )
        user = (
            f"项目标题：{request.title}\n"
            f"目标剧种：{request.target_format}\n"
            "请分析下面章节，输出字段：summary, characters, key_events, conflicts, emotions, locations, props。\n\n"
            f"章节标题：{chapter.title}\n"
            f"章节正文：\n{chapter.raw_text}"
        )
        return system, user

    @staticmethod
    def story_bible(
        analyses: list[ChapterAnalysis],
        request: AdaptationRequest,
    ) -> tuple[str, str]:
        system = (
            "你是剧本开发顾问。"
            "请基于章节理解结果整合 Story Bible，并返回严格 JSON。"
        )
        user = (
            f"项目标题：{request.title}\n"
            f"目标剧种：{request.target_format}\n"
            f"整体风格：{request.tone}\n"
            "请输出字段：logline, synopsis, theme, characters, locations, timeline, props。\n\n"
            f"章节分析：\n{_json([item.model_dump() for item in analyses])}"
        )
        return system, user

    @staticmethod
    def outline(
        analyses: list[ChapterAnalysis],
        story_bible: StoryBible,
        request: AdaptationRequest,
    ) -> tuple[str, str]:
        system = (
            "你是资深编剧统筹。"
            "请把小说分析结果转成结构化剧本大纲，输出严格 JSON。"
        )
        user = (
            f"结构类型：{request.structure_type}\n"
            f"压缩策略：{request.compression_strategy}\n"
            f"节奏策略：{request.pacing_policy}\n"
            "请输出字段：acts, scene_plans。scene_plans 必须包含 scene_id, act_id, title, objective, chapter_refs, conflict, notes。\n\n"
            f"Story Bible：\n{_json(story_bible.model_dump())}\n\n"
            f"章节分析：\n{_json([item.model_dump() for item in analyses])}"
        )
        return system, user

    @staticmethod
    def scene(
        scene_plan: ScenePlan,
        story_bible: StoryBible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
    ) -> tuple[str, str]:
        system = (
            "你是小说改编编剧。"
            "请根据给定 Scene Plan 输出单场景剧本 JSON，不要输出 YAML，也不要解释。"
        )
        user = (
            f"项目标题：{request.title}\n"
            f"目标剧种：{request.target_format}\n"
            f"对白风格：{request.style_guide.dialogue_style}\n"
            f"叙述风格：{request.style_guide.narration_style}\n"
            "请输出字段：title, time_of_day, objective, summary, beats, transitions, source_refs。"
            "beats 中每项必须包含 beat_id, type, text，可选 speaker_ref, emotion。\n\n"
            f"Scene Plan：\n{_json(scene_plan.model_dump())}\n\n"
            f"Story Bible：\n{_json(story_bible.model_dump())}\n\n"
            f"来源章节：\n{chapter.raw_text}"
        )
        return system, user

    @staticmethod
    def quality(document: ScreenplayDocument) -> tuple[str, str]:
        system = (
            "你是剧本质检编辑。"
            "请审查这个 YAML 对应的结构化对象，输出严格 JSON。"
        )
        user = (
            "请输出字段：warnings, revision_suggestions。重点关注人物一致性、场景跳跃、逻辑断层、对白口吻。\n\n"
            f"剧本对象：\n{_json(document.model_dump())}"
        )
        return system, user

