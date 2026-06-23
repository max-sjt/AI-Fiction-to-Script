from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_fiction_to_script.models.schema import StyleGuide


class RuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParsedExcerpt(RuntimeModel):
    excerpt_id: str
    text: str


class ParsedChapter(RuntimeModel):
    chapter_id: str
    title: str
    raw_text: str
    raw_text_ref: str
    excerpts: list[ParsedExcerpt] = Field(default_factory=list)


class ChapterAnalysis(RuntimeModel):
    chapter_id: str
    title: str
    summary: str
    characters: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    emotions: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)


class ModelRouting(RuntimeModel):
    summary_model: str = "qwen-plus"
    planning_model: str = "qwen-max"
    generation_model: str = "qwen-max"
    validation_model: str = "qwen-turbo"


class AdaptationRequest(RuntimeModel):
    project_id: str
    title: str
    original_novel_title: str
    original_author: str
    target_format: str = "tv_drama"
    language: str = "zh-CN"
    genre: list[str] = Field(default_factory=list)
    tone: str = "balanced"
    adaptation_goal: str = "将小说改编为可编辑剧本初稿"
    compression_strategy: str = "merge_minor_events"
    pacing_policy: str = "preserve_key_conflicts"
    structure_type: str = "continuous_sequence"
    style_guide: StyleGuide = Field(default_factory=StyleGuide)
    provider: Literal["qwen", "mock"] = "mock"
    model_name: str = ""
    model_routing: ModelRouting = Field(default_factory=ModelRouting)
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_scenes_per_chapter: int = Field(default=2, ge=1, le=5)
    detail_level: Literal["fast", "standard", "detailed"] = "standard"
    max_beats_per_scene: int = Field(default=6, ge=4, le=12)
    chapter_context_chars: int = Field(default=700, ge=180, le=2400)


class VersionRecord(RuntimeModel):
    project_id: str
    version_id: str
    created_at: str
    note: str = ""
    script_yaml_path: str
    script_json_path: str
    intermediates_path: str


class ProjectIndex(RuntimeModel):
    project_id: str
    latest_version: str | None = None
    versions: list[VersionRecord] = Field(default_factory=list)
