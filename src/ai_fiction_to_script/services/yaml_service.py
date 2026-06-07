from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from ai_fiction_to_script.models.runtime import ParsedChapter
from ai_fiction_to_script.models.schema import Beat, Scene, ScreenplayDocument, Script, ScriptAct


def dump_yaml(document: ScreenplayDocument) -> str:
    payload = document.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def dump_public_yaml(document: ScreenplayDocument, chapters: list[ParsedChapter]) -> str:
    export_document = _build_export_document(document, chapters)
    return dump_yaml(export_document)


def _build_export_document(document: ScreenplayDocument, chapters: list[ParsedChapter]) -> ScreenplayDocument:
    sanitized_acts: list[ScriptAct] = []
    for act in document.script.acts:
        sanitized_scenes = [_sanitize_scene_for_export(scene, document) for scene in act.scenes]
        sanitized_acts.append(ScriptAct(act_id=act.act_id, title=act.title, scenes=sanitized_scenes))

    regeneration_bundle = {
        "source_chapters": [
            {
                "chapter_id": chapter.chapter_id,
                "title": chapter.title,
                "text": chapter.raw_text,
            }
            for chapter in chapters
        ]
    }
    extensions = dict(document.extensions)
    extensions["regeneration_bundle"] = regeneration_bundle

    return document.model_copy(
        update={
            "script": Script(acts=sanitized_acts),
            "extensions": extensions,
        }
    )


def _sanitize_scene_for_export(scene: Scene, document: ScreenplayDocument) -> Scene:
    sanitized_beats = [_sanitize_beat_for_export(beat, document) for beat in scene.beats]
    return scene.model_copy(update={"beats": sanitized_beats})


def _sanitize_beat_for_export(beat: Beat, document: ScreenplayDocument) -> Beat:
    speaker_name = _speaker_name(document, beat.speaker_ref)
    cleaned_type, cleaned_speaker_ref, cleaned_text = _normalize_exported_beat_content(
        beat.type,
        beat.speaker_ref,
        speaker_name,
        beat.text,
    )
    return beat.model_copy(
        update={
            "type": cleaned_type,
            "speaker_ref": cleaned_speaker_ref,
            "text": cleaned_text,
        }
    )


def _speaker_name(document: ScreenplayDocument, speaker_ref: str | None) -> str:
    if not speaker_ref:
        return ""
    for character in document.story_bible.characters:
        if character.character_id == speaker_ref:
            return character.name
    return speaker_ref


def _normalize_exported_beat_content(
    beat_type: str,
    speaker_ref: str | None,
    speaker_name: str,
    text: str,
) -> tuple[str, str | None, str]:
    cleaned_type = beat_type
    cleaned_speaker_ref = speaker_ref
    cleaned_text = str(text or "").strip()
    tag, tag_speaker, cleaned_text = _strip_audio_markup(cleaned_text)

    if tag in {"SFX", "BGM", "FX"}:
        cleaned_type = "action"
        cleaned_speaker_ref = None
    elif tag in {"VO", "OS", "旁白"} and cleaned_type == "dialogue" and not cleaned_speaker_ref:
        cleaned_speaker_ref = speaker_ref
        if not cleaned_speaker_ref and tag_speaker and tag_speaker == speaker_name:
            cleaned_speaker_ref = speaker_ref

    if cleaned_type == "dialogue":
        inferred_speaker, cleaned_text = _split_dialogue_prefix(speaker_name, cleaned_text)
        if not cleaned_speaker_ref and inferred_speaker and inferred_speaker == speaker_name:
            cleaned_speaker_ref = speaker_ref
        if _looks_like_narrative_text(cleaned_text, speaker_name):
            cleaned_type = "action"
            cleaned_speaker_ref = None

    return cleaned_type, cleaned_speaker_ref, cleaned_text.strip()


def _split_dialogue_prefix(speaker_name: str, text: str) -> tuple[str, str]:
    cleaned_text = text.strip()
    if speaker_name:
        for prefix in (f"{speaker_name}：", f"{speaker_name}:"):
            if cleaned_text.startswith(prefix):
                return speaker_name, cleaned_text[len(prefix) :].strip()
    match = re.match(r"^(?P<speaker>[^：:\s]{1,12})[：:](?P<text>.+)$", cleaned_text)
    if match:
        return match.group("speaker").strip(), match.group("text").strip()
    return "", cleaned_text


def _strip_audio_markup(text: str) -> tuple[str, str, str]:
    cleaned_text = text.strip()
    match = re.match(r"^\[(?P<tag>[A-Za-z]+|旁白)(?:[\/|／｜](?P<speaker>[^\]]+))?\]\s*(?P<text>.+)$", cleaned_text)
    if not match:
        return "", "", cleaned_text
    tag = match.group("tag").strip().upper() if match.group("tag") != "旁白" else "旁白"
    speaker = str(match.group("speaker") or "").strip()
    body = match.group("text").strip()
    return tag, speaker, body


def _looks_like_narrative_text(text: str, speaker_name: str) -> bool:
    cleaned_text = text.strip()
    if not cleaned_text:
        return True
    if speaker_name:
        dialogue_prefixes = (
            f"{speaker_name}说",
            f"{speaker_name}问",
            f"{speaker_name}喊",
            f"{speaker_name}答",
            f"{speaker_name}道",
        )
        if any(cleaned_text.startswith(prefix) for prefix in dialogue_prefixes):
            return False
        if cleaned_text.startswith(speaker_name):
            suffix = cleaned_text[len(speaker_name) :]
            if any(
                suffix.startswith(prefix)
                for prefix in ("没有", "未", "只是", "看", "盯", "望", "转", "抬", "低", "走", "站", "坐", "拿", "放", "沉默", "点头", "摇头", "皱")
            ):
                return True
    return any(marker in cleaned_text for marker in ("镜头", "画面", "特写", "动作", "推近", "转身", "走入", "放在", "抬眼", "盯着", "看着", "没有回答"))


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
