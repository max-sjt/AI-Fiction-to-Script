from __future__ import annotations

import json
import mimetypes
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from ai_fiction_to_script import __version__
from ai_fiction_to_script.services.cache_store import build_cache_store
from ai_fiction_to_script.services.workbench import WorkbenchService
from ai_fiction_to_script.settings import WebCacheSettings


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class WorkbenchRequestHandler(BaseHTTPRequestHandler):
    service: WorkbenchService
    server_started_at: str = ""
    cache_backend: str = "disabled"

    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._serve_static("index.html")
                return
            if parsed.path.startswith("/assets/"):
                self._serve_static(parsed.path.removeprefix("/assets/"))
                return
            if parsed.path == "/api/health":
                self._send_json(
                    {
                        "ok": True,
                        "data": {
                            "status": "healthy",
                            "version": __version__,
                            "server_started_at": self.server_started_at,
                            "cache_backend": self.cache_backend,
                        },
                    }
                )
                return
            if parsed.path == "/api/projects":
                self._send_json({"ok": True, "data": {"projects": self.service.list_projects()}})
                return
            if len(self._path_parts(parsed.path)) == 3 and self._path_parts(parsed.path)[:2] == ["api", "tasks"]:
                task_id = self._path_parts(parsed.path)[2]
                self._send_json({"ok": True, "data": self.service.get_task_status(task_id)})
                return
            if len(self._path_parts(parsed.path)) == 4 and self._path_parts(parsed.path)[:2] == ["api", "tasks"] and self._path_parts(parsed.path)[3] == "stream":
                task_id = self._path_parts(parsed.path)[2]
                self._stream_task(task_id)
                return

            parts = self._path_parts(parsed.path)
            if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "versions":
                project_id = parts[2]
                self._send_json({"ok": True, "data": {"project_id": project_id, "versions": self.service.list_versions(project_id)}})
                return
            if len(parts) == 5 and parts[:2] == ["api", "projects"] and parts[3] == "versions":
                project_id = parts[2]
                version_id = parts[4]
                self._send_json({"ok": True, "data": self.service.get_version_payload(project_id, version_id)})
                return
            if len(parts) == 6 and parts[:2] == ["api", "projects"] and parts[3] == "versions" and parts[5] == "export-yaml":
                project_id = parts[2]
                version_id = parts[4]
                self._send_json(
                    {"ok": True, "data": {"project_id": project_id, "version_id": version_id, "yaml_text": self.service.export_version_yaml(project_id, version_id)}}
                )
                return
            if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "diff":
                project_id = parts[2]
                query = parse_qs(parsed.query)
                version_a = query.get("from", [""])[0]
                version_b = query.get("to", [""])[0]
                if not version_a or not version_b:
                    raise ApiError(HTTPStatus.BAD_REQUEST, "Both 'from' and 'to' query parameters are required.")
                self._send_json({"ok": True, "data": self.service.diff_versions(project_id, version_a, version_b)})
                return

            raise ApiError(HTTPStatus.NOT_FOUND, f"Route not found: {parsed.path}")
        except ApiError as exc:
            self._send_json({"ok": False, "error": exc.message}, status=exc.status)
        except FileNotFoundError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_DELETE(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            parts = self._path_parts(parsed.path)
            if len(parts) == 6 and parts[:2] == ["api", "projects"] and parts[3] == "versions" and parts[5] == "delete":
                project_id = parts[2]
                version_id = parts[4]
                self._send_json(
                    {"ok": True, "data": self.service.delete_version(project_id, version_id)},
                    status=HTTPStatus.OK,
                )
                return

            raise ApiError(HTTPStatus.NOT_FOUND, f"Route not found: {parsed.path}")
        except ApiError as exc:
            self._send_json({"ok": False, "error": exc.message}, status=exc.status)
        except FileNotFoundError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            payload = self._read_json_body()

            if parsed.path == "/api/adapt":
                self._send_json({"ok": True, "data": self.service.adapt(payload)}, status=HTTPStatus.CREATED)
                return
            if parsed.path == "/api/adapt-async":
                self._send_json({"ok": True, "data": self.service.start_adapt_async(payload)}, status=HTTPStatus.CREATED)
                return
            if parsed.path == "/api/regenerate-from-yaml-async":
                self._send_json({"ok": True, "data": self.service.start_regenerate_from_yaml_async(payload)}, status=HTTPStatus.CREATED)
                return

            parts = self._path_parts(parsed.path)
            if len(parts) == 6 and parts[:2] == ["api", "projects"] and parts[3] == "versions" and parts[5] == "save":
                project_id = parts[2]
                version_id = parts[4]
                yaml_text = payload.get("yaml_text", "")
                note = payload.get("note", "")
                self._send_json(
                    {"ok": True, "data": self.service.save_edited_yaml(project_id, version_id, yaml_text, note)},
                    status=HTTPStatus.CREATED,
                )
                return
            if len(parts) == 6 and parts[:2] == ["api", "projects"] and parts[3] == "versions" and parts[5] == "regenerate-scene":
                project_id = parts[2]
                version_id = parts[4]
                scene_id = payload.get("scene_id", "")
                if not scene_id:
                    raise ApiError(HTTPStatus.BAD_REQUEST, "scene_id is required.")
                self._send_json(
                    {
                        "ok": True,
                        "data": self.service.regenerate_scene(
                            project_id=project_id,
                            version_id=version_id,
                            scene_id=scene_id,
                            instruction=payload.get("instruction", ""),
                            provider_override=payload.get("provider", ""),
                            api_key=payload.get("api_key", ""),
                            tone_override=payload.get("tone", ""),
                            note=payload.get("note", ""),
                        ),
                    },
                    status=HTTPStatus.CREATED,
                )
                return
            if len(parts) == 6 and parts[:2] == ["api", "projects"] and parts[3] == "versions" and parts[5] == "regenerate-scene-async":
                project_id = parts[2]
                version_id = parts[4]
                scene_id = payload.get("scene_id", "")
                if not scene_id:
                    raise ApiError(HTTPStatus.BAD_REQUEST, "scene_id is required.")
                self._send_json(
                    {
                        "ok": True,
                        "data": self.service.start_regenerate_scene_async(
                            project_id=project_id,
                            version_id=version_id,
                            scene_id=scene_id,
                            instruction=payload.get("instruction", ""),
                            provider_override=payload.get("provider", ""),
                            api_key=payload.get("api_key", ""),
                            tone_override=payload.get("tone", ""),
                            note=payload.get("note", ""),
                        ),
                    },
                    status=HTTPStatus.CREATED,
                )
                return

            raise ApiError(HTTPStatus.NOT_FOUND, f"Route not found: {parsed.path}")
        except ApiError as exc:
            self._send_json({"ok": False, "error": exc.message}, status=exc.status)
        except FileNotFoundError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _serve_static(self, asset_name: str) -> None:
        asset_root = resources.files("ai_fiction_to_script.web").joinpath("static")
        asset = asset_root.joinpath(asset_name)
        if not asset.is_file():
            raise ApiError(HTTPStatus.NOT_FOUND, f"Static asset not found: {asset_name}")
        content = asset.read_bytes()
        mime_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self._send_no_cache_headers()
        self.end_headers()
        self.wfile.write(content)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object.")
        return data

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self._send_no_cache_headers()
        self.end_headers()
        self.wfile.write(raw)

    def _stream_task(self, task_id: str) -> None:
        task = self.service.get_task_status(task_id)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Connection", "keep-alive")
        self._send_no_cache_headers()
        self.end_headers()

        last_updated_at = ""
        while True:
            current_task = task if not last_updated_at else self.service.get_task_status(task_id)
            if current_task["updated_at"] != last_updated_at:
                self._send_sse("task", current_task)
                last_updated_at = current_task["updated_at"]
            if current_task["status"] in {"completed", "failed"}:
                return
            try:
                self.wfile.write(b": keep-alive\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            time.sleep(0.1)

    def _send_sse(self, event: str, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False)
        message = f"event: {event}\ndata: {raw}\n\n".encode("utf-8")
        try:
            self.wfile.write(message)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def _path_parts(self, path: str) -> list[str]:
        return [unquote(part) for part in path.strip("/").split("/") if part]

    def _send_no_cache_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")


def create_server(host: str, port: int, version_root: str | Path = ".novel2script") -> ThreadingHTTPServer:
    cache_settings = WebCacheSettings.from_env()
    cache_store = build_cache_store(
        redis_url=cache_settings.redis_url,
        enabled=cache_settings.enabled,
        prefix=cache_settings.key_prefix,
    )
    service = WorkbenchService(version_root, cache_store=cache_store, cache_settings=cache_settings)
    handler_class = type(
        "BoundWorkbenchRequestHandler",
        (WorkbenchRequestHandler,),
        {
            "service": service,
            "server_started_at": datetime.now(timezone.utc).isoformat(),
            "cache_backend": cache_store.backend_name,
        },
    )
    return ThreadingHTTPServer((host, port), handler_class)


def run_server(host: str, port: int, version_root: str | Path = ".novel2script") -> None:
    server = create_server(host, port, version_root)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
