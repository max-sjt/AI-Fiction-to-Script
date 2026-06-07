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
        assert 'id="resetProjectsButton"' in html
        assert 'id="uploadYamlFile"' in html
        assert 'id="regenerateFromYamlButton"' in html
        assert "中文" in html
        assert cache_control == "no-store, max-age=0"
    finally:
        stop_server(server, thread)


def test_web_server_serves_frontend_yaml_workflow_wiring(tmp_path) -> None:
    version_root = tmp_path / ".novel2script"
    seed_project(version_root)
    server, thread, base_url = start_server(version_root)
    try:
        with urlopen(f"{base_url}/assets/app.js") as response:  # noqa: S310
            app_js = response.read().decode("utf-8")
        assert "uploadYamlFile" in app_js
        assert "regenerateFromYamlButton" in app_js
        assert "/api/regenerate-from-yaml-async" in app_js
        assert "/export-yaml" in app_js
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
        assert health["data"]["cache_backend"] in {"disabled", "redis"}
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


def test_web_server_supports_async_adapt_and_task_polling(tmp_path) -> None:
    version_root = tmp_path / ".novel2script"
    server, thread, base_url = start_server(version_root)

    def fake_start_adapt_async(payload: dict) -> dict:
        return {
            "preview": {
                "project_id": "async-demo",
                "version": {"version_id": "v0001"},
            },
            "task": {
                "task_id": "task-123",
                "kind": "adapt",
                "project_id": "async-demo",
                "preview_version_id": "v0001",
                "status": "running",
                "final_version_id": "",
                "error": "",
                "created_at": "2026-06-06T00:00:00+00:00",
                "updated_at": "2026-06-06T00:00:00+00:00",
                "result": None,
            },
        }

    def fake_get_task_status(task_id: str) -> dict:
        assert task_id == "task-123"
        return {
            "task_id": "task-123",
            "kind": "adapt",
            "project_id": "async-demo",
            "preview_version_id": "v0001",
            "status": "completed",
            "final_version_id": "v0002",
            "error": "",
            "created_at": "2026-06-06T00:00:00+00:00",
            "updated_at": "2026-06-06T00:00:03+00:00",
            "result": {
                "project_id": "async-demo",
                "version": {"version_id": "v0002"},
            },
        }

    server.RequestHandlerClass.service.start_adapt_async = fake_start_adapt_async
    server.RequestHandlerClass.service.get_task_status = fake_get_task_status
    try:
        created = api_request(
            base_url,
            "/api/adapt-async",
            method="POST",
            payload={"title": "异步测试"},
        )
        assert created["ok"] is True
        assert created["data"]["task"]["task_id"] == "task-123"

        polled = api_request(base_url, "/api/tasks/task-123")
        assert polled["ok"] is True
        assert polled["data"]["status"] == "completed"
        assert polled["data"]["final_version_id"] == "v0002"
    finally:
        stop_server(server, thread)


def test_web_server_exports_compact_yaml_bundle(tmp_path) -> None:
    version_root = tmp_path / ".novel2script"
    seed_project(version_root)
    server, thread, base_url = start_server(version_root)
    try:
        exported = api_request(base_url, "/api/projects/web-demo/versions/v0001/export-yaml")
        assert exported["ok"] is True
        yaml_text = exported["data"]["yaml_text"]
        assert "story_bible:" not in yaml_text
        assert "outline:" not in yaml_text
        assert "text:" in yaml_text
        assert "scenes:" in yaml_text
    finally:
        stop_server(server, thread)


def test_web_server_supports_async_regeneration_from_yaml_bundle(tmp_path) -> None:
    version_root = tmp_path / ".novel2script"
    server, thread, base_url = start_server(version_root)

    def fake_start_regenerate_from_yaml_async(payload: dict) -> dict:
        assert "yaml_text" in payload
        return {
            "preview": {
                "project_id": "yaml-demo",
                "version": {"version_id": "preview"},
            },
            "task": {
                "task_id": "task-yaml-123",
                "kind": "adapt",
                "project_id": "yaml-demo",
                "preview_version_id": "preview",
                "status": "running",
                "final_version_id": "",
                "error": "",
                "created_at": "2026-06-06T00:00:00+00:00",
                "updated_at": "2026-06-06T00:00:00+00:00",
                "result": None,
            },
        }

    server.RequestHandlerClass.service.start_regenerate_from_yaml_async = fake_start_regenerate_from_yaml_async
    try:
        response = api_request(
            base_url,
            "/api/regenerate-from-yaml-async",
            method="POST",
            payload={"yaml_text": "schema_version: compact-1.0"},
        )
        assert response["ok"] is True
        assert response["data"]["task"]["task_id"] == "task-yaml-123"
        assert response["data"]["preview"]["version"]["version_id"] == "preview"
    finally:
        stop_server(server, thread)


def test_web_server_can_delete_version_and_remove_files(tmp_path) -> None:
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
        assert (version_root / "web-demo" / "versions" / "v0001").exists()
        assert (version_root / "web-demo" / "versions" / "v0002").exists()

        deleted = api_request(
            base_url,
            "/api/projects/web-demo/versions/v0001/delete",
            method="DELETE",
        )
        assert deleted["ok"] is True
        assert deleted["data"]["project_exists"] is True
        assert [item["version_id"] for item in deleted["data"]["versions"]] == ["v0002"]
        assert not (version_root / "web-demo" / "versions" / "v0001").exists()
        assert (version_root / "web-demo" / "versions" / "v0002").exists()
    finally:
        stop_server(server, thread)


def test_web_server_delete_last_version_removes_project(tmp_path) -> None:
    version_root = tmp_path / ".novel2script"
    seed_project(version_root)
    server, thread, base_url = start_server(version_root)
    try:
        deleted = api_request(
            base_url,
            "/api/projects/web-demo/versions/v0001/delete",
            method="DELETE",
        )
        assert deleted["ok"] is True
        assert deleted["data"]["project_exists"] is False
        assert deleted["data"]["versions"] == []

        projects = api_request(base_url, "/api/projects")
        assert projects["ok"] is True
        assert projects["data"]["projects"] == []
        assert not (version_root / "web-demo").exists()
    finally:
        stop_server(server, thread)

