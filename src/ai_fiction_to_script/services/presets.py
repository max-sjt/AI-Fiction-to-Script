from __future__ import annotations

from ai_fiction_to_script.models.schema import StyleGuide


SCRIPT_TYPE_PRESETS: dict[str, dict[str, str]] = {
    "film": {
        "label_zh": "电影剧本",
        "label_en": "Film Screenplay",
        "goal": "将小说改编为电影剧本，强调集中冲突、镜头感和完整弧线。",
        "instruction": "以视觉化场面、镜头推进和单线主冲突为核心，减少解释性旁白，让每场戏都能直接拍摄。",
    },
    "tv_drama": {
        "label_zh": "电视剧剧本",
        "label_en": "TV Drama Screenplay",
        "goal": "将小说改编为电视剧剧本，强调连续场景推进、人物关系和持续悬念。",
        "instruction": "保持连续剧的追看感，场景之间要有钩子、人物关系递进和可延续的悬念。",
    },
    "short_drama": {
        "label_zh": "短剧剧本",
        "label_en": "Short Drama Screenplay",
        "goal": "将小说改编为短剧剧本，强调快节奏、强反转和高密度冲突。",
        "instruction": "每场都尽快抛出冲突或反转，压缩铺垫，让节奏短促且高信息密度。",
    },
    "stage_play": {
        "label_zh": "舞台剧剧本",
        "label_en": "Stage Play Script",
        "goal": "将小说改编为舞台剧剧本，强调台词张力、场面调度和有限空间表达。",
        "instruction": "优先通过人物对白、停顿和舞台调度推进冲突，减少频繁换景和纯镜头化描述。",
    },
    "animation": {
        "label_zh": "动画剧本",
        "label_en": "Animation Script",
        "goal": "将小说改编为动画剧本，强调视觉想象力、动作表现和角色风格化。",
        "instruction": "突出夸张动作、视觉奇观和角色风格化表达，让画面想象力明显强于写实戏剧。",
    },
    "audio_drama": {
        "label_zh": "广播剧剧本",
        "label_en": "Audio Drama Script",
        "goal": "将小说改编为广播剧剧本，强调声音线索、对白表现和听觉节奏。",
        "instruction": "依赖对白、声音线索和听觉节奏推进剧情，避免只有画面才能理解的描述。",
    },
}


TONE_PRESETS: dict[str, dict[str, str]] = {
    "balanced": {
        "label_zh": "平衡",
        "label_en": "Balanced",
        "dialogue": "自然克制",
        "narration": "清晰平衡",
        "pacing": "平衡",
        "direction": "情绪表达保持克制与清晰，不走极端，但要让冲突足够可感。",
    },
    "serious": {
        "label_zh": "严肃",
        "label_en": "Serious",
        "dialogue": "凝练严肃",
        "narration": "稳重克制",
        "pacing": "沉稳",
        "direction": "去掉戏谑和轻浮表达，整体压低玩笑感，强化责任、代价和压迫感。",
    },
    "angry": {
        "label_zh": "愤怒",
        "label_en": "Angry",
        "dialogue": "锋利压迫",
        "narration": "情绪强烈",
        "pacing": "急促",
        "direction": "让对白更锋利、冲突更外露，人物行动带着明显的对抗和急迫。",
    },
    "gentle": {
        "label_zh": "温柔",
        "label_en": "Gentle",
        "dialogue": "柔和细腻",
        "narration": "温润细致",
        "pacing": "舒缓",
        "direction": "保留冲突但弱化尖锐攻击性，用更柔和、体察性的表达推进关系。",
    },
    "suspenseful": {
        "label_zh": "悬疑",
        "label_en": "Suspenseful",
        "dialogue": "试探留白",
        "narration": "神秘克制",
        "pacing": "张弛交替",
        "direction": "信息分配要克制，给足留白、误导和不确定性，让观众持续猜测。",
    },
    "humorous": {
        "label_zh": "幽默",
        "label_en": "Humorous",
        "dialogue": "轻巧俏皮",
        "narration": "轻松灵动",
        "pacing": "明快",
        "direction": "允许机智、轻巧和反差笑点，但不能破坏主线事件的可理解性。",
    },
    "dark": {
        "label_zh": "暗黑",
        "label_en": "Dark",
        "dialogue": "冷厉压抑",
        "narration": "阴郁浓重",
        "pacing": "压迫式推进",
        "direction": "强化压抑、危险和失控感，让环境、对白和动作都带有持续阴影。",
    },
    "lyrical": {
        "label_zh": "抒情",
        "label_en": "Lyrical",
        "dialogue": "含蓄诗意",
        "narration": "画面感强",
        "pacing": "舒展",
        "direction": "突出意象、节奏和情绪波纹，让表达更有诗意但仍保持剧情推进。",
    },
    "cold": {
        "label_zh": "冷峻",
        "label_en": "Cold",
        "dialogue": "克制疏离",
        "narration": "冷静客观",
        "pacing": "精准",
        "direction": "避免煽情，改用更冷静、疏离、精准的措辞和行动逻辑。",
    },
    "uplifting": {
        "label_zh": "振奋",
        "label_en": "Uplifting",
        "dialogue": "坚定鼓舞",
        "narration": "昂扬积极",
        "pacing": "持续上扬",
        "direction": "即使处在困境，也让人物行动和叙述朝希望、信念和反弹力聚焦。",
    },
}


def build_style_guide_for_tone(tone: str) -> StyleGuide:
    preset = TONE_PRESETS.get(tone, TONE_PRESETS["balanced"])
    return StyleGuide(
        dialogue_style=preset["dialogue"],
        narration_style=preset["narration"],
        pacing_style=preset["pacing"],
    )


def build_adaptation_goal(script_type: str) -> str:
    preset = SCRIPT_TYPE_PRESETS.get(script_type, SCRIPT_TYPE_PRESETS["tv_drama"])
    return preset["goal"]


def build_script_type_instruction(script_type: str) -> str:
    preset = SCRIPT_TYPE_PRESETS.get(script_type, SCRIPT_TYPE_PRESETS["tv_drama"])
    return preset["instruction"]


def build_tone_instruction(tone: str) -> str:
    preset = TONE_PRESETS.get(tone, TONE_PRESETS["balanced"])
    return preset["direction"]
