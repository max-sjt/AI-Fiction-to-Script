from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_fiction_to_script.models.runtime import AdaptationRequest, ChapterAnalysis, ParsedChapter, VersionRecord
from ai_fiction_to_script.models.schema import (
    ActOutline,
    AdaptationSettings,
    MetaInfo,
    Outline,
    QualityReport,
    ScenePlan,
    ScreenplayDocument,
    Script,
    ScriptAct,
    SourceChapter,
    SourceInfo,
)
from ai_fiction_to_script.services.ai_client import BaseAIClient
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore


@dataclass(slots=True)
class AdaptationResult:
    document: ScreenplayDocument
    chapters: list[ParsedChapter]
    analyses: list[ChapterAnalysis]
    version: VersionRecord | None = None


class AdaptationEngine:
    def __init__(
        self,
        parser: ChapterParser,
        ai_client: BaseAIClient,
        quality_checker: QualityChecker,
        version_store: VersionStore | None = None,
    ) -> None:
        self._parser = parser
        self._ai_client = ai_client
        self._quality_checker = quality_checker
        self._version_store = version_store

    def run(self, input_path: str | Path, request: AdaptationRequest, note: str = "") -> AdaptationResult:
        chapters = self._parser.parse(input_path)
        if len(chapters) < 3:
            raise ValueError("输入小说章节数不足 3 章，无法满足题目要求。")

        analyses = [self._ai_client.analyze_chapter(chapter, request) for chapter in chapters]
        story_bible = self._ai_client.build_story_bible(analyses, request)
        outline = self._normalize_outline(self._ai_client.plan_outline(analyses, story_bible, request), analyses)

        chapter_map = {chapter.chapter_id: chapter for chapter in chapters}
        scenes_by_act = defaultdict(list)
        for scene_plan in outline.scene_plans:
            chapter = self._resolve_scene_chapter(scene_plan, chapter_map, chapters)
            scene = self._ai_client.generate_scene(scene_plan, story_bible, chapter, request)
            scenes_by_act[scene_plan.act_id].append(scene)

        script = Script(
            acts=[
                ScriptAct(act_id=act.act_id, title=act.name, scenes=scenes_by_act.get(act.act_id, []))
                for act in outline.acts
            ]
        )

        document = ScreenplayDocument(
            meta=MetaInfo(
                project_id=request.project_id,
                title=request.title,
                original_novel_title=request.original_novel_title,
                original_author=request.original_author,
                target_format=request.target_format,
                language=request.language,
                genre=request.genre,
                tone=request.tone,
                created_at=datetime.now(timezone.utc).isoformat(),
                model_provider=request.provider,
                model_name=self._resolve_model_name(request),
            ),
            source=SourceInfo(
                chapter_count=len(chapters),
                chapters=[
                    SourceChapter(
                        chapter_id=chapter.chapter_id,
                        title=chapter.title,
                        raw_text_ref=chapter.raw_text_ref,
                        summary=self._analysis_lookup(analyses)[chapter.chapter_id].summary,
                        excerpt_count=len(chapter.excerpts),
                    )
                    for chapter in chapters
                ],
            ),
            adaptation=AdaptationSettings(
                adaptation_goal=request.adaptation_goal,
                compression_strategy=request.compression_strategy,
                pacing_policy=request.pacing_policy,
                structure_type=request.structure_type,
                style_guide=request.style_guide,
            ),
            story_bible=story_bible,
            outline=outline,
            script=script,
            quality=QualityReport(),
            extensions={
                "generator": "ai-fiction-to-script",
                "local_versioning": True,
            },
        )

        quality = self._quality_checker.review(document)
        ai_warnings, ai_suggestions = self._ai_client.review_document(document, request)
        quality.warnings = _merge_unique(quality.warnings, ai_warnings)
        quality.revision_suggestions = _merge_unique(quality.revision_suggestions, ai_suggestions)
        document = document.model_copy(update={"quality": quality})

        version = None
        if self._version_store:
            version = self._version_store.save(
                request.project_id,
                document,
                intermediates={
                    "request": request.model_dump(mode="json"),
                    "chapters": [chapter.model_dump(mode="json") for chapter in chapters],
                    "chapter_analyses": [analysis.model_dump(mode="json") for analysis in analyses],
                    "story_bible": story_bible.model_dump(mode="json"),
                    "outline": outline.model_dump(mode="json"),
                },
                note=note,
            )

        return AdaptationResult(document=document, chapters=chapters, analyses=analyses, version=version)

    def _analysis_lookup(self, analyses: list[ChapterAnalysis]) -> dict[str, ChapterAnalysis]:
        return {analysis.chapter_id: analysis for analysis in analyses}

    def _normalize_outline(self, outline: Outline, analyses: list[ChapterAnalysis]) -> Outline:
        if not outline.scene_plans:
            fallback_scene_plans = [
                ScenePlan(
                    scene_id=f"s{index:03d}",
                    act_id="a1" if index == 1 else "a2" if index < len(analyses) else "a3",
                    title=analysis.title,
                    objective=analysis.conflicts[0] if analysis.conflicts else "推进剧情",
                    chapter_refs=[analysis.chapter_id],
                    conflict=analysis.conflicts[0] if analysis.conflicts else "",
                    notes=analysis.summary,
                )
                for index, analysis in enumerate(analyses, start=1)
            ]
            outline = outline.model_copy(update={"scene_plans": fallback_scene_plans})

        if not outline.acts:
            outline = outline.model_copy(
                update={
                    "acts": [
                        ActOutline(act_id="a1", name="开端", purpose="建立冲突", scene_count=0),
                        ActOutline(act_id="a2", name="发展", purpose="升级冲突", scene_count=0),
                        ActOutline(act_id="a3", name="结局", purpose="阶段收束", scene_count=0),
                    ]
                }
            )

        counts = defaultdict(int)
        for plan in outline.scene_plans:
            counts[plan.act_id] += 1
        acts = [
            act.model_copy(update={"scene_count": counts[act.act_id]})
            for act in outline.acts
        ]
        return outline.model_copy(update={"acts": acts})

    def _resolve_scene_chapter(
        self,
        scene_plan: ScenePlan,
        chapter_map: dict[str, ParsedChapter],
        chapters: list[ParsedChapter],
    ) -> ParsedChapter:
        for chapter_id in scene_plan.chapter_refs:
            if chapter_id in chapter_map:
                return chapter_map[chapter_id]
        return chapters[0]

    def _resolve_model_name(self, request: AdaptationRequest) -> str:
        if request.provider == "mock":
            return "mock-qwen-planner"
        return request.model_routing.generation_model


def _merge_unique(base: list[str], new_items: list[str]) -> list[str]:
    output = list(base)
    for item in new_items:
        if item and item not in output:
            output.append(item)
    return output

