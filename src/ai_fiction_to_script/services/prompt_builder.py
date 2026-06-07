from __future__ import annotations

import json
from typing import Any

from ai_fiction_to_script.models.runtime import AdaptationRequest, ChapterAnalysis, ParsedChapter
from ai_fiction_to_script.models.schema import ScenePlan, ScreenplayDocument, StoryBible
from ai_fiction_to_script.services.presets import build_script_type_instruction, build_tone_instruction


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _truncate_text(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def _chapter_scene_context(chapter: ParsedChapter) -> str:
    excerpt_lines: list[str] = []
    for excerpt in chapter.excerpts[:3]:
        excerpt_lines.append(f"- {excerpt.excerpt_id}: {_truncate_text(excerpt.text)}")
    if not excerpt_lines:
        excerpt_lines.append(f"- p001: {_truncate_text(chapter.raw_text)}")

    return (
        f"章节标题：{chapter.title}\n"
        f"章节摘要：{_truncate_text(chapter.raw_text, limit=180)}\n"
        "关键摘录：\n"
        + "\n".join(excerpt_lines)
    )


def _story_bible_scene_context(story_bible: StoryBible) -> str:
    character_names = "、".join(character.name for character in story_bible.characters[:5]) or "未提供"
    location_names = "、".join(location.name for location in story_bible.locations[:4]) or "未提供"
    themes = "、".join(story_bible.theme[:4]) or "未提供"
    return (
        f"logline：{_truncate_text(story_bible.logline, limit=120)}\n"
        f"synopsis：{_truncate_text(story_bible.synopsis, limit=180)}\n"
        f"主题：{themes}\n"
        f"主要角色：{character_names}\n"
        f"主要地点：{location_names}"
    )


def _scene_plan_context(scene_plan: ScenePlan) -> str:
    lines = [
        f"场景标题：{scene_plan.title}",
        f"场景目标：{scene_plan.objective}",
    ]
    if scene_plan.focus_event:
        lines.append(f"焦点事件：{scene_plan.focus_event}")
    if scene_plan.conflict:
        lines.append(f"核心冲突：{scene_plan.conflict}")
    if scene_plan.bridge_in:
        lines.append(f"入场承接：{scene_plan.bridge_in}")
    if scene_plan.bridge_out:
        lines.append(f"出场去向：{scene_plan.bridge_out}")
    if scene_plan.notes:
        lines.append(f"补充说明：{scene_plan.notes}")
    return "\n".join(lines)


class PromptBuilder:
    @staticmethod
    def chapter_analysis(chapter: ParsedChapter, request: AdaptationRequest) -> tuple[str, str]:
        system = (
            "你是专业小说改编分析师。"
            "请先理解小说章节，再输出严格 JSON，不要输出额外解释。"
        )
        user = (
            f"项目标题：{request.title}\n"
            f"目标剧本类型：{request.target_format}\n"
            f"目标语气：{request.tone}\n"
            f"剧本类型执行要点：{build_script_type_instruction(request.target_format)}\n"
            f"语气执行要点：{build_tone_instruction(request.tone)}\n"
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
            f"目标剧本类型：{request.target_format}\n"
            f"改编目标：{request.adaptation_goal}\n"
            f"整体语气：{request.tone}\n"
            f"剧本类型执行要点：{build_script_type_instruction(request.target_format)}\n"
            f"语气执行要点：{build_tone_instruction(request.tone)}\n"
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
            "请把小说分析结果转成连续推进的结构化剧本大纲，输出严格 JSON。"
        )
        user = (
            f"目标剧本类型：{request.target_format}\n"
            f"改编目标：{request.adaptation_goal}\n"
            f"结构类型：{request.structure_type}\n"
            f"压缩策略：{request.compression_strategy}\n"
            f"节奏策略：{request.pacing_policy}\n"
            f"语气：{request.tone}\n"
            f"剧本类型执行要点：{build_script_type_instruction(request.target_format)}\n"
            f"语气执行要点：{build_tone_instruction(request.tone)}\n"
            "请输出字段：acts, scene_plans。scene_plans 必须包含 scene_id, act_id, title, objective, chapter_refs, conflict, notes，"
            "并尽量补充 focus_event, bridge_in, bridge_out 以保证场景之间连续。\n"
            "不要使用 A1/A2/A3、开端/发展/结局 这种机械三段式标签来硬切故事。acts 可以只保留一个 main 容器，真正的节奏由 scene_plans 决定。\n"
            "请按照小说内容自然分场，每章可以拆成 1 到 2 个连续场景；场景标题要贴近事件，不要直接复述“第一章/第二章”。\n"
            "最终 YAML 只是对最终剧本结果的结构化落盘，不是先写 YAML 再反推剧本。\n"
            "大纲和场景设计必须真正体现目标剧本类型与语气，不要只在标签里重复这些要求。\n\n"
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
            f"目标剧本类型：{request.target_format}\n"
            f"改编目标：{request.adaptation_goal}\n"
            f"整体语气：{request.tone}\n"
            f"对白风格：{request.style_guide.dialogue_style}\n"
            f"叙述风格：{request.style_guide.narration_style}\n"
            f"节奏风格：{request.style_guide.pacing_style}\n"
            f"剧本类型执行要点：{build_script_type_instruction(request.target_format)}\n"
            f"语气执行要点：{build_tone_instruction(request.tone)}\n"
            "请输出字段：title, time_of_day, objective, summary, beats, transitions, source_refs。"
            "beats 中每项必须包含 beat_id, type, text，可选 speaker_ref, emotion，且 beats 最多 4 条。\n"
            "如果输出 speaker_ref 或 location_ref，必须使用 Story Bible 已提供的 character_id / location_id，不要使用人物名或地点名。\n"
            "如果 Scene Plan 的 objective 或 notes 带有本次修改要求，必须优先执行，不能沿用旧场景表达。\n"
            "请让场景自然承接上一场并给下一场留出动势，开头用极短的上下文接续即可，不要机械写成 A1/A2/A3 或章节摘要拼贴。\n"
            "请按上述剧本类型和语气要求重写这个场景，而不是只把原小说内容换一种说法复述。\n\n"
            f"Scene Plan：\n{_json(scene_plan.model_dump())}\n\n"
            f"场景上下文：\n{_scene_plan_context(scene_plan)}\n\n"
            f"Story Bible 摘要：\n{_story_bible_scene_context(story_bible)}\n\n"
            f"来源章节：\n{_chapter_scene_context(chapter)}"
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
