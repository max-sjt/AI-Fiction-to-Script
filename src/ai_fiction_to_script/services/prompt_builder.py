from __future__ import annotations

import json
from typing import Any

from ai_fiction_to_script.models.runtime import AdaptationRequest, ChapterAnalysis, ParsedChapter
from ai_fiction_to_script.models.schema import Outline, ScenePlan, ScreenplayDocument, StoryBible
from ai_fiction_to_script.services.presets import build_script_type_instruction, build_tone_instruction


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _truncate_text(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def _text_char_count(text: str) -> int:
    return len("".join(text.split()))


def _length_ratio(request: AdaptationRequest) -> tuple[float, float, str]:
    if request.detail_level == "fast":
        return 0.6, 0.8, "快速模式：生成原章节字数的 60%-80%，在保留章节脉络和关键事件的前提下压缩表达，方便作者快速理清剧情走向。"
    if request.detail_level == "detailed":
        return 1.5, 2.5, "详写模式：生成原章节字数的 150%-250%，在原章节基础上扩写细节，补足动作、环境、人物反应、情绪层次和戏剧化细节。"
    return 0.8, 1.5, "标准模式：生成原章节字数的 80%-150%，在原章节基础上适度改写和扩写，重点丰富对话、冲突交锋和人物表达。"


def _target_length_range(source_chars: int, request: AdaptationRequest) -> tuple[int, int]:
    min_ratio, max_ratio, _ = _length_ratio(request)
    return max(1, round(source_chars * min_ratio)), max(1, round(source_chars * max_ratio))


def _length_budget_instruction(request: AdaptationRequest, source_chars: int, unit_name: str = "本章剧本单元") -> str:
    min_chars, max_chars = _target_length_range(source_chars, request)
    _, _, purpose = _length_ratio(request)
    return (
        f"{purpose}\n"
        f"{unit_name}来源章节约 {source_chars} 字，最终生成正文目标为 {min_chars}-{max_chars} 字。"
        "这里的字数指 ACTION / 台词 / NARRATION 等主体剧本文本合计，不包含标题、TIME、SUMMARY、TRANSITION、END SCENE。"
    )


def _chapter_scene_context(chapter: ParsedChapter) -> str:
    excerpt_lines: list[str] = []
    for excerpt in chapter.excerpts[:2]:
        excerpt_lines.append(f"- {excerpt.excerpt_id}: {_truncate_text(excerpt.text, limit=120)}")
    if not excerpt_lines:
        excerpt_lines.append(f"- p001: {_truncate_text(chapter.raw_text, limit=120)}")

    return (
        f"章节标题：{chapter.title}\n"
        f"章节摘要：{_truncate_text(chapter.raw_text, limit=120)}\n"
        "关键摘录：\n"
        + "\n".join(excerpt_lines)
    )


def _chapter_scene_context_with_limit(chapter: ParsedChapter, limit: int) -> str:
    excerpt_lines: list[str] = []
    for excerpt in chapter.excerpts[:4]:
        excerpt_lines.append(f"- {excerpt.excerpt_id}: {_truncate_text(excerpt.text, limit=min(180, limit // 4 or 120))}")
    if not excerpt_lines:
        excerpt_lines.append(f"- p001: {_truncate_text(chapter.raw_text, limit=limit)}")
    return (
        f"章节标题：{chapter.title}\n"
        f"章节摘要：{_truncate_text(chapter.raw_text, limit=limit)}\n"
        "关键摘录：\n"
        + "\n".join(excerpt_lines)
    )


def _story_bible_scene_context(story_bible: StoryBible) -> str:
    character_names = "、".join(character.name for character in story_bible.characters[:5]) or "未提供"
    location_names = "、".join(location.name for location in story_bible.locations[:4]) or "未提供"
    themes = "、".join(story_bible.theme[:4]) or "未提供"
    return (
        f"logline：{_truncate_text(story_bible.logline, limit=80)}\n"
        f"synopsis：{_truncate_text(story_bible.synopsis, limit=120)}\n"
        f"主题：{themes}\n"
        f"主要角色：{character_names}\n"
        f"主要地点：{location_names}"
    )


def _chapters_context(chapters: list[ParsedChapter], limit: int = 180) -> str:
    blocks: list[str] = []
    for chapter in chapters:
        blocks.append(
            "\n".join(
                [
                    f"章节ID：{chapter.chapter_id}",
                    f"章节标题：{chapter.title}",
                    f"章节内容摘录：{_truncate_text(chapter.raw_text, limit=limit)}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _chapters_length_budget_context(chapters: list[ParsedChapter], request: AdaptationRequest) -> str:
    blocks: list[str] = []
    for chapter in chapters:
        source_chars = _text_char_count(chapter.raw_text)
        min_chars, max_chars = _target_length_range(source_chars, request)
        blocks.append(
            "\n".join(
                [
                    f"章节ID：{chapter.chapter_id}",
                    f"原章节字数：{source_chars}",
                    f"目标剧本正文字数：{min_chars}-{max_chars}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _scene_plan_context(scene_plan: ScenePlan) -> str:
    lines = [
        f"章节剧本单元标题：{scene_plan.title}",
        f"章节剧本单元目标：{scene_plan.objective}",
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


def _beat_budget_instruction(request: AdaptationRequest, unit_name: str = "每场") -> str:
    max_beats = request.max_beats_per_scene
    if request.detail_level == "fast":
        return (
            f"{unit_name}主体内容控制在 3-{max_beats} 条 beat；"
            "只保留主线事件、关键转折和必要台词，禁止扩写环境、心理和反应细节。"
        )
    if request.detail_level == "detailed":
        min_beats = max(9, max_beats - 2)
        return (
            f"{unit_name}主体内容可拆为 {min_beats}-{max_beats} 条 beat，"
            "单条 beat 必须写得更充分，重点扩写动作过程、环境压力、人物反应、情绪层次和冲突余波。"
        )
    min_beats = max(4, max_beats - 1)
    return (
        f"{unit_name}主体内容可拆为 {min_beats}-{max_beats} 条 beat，"
        "重点丰富对白、冲突交锋和人物表达，不要只写剧情摘要。"
    )


def _detail_execution_instruction(request: AdaptationRequest) -> str:
    if request.detail_level == "fast":
        return (
            "详细度执行：快速模式必须明显短于标准和详写。"
            "写法是剧情梗概式剧本，只写主线动作和少量关键对白；"
            "不要写铺垫、环境描摹、心理反复、人物停顿和细节反应。"
        )
    if request.detail_level == "detailed":
        return (
            "详细度执行：详写模式必须明显长于快速和标准。"
            "每个关键事件都要扩成完整戏剧过程：进入状态、动作推进、对话交锋、环境压迫、人物反应、情绪变化、冲突余波都要写出来；"
            "不能用一句话概括本该展开的动作或情绪。"
        )
    return (
        "详细度执行：标准模式必须明显长于快速，但短于详写。"
        "写法是完整初稿，围绕关键事件补足对白、冲突交锋和人物表达；"
        "可以适度写动作与反应，但不要像详写模式那样大段扩写环境和心理层次。"
    )


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
            "并尽量补充 focus_event, bridge_in, bridge_out 以保证章节之间连续。\n"
            "不要使用 A1/A2/A3、开端/发展/结局 这种机械三段式标签来硬切故事。acts 可以只保留一个 main 容器，真正的节奏由 scene_plans 决定。\n"
            "必须按小说章节输出：每个原小说章节只对应一个 scene_plan，一个 scene_plan 就是一章的完整剧本单元。\n"
            "严禁为了让模型更快生成而把同一章拆成多个场景、多个分点、多个小段任务；速度由流式整篇生成保证，不由拆章保证。\n"
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
        source_chars = _text_char_count(chapter.raw_text)
        system = (
            "你是小说改编编剧。"
            "请根据给定章节剧本单元计划输出单个章节剧本 JSON，不要输出 YAML，也不要解释。"
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
            f"{_detail_execution_instruction(request)}\n"
            f"长度要求：{_length_budget_instruction(request, source_chars)}\n"
            "请输出字段：title, time_of_day, objective, summary, beats, transitions, source_refs。"
            f"beats 中每项必须包含 beat_id, type, text，可选 speaker_ref, emotion。{_beat_budget_instruction(request)}\n"
            "如果输出 speaker_ref 或 location_ref，必须使用 Story Bible 已提供的 character_id / location_id，不要使用人物名或地点名。\n"
            "如果 Scene Plan 的 objective 或 notes 带有本次修改要求，必须优先执行，不能沿用旧场景表达。\n"
            "不要使用 [VO]、不要使用 [SFX]、不要使用 [BGM]、不要使用 OS、不要使用旁白标签或广播剧脚本括号标记；对白只写台词内容，动作只写动作描述。\n"
            "请让章节剧本自然承接前后章节并给下一章留出动势，开头用极短的上下文接续即可，不要机械写成 A1/A2/A3 或章节摘要拼贴。\n"
            "只能输出这一章的完整剧本单元，不要把章节拆成多个场景或分点任务。\n"
            "请按上述剧本类型和语气要求重写这个章节剧本，而不是只把原小说内容换一种说法复述。\n\n"
            f"章节剧本单元上下文：\n{_scene_plan_context(scene_plan)}\n\n"
            f"Story Bible 摘要：\n{_story_bible_scene_context(story_bible)}\n\n"
            f"来源章节：\n{_chapter_scene_context_with_limit(chapter, request.chapter_context_chars)}"
        )
        return system, user

    @staticmethod
    def screenplay_scene_text(
        scene_plan: ScenePlan,
        story_bible: StoryBible,
        chapter: ParsedChapter,
        request: AdaptationRequest,
    ) -> tuple[str, str]:
        source_chars = _text_char_count(chapter.raw_text)
        system = (
            "你是小说改编编剧。"
            "请创作单个章节剧本单元的纯文本剧本，不要输出 JSON，不要输出 YAML，不要解释。"
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
            f"{_detail_execution_instruction(request)}\n"
            f"长度要求：{_length_budget_instruction(request, source_chars)}\n"
            "请按下面格式输出单个章节剧本单元的纯文本剧本，本地程序会再转换成 YAML 结构：\n"
            f"CHAPTER_UNIT {scene_plan.scene_id} | {scene_plan.title}\n"
            "TIME: day/night\n"
            "SUMMARY: 一句话概括本场戏\n"
            "ACTION: 动作或画面\n"
            "c001: 角色台词\n"
            "NARRATION: 旁白或说明\n"
            "TRANSITION: 转场提示\n"
            "END SCENE\n\n"
            "规则：\n"
            "- 只能输出这一章对应的完整剧本单元，不要新增场次，不要把本章拆成多个 SCENE 或多个 CHAPTER_UNIT。\n"
            "- 台词行优先使用 Story Bible 中的 character_id，例如 c001: 台词内容。\n"
            f"- {_beat_budget_instruction(request)}\n"
            "- 剧本类型、语气和详细度是创作方向，只能体现在对白、动作、节奏和结构里；严禁把“电视剧处理”“语气执行”“详细度执行”等配置说明原句写进剧本正文。\n"
            "- 不要输出 markdown 代码块。\n"
            "- 如果 Scene Plan 的 objective 或 notes 带有本次修改要求，必须优先执行。\n\n"
            f"章节剧本单元上下文：\n{_scene_plan_context(scene_plan)}\n\n"
            f"Story Bible 摘要：\n{_story_bible_scene_context(story_bible)}\n\n"
            f"来源章节：\n{_chapter_scene_context_with_limit(chapter, request.chapter_context_chars)}"
        )
        return system, user

    @staticmethod
    def full_script(
        outline: Outline,
        story_bible: StoryBible,
        chapters: list[ParsedChapter],
        request: AdaptationRequest,
    ) -> tuple[str, str]:
        system = (
            "你是小说改编编剧。"
            "请根据给定大纲与章节信息，一次性输出整部剧本的严格 JSON，不要解释，不要输出 YAML。"
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
            f"{_detail_execution_instruction(request)}\n"
            f"整体长度规则：{_length_ratio(request)[2]} 每个 scene_id 必须按其来源章节字数生成对应比例的正文长度。\n"
            "请输出字段：scenes。\n"
            "scenes 必须严格覆盖 Outline 里的全部 scene_id，并按原顺序返回。\n"
            f"每个 scene 必须包含：scene_id, title, time_of_day, objective, summary, beats, transitions, source_refs。\n"
            f"beats 中每项必须包含：beat_id, type, text，可选 speaker_ref, emotion；{_beat_budget_instruction(request)}\n"
            "如果输出 speaker_ref 或 location_ref，必须使用 Story Bible 中已有的 ID，不要输出人物名或地点名。\n"
            "Outline 中每个 scene_id 代表一个原小说章节的完整剧本单元；不要把同一章拆成多个 scenes 或分点任务。\n"
            "不要新增场次，不要遗漏场次。\n\n"
            f"Outline：\n{_json(outline.model_dump())}\n\n"
            f"Story Bible 摘要：\n{_story_bible_scene_context(story_bible)}\n\n"
            f"章节内容：\n{_chapters_context(chapters, request.chapter_context_chars)}\n\n"
            f"逐章字数预算：\n{_chapters_length_budget_context(chapters, request)}\n\n"
            f"详细度：{request.detail_level}"
        )
        return system, user

    @staticmethod
    def screenplay_text(
        outline: Outline,
        story_bible: StoryBible,
        chapters: list[ParsedChapter],
        request: AdaptationRequest,
    ) -> tuple[str, str]:
        system = (
            "你是小说改编编剧。"
            "请先创作纯文本剧本，不要输出 JSON，不要输出 YAML，不要解释。"
        )
        scene_lines = []
        for scene_plan in outline.scene_plans:
            scene_lines.append(
                "\n".join(
                    [
                        f"CHAPTER_UNIT {scene_plan.scene_id} | {scene_plan.title}",
                        f"目标：{scene_plan.objective}",
                        f"焦点：{scene_plan.focus_event or scene_plan.notes}",
                    ]
                )
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
            f"{_detail_execution_instruction(request)}\n"
            f"整体长度规则：{_length_ratio(request)[2]} 每个 CHAPTER_UNIT 必须按其来源章节字数生成对应比例的正文长度。\n"
            "请按下面格式输出纯文本剧本，本地程序会再转换成 YAML 结构：\n"
            "CHAPTER_UNIT s001 | 章节剧本标题\n"
            "TIME: day/night\n"
            "SUMMARY: 一句话概括本场戏\n"
            "ACTION: 动作或画面\n"
            "c001: 角色台词\n"
            "NARRATION: 旁白或说明\n"
            "TRANSITION: 转场提示\n"
            "END SCENE\n\n"
            "规则：\n"
            "- 必须严格覆盖待生成章节剧本单元清单里的全部 scene_id，并按原顺序返回。\n"
            "- 每个 scene_id 代表一个原小说章节；不要把同一章拆成多个 SCENE 或多个 CHAPTER_UNIT，也不要用分点代替完整剧本。\n"
            "- 台词行优先使用 Story Bible 中的 character_id，例如 c001: 台词内容。\n"
            f"- {_beat_budget_instruction(request)}\n"
            "- 不要新增场次，不要遗漏场次，不要输出 markdown 代码块。\n\n"
            f"待生成章节剧本单元清单：\n{chr(10).join(scene_lines)}\n\n"
            f"Story Bible 摘要：\n{_story_bible_scene_context(story_bible)}\n\n"
            f"章节摘要：\n{_chapters_context(chapters)}\n\n"
            f"逐章字数预算：\n{_chapters_length_budget_context(chapters, request)}"
        )
        return system, user

    @staticmethod
    def quality(document: ScreenplayDocument) -> tuple[str, str]:
        system = (
            "你是剧本质检编辑。"
            "请审查这个 YAML 对应的结构化对象，输出严格 JSON。"
        )
        scenes = []
        for act in document.script.acts:
            for scene in act.scenes:
                scenes.append(
                    {
                        "scene_id": scene.scene_id,
                        "title": scene.title,
                        "summary": scene.summary,
                        "chapter_refs": scene.chapter_refs,
                        "beats": [
                            {
                                "type": beat.type,
                                "speaker_ref": beat.speaker_ref,
                                "text": _truncate_text(beat.text, 120),
                            }
                            for beat in scene.beats[:4]
                        ],
                    }
                )
        review_payload = {
            "meta": {
                "target_format": document.meta.target_format,
                "tone": document.meta.tone,
                "genre": document.meta.genre,
            },
            "story_bible": {
                "logline": document.story_bible.logline,
                "characters": [
                    {"character_id": character.character_id, "name": character.name, "role": character.role}
                    for character in document.story_bible.characters[:8]
                ],
            },
            "scenes": scenes,
        }
        user = (
            "请输出字段：warnings, revision_suggestions，每项不超过 5 条。"
            "重点关注人物一致性、场景跳跃、逻辑断层、对白口吻和所选剧本类型/语气是否被执行。\n\n"
            f"剧本审查摘要：\n{_json(review_payload)}"
        )
        return system, user
