from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ai_fiction_to_script.models.runtime import ParsedChapter
from ai_fiction_to_script.models.schema import ScreenplayDocument


def dump_yaml(document: ScreenplayDocument) -> str:
    payload = document.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def dump_public_yaml(document: ScreenplayDocument, chapters: list[ParsedChapter]) -> str:
    character_lookup = {character.character_id: character.name for character in document.story_bible.characters}
    location_lookup = {location.location_id: location.name for location in document.story_bible.locations}

    payload: dict[str, Any] = {
        "schema_version": "compact-1.0",
        "meta": {
            "project_id": document.meta.project_id,
            "title": document.meta.title,
            "original_novel_title": document.meta.original_novel_title,
            "original_author": document.meta.original_author,
            "target_format": document.meta.target_format,
            "language": document.meta.language,
            "genre": document.meta.genre,
            "tone": document.meta.tone,
        },
        "source": {
            "chapters": [
                {
                    "chapter_id": chapter.chapter_id,
                    "title": chapter.title,
                    "text": chapter.raw_text,
                }
                for chapter in chapters
            ]
        },
        "script": {
            "scenes": [],
        },
    }

    for act in document.script.acts:
        for scene in act.scenes:
            payload["script"]["scenes"].append(
                {
                    "scene_id": scene.scene_id,
                    "title": scene.title,
                    "chapter_refs": scene.chapter_refs,
                    "time_of_day": scene.time_of_day,
                    "location": location_lookup.get(scene.location_ref or "", ""),
                    "objective": scene.objective,
                    "summary": scene.summary,
                    "beats": [
                        {
                            "type": beat.type,
                            "speaker": character_lookup.get(beat.speaker_ref or "", ""),
                            "text": beat.text,
                            "emotion": beat.emotion,
                        }
                        for beat in scene.beats
                    ],
                }
            )

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
