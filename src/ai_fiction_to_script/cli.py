from __future__ import annotations

import re
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ai_fiction_to_script import __version__
from ai_fiction_to_script.models.runtime import AdaptationRequest, ModelRouting
from ai_fiction_to_script.pipeline.engine import AdaptationEngine
from ai_fiction_to_script.services.presets import build_adaptation_goal, build_style_guide_for_tone
from ai_fiction_to_script.services.ai_client import MockAIClient, QwenAIClient
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore
from ai_fiction_to_script.services.workbench import WorkbenchService
from ai_fiction_to_script.services.yaml_service import load_yaml, write_schema, write_yaml
from ai_fiction_to_script.settings import QwenSettings
from ai_fiction_to_script.web.server import run_server

app = typer.Typer(help="AI Fiction to Script CLI.")
console = Console()


@app.callback()
def main() -> None:
    """CLI entrypoint."""
    _configure_utf8_stdio()


@app.command("adapt")
def adapt(
    input_path: Path = typer.Argument(..., help="Novel text file or a directory of chapter files."),
    title: str = typer.Option("", "--title", "-t", help="Screenplay title."),
    original_author: str = typer.Option("unknown-author", "--original-author", "-a", help="Original novel author."),
    original_title: str = typer.Option("", "--original-title", help="Original novel title."),
    project_id: str = typer.Option("", "--project-id", help="Project identifier used by the local version store."),
    target_format: str = typer.Option("tv_drama", "--target-format", "--type", help="Target format: film, tv_drama, short_drama, stage_play."),
    genre: str = typer.Option("", "--genre", "-g", help="Comma-separated genres."),
    tone: str = typer.Option("balanced", "--tone", help="Overall tone."),
    provider: str = typer.Option("mock", "--provider", "-p", help="AI provider: mock or qwen."),
    model_name: str = typer.Option("", "--model", "--model-name", help="Qwen model name, e.g. qwen3.6-flash."),
    detail_level: str = typer.Option("standard", "--detail", help="Generation detail: fast, standard, detailed."),
    output: Path = typer.Option(Path("output/screenplay.yaml"), "--output", "-o", help="Where to write the generated YAML."),
    version_root: Path = typer.Option(Path(".novel2script"), "--version-root", help="Local version store root."),
    note: str = typer.Option("", "--note", "-n", help="Version note saved into the local version store."),
) -> None:
    request = _build_request(
        input_path=input_path,
        title=title,
        original_author=original_author,
        original_title=original_title,
        project_id=project_id,
        target_format=target_format,
        genre=genre,
        tone=tone,
        provider=_resolve_provider(provider),
        model_name=model_name,
        detail_level=detail_level,
    )
    _run_adaptation(input_path, request, output, version_root, note)


@app.command("quick")
def quick(
    input_path: Path = typer.Argument(..., help="Novel text file or a directory of chapter files."),
    title: str = typer.Option("", "--title", "-t", help="Screenplay title. Defaults to the input filename."),
    provider: str = typer.Option("auto", "--provider", "-p", help="AI provider: auto, mock, or qwen."),
    output_dir: Path = typer.Option(Path("output"), "--output-dir", "-d", help="Directory for the generated YAML."),
    model_name: str = typer.Option("", "--model", "--model-name", help="Qwen model name, e.g. qwen3.6-flash."),
    detail_level: str = typer.Option("standard", "--detail", help="Generation detail: fast, standard, detailed."),
    original_author: str = typer.Option("unknown-author", "--author", "-a", help="Original novel author."),
    note: str = typer.Option("", "--note", "-n", help="Version note saved into the local version store."),
    version_root: Path = typer.Option(Path(".novel2script"), "--version-root", help="Local version store root."),
) -> None:
    resolved_provider = _resolve_provider(provider)
    request = _build_request(
        input_path=input_path,
        title=title,
        original_author=original_author,
        original_title="",
        project_id="",
        target_format="tv_drama",
        genre="",
        tone="balanced",
        provider=resolved_provider,
        model_name=model_name,
        detail_level=detail_level,
    )
    output = output_dir / f"{request.project_id}.yaml"
    _run_adaptation(input_path, request, output, version_root, note)
    console.print(f"[cyan]Next[/cyan] validate with: novel2script validate {output}")


def _run_adaptation(
    input_path: Path,
    request: AdaptationRequest,
    output: Path,
    version_root: Path,
    note: str,
) -> None:
    engine = AdaptationEngine(
        parser=ChapterParser(),
        ai_client=_build_ai_client(request.provider),
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


def _build_request(
    input_path: Path,
    title: str,
    original_author: str,
    original_title: str,
    project_id: str,
    target_format: str,
    genre: str,
    tone: str,
    provider: str,
    model_name: str,
    detail_level: str,
) -> AdaptationRequest:
    resolved_title = title or input_path.stem
    resolved_detail = _normalize_detail_level(detail_level)
    detail_config = _detail_config(resolved_detail)
    return AdaptationRequest(
        project_id=project_id or _slugify(resolved_title),
        title=resolved_title,
        original_novel_title=original_title or resolved_title,
        original_author=original_author,
        target_format=target_format,
        genre=_split_csv(genre),
        tone=tone,
        adaptation_goal=build_adaptation_goal(target_format),
        style_guide=build_style_guide_for_tone(tone),
        provider=provider,
        model_name=model_name,
        model_routing=_model_routing(provider, model_name),
        temperature=0.2 if resolved_detail == "fast" else 0.3,
        max_scenes_per_chapter=detail_config["max_scenes_per_chapter"],
        detail_level=resolved_detail,
        max_beats_per_scene=detail_config["max_beats_per_scene"],
        chapter_context_chars=detail_config["chapter_context_chars"],
    )


def _resolve_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized == "auto":
        settings = QwenSettings.from_env()
        return "qwen" if settings.api_key else "mock"
    return normalized


def _normalize_detail_level(value: str) -> str:
    aliases = {
        "quick": "fast",
        "speed": "fast",
        "fast": "fast",
        "standard": "standard",
        "normal": "standard",
        "balanced": "standard",
        "detail": "detailed",
        "detailed": "detailed",
        "rich": "detailed",
        "full": "detailed",
    }
    normalized = value.strip().lower()
    if normalized not in aliases:
        raise typer.BadParameter("detail must be one of: fast, standard, detailed")
    return aliases[normalized]


def _detail_config(detail_level: str) -> dict[str, int]:
    if detail_level == "fast":
        return {"max_scenes_per_chapter": 1, "max_beats_per_scene": 6, "chapter_context_chars": 600}
    if detail_level == "detailed":
        return {"max_scenes_per_chapter": 1, "max_beats_per_scene": 12, "chapter_context_chars": 1600}
    return {"max_scenes_per_chapter": 1, "max_beats_per_scene": 10, "chapter_context_chars": 1200}


def _model_routing(provider: str, model_name: str) -> ModelRouting:
    if provider != "qwen":
        return ModelRouting()
    selected_model = model_name or "qwen3.6-flash"
    return ModelRouting(
        summary_model=selected_model,
        planning_model=selected_model,
        generation_model=selected_model,
        validation_model=selected_model,
    )


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.strip())
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-") or "novel-project"


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    app()
