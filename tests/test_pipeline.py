from __future__ import annotations

from pathlib import Path

from ai_fiction_to_script.models.runtime import AdaptationRequest
from ai_fiction_to_script.pipeline.engine import AdaptationEngine
from ai_fiction_to_script.services.ai_client import MockAIClient
from ai_fiction_to_script.models.schema import ActOutline, Outline, ScenePlan
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore
from ai_fiction_to_script.services.yaml_service import dump_yaml, load_yaml, write_schema


def sample_novel_path() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "sample_novel.txt"


def test_pipeline_generates_document_and_version(tmp_path) -> None:
    engine = AdaptationEngine(
        parser=ChapterParser(),
        ai_client=MockAIClient(),
        quality_checker=QualityChecker(),
        version_store=VersionStore(tmp_path / ".novel2script"),
    )
    request = AdaptationRequest(
        project_id="pipeline-project",
        title="老街回声",
        original_novel_title="老街回声",
        original_author="测试作者",
    )

    result = engine.run(sample_novel_path(), request, note="initial")

    assert result.document.schema_version == "2.0"
    assert result.document.source.chapter_count == 3
    assert len(result.document.script.acts) == 1
    assert result.document.script.acts[0].act_id == "main"
    assert result.document.outline.acts[0].act_id == "main"
    assert result.document.extensions["ingestion"]["minimum_required_chapters"] == 3
    assert any(act.scenes for act in result.document.script.acts)
    assert result.version is not None
    assert result.version.version_id == "v0001"


def test_pipeline_outputs_one_script_unit_per_source_chapter_even_if_outline_splits(tmp_path) -> None:
    class SplittingMockAIClient(MockAIClient):
        def plan_outline(self, analyses, story_bible, request):
            scene_plans = []
            for chapter_index, analysis in enumerate(analyses, start=1):
                for local_index in range(2):
                    scene_plans.append(
                        ScenePlan(
                            scene_id=f"s{len(scene_plans) + 1:03d}",
                            act_id="main",
                            title=f"{analysis.title}-{local_index + 1}",
                            objective=f"segment {local_index + 1}",
                            chapter_refs=[analysis.chapter_id],
                            conflict="split conflict",
                            notes="split notes",
                            focus_event=f"split event {local_index + 1}",
                        )
                    )
            return Outline(
                structure_type=request.structure_type,
                acts=[ActOutline(act_id="main", name="正文", purpose="split", scene_count=len(scene_plans))],
                scene_plans=scene_plans,
            )

    engine = AdaptationEngine(
        parser=ChapterParser(),
        ai_client=SplittingMockAIClient(),
        quality_checker=QualityChecker(),
        version_store=None,
    )
    request = AdaptationRequest(
        project_id="chapter-units",
        title="chapter-units",
        original_novel_title="chapter-units",
        original_author="tester",
        max_scenes_per_chapter=5,
        detail_level="detailed",
    )

    result = engine.run(sample_novel_path(), request)
    scenes = result.document.script.acts[0].scenes

    assert len(scenes) == result.document.source.chapter_count
    assert [scene.chapter_refs for scene in scenes] == [["ch01"], ["ch02"], ["ch03"]]
    assert [plan.chapter_refs for plan in result.document.outline.scene_plans] == [["ch01"], ["ch02"], ["ch03"]]


def test_yaml_roundtrip_and_schema_export(tmp_path) -> None:
    engine = AdaptationEngine(
        parser=ChapterParser(),
        ai_client=MockAIClient(),
        quality_checker=QualityChecker(),
        version_store=None,
    )
    request = AdaptationRequest(
        project_id="roundtrip-project",
        title="老街回声",
        original_novel_title="老街回声",
        original_author="测试作者",
    )
    result = engine.run(sample_novel_path(), request)
    yaml_path = tmp_path / "screenplay.yaml"
    yaml_path.write_text(dump_yaml(result.document), encoding="utf-8")

    loaded = load_yaml(yaml_path)
    schema_path = write_schema(tmp_path / "screenplay.schema.json")

    assert loaded.schema_version == "2.0"
    assert loaded.meta.title == "老街回声"
    assert loaded.extensions["production_notes"]["draft_stage"] == "first_pass"
    assert schema_path.exists()
