from __future__ import annotations

import json

from ai_fiction_to_script.models.runtime import AdaptationRequest, ParsedChapter
from ai_fiction_to_script.models.schema import (
    ActOutline,
    Beat,
    CharacterCard,
    LocationCard,
    Outline,
    Scene,
    ScenePlan,
    SourceRef,
    StoryBible,
)
from ai_fiction_to_script.settings import QwenSettings
from ai_fiction_to_script.services.ai_client import (
    QwenAIClient,
    _build_scene_from_screenplay_text,
    _normalize_beat_id,
    _normalize_beat_type,
    _normalize_named_mapping_list,
    _normalize_relation_list,
    _normalize_scene_refs,
    _normalize_scene_title,
    _normalize_transition,
)


def test_normalize_beat_fields_accepts_qwen_dirty_values() -> None:
    assert _normalize_beat_id(1, 1) == "1"
    assert _normalize_beat_id(None, 2) == "b002"
    assert _normalize_beat_type("setup") == "narration"
    assert _normalize_beat_type("speech") == "dialogue"
    assert _normalize_beat_type("unknown-label") == "action"


def test_normalize_mapping_lists_accepts_plain_strings() -> None:
    assert _normalize_named_mapping_list("林然", "name") == [{"name": "林然"}]
    assert _normalize_named_mapping_list(["旧仓库", {"name": "天台"}], "name") == [{"name": "旧仓库"}, {"name": "天台"}]
    assert _normalize_relation_list(["陈默"]) == [{"target_character_id": "陈默", "relation": "关联"}]


def test_normalize_transition_accepts_string_and_entry_exit_mapping() -> None:
    assert _normalize_transition("切到天台") is not None
    transition = _normalize_transition({"entry": "切入夜景", "exit": "黑场"})
    assert transition is not None
    assert transition.next_scene_hint == "切入夜景"


def test_normalize_scene_title_strips_chapter_and_act_prefix() -> None:
    assert _normalize_scene_title("第一章：雨夜来客", 1) == "雨夜来客"
    assert _normalize_scene_title("场 一章：雨夜来客", 2) == "雨夜来客"
    assert _normalize_scene_title("A1 开端：雨夜来客", 3) == "雨夜来客"
    assert _normalize_scene_title("", 4) == "场景4"


def test_normalize_scene_refs_maps_names_aliases_and_unknown_values() -> None:
    story_bible = StoryBible(
        logline="logline",
        synopsis="synopsis",
        characters=[
            CharacterCard(character_id="c001", name="林默", role="protagonist"),
            CharacterCard(character_id="c002", name="黑衣男人", role="supporting"),
        ],
        locations=[LocationCard(location_id="l001", name="旧时光古董店")],
    )
    scene = Scene(
        scene_id="s001",
        title="Scene",
        chapter_refs=["ch001"],
        location_ref="旧时光古董店",
        objective="Push the conflict",
        beats=[
            Beat(beat_id="b001", type="dialogue", text="林默：继续说。", speaker_ref="林默"),
            Beat(beat_id="b002", type="dialogue", text="来客：无论付出什么代价。", speaker_ref="来客"),
            Beat(beat_id="b003", type="dialogue", text="陌生人：别来。", speaker_ref="陌生人"),
        ],
        source_refs=[SourceRef(chapter_id="ch001", excerpt_id="p001")],
    )

    normalized = _normalize_scene_refs(scene, story_bible)

    assert normalized.location_ref == "l001"
    assert normalized.beats[0].speaker_ref == "c001"
    assert normalized.beats[1].speaker_ref == "c002"
    assert normalized.beats[2].speaker_ref is None


def test_normalize_scene_refs_demotes_narrative_dialogue_with_dirty_speaker() -> None:
    story_bible = StoryBible(
        logline="logline",
        synopsis="synopsis",
        characters=[CharacterCard(character_id="c001", name="林默", role="protagonist")],
    )
    scene = Scene(
        scene_id="s001",
        title="Scene",
        chapter_refs=["ch001"],
        objective="Push the conflict",
        beats=[
            Beat(
                beat_id="b001",
                type="dialogue",
                text="林默没有回答，只是盯着那枚怀表。",
                speaker_ref="默没有回",
            )
        ],
        source_refs=[SourceRef(chapter_id="ch001", excerpt_id="p001")],
    )

    normalized = _normalize_scene_refs(scene, story_bible)

    assert normalized.beats[0].type == "action"
    assert normalized.beats[0].speaker_ref is None


