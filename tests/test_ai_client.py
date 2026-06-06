from __future__ import annotations

from ai_fiction_to_script.services.ai_client import (
    _normalize_beat_id,
    _normalize_beat_type,
    _normalize_named_mapping_list,
    _normalize_relation_list,
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
