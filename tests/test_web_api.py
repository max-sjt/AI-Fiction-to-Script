from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from ai_fiction_to_script import __version__
from ai_fiction_to_script.models.runtime import AdaptationRequest
from ai_fiction_to_script.pipeline.engine import AdaptationEngine
from ai_fiction_to_script.services.ai_client import MockAIClient
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore
from ai_fiction_to_script.web.server import create_server


def sample_novel_path() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "sample_novel.txt"


def seed_project(version_root: Path) -> None:
    engine = AdaptationEngine(
        parser=ChapterParser(),
        ai_client=MockAIClient(),
        quality_checker=QualityChecker(),
        version_store=VersionStore(version_root),
    )
    request = AdaptationRequest(
        project_id="web-demo",
        title="老街回声",
        original_novel_title="老街回声",
        original_author="测试作者",
    )
    engine.run(sample_novel_path(), request, note="seed")


def api_request(base_url: str, path: str, method: str = "GET", payload: dict | None = None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(f"{base_url}{path}", data=data, method=method, headers=headers)
    with urlopen(request) as response:  # noqa: S310
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def start_server(version_root: Path):
    server = create_server("127.0.0.1", 0, version_root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    return server, thread, base_url


def stop_server(server, thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_web_server_lists_projects_and_serves_html(tmp_path) -> None:
    version_root = tmp_path / ".novel2script"
    seed_project(version_root)
    server, thread, base_url = start_server(version_root)
    try:
        projects = api_request(base_url, "/api/projects")
        assert projects["ok"] is True
        assert projects["data"]["projects"][0]["project_id"] == "web-demo"

        with urlopen(f"{base_url}/") as response:  # noqa: S310
            html = response.read().decode("utf-8")
            cache_control = response.headers.get("Cache-Control")
        assert "Qwen 剧本生成工作台" in html
        assert 'id="languageSelect"' in html
        assert 'id="buildBadge"' in html
        assert "中文" in html
        assert cache_control == "no-store, max-age=0"
    finally:
        stop_server(server, thread)


def test_web_server_health_includes_version_and_start_time(tmp_path) -> None:
    version_root = tmp_path / ".novel2script"
    seed_project(version_root)
    server, thread, base_url = start_server(version_root)
    try:
        health = api_request(base_url, "/api/health")
        assert health["ok"] is True
        assert health["data"]["status"] == "healthy"
        assert health["data"]["version"] == __version__
        assert "T" in health["data"]["server_started_at"]
    finally:
        stop_server(server, thread)


def test_web_server_can_save_edit_and_regenerate_scene(tmp_path) -> None:
    version_root = tmp_path / ".novel2script"
    seed_project(version_root)
    server, thread, base_url = start_server(version_root)
    try:
        version_payload = api_request(base_url, "/api/projects/web-demo/versions/v0001")
        yaml_text = version_payload["data"]["yaml_text"] + "\n"

        saved = api_request(
            base_url,
            "/api/projects/web-demo/versions/v0001/save",
            method="POST",
            payload={"yaml_text": yaml_text, "note": "edited in web"},
        )
        assert saved["ok"] is True
        assert saved["data"]["version"]["version_id"] == "v0002"

        diff_payload = api_request(base_url, "/api/projects/web-demo/diff?from=v0001&to=v0002")
        assert diff_payload["ok"] is True
        assert "screenplay.yaml" in diff_payload["data"]["diff"]

        regenerated = api_request(
            base_url,
            "/api/projects/web-demo/versions/v0002/regenerate-scene",
            method="POST",
            payload={
                "scene_id": "s001",
                "instruction": "Raise the protagonist's urgency.",
                "tone": "dark",
                "note": "web scene pass",
            },
        )
        assert regenerated["ok"] is True
        assert regenerated["data"]["version"]["version_id"] == "v0003"
        assert regenerated["data"]["document"]["meta"]["tone"] == "dark"
        assert regenerated["data"]["scene_comparison"]["scene_id"] == "s001"
        assert regenerated["data"]["scene_comparison"]["instruction"] == "Raise the protagonist's urgency."
        assert regenerated["data"]["scene_comparison"]["before"]["rendered"]
        assert regenerated["data"]["scene_comparison"]["after"]["rendered"]
    finally:
        stop_server(server, thread)


def test_web_server_passes_regenerate_overrides(tmp_path) -> None:
    version_root = tmp_path / ".novel2script"
    server, thread, base_url = start_server(version_root)
    captured: dict[str, str] = {}

    def fake_regenerate_scene(
        project_id: str,
        version_id: str,
        scene_id: str,
        instruction: str = "",
        provider_override: str = "",
        api_key: str = "",
        tone_override: str = "",
        note: str = "",
    ) -> dict:
        captured.update(
            {
                "project_id": project_id,
                "version_id": version_id,
                "scene_id": scene_id,
                "instruction": instruction,
                "provider_override": provider_override,
                "api_key": api_key,
                "tone_override": tone_override,
                "note": note,
            }
        )
        return {"version": {"version_id": "v9999"}}

    server.RequestHandlerClass.service.regenerate_scene = fake_regenerate_scene
    try:
        response = api_request(
            base_url,
            "/api/projects/demo-project/versions/v0001/regenerate-scene",
            method="POST",
            payload={
                "scene_id": "s007",
                "instruction": "Make it darker.",
                "provider": "qwen",
                "api_key": "demo-key",
                "tone": "dark",
                "note": "web override pass",
            },
        )
        assert response["ok"] is True
        assert response["data"]["version"]["version_id"] == "v9999"
        assert captured == {
            "project_id": "demo-project",
            "version_id": "v0001",
            "scene_id": "s007",
            "instruction": "Make it darker.",
            "provider_override": "qwen",
            "api_key": "demo-key",
            "tone_override": "dark",
            "note": "web override pass",
        }
    finally:
        stop_server(server, thread)
