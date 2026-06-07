from __future__ import annotations

from ai_fiction_to_script.utils.text import extract_character_candidates, extract_location_candidates


def test_extract_candidates_prefers_named_people_and_clean_locations() -> None:
    text = (
        "林然在老街咖啡馆守到打烊。"
        "姐姐林薇失踪已经七天，他收到短信：如果想知道真相，就去旧仓库。"
        "沈青站在货架边。"
        "陈默承认自己替那家公司传过话。"
        "循着录音里的地址，林然和沈青赶到旧城区天台。"
    )

    characters = extract_character_candidates(text)
    locations = extract_location_candidates(text)

    assert characters[:4] == ["林然", "林薇", "沈青", "陈默"]
    assert "如果想知" not in characters
    assert locations[:3] == ["老街咖啡馆", "旧仓库", "旧城区天台"]
    assert all(not item.startswith(("林然在", "就去", "林然和沈青赶到")) for item in locations)


def test_extract_candidates_filters_sentence_fragments_from_regeneration_source() -> None:
    text = (
        "林然在老街咖啡馆守到打烊，窗外的雨把街灯晕成一片模糊的光。"
        "姐姐林薇失踪已经七天，他却只收到一条没有署名的短信：如果想知道真相，就去旧仓库。"
        "林然本想删掉短信，但想到母亲整夜不睡，他还是把手机攥进掌心。"
        "老板周叔提醒他，旧仓库那一带早就废弃，深夜过去不安全。"
        "林然嘴上说知道，心里却更确定那条短信不是恶作剧。"
        "旧仓库在河堤后面，铁门半掩，里面居然还亮着昏黄的灯。"
        "林然刚踏进去，就看见调查记者沈青站在货架边翻找资料。"
        "陈默承认自己替那家公司传过话。"
        "循着录音里的地址，林然和沈青赶到旧城区天台。"
        "霓虹灯从楼缝里切进来，把每个人的脸都照得忽明忽暗。"
    )

    characters = extract_character_candidates(text, limit=8)
    locations = extract_location_candidates(text, limit=8)

    assert "林然" in characters
    assert "林薇" in characters
    assert "沈青" in characters
    assert "陈默" in characters
    assert not {"却只", "林然本", "整夜", "林然嘴上", "嘴上", "说知"} & set(characters)
    assert "老街咖啡馆" in locations
    assert "旧仓库" in locations
    assert "旧城区天台" in locations
    assert not {"窗外的雨把街", "旧仓库在河堤", "霓虹灯从楼", "玻璃"} & set(locations)
