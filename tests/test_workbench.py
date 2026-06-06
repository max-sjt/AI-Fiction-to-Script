from __future__ import annotations

from pathlib import Path

from ai_fiction_to_script.models.runtime import ModelRouting
from ai_fiction_to_script.services.ai_client import HybridAIClient
from ai_fiction_to_script.services.workbench import WorkbenchService


def sample_novel_text() -> str:
    return (Path(__file__).resolve().parents[1] / "examples" / "sample_novel.txt").read_text(encoding="utf-8")


def test_workbench_uses_unicode_title_as_project_id(tmp_path) -> None:
    payload = WorkbenchService(tmp_path / ".novel2script").adapt(
        {
            "title": "中文标题项目",
            "original_author": "测试作者",
            "original_title": "中文标题原著",
            "script_type": "tv_drama",
            "tone": "balanced",
            "genre": "悬疑",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )

    assert payload["project_id"] == "中文标题项目"


def test_workbench_can_generate_from_single_chapter_text(tmp_path) -> None:
    payload = WorkbenchService(tmp_path / ".novel2script").adapt(
        {
            "title": "单章项目",
            "original_author": "测试作者",
            "original_title": "单章原著",
            "script_type": "film",
            "tone": "serious",
            "genre": "悬疑",
            "novel_text": "第三章 屋顶对峙\n\n循着录音里的地址，林然和沈青赶到旧城区天台。风很大，霓虹灯从楼缝里切进来，把每个人的脸都照得忽明忽暗。\n\n陈默提出交换条件：只要林然交出录音笔，他就带他们去见林薇。林然意识到，真正的选择不是相信谁，而是要不要拿姐姐的安全赌一次真相。",
            "provider": "mock",
        }
    )

    assert payload["version"]["version_id"] == "v0001"
    assert payload["document"]["source"]["chapter_count"] == 1
    assert payload["scene_options"]


def test_workbench_uses_faster_qwen_routing_for_web_requests(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")

    routing = service._web_model_routing("qwen")

    assert isinstance(routing, ModelRouting)
    assert routing.summary_model == "qwen3.6-flash"
    assert routing.planning_model == "qwen3.6-flash"
    assert routing.generation_model == "qwen3.6-flash"
    assert routing.validation_model == "qwen3.6-flash"


def test_workbench_uses_hybrid_qwen_client_for_web_speed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "demo-key")
    service = WorkbenchService(tmp_path / ".novel2script")

    client = service._build_ai_client("qwen")

    assert isinstance(client, HybridAIClient)
