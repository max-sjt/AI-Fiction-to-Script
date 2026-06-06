from __future__ import annotations

from ai_fiction_to_script.services.chapter_parser import ChapterParser


def test_parser_can_infer_chapters_from_pasted_text_blocks(tmp_path) -> None:
    novel_path = tmp_path / "pasted.txt"
    novel_path.write_text(
        "\n\n".join(
            [
                "林然在雨夜里收到一条匿名短信，要求他去旧仓库。老板提醒他那里危险，但他还是决定出门。",
                "旧仓库里亮着灯，沈青正在翻找文件。她递来录音笔，让林然第一次意识到姐姐的失踪不是意外。",
                "天台上，陈默提出用录音笔交换林薇的下落。林然必须在真相和姐姐安全之间做选择。",
            ]
        ),
        encoding="utf-8",
    )

    chapters = ChapterParser().parse(novel_path)

    assert len(chapters) == 3
    assert chapters[0].title == "第1章（自动拆分）"
    assert chapters[1].raw_text.startswith("旧仓库里亮着灯")


def test_parser_accepts_indented_chapter_headings(tmp_path) -> None:
    novel_path = tmp_path / "indented.txt"
    novel_path.write_text(
        "  第一章 雨夜来信\n林然收到匿名短信。\n\n  第二章 旧仓库灯光\n沈青递来录音笔。\n\n  第三章 屋顶对峙\n陈默提出交换条件。",
        encoding="utf-8",
    )

    chapters = ChapterParser().parse(novel_path)

    assert len(chapters) == 3
    assert chapters[0].title.strip() == "第一章 雨夜来信"
