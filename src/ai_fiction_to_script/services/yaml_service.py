from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ai_fiction_to_script.models.schema import ScreenplayDocument


def dump_yaml(document: ScreenplayDocument) -> str:
    payload = document.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def write_yaml(document: ScreenplayDocument, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(document), encoding="utf-8")
    return path


def write_json(document: ScreenplayDocument, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_yaml(path: str | Path) -> ScreenplayDocument:
    payload: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ScreenplayDocument.model_validate(payload)


def write_schema(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(ScreenplayDocument.model_json_schema(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path

