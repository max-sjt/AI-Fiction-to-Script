from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ai_fiction_to_script.cli import _build_request, app
from ai_fiction_to_script.services.yaml_service import load_yaml


runner = CliRunner()


def sample_novel_path() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "sample_novel.txt"


def test_adapt_creates_yaml_and_local_version(tmp_path) -> None:
    output_path = tmp_path / "screenplay.yaml"
    version_root = tmp_path / ".novel2script"
    result = runner.invoke(
        app,
        [
            "adapt",
            str(sample_novel_path()),
            "--title",
            "老街回声",
            "--original-author",
            "测试作者",
            "--project-id",
            "demo-project",
            "--output",
            str(output_path),
            "--version-root",
            str(version_root),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output_path.exists()
    assert (version_root / "demo-project" / "index.json").exists()

    document = load_yaml(output_path)
    assert document.schema_version == "2.0"
    assert document.source.chapter_count == 3


def test_quick_creates_yaml_with_inferred_defaults(tmp_path) -> None:
    output_dir = tmp_path / "out"
    version_root = tmp_path / ".novel2script"

    result = runner.invoke(
        app,
        [
            "quick",
            str(sample_novel_path()),
            "--output-dir",
            str(output_dir),
            "--version-root",
            str(version_root),
            "--detail",
            "fast",
        ],
    )

    assert result.exit_code == 0, result.output
    output_path = output_dir / "sample_novel.yaml"
    assert output_path.exists()
    assert (version_root / "sample_novel" / "index.json").exists()

    document = load_yaml(output_path)
    assert document.meta.title == "sample_novel"
    assert document.meta.model_provider == "mock"


def test_cli_detail_levels_keep_one_script_unit_per_chapter() -> None:
    detailed_request = _build_request(
        input_path=sample_novel_path(),
        title="detail-demo",
        original_author="tester",
        original_title="detail-demo",
        project_id="detail-demo",
        target_format="film",
        genre="",
        tone="balanced",
        provider="mock",
        model_name="",
        detail_level="detailed",
    )

    assert detailed_request.max_scenes_per_chapter == 1
    assert detailed_request.max_beats_per_scene == 12
    assert detailed_request.chapter_context_chars == 1600


def test_export_schema_and_regenerate_scene(tmp_path) -> None:
    output_path = tmp_path / "screenplay.yaml"
    version_root = tmp_path / ".novel2script"
    schema_path = tmp_path / "screenplay.schema.json"

    adapt_result = runner.invoke(
        app,
        [
            "adapt",
            str(sample_novel_path()),
            "--title",
            "老街回声",
            "--original-author",
            "测试作者",
            "--project-id",
            "demo-project",
            "--output",
            str(output_path),
            "--version-root",
            str(version_root),
        ],
    )
    assert adapt_result.exit_code == 0, adapt_result.output

    schema_result = runner.invoke(app, ["export-schema", "--output", str(schema_path)])
    assert schema_result.exit_code == 0, schema_result.output
    assert schema_path.exists()
    assert '"schema_version"' in schema_path.read_text(encoding="utf-8")

    regenerate_result = runner.invoke(
        app,
        [
            "regenerate-scene",
            "demo-project",
            "v0001",
            "s001",
            "--instruction",
            "强化主角对匿名短信的怀疑感",
            "--version-root",
            str(version_root),
            "--note",
            "scene regeneration",
        ],
    )
    assert regenerate_result.exit_code == 0, regenerate_result.output
    assert (version_root / "demo-project" / "versions" / "v0002" / "screenplay.yaml").exists()
