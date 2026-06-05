from __future__ import annotations

from pathlib import Path

from ai_fiction_to_script.models.runtime import AdaptationRequest
from ai_fiction_to_script.pipeline.engine import AdaptationEngine
from ai_fiction_to_script.services.ai_client import MockAIClient
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

    assert result.document.source.chapter_count == 3
    assert len(result.document.script.acts) == 3
    assert any(act.scenes for act in result.document.script.acts)
    assert result.version is not None
    assert result.version.version_id == "v0001"


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

    assert loaded.meta.title == "老街回声"
    assert schema_path.exists()

