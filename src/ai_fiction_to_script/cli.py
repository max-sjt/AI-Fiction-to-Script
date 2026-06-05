from __future__ import annotations

import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ai_fiction_to_script import __version__
from ai_fiction_to_script.models.schema import ScreenplayDocument
from ai_fiction_to_script.pipeline.engine import AdaptationEngine
from ai_fiction_to_script.services.ai_client import MockAIClient, QwenAIClient
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore
from ai_fiction_to_script.services.workbench import WorkbenchService
from ai_fiction_to_script.services.yaml_service import load_yaml, write_schema, write_yaml
from ai_fiction_to_script.settings import QwenSettings
from ai_fiction_to_script.web.server import run_server
from ai_fiction_to_script.models.runtime import AdaptationRequest

app = typer.Typer(help="AI Fiction to Script CLI.")
console = Console()


@app.callback()
def main() -> None:
    """CLI entrypoint."""


@app.command("adapt")
def adapt(
    input_path: Path = typer.Argument(..., help="Novel text file or a directory of chapter files."),
    title: str = typer.Option("", help="Screenplay title."),
    original_author: str = typer.Option("unknown-author", help="Original novel author."),
    original_title: str = typer.Option("", help="Original novel title."),
    project_id: str = typer.Option("", help="Project identifier used by the local version store."),
    target_format: str = typer.Option("tv_drama", help="Target format: film, tv_drama, short_drama, stage_play."),
    genre: str = typer.Option("", help="Comma-separated genres."),
    tone: str = typer.Option("balanced", help="Overall tone."),
    provider: str = typer.Option("mock", help="AI provider: mock or qwen."),
    output: Path = typer.Option(Path("output/screenplay.yaml"), help="Where to write the generated YAML."),
    version_root: Path = typer.Option(Path(".novel2script"), help="Local version store root."),
    note: str = typer.Option("", help="Version note saved into the local version store."),
) -> None:
    resolved_title = title or input_path.stem
    resolved_original_title = original_title or resolved_title
    resolved_project_id = project_id or _slugify(resolved_title)
    request = AdaptationRequest(
        project_id=resolved_project_id,
        title=resolved_title,
        original_novel_title=resolved_original_title,
        original_author=original_author,
        target_format=target_format,
        genre=_split_csv(genre),
        tone=tone,
        provider=provider,
    )

    engine = AdaptationEngine(
        parser=ChapterParser(),
        ai_client=_build_ai_client(provider),
        quality_checker=QualityChecker(),
        version_store=VersionStore(version_root),
    )
    result = engine.run(input_path=input_path, request=request, note=note)
    write_yaml(result.document, output)

    console.print(f"[green]YAML written to[/green] {output}")
    if result.version:
        console.print(f"[green]Saved version[/green] {result.version.version_id} -> {result.version.script_yaml_path}")
    console.print(f"[cyan]Quality confidence[/cyan] {result.document.quality.confidence}")
    for warning in result.document.quality.warnings:
        console.print(f"[yellow]- {warning}[/yellow]")


@app.command("validate")
def validate(script_path: Path = typer.Argument(..., help="YAML screenplay path.")) -> None:
    document = load_yaml(script_path)
    quality = QualityChecker().review(document)
    console.print(f"[green]Schema validation passed[/green] {script_path}")
    console.print(f"[cyan]Confidence[/cyan] {quality.confidence}")
    if quality.warnings:
        for warning in quality.warnings:
            console.print(f"[yellow]- {warning}[/yellow]")


@app.command("list-versions")
def list_versions(
    project_id: str = typer.Argument(..., help="Project identifier."),
    version_root: Path = typer.Option(Path(".novel2script"), help="Local version store root."),
) -> None:
    versions = WorkbenchService(version_root).list_versions(project_id)
    table = Table(title=f"{project_id} versions")
    table.add_column("Version")
    table.add_column("Created At")
    table.add_column("Note")
    for version in versions:
        table.add_row(version["version_id"], version["created_at"], version["note"])
    console.print(table)


@app.command("diff")
def diff_versions(
    project_id: str = typer.Argument(..., help="Project identifier."),
    version_a: str = typer.Argument(..., help="Base version."),
    version_b: str = typer.Argument(..., help="Target version."),
    version_root: Path = typer.Option(Path(".novel2script"), help="Local version store root."),
) -> None:
    diff_text = WorkbenchService(version_root).diff_versions(project_id, version_a, version_b)["diff"]
    console.print(diff_text or "[green]No differences between the selected versions.[/green]")


@app.command("regenerate-scene")
def regenerate_scene(
    project_id: str = typer.Argument(..., help="Project identifier."),
    version_id: str = typer.Argument(..., help="Base version ID."),
    scene_id: str = typer.Argument(..., help="Scene ID to regenerate."),
    instruction: str = typer.Option("", help="Additional rewrite instruction."),
    provider: str = typer.Option("", help="Override AI provider: mock or qwen."),
    version_root: Path = typer.Option(Path(".novel2script"), help="Local version store root."),
    note: str = typer.Option("", help="Version note."),
) -> None:
    payload = WorkbenchService(version_root).regenerate_scene(
        project_id=project_id,
        version_id=version_id,
        scene_id=scene_id,
        instruction=instruction,
        provider_override=provider,
        note=note,
    )
    console.print(f"[green]Scene regenerated[/green] {scene_id} -> {payload['version']['version_id']}")


@app.command("export-schema")
def export_schema(
    output: Path = typer.Option(Path("schemas/screenplay.schema.json"), help="JSON Schema output path."),
) -> None:
    target = write_schema(output)
    console.print(f"[green]JSON Schema exported[/green] {target}")


@app.command("web")
def web(
    host: str = typer.Option("127.0.0.1", help="Host interface to bind."),
    port: int = typer.Option(8098, help="Port to listen on."),
    version_root: Path = typer.Option(Path(".novel2script"), help="Local version store root."),
) -> None:
    console.print(f"[green]Starting web console[/green] http://{host}:{port}")
    run_server(host=host, port=port, version_root=version_root)


@app.command("version")
def show_version() -> None:
    console.print(__version__)


def _build_ai_client(provider: str):
    if provider == "mock":
        return MockAIClient()
    if provider == "qwen":
        return QwenAIClient(QwenSettings.from_env())
    raise typer.BadParameter(f"Unsupported provider: {provider}")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.strip())
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-") or "novel-project"


if __name__ == "__main__":
    app()
