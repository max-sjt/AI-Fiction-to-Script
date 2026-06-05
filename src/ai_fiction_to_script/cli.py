from __future__ import annotations

import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ai_fiction_to_script import __version__
from ai_fiction_to_script.models.runtime import AdaptationRequest, ParsedChapter
from ai_fiction_to_script.models.schema import Outline, ScenePlan, Script, ScriptAct, StoryBible
from ai_fiction_to_script.pipeline.engine import AdaptationEngine
from ai_fiction_to_script.services.ai_client import MockAIClient, QwenAIClient
from ai_fiction_to_script.services.chapter_parser import ChapterParser
from ai_fiction_to_script.services.quality_checker import QualityChecker
from ai_fiction_to_script.services.version_store import VersionStore
from ai_fiction_to_script.services.yaml_service import load_yaml, write_schema, write_yaml
from ai_fiction_to_script.settings import QwenSettings

app = typer.Typer(help="AI Fiction to Script CLI.")
console = Console()


@app.callback()
def main() -> None:
    """CLI entrypoint."""


@app.command("adapt")
def adapt(
    input_path: Path = typer.Argument(..., help="Novel text file or a directory of chapter files."),
    title: str = typer.Option("", help="Screenplay title."),
    original_author: str = typer.Option("未知作者", help="Original novel author."),
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

    ai_client = _build_ai_client(provider)
    engine = AdaptationEngine(
        parser=ChapterParser(),
        ai_client=ai_client,
        quality_checker=QualityChecker(),
        version_store=VersionStore(version_root),
    )
    result = engine.run(input_path=input_path, request=request, note=note)
    write_yaml(result.document, output)

    console.print(f"[green]YAML 已输出到[/green] {output}")
    if result.version:
        console.print(f"[green]版本已保存[/green] {result.version.version_id} -> {result.version.script_yaml_path}")
    console.print(f"[cyan]质量置信度[/cyan] {result.document.quality.confidence}")
    for warning in result.document.quality.warnings:
        console.print(f"[yellow]- {warning}[/yellow]")


@app.command("validate")
def validate(script_path: Path = typer.Argument(..., help="YAML screenplay path.")) -> None:
    document = load_yaml(script_path)
    quality = QualityChecker().review(document)
    console.print(f"[green]Schema 验证通过[/green] {script_path}")
    console.print(f"[cyan]置信度[/cyan] {quality.confidence}")
    if quality.warnings:
        for warning in quality.warnings:
            console.print(f"[yellow]- {warning}[/yellow]")


@app.command("list-versions")
def list_versions(
    project_id: str = typer.Argument(..., help="Project identifier."),
    version_root: Path = typer.Option(Path(".novel2script"), help="Local version store root."),
) -> None:
    versions = VersionStore(version_root).list_versions(project_id)
    table = Table(title=f"{project_id} versions")
    table.add_column("Version")
    table.add_column("Created At")
    table.add_column("Note")
    for version in versions:
        table.add_row(version.version_id, version.created_at, version.note)
    console.print(table)


@app.command("diff")
def diff_versions(
    project_id: str = typer.Argument(..., help="Project identifier."),
    version_a: str = typer.Argument(..., help="Base version."),
    version_b: str = typer.Argument(..., help="Target version."),
    version_root: Path = typer.Option(Path(".novel2script"), help="Local version store root."),
) -> None:
    diff_text = VersionStore(version_root).diff(project_id, version_a, version_b)
    console.print(diff_text or "[green]两个版本没有差异。[/green]")


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
    store = VersionStore(version_root)
    document = store.load_document(project_id, version_id)
    request = AdaptationRequest.model_validate(store.load_intermediate(project_id, version_id, "request"))
    if provider:
        request = request.model_copy(update={"provider": provider})
    chapters = [ParsedChapter.model_validate(item) for item in store.load_intermediate(project_id, version_id, "chapters")]
    outline = Outline.model_validate(store.load_intermediate(project_id, version_id, "outline"))
    story_bible = StoryBible.model_validate(store.load_intermediate(project_id, version_id, "story_bible"))
    scene_plan = _find_scene_plan(outline.scene_plans, scene_id)
    if instruction:
        scene_plan = scene_plan.model_copy(
            update={
                "objective": f"{scene_plan.objective}；附加要求：{instruction}",
                "notes": f"{scene_plan.notes} | {instruction}".strip(),
            }
        )
    chapter = _resolve_scene_source(scene_plan, chapters)
    scene = _build_ai_client(request.provider).generate_scene(scene_plan, story_bible, chapter, request)
    updated_script = _replace_scene(document.script, scene_plan.act_id, scene_id, scene)
    updated_document = document.model_copy(update={"script": updated_script})
    quality = QualityChecker().review(updated_document)
    ai_warnings, ai_suggestions = _build_ai_client(request.provider).review_document(updated_document, request)
    quality.warnings = _merge_unique(quality.warnings, ai_warnings)
    quality.revision_suggestions = _merge_unique(quality.revision_suggestions, ai_suggestions)
    updated_document = updated_document.model_copy(update={"quality": quality})

    version = store.save(
        project_id,
        updated_document,
        intermediates={
            "request": request.model_dump(mode="json"),
            "chapters": [chapter.model_dump(mode="json") for chapter in chapters],
            "story_bible": story_bible.model_dump(mode="json"),
            "outline": outline.model_dump(mode="json"),
        },
        note=note or f"regenerate {scene_id}",
    )
    console.print(f"[green]场景已重生成[/green] {scene_id} -> {version.version_id}")


@app.command("export-schema")
def export_schema(
    output: Path = typer.Option(Path("schemas/screenplay.schema.json"), help="JSON Schema output path."),
) -> None:
    target = write_schema(output)
    console.print(f"[green]JSON Schema 已导出[/green] {target}")


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


def _find_scene_plan(scene_plans: list[ScenePlan], scene_id: str) -> ScenePlan:
    for scene_plan in scene_plans:
        if scene_plan.scene_id == scene_id:
            return scene_plan
    raise typer.BadParameter(f"Scene plan not found: {scene_id}")


def _resolve_scene_source(scene_plan: ScenePlan, chapters: list[ParsedChapter]) -> ParsedChapter:
    chapter_map = {chapter.chapter_id: chapter for chapter in chapters}
    for chapter_id in scene_plan.chapter_refs:
        if chapter_id in chapter_map:
            return chapter_map[chapter_id]
    return chapters[0]


def _replace_scene(script: Script, act_id: str, scene_id: str, replacement) -> Script:
    acts: list[ScriptAct] = []
    replaced = False
    for act in script.acts:
        scenes = []
        for scene in act.scenes:
            if act.act_id == act_id and scene.scene_id == scene_id:
                scenes.append(replacement)
                replaced = True
            else:
                scenes.append(scene)
        acts.append(ScriptAct(act_id=act.act_id, title=act.title, scenes=scenes))
    if not replaced:
        raise typer.BadParameter(f"Scene not found in script: {scene_id}")
    return Script(acts=acts)


def _merge_unique(base: list[str], new_items: list[str]) -> list[str]:
    output = list(base)
    for item in new_items:
        if item and item not in output:
            output.append(item)
    return output


if __name__ == "__main__":
    app()
