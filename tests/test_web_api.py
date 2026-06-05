from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

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
        assert "Screenplay Workbench" in html
        assert 'id="languageSelect"' in html
        assert "中文" in html
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
                "note": "web scene pass",
            },
        )
        assert regenerated["ok"] is True
        assert regenerated["data"]["version"]["version_id"] == "v0003"
    finally:
        stop_server(server, thread)
