from __future__ import annotations

import json

from ai_fiction_to_script.models.schema import Beat, CharacterCard, LocationCard, Scene, SourceRef, StoryBible
from ai_fiction_to_script.settings import QwenSettings
from ai_fiction_to_script.services.ai_client import (
    QwenAIClient,
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
