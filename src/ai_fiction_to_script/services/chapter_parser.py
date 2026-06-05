from __future__ import annotations

import re
from pathlib import Path

from ai_fiction_to_script.models.runtime import ParsedChapter, ParsedExcerpt
from ai_fiction_to_script.utils.ids import make_id
from ai_fiction_to_script.utils.text import make_excerpt_map, normalize_text


CHAPTER_HEADING_RE = re.compile(
    r"^(第[0-9一二三四五六七八九十百千万零两]+[章回节卷部篇集].*|Chapter\s+\d+.*|CHAPTER\s+\d+.*|##\s+.+)$",
    re.MULTILINE,
)


class ChapterParser:
    def parse(self, input_path: str | Path) -> list[ParsedChapter]:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input path not found: {path}")
        if path.is_dir():
            return self._parse_directory(path)
        return self._parse_file(path)

    def _parse_directory(self, path: Path) -> list[ParsedChapter]:
        chapters: list[ParsedChapter] = []
        files = sorted(
            [item for item in path.iterdir() if item.is_file() and item.suffix.lower() in {".txt", ".md"}],
            key=lambda item: item.name,
        )
        for index, file_path in enumerate(files, start=1):
            raw_text = normalize_text(file_path.read_text(encoding="utf-8"))
            title = file_path.stem
            chapters.append(self._build_chapter(make_id("ch", index, width=2), title, raw_text, file_path))
        return chapters

    def _parse_file(self, path: Path) -> list[ParsedChapter]:
        raw_text = normalize_text(path.read_text(encoding="utf-8"))
        matches = list(CHAPTER_HEADING_RE.finditer(raw_text))
        if not matches:
            return [self._build_chapter(make_id("ch", 1, width=2), path.stem, raw_text, path)]
        chapters: list[ParsedChapter] = []
        for index, match in enumerate(matches, start=1):
            start = match.start()
            end = matches[index].start() if index < len(matches) else len(raw_text)
            block = raw_text[start:end].strip()
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            title = lines[0]
            body = "\n".join(lines[1:]).strip()
            chapters.append(self._build_chapter(make_id("ch", index, width=2), title, body, path))
        return chapters

    def _build_chapter(self, chapter_id: str, title: str, body: str, source_path: Path) -> ParsedChapter:
        excerpts = [
            ParsedExcerpt(excerpt_id=excerpt_id, text=text)
            for excerpt_id, text in make_excerpt_map(body)
        ]
        return ParsedChapter(
            chapter_id=chapter_id,
            title=title,
            raw_text=body,
            raw_text_ref=str(source_path),
            excerpts=excerpts,
        )

