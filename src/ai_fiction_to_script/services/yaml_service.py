from __future__ import annotations

import json
import re
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
        "schema_version": "screenplay-project-1.0",
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
        "story": {
            "logline": document.story_bible.logline,
            "synopsis": document.story_bible.synopsis,
            "themes": document.story_bible.theme,
            "props": document.story_bible.props,
        },
        "characters": [
            {
                "character_id": character.character_id,
                "name": character.name,
                "role": character.role,
                "traits": character.traits,
                "goal": character.goal,
                "conflict": character.conflict,
                "arc": character.arc,
                "voice": character.voice,
            }
            for character in document.story_bible.characters
        ],
        "locations": [
            {
                "location_id": location.location_id,
                "name": location.name,
                "description": location.description,
                "mood": location.mood,
            }
            for location in document.story_bible.locations
        ],
        "scenes": [],
        "appendix": {
            "source_chapters": [
                {
                    "chapter_id": chapter.chapter_id,
                    "title": chapter.title,
                    "text": chapter.raw_text,
                }
                for chapter in chapters
            ]
        },
    }

    for act in document.script.acts:
        for scene in act.scenes:
            payload["scenes"].append(
                {
                    "scene_id": scene.scene_id,
                    "title": scene.title,
                    "source_chapters": scene.chapter_refs,
                    "setting": {
                        "time_of_day": scene.time_of_day,
                        "location": location_lookup.get(scene.location_ref or "", ""),
                    },
                    "objective": scene.objective,
                    "summary": scene.summary,
                    "lines": [
                        _build_public_line(character_lookup.get(beat.speaker_ref or "", ""), beat.type, beat.text, beat.emotion)
                        for beat in scene.beats
                    ],
                }
            )

    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def _build_public_line(speaker_name: str, beat_type: str, text: str, emotion: str) -> dict[str, Any]:
    cleaned_text = str(text or "").strip()
    kind = "transition" if beat_type == "transition" else "narration" if beat_type == "narration" else beat_type
    cleaned_speaker, spoken_text = _extract_dialogue_speaker(speaker_name, cleaned_text)

    if kind == "dialogue":
        if not cleaned_speaker or _looks_like_narrative_line(spoken_text, cleaned_speaker):
            kind = "action"
            cleaned_speaker = ""
            spoken_text = cleaned_text
        else:
            spoken_text = spoken_text.strip()

    payload: dict[str, Any] = {
        "kind": kind,
        "text": spoken_text or cleaned_text,
    }
    if cleaned_speaker:
        payload["speaker"] = cleaned_speaker
    if emotion:
        payload["emotion"] = emotion
    return payload


def _extract_dialogue_speaker(speaker_name: str, text: str) -> tuple[str, str]:
    cleaned_speaker = speaker_name.strip()
    cleaned_text = text.strip()
    if cleaned_speaker:
        for prefix in (f"{cleaned_speaker}：", f"{cleaned_speaker}:"):
            if cleaned_text.startswith(prefix):
                return cleaned_speaker, cleaned_text[len(prefix) :].strip()
    match = re.match(r"^(?P<speaker>[^：:\s]{1,12})[：:](?P<text>.+)$", cleaned_text)
    if match:
        return match.group("speaker").strip(), match.group("text").strip()
    return cleaned_speaker, cleaned_text


def _looks_like_narrative_line(text: str, speaker_name: str) -> bool:
    cleaned_text = text.strip()
    if not cleaned_text:
        return True
    dialogue_prefixes = (
        f"{speaker_name}：",
        f"{speaker_name}:",
        f"{speaker_name}说",
        f"{speaker_name}问",
        f"{speaker_name}喊",
        f"{speaker_name}答",
        f"{speaker_name}道",
    )
    if speaker_name and any(cleaned_text.startswith(prefix) for prefix in dialogue_prefixes):
        return False
    if cleaned_text.startswith(speaker_name):
        narrative_prefixes = (
            "没有",
            "未",
            "只是",
            "看",
            "盯",
            "望",
            "转",
            "抬",
            "低",
            "走",
            "站",
            "坐",
            "拿",
            "放",
            "沉默",
            "点头",
            "摇头",
            "皱",
        )
        suffix = cleaned_text[len(speaker_name) :]
        if any(suffix.startswith(prefix) for prefix in narrative_prefixes):
            return True
    narrative_markers = ("镜头", "画面", "特写", "动作", "推近", "转身", "走入", "放在", "抬眼", "盯着", "看着", "没有回答")
    return any(marker in cleaned_text for marker in narrative_markers)


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
