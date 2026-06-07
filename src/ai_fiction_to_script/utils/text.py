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
        re.compile(r"(?:店主|记者|男人|女人|少年|少女|老人|老妇人|先生|女士)?([\u4e00-\u9fff]{2,4})(?=说|问|答|喊|叫|道|想|看|听|转身|抬头|低头|走向|来到)"),
        re.compile(r"([\u4e00-\u9fff]{2,4})(?=正|正在|忽然|缓缓|猛地|突然|站在|坐在)"),
    ]
    results: list[str] = []
    for pattern in patterns:
        results.extend(match.group(1) for match in pattern.finditer(text))
    if not results:
        results = extract_candidate_terms(text, limit=limit)
    deduped: list[str] = []
    for item in results:
        cleaned = item.strip()
        if cleaned and cleaned not in STOP_TERMS and cleaned not in deduped:
            deduped.append(cleaned)
        if len(deduped) >= limit:
            break
    return deduped


def extract_location_candidates(text: str, limit: int = 4) -> list[str]:
    patterns = [
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
        cleaned = item[:12].strip()
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
        if len(deduped) >= limit:
            break
    return deduped


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_json_object(text: str) -> dict:
    cleaned = strip_code_fences(text)
    return json.loads(cleaned)