def test_qwen_streaming_chat_collects_content_deltas(monkeypatch) -> None:
    payload = {
        "title": "Scene 1",
        "time_of_day": "night",
        "objective": "Push the conflict",
        "summary": "A streamed summary",
        "beats": [{"beat_id": "b001", "type": "action", "text": "First streamed beat"}],
        "transitions": {"next_scene_hint": "Cut away", "transition_type": "cut"},
        "source_refs": [{"chapter_id": "ch001", "excerpt_id": "p001"}],
    }
    text = json.dumps(payload, ensure_ascii=False)
    midpoint = len(text) // 2
    sse_lines = [
        f"data: {json.dumps({'choices': [{'delta': {'content': text[:midpoint]}}]}, ensure_ascii=False)}",
        "",
        f"data: {json.dumps({'choices': [{'delta': {'content': text[midpoint:]}}]}, ensure_ascii=False)}",
        "data: [DONE]",
    ]

    class FakeStreamResponse:
        is_error = False
        status_code = 200
        text = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def iter_lines(self):
            return iter(sse_lines)

    monkeypatch.setattr(
        "ai_fiction_to_script.services.ai_client.httpx.stream",
        lambda *args, **kwargs: FakeStreamResponse(),
    )

    client = QwenAIClient(QwenSettings(api_key="demo-key"))
    streamed: list[str] = []

    result = client._chat_json_stream("qwen-test", "system", "user", 0.3, on_delta=lambda acc, delta: streamed.append(delta))

    assert result["summary"] == "A streamed summary"
    assert streamed
    assert "".join(streamed) == text


def test_qwen_full_script_stream_generates_text_then_parses_to_script(monkeypatch) -> None:
    outline = Outline(
        structure_type="continuous_sequence",
        acts=[ActOutline(act_id="main", name="正文", purpose="continuous", scene_count=1)],
        scene_plans=[
            ScenePlan(
                scene_id="s001",
                act_id="main",
                title="天台对峙",
                objective="揭开短信来源",
                chapter_refs=["ch001"],
                conflict="主角逼问真相",
                notes="雨夜天台",
            )
        ],
    )
    story_bible = StoryBible(
        logline="雨夜里追查真相。",
        synopsis="主角在天台逼近答案。",
        characters=[CharacterCard(character_id="c001", name="林然", role="protagonist")],
        locations=[LocationCard(location_id="l001", name="天台")],
    )
    chapters = [
        ParsedChapter(
            chapter_id="ch001",
            title="第三章 天台",
            raw_text="林然赶到天台，发现短信来自熟人。",
            raw_text_ref="memory://ch001",
        )
    ]
    request = AdaptationRequest(
        project_id="demo",
        title="老街回声",
        original_novel_title="老街回声",
        original_author="tester",
        provider="qwen",
    )

    def fake_chat_text_stream(self, model, system, user, temperature, on_delta=None):
        assert "纯文本剧本" in system
        assert "SCENE s001" in user
        text = "\n".join(
            [
                "SCENE s001 | 天台对峙",
                "TIME: night",
                "SUMMARY: 林然在雨夜天台逼近短信真相。",
                "ACTION: 雨水拍在栏杆上，林然攥紧手机。",
                "c001: 这条短信到底是谁发的？",
                "TRANSITION: 切到手机屏幕亮起。",
                "END SCENE",
            ]
        )
        if on_delta is not None:
            on_delta(text, text)
        return text

    monkeypatch.setattr(QwenAIClient, "_chat_text_stream", fake_chat_text_stream)

    script = QwenAIClient(QwenSettings(api_key="demo-key")).generate_script_stream(
        outline,
        story_bible,
        chapters,
        request,
    )

    scene = script.acts[0].scenes[0]
    assert scene.scene_id == "s001"
    assert scene.title == "天台对峙"
    assert scene.time_of_day == "night"
    assert scene.summary == "林然在雨夜天台逼近短信真相。"
    assert [(beat.type, beat.speaker_ref, beat.text) for beat in scene.beats] == [
        ("action", None, "雨水拍在栏杆上，林然攥紧手机。"),
        ("dialogue", "c001", "这条短信到底是谁发的？"),
    ]
    assert scene.transitions is not None
    assert scene.transitions.next_scene_hint == "切到手机屏幕亮起。"


