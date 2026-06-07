from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    chapter_count: int = Field(..., ge=3)
    chapters: list[SourceChapter] = Field(default_factory=list, min_length=3)

    @model_validator(mode="after")
    def validate_chapter_count(self) -> "SourceInfo":
        if len(self.chapters) != self.chapter_count:
            raise ValueError("source.chapter_count must equal the number of source.chapters.")
        return self


class StyleGuide(SchemaModel):
    dialogue_style: str = "自然、口语化"
    narration_style: str = "简洁、清晰"
    pacing_style: str = "平衡"


class AdaptationSettings(SchemaModel):
    adaptation_goal: str
    compression_strategy: str = "merge_minor_events"
    pacing_policy: str = "preserve_key_conflicts"
    structure_type: str = "continuous_sequence"
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
    chapter_refs: list[str] = Field(default_factory=list, min_length=1)


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
    chapter_refs: list[str] = Field(default_factory=list, min_length=1)
    conflict: str = ""
    notes: str = ""
    focus_event: str = ""
    bridge_in: str = ""
    bridge_out: str = ""


class ActOutline(SchemaModel):
    act_id: str
    name: str
    purpose: str
    scene_count: int = Field(default=0, ge=0)


class Outline(SchemaModel):
    structure_type: str = "three_act"
    acts: list[ActOutline] = Field(default_factory=list, min_length=1)
    scene_plans: list[ScenePlan] = Field(default_factory=list, min_length=1)


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
    chapter_refs: list[str] = Field(default_factory=list, min_length=1)
    location_ref: str | None = None
    time_of_day: str = ""
    objective: str
    summary: str = ""
    beats: list[Beat] = Field(default_factory=list)
    transitions: SceneTransition | None = None
    source_refs: list[SourceRef] = Field(default_factory=list, min_length=1)


class ScriptAct(SchemaModel):
    act_id: str
    title: str
    scenes: list[Scene] = Field(default_factory=list)


class Script(SchemaModel):
    acts: list[ScriptAct] = Field(default_factory=list, min_length=1)


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
    schema_version: str = Field(default="2.0")
    meta: MetaInfo
    source: SourceInfo
    adaptation: AdaptationSettings
    story_bible: StoryBible
    outline: Outline
    script: Script
    quality: QualityReport = Field(default_factory=QualityReport)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_payload(cls, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload

        data = dict(payload)
        data["schema_version"] = "2.0"

        source = data.get("source")
        if isinstance(source, dict):
            source = dict(source)
            chapters = source.get("chapters")
            if isinstance(chapters, list):
                source["chapter_count"] = len(chapters)
            data["source"] = source

        extensions = data.get("extensions")
        if not isinstance(extensions, dict):
            extensions = {}
        extensions.setdefault(
            "ingestion",
            {
                "minimum_required_chapters": 3,
                "uploaded_input_ref": "",
                "chapter_split_method": "heading_based",
            },
        )
        extensions.setdefault(
            "production_notes",
            {
                "draft_stage": "first_pass",
                "recommended_episode_count": 1,
                "recommended_runtime_minutes": 25,
                "review_owner": "human_editor",
            },
        )
        data["extensions"] = extensions
        return data

    @model_validator(mode="after")
    def validate_references(self) -> "ScreenplayDocument":
        source_chapter_ids = [chapter.chapter_id for chapter in self.source.chapters]
        if len(source_chapter_ids) != len(set(source_chapter_ids)):
            raise ValueError("source.chapters.chapter_id must be unique.")

        character_ids = [character.character_id for character in self.story_bible.characters]
        if len(character_ids) != len(set(character_ids)):
            raise ValueError("story_bible.characters.character_id must be unique.")

        location_ids = [location.location_id for location in self.story_bible.locations]
        if len(location_ids) != len(set(location_ids)):
            raise ValueError("story_bible.locations.location_id must be unique.")

        act_ids = [act.act_id for act in self.outline.acts]
        if len(act_ids) != len(set(act_ids)):
            raise ValueError("outline.acts.act_id must be unique.")

        scene_plan_ids = [scene_plan.scene_id for scene_plan in self.outline.scene_plans]
        if len(scene_plan_ids) != len(set(scene_plan_ids)):
            raise ValueError("outline.scene_plans.scene_id must be unique.")

        chapter_id_set = set(source_chapter_ids)
        character_id_set = set(character_ids)
        location_id_set = set(location_ids)
        act_id_set = set(act_ids)

        for event in self.story_bible.timeline:
            missing = set(event.chapter_refs) - chapter_id_set
            if missing:
                raise ValueError(f"timeline event `{event.event_id}` references unknown chapters: {sorted(missing)}")

        for scene_plan in self.outline.scene_plans:
            if scene_plan.act_id not in act_id_set:
                raise ValueError(f"scene_plan `{scene_plan.scene_id}` references unknown act `{scene_plan.act_id}`.")
            missing = set(scene_plan.chapter_refs) - chapter_id_set
            if missing:
                raise ValueError(f"scene_plan `{scene_plan.scene_id}` references unknown chapters: {sorted(missing)}")

        script_act_ids = [act.act_id for act in self.script.acts]
        if len(script_act_ids) != len(set(script_act_ids)):
            raise ValueError("script.acts.act_id must be unique.")

        for act_id in script_act_ids:
            if act_id not in act_id_set:
                raise ValueError(f"script act `{act_id}` is not present in outline.acts.")

        script_scene_ids: list[str] = []
        for act in self.script.acts:
            for scene in act.scenes:
                script_scene_ids.append(scene.scene_id)
                missing = set(scene.chapter_refs) - chapter_id_set
                if missing:
                    raise ValueError(f"scene `{scene.scene_id}` references unknown chapters: {sorted(missing)}")
                if scene.location_ref and scene.location_ref not in location_id_set:
                    raise ValueError(f"scene `{scene.scene_id}` references unknown location `{scene.location_ref}`.")
                for beat in scene.beats:
                    if beat.speaker_ref and beat.speaker_ref not in character_id_set:
                        raise ValueError(f"beat `{beat.beat_id}` references unknown speaker `{beat.speaker_ref}`.")
                for source_ref in scene.source_refs:
                    if source_ref.chapter_id not in chapter_id_set:
                        raise ValueError(
                            f"scene `{scene.scene_id}` source_ref references unknown chapter `{source_ref.chapter_id}`."
                        )

        if len(script_scene_ids) != len(set(script_scene_ids)):
            raise ValueError("script scenes must use unique scene_id values.")

        return self
