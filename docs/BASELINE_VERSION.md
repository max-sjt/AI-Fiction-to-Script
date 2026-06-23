# Baseline Version

Base version: `v0.4.0`

This baseline records the refactored local version used before the next round of feature work. It is intended as the stable reference for rollback, comparison, and future release notes.

## Scope

- Minimum input: 3 or more novel chapters.
- Output format: editable `ScreenplayDocument` YAML, schema version `2.0`.
- Runtime entry points: Web workbench and CLI.
- Storage: local project versions under `.novel2script/<project>/versions/v000x/`.
- Model provider path: mock local generation and Alibaba Cloud Bailian / DashScope Qwen compatible generation.

## Added Since Previous Working Build

- Web model selector that can load available Bailian models through the configured OpenAI-compatible `/models` endpoint.
- Request-level `model_name` support so generation, YAML regeneration, and scene regeneration can use the selected model.
- UTF-8-safe CLI output and task error logging for non-ASCII Chinese content.
- Concurrent chapter analysis and scene generation in the pipeline to reduce total generation time.
- Schema design documentation in `docs/SCREENPLAY_YAML_SCHEMA_DESIGN.md`.

## Versioning Rules

- Treat `v0.4.0` as the base tag for this refactor.
- Keep generated project versions immutable once written; create a new `v000x` folder for each edit or regeneration.
- Keep intermediate data (`request`, `chapters`, `chapter_analyses`, `story_bible`, `outline`) with each generated version so future regeneration can reproduce context.
- Record user-facing behavior changes in this document or a changelog before moving to the next base version.

## Suggested Git Marker

After reviewing the changes, create a local tag if you want a Git-level rollback point:

```powershell
git tag v0.4.0-base
```