def test_build_scene_from_screenplay_text_preserves_explicit_speaker_id() -> None:
    scene_plan = ScenePlan(
        scene_id="s002",
        act_id="main",
        title="旧仓库灯光",
        objective="沈青交出录音笔",
        chapter_refs=["ch002"],
        conflict="沈青不确定林然是否值得信任",
        notes="废弃仓库",
    )
    story_bible = StoryBible(
        logline="调查失踪真相。",
        synopsis="林然和沈青在旧仓库交换线索。",
        characters=[
            CharacterCard(character_id="c001", name="林然", role="protagonist"),
            CharacterCard(character_id="c002", name="沈青", role="supporting"),
        ],
    )
    chapter = ParsedChapter(
        chapter_id="ch002",
        title="旧仓库",
        raw_text="沈青告诉林然她也在查林薇。",
        raw_text_ref="memory://ch002",
    )
    text = "\n".join(
        [
            "SCENE s002 | 旧仓库灯光",
            "TIME: night",
            "SUMMARY: 沈青在旧仓库交出关键录音。",
            "ACTION: 昏黄灯泡摇晃，文件散落在木箱上。",
            "c002: 放下戒备。我不是来救你的，是来查案的。",
            "TRANSITION: 录音笔的红灯亮起。",
            "END SCENE",
        ]
    )

    scene = _build_scene_from_screenplay_text(text, scene_plan, chapter, story_bible)

    assert scene.scene_id == "s002"
    assert scene.title == "旧仓库灯光"
    assert [(beat.type, beat.speaker_ref, beat.text) for beat in scene.beats] == [
        ("action", None, "昏黄灯泡摇晃，文件散落在木箱上。"),
        ("dialogue", "c002", "放下戒备。我不是来救你的，是来查案的。"),
    ]


def test_qwen_scene_stream_generates_text_then_parses_to_scene(monkeypatch) -> None:
    scene_plan = ScenePlan(
        scene_id="s002",
        act_id="main",
        title="旧仓库灯光",
        objective="沈青交出录音笔",
        chapter_refs=["ch002"],
        conflict="沈青不确定林然是否值得信任",
        notes="废弃仓库",
    )
    story_bible = StoryBible(
        logline="调查失踪真相。",
        synopsis="林然和沈青在旧仓库交换线索。",
        characters=[
            CharacterCard(character_id="c001", name="林然", role="protagonist"),
            CharacterCard(character_id="c002", name="沈青", role="supporting"),
        ],
    )
    chapter = ParsedChapter(
        chapter_id="ch002",
        title="旧仓库",
        raw_text="沈青告诉林然她也在查林薇。",
        raw_text_ref="memory://ch002",
    )
    request = AdaptationRequest(
        project_id="demo",
        title="老街回声",
        original_novel_title="老街回声",
        original_author="tester",
        provider="qwen",
    )

    def fake_chat_text_stream(self, model, system, user, temperature, on_delta=None):
        assert "单场景纯文本剧本" in system
        assert "SCENE s002" in user
        text = "\n".join(
            [
                "SCENE s002 | 旧仓库灯光",
                "TIME: night",
                "SUMMARY: 沈青在旧仓库交出关键录音。",
                "ACTION: 昏黄灯泡摇晃，文件散落在木箱上。",
                "c002: 放下戒备。我不是来救你的，是来查案的。",
                "TRANSITION: 录音笔的红灯亮起。",
                "END SCENE",
            ]
        )
        if on_delta is not None:
            on_delta(text, text)
        return text

    monkeypatch.setattr(QwenAIClient, "_chat_text_stream", fake_chat_text_stream)

    scene = QwenAIClient(QwenSettings(api_key="demo-key")).generate_scene_stream(scene_plan, story_bible, chapter, request)

    assert [(beat.type, beat.speaker_ref, beat.text) for beat in scene.beats] == [
        ("action", None, "昏黄灯泡摇晃，文件散落在木箱上。"),
        ("dialogue", "c002", "放下戒备。我不是来救你的，是来查案的。"),
    ]
