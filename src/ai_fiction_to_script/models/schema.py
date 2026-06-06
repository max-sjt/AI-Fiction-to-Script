from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class MetaInfo(SchemaModel):
    project_id: str = Field(..., description="Unique project identifier.")
    title: str = Field(..., description="Screenplay title.")
    original_novel_title: str = Field(..., description="Original novel title.")
    original_author: str = Field(..., description="Original novel author.")
    target_format: str = Field(..., description="Target screenplay format, such as film or tv_drama.")
    language: str = Field(default="zh-CN")
    genre: list[str] = Field(default_factory=list)
    tone: str = Field(default="balanced")
    created_at: str = Field(..., description="ISO 8601 timestamp.")
    model_provider: str = Field(default="qwen")
    model_name: str = Field(default="qwen-max")


class SourceChapter(SchemaModel):
    chapter_id: str
    title: str
    raw_text_ref: str
    summary: str = ""
    excerpt_count: int = Field(default=0, ge=0)


class SourceInfo(SchemaModel):
    chapter_count: int = Field(..., ge=1)
    chapters: list[SourceChapter] = Field(default_factory=list)


class StyleGuide(SchemaModel):
    dialogue_style: str = "自然口语化"
    narration_style: str = "简洁清晰"
    pacing_style: str = "平衡"


class AdaptationSettings(SchemaModel):
    adaptation_goal: str
    compression_strategy: str = "merge_minor_events"
    pacing_policy: str = "preserve_key_conflicts"
    structure_type: str = "three_act"
    style_guide: StyleGuide = Field(default_factory=StyleGuide)


class CharacterRelation(SchemaModel):
    target_character_id: str
    relation: str
    notes: str = ""


class CharacterCard(SchemaModel):
    character_id: str
    name: str
    role: str
    traits: list[str] = Field(default_factory=list)
    goal: str = ""
    conflict: str = ""
    arc: str = ""
    voice: str = ""
    relations: list[CharacterRelation] = Field(default_factory=list)


class LocationCard(SchemaModel):
    location_id: str
    name: str
    description: str = ""
    mood: str = ""


class TimelineEvent(SchemaModel):
    event_id: str
    time_order: int = Field(..., ge=1)
    summary: str
    chapter_refs: list[str] = Field(default_factory=list)


class StoryBible(SchemaModel):
    logline: str
    synopsis: str
    theme: list[str] = Field(default_factory=list)
    characters: list[CharacterCard] = Field(default_factory=list)
    locations: list[LocationCard] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)


class ScenePlan(SchemaModel):
    scene_id: str
    act_id: str
    title: str
    objective: str
    chapter_refs: list[str] = Field(default_factory=list)
    conflict: str = ""
    notes: str = ""


class ActOutline(SchemaModel):
    act_id: str
    name: str
    purpose: str
    scene_count: int = Field(default=0, ge=0)


class Outline(SchemaModel):
    structure_type: str = "three_act"
    acts: list[ActOutline] = Field(default_factory=list)
    scene_plans: list[ScenePlan] = Field(default_factory=list)


class SourceRef(SchemaModel):
    chapter_id: str
    excerpt_id: str


class SceneTransition(SchemaModel):
    next_scene_hint: str = ""
    transition_type: str = "cut"


class Beat(SchemaModel):
    beat_id: str
    type: Literal["action", "dialogue", "transition", "narration"]
    text: str
    speaker_ref: str | None = None
    emotion: str = ""


class Scene(SchemaModel):
    scene_id: str
    title: str
    chapter_refs: list[str] = Field(default_factory=list)
    location_ref: str | None = None
    time_of_day: str = ""
    objective: str
    summary: str = ""
    beats: list[Beat] = Field(default_factory=list)
    transitions: SceneTransition | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)


class ScriptAct(SchemaModel):
    act_id: str
    title: str
    scenes: list[Scene] = Field(default_factory=list)


class Script(SchemaModel):
    acts: list[ScriptAct] = Field(default_factory=list)


class ContinuityChecks(SchemaModel):
    character_consistency: bool = True
    timeline_consistency: bool = True
    location_consistency: bool = True
    reference_consistency: bool = True


class QualityReport(SchemaModel):
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    revision_suggestions: list[str] = Field(default_factory=list)
    continuity_checks: ContinuityChecks = Field(default_factory=ContinuityChecks)


class ScreenplayDocument(SchemaModel):
    schema_version: str = Field(default="1.0")
    meta: MetaInfo
    source: SourceInfo
    adaptation: AdaptationSettings
    story_bible: StoryBible
    outline: Outline
    script: Script
    quality: QualityReport = Field(default_factory=QualityReport)
    extensions: dict[str, Any] = Field(default_factory=dict)
