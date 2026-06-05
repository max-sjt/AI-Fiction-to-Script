from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ai_fiction_to_script.cli import app


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

