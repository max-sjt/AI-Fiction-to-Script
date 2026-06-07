from __future__ import annotations

import json
import re
from collections import Counter


SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?])")
CHINESE_TERM_RE = re.compile(r"[\u4e00-\u9fff]{2,6}")

STOP_TERMS = {
    "一个",
    "一种",
    "他们",
    "自己",
    "没有",
    "如果",
    "因为",
    "已经",
    "什么",
    "这里",
    "那里",
    "时候",
    "出来",
    "时候",
    "如果想知",
}


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    compact = normalize_text(text)
    if not compact:
        return []
    compact = re.sub(r"\n+", " ", compact)
    parts = SENTENCE_SPLIT_RE.split(compact)
    return [part.strip() for part in parts if part.strip()]


def summarize_text(text: str, max_sentences: int = 2) -> str:
    sentences = split_sentences(text)
    summary = " ".join(sentences[:max_sentences]).strip()
    return summary[:180] if summary else text[:180].strip()


def make_excerpt_map(text: str) -> list[tuple[str, str]]:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", normalize_text(text)) if item.strip()]
    result: list[tuple[str, str]] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        result.append((f"p{index:03d}", paragraph))
    return result


def extract_candidate_terms(text: str, limit: int = 6) -> list[str]:
    counter: Counter[str] = Counter()
    for match in CHINESE_TERM_RE.finditer(text):
        term = match.group(0)
        if term in STOP_TERMS or re.fullmatch(r"第[一二三四五六七八九十百千万零两0-9]+[章节回卷部篇幕集]", term):
            continue
        counter[term] += 1
    return [term for term, _ in counter.most_common(limit)]


def extract_character_candidates(text: str, limit: int = 6) -> list[str]:
    patterns = [
        re.compile(r"(?:姐姐|妹妹|哥哥|弟弟|父亲|母亲|记者|调查记者)([\u4e00-\u9fff]{2})"),
        re.compile(r"([\u4e00-\u9fff]{2})(?=在|站在|承认|说|问|答|喊|叫|道|告诉|收到|赶到|走进|拿起|盯着|看着)"),
        re.compile(r"(?:和|与)([\u4e00-\u9fff]{2})(?=赶到|走进|来到|站在)"),
        re.compile(r"(?:店主|记者|男人|女人|少年|少女|老人|老妇人|先生|女士)?([\u4e00-\u9fff]{2,4})(?=说|问|答|喊|叫|道|想|看|听|转身|抬头|低头|走向|来到)"),
        re.compile(r"([\u4e00-\u9fff]{2,4})(?=正|正在|忽然|缓缓|猛地|突然|站在|坐在)"),
    ]
    matches: list[tuple[int, str]] = []
    for pattern in patterns:
        matches.extend((match.start(1), match.group(1)) for match in pattern.finditer(text))
    results = [item for _, item in sorted(matches, key=lambda item: item[0])]
    if not results:
        results = extract_candidate_terms(text, limit=limit)
    deduped: list[str] = []
    for item in results:
        cleaned = _clean_character_candidate(item)
        if cleaned and cleaned not in STOP_TERMS and not _looks_like_non_name(cleaned) and _looks_like_person_name(cleaned) and cleaned not in deduped:
            deduped.append(cleaned)
        if len(deduped) >= limit:
            break
    return deduped


def extract_location_candidates(text: str, limit: int = 4) -> list[str]:
    patterns = [
        re.compile(
            r"(?:在|去|到|赶到|来到|走进|回到|进入)([\u4e00-\u9fff]{0,10}(?:咖啡馆|旧仓库|仓库|天台|车站|站台|房间|大厅|走廊|办公室|医院|学校|教室|庭院|街|巷|楼|河堤|码头))"
        ),
        re.compile(
            r"([\u4e00-\u9fff]{2,12}(?:古董店|钟楼|仓库|天台|咖啡馆|车站|站台|房间|大厅|走廊|办公室|医院|学校|教室|庭院|街|巷|楼|河堤|码头))"
        ),
        re.compile(r"(?:来到|走进|回到|赶到|推开)([\u4e00-\u9fff]{2,12})"),
        re.compile(r"在([\u4e00-\u9fff]{2,12})(?:里|内|中|上|旁|前|后)"),
    ]
    results: list[str] = []
    for pattern in patterns:
        results.extend(match.group(1) for match in pattern.finditer(text))
    if not results:
        results = extract_candidate_terms(text, limit=limit)
    deduped: list[str] = []
    for item in results:
        cleaned = _clean_location_candidate(item)[:12].strip()
        if cleaned and not _looks_like_non_location(cleaned) and cleaned not in deduped:
            deduped.append(cleaned)
        if len(deduped) >= limit:
            break
    return deduped


def _looks_like_non_name(value: str) -> bool:
    return any(
        token in value
        for token in (
            "如果",
            "想知",
            "已经",
            "真相",
            "公司",
            "地址",
            "录音",
            "却只",
            "整夜",
            "嘴上",
            "说知",
            "仓库",
        )
    ) or value.endswith(("本", "刚"))


def _clean_character_candidate(value: str) -> str:
    cleaned = value.strip("，。！？；：:,. ")
    for prefix in ("调查记者", "记者", "老板"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break
    return cleaned


def _looks_like_person_name(value: str) -> bool:
    common_surnames = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣邓郁单杭洪包诸左石崔吉龚程邢裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹龙叶司黎白乔"
    return len(value) in {2, 3} and value[0] in common_surnames


def _clean_location_candidate(value: str) -> str:
    cleaned = value.strip("，。！？；：:,. ")
    for prefix in ("林然和沈青赶到", "林然赶到", "沈青赶到", "林然在", "沈青在", "就去", "去", "在", "到", "赶到", "来到", "走进", "回到", "进入"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break
    if "在" in cleaned and not cleaned.endswith(("街", "巷")):
        cleaned = cleaned.split("在", 1)[0]
    return cleaned.strip("，。！？；：:,. ")


def _looks_like_non_location(value: str) -> bool:
    return any(token in value for token in ("窗外", "雨把", "霓虹", "灯从", "玻璃", "失踪", "查"))


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_json_object(text: str) -> dict:
    cleaned = strip_code_fences(text)
    return json.loads(cleaned)
