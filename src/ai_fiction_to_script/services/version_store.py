from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fiction_to_script.models.runtime import ProjectIndex, VersionRecord
from ai_fiction_to_script.models.schema import ScreenplayDocument
from ai_fiction_to_script.services.yaml_service import dump_yaml, load_yaml, write_json, write_yaml


class VersionStore:
    def __init__(self, root: str | Path = ".novel2script") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        project_id: str,
        document: ScreenplayDocument,
        intermediates: dict[str, Any],
        note: str = "",
    ) -> VersionRecord:
        index = self._load_index(project_id)
        version_number = len(index.versions) + 1
        version_id = f"v{version_number:04d}"
        version_dir = self.root / project_id / "versions" / version_id
        intermediates_dir = version_dir / "intermediates"
        version_dir.mkdir(parents=True, exist_ok=True)
        intermediates_dir.mkdir(parents=True, exist_ok=True)

        yaml_path = write_yaml(document, version_dir / "screenplay.yaml")
        json_path = write_json(document, version_dir / "screenplay.json")
        for name, payload in intermediates.items():
            target = intermediates_dir / f"{name}.json"
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        record = VersionRecord(
            project_id=project_id,
            version_id=version_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            note=note,
            script_yaml_path=str(yaml_path),
            script_json_path=str(json_path),
            intermediates_path=str(intermediates_dir),
        )
        index.versions.append(record)
        index.latest_version = version_id
        self._write_index(index)
        return record

    def list_versions(self, project_id: str) -> list[VersionRecord]:
        return self._load_index(project_id).versions

    def load_document(self, project_id: str, version_id: str) -> ScreenplayDocument:
        record = self._find_record(project_id, version_id)
        return load_yaml(record.script_yaml_path)

    def load_intermediate(self, project_id: str, version_id: str, name: str):
        record = self._find_record(project_id, version_id)
        path = Path(record.intermediates_path) / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Intermediate not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def get_record(self, project_id: str, version_id: str) -> VersionRecord:
        return self._find_record(project_id, version_id)

    def diff(self, project_id: str, version_a: str, version_b: str) -> str:
        record_a = self._find_record(project_id, version_a)
        record_b = self._find_record(project_id, version_b)
        text_a = Path(record_a.script_yaml_path).read_text(encoding="utf-8").splitlines()
        text_b = Path(record_b.script_yaml_path).read_text(encoding="utf-8").splitlines()
        diff = difflib.unified_diff(
            text_a,
            text_b,
            fromfile=record_a.script_yaml_path,
            tofile=record_b.script_yaml_path,
            lineterm="",
        )
        return "\n".join(diff)

    def _project_dir(self, project_id: str) -> Path:
        return self.root / project_id

    def _index_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "index.json"

    def _load_index(self, project_id: str) -> ProjectIndex:
        index_path = self._index_path(project_id)
        if not index_path.exists():
            return ProjectIndex(project_id=project_id)
        return ProjectIndex.model_validate(json.loads(index_path.read_text(encoding="utf-8")))

    def _write_index(self, index: ProjectIndex) -> None:
        project_dir = self._project_dir(index.project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        self._index_path(index.project_id).write_text(
            json.dumps(index.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _find_record(self, project_id: str, version_id: str) -> VersionRecord:
        index = self._load_index(project_id)
        for record in index.versions:
            if record.version_id == version_id:
                return record
        raise ValueError(f"Version not found: {project_id}/{version_id}")
