from __future__ import annotations

from ai_fiction_to_script.models.runtime import AdaptationRequest, ChapterAnalysis, ParsedChapter, ParsedExcerpt
from ai_fiction_to_script.models.schema import ActOutline, Outline, ScenePlan, StoryBible
from ai_fiction_to_script.services.presets import (
    build_adaptation_goal,
    build_script_type_instruction,
    build_style_guide_for_tone,
    build_tone_instruction,
)
from ai_fiction_to_script.services.prompt_builder import PromptBuilder


def make_request() -> AdaptationRequest:
    return AdaptationRequest(
        project_id="prompt-project",
        title="夜行站台",
        original_novel_title="夜行站台",
        original_author="测试作者",
        target_format="audio_drama",
        tone="suspenseful",
        adaptation_goal=build_adaptation_goal("audio_drama"),
        style_guide=build_style_guide_for_tone("suspenseful"),
        provider="mock",
    )


def test_scene_prompt_includes_script_type_and_tone_instructions() -> None:
    request = make_request()
    chapter = ParsedChapter(
        chapter_id="ch01",
        title="第一章 站台",
        raw_text="深夜站台上只剩广播声和脚步声。广播突然重复同一句话，主角意识到有人在盯着自己。",
        raw_text_ref="memory://chapter-1",
        excerpts=[
            ParsedExcerpt(excerpt_id="p001", text="深夜站台上只剩广播声和脚步声。"),
            ParsedExcerpt(excerpt_id="p002", text="广播突然重复同一句话，主角意识到有人在盯着自己。"),
        ],
    )
    scene_plan = ScenePlan(
        scene_id="s001",
        act_id="a1",
        title="深夜站台",
        objective="制造不安感",
        chapter_refs=["ch01"],
    )
    story_bible = StoryBible(logline="logline", synopsis="synopsis")

    _, user = PromptBuilder.scene(scene_plan, story_bible, chapter, request)

    assert "目标剧本类型：audio_drama" in user
    assert f"剧本类型执行要点：{build_script_type_instruction('audio_drama')}" in user
    assert f"语气执行要点：{build_tone_instruction('suspenseful')}" in user
    assert "而不是只把原小说内容换一种说法复述" in user
    assert "关键摘录：" in user
    assert "p001" in user
    assert "广播突然重复同一句话" in user
    assert "Story Bible 摘要：" in user
    assert "主要角色：" in user
    assert "标准模式" in user
    assert "最终生成正文目标为" in user
    assert "Story Bible：\n{" not in user
    assert "character_id / location_id" in user
    assert "章节剧本单元上下文：" in user
    assert "不要使用 [VO]" in user
    assert "不要使用 [SFX]" in user
    assert "Scene Plan：\n{" not in user


def test_outline_prompt_explicitly_requires_format_and_tone_execution() -> None:
    request = make_request()
    analyses = [
        ChapterAnalysis(
            chapter_id="ch01",
            title="第一章 站台",
            summary="深夜站台上，主角听见异常广播。",
            conflicts=["主角不确定广播是否在针对自己。"],
        )
    ]
    story_bible = StoryBible(logline="logline", synopsis="synopsis")

    _, user = PromptBuilder.outline(analyses, story_bible, request)

    assert f"剧本类型执行要点：{build_script_type_instruction('audio_drama')}" in user
    assert f"语气执行要点：{build_tone_instruction('suspenseful')}" in user
    assert "必须真正体现目标剧本类型与语气" in user
    assert "不要使用 A1/A2/A3" in user
    assert "最终 YAML 只是对最终剧本结果的结构化落盘" in user


def test_screenplay_text_prompt_uses_request_length_budget() -> None:
    request = make_request().model_copy(update={"detail_level": "detailed", "max_beats_per_scene": 12})
    outline = Outline(
        structure_type="continuous_sequence",
        acts=[ActOutline(act_id="main", name="正文", purpose="continuous", scene_count=1)],
        scene_plans=[
            ScenePlan(
                scene_id="s001",
                act_id="main",
                title="深夜站台",
                objective="制造不安感",
                chapter_refs=["ch01"],
            )
        ],
    )
    story_bible = StoryBible(logline="logline", synopsis="synopsis")
    chapters = [
        ParsedChapter(
            chapter_id="ch01",
            title="第一章 站台",
            raw_text="深夜站台上只剩广播声和脚步声。",
            raw_text_ref="memory://chapter-1",
        )
    ]

    _, user = PromptBuilder.screenplay_text(outline, story_bible, chapters, request)

    assert "详写模式" in user
    assert "原章节字数：15" in user
    assert "目标剧本正文字数：22-38" in user
    assert "60%-80%" not in user


def test_scene_text_prompt_maps_detail_to_source_length_ratios() -> None:
    chapter = ParsedChapter(
        chapter_id="ch01",
        title="第一章",
        raw_text="一" * 100,
        raw_text_ref="memory://chapter-1",
    )
    scene_plan = ScenePlan(scene_id="s001", act_id="main", title="第一章", objective="推进剧情", chapter_refs=["ch01"])
    story_bible = StoryBible(logline="logline", synopsis="synopsis")

    _, fast_user = PromptBuilder.screenplay_scene_text(
        scene_plan,
        story_bible,
        chapter,
        make_request().model_copy(update={"detail_level": "fast", "max_beats_per_scene": 6}),
    )
    _, standard_user = PromptBuilder.screenplay_scene_text(
        scene_plan,
        story_bible,
        chapter,
        make_request().model_copy(update={"detail_level": "standard", "max_beats_per_scene": 10}),
    )
    _, detailed_user = PromptBuilder.screenplay_scene_text(
        scene_plan,
        story_bible,
        chapter,
        make_request().model_copy(update={"detail_level": "detailed", "max_beats_per_scene": 12}),
    )

    assert "60%-80%" in fast_user
    assert "最终生成正文目标为 60-80 字" in fast_user
    assert "快速模式必须明显短于标准和详写" in fast_user
    assert "禁止扩写环境、心理和反应细节" in fast_user
    assert "80%-150%" in standard_user
    assert "最终生成正文目标为 80-150 字" in standard_user
    assert "标准模式必须明显长于快速，但短于详写" in standard_user
    assert "不要只写剧情摘要" in standard_user
    assert "150%-250%" in detailed_user
    assert "最终生成正文目标为 150-250 字" in detailed_user
    assert "详写模式必须明显长于快速和标准" in detailed_user
    assert "环境压迫、人物反应、情绪变化" in detailed_user
    assert "严禁把“电视剧处理”“语气执行”“详细度执行”等配置说明原句写进剧本正文" in detailed_user
