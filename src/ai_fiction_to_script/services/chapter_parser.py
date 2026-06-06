from __future__ import annotations

import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from ai_fiction_to_script.models.runtime import ParsedChapter, ParsedExcerpt
from ai_fiction_to_script.utils.ids import make_id
from ai_fiction_to_script.utils.text import make_excerpt_map, normalize_text


CHAPTER_HEADING_RE = re.compile(
    r"^\s*(第[0-9一二三四五六七八九十百千万零两]+[章节回卷部篇集].*|Chapter\s+\d+.*|CHAPTER\s+\d+.*|##\s+.+)$",
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
            [item for item in path.iterdir() if item.is_file() and item.suffix.lower() in {".txt", ".md", ".doc", ".docx"}],
            key=lambda item: item.name,
        )
        for index, file_path in enumerate(files, start=1):
            raw_text = self._read_supported_text(file_path)
            title = file_path.stem
            chapters.append(self._build_chapter(make_id("ch", index, width=2), title, raw_text, file_path))
        return chapters

    def _parse_file(self, path: Path) -> list[ParsedChapter]:
        raw_text = self._read_supported_text(path)
        matches = list(CHAPTER_HEADING_RE.finditer(raw_text))
        if len(matches) < 3:
            inferred = self._infer_chapters_from_blocks(raw_text, path)
            if len(inferred) >= 3:
                return inferred
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

    def _infer_chapters_from_blocks(self, raw_text: str, source_path: Path) -> list[ParsedChapter]:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", raw_text) if block.strip()]
        substantial_blocks = [block for block in blocks if len(block.replace("\n", "").strip()) >= 30]
        if len(substantial_blocks) < 3:
            return []

        chapters: list[ParsedChapter] = []
        for index, block in enumerate(substantial_blocks, start=1):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            title_candidate = lines[0]
            if self._looks_like_heading(title_candidate):
                title = title_candidate
                body = "\n".join(lines[1:]).strip()
            else:
                title = f"第{index}章（自动拆分）"
                body = "\n".join(lines).strip()
            if not body:
                continue
            chapters.append(self._build_chapter(make_id("ch", index, width=2), title, body, source_path))
        return chapters

    def _looks_like_heading(self, line: str) -> bool:
        if CHAPTER_HEADING_RE.match(line):
            return True
        if len(line) > 24:
            return False
        if re.match(r"^(序章|楔子|引子|终章|尾声)$", line):
            return True
        return bool(re.match(r"^(第?[0-9一二三四五六七八九十百千万零两]+[章节回卷部篇集幕折话])", line))

    def _read_supported_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return normalize_text(path.read_text(encoding="utf-8"))
        if suffix == ".docx":
            return self._read_docx_text(path)
        if suffix == ".doc":
            return self._read_doc_text(path)
        raise ValueError(f"Unsupported file type: {path.suffix}")

    def _read_docx_text(self, path: Path) -> str:
        try:
            with zipfile.ZipFile(path) as archive:
                xml_content = archive.read("word/document.xml")
        except KeyError as exc:
            raise ValueError(f"Invalid docx file structure: {path}") from exc

        root = ET.fromstring(xml_content)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", namespace):
            texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
            line = "".join(texts).strip()
            if line:
                paragraphs.append(line)
        return normalize_text("\n\n".join(paragraphs))

    def _read_doc_text(self, path: Path) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            output_path = Path(temp_file.name)
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$word = New-Object -ComObject Word.Application; "
                "$word.Visible = $false; "
                "$doc = $word.Documents.Open('" + str(path).replace("'", "''") + "'); "
                "$doc.SaveAs([ref]'" + str(output_path).replace("'", "''") + "', [ref]2); "
                "$doc.Close(); "
                "$word.Quit();"
            ),
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=90)
            if result.returncode != 0 or not output_path.exists():
                raise ValueError(
                    "Unable to read .doc file automatically. Please convert it to .docx or .txt, or ensure Microsoft Word is installed."
                )
            return normalize_text(output_path.read_text(encoding="utf-8", errors="ignore"))
        finally:
            if output_path.exists():
                output_path.unlink(missing_ok=True)
