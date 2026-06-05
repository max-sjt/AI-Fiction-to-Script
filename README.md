# AI Fiction to Script

`AI Fiction to Script` is a modular Qwen-powered tool that converts novels with at least three chapters into structured, editable YAML screenplay drafts.

The project follows a staged pipeline:

1. Understand the source chapters
2. Build a story bible
3. Plan the screenplay outline
4. Generate scene-level screenplay content
5. Validate structure and continuity

## Current Version

- `v0.4.0`
- Includes CLI workflow, local version store, schema export, scene regeneration, and a visual Web workbench

## Core Features

- Convert fiction into structured YAML screenplay drafts
- Preserve chapter references for traceability
- Save every generated result into a local version store
- Compare versions with unified diffs
- Regenerate a single scene without rerunning the whole project
- Edit YAML directly in a browser-based workbench

## Project Layout

- `src/ai_fiction_to_script/models/`: Pydantic schema and runtime models
- `src/ai_fiction_to_script/services/`: parsing, generation, validation, versioning, and workbench services
- `src/ai_fiction_to_script/pipeline/`: orchestration engine
- `src/ai_fiction_to_script/web/`: lightweight Web server and static UI assets
- `docs/`: architecture and schema documentation
- `examples/`: sample inputs
- `tests/`: CLI, pipeline, and Web API tests

## Install

```bash
pip install -e .
```

If you already installed an older editable version, rerun the same command after pulling the latest changes so the new `web` command is available.

## Qwen Configuration

Set your DashScope / Qwen API key before using the live provider:

```bash
set DASHSCOPE_API_KEY=your_key_here
```

Optional environment variables:

- `QWEN_BASE_URL`
- `QWEN_TIMEOUT_SECONDS`

## CLI Usage

Generate a draft from a text file:

```bash
novel2script adapt examples/sample_novel.txt --title OldStreetEcho --original-author DemoAuthor --project-id demo-project
```

List saved versions:

```bash
novel2script list-versions demo-project
```

Regenerate one scene:

```bash
novel2script regenerate-scene demo-project v0001 s001 --instruction "Increase the protagonist's urgency."
```

Export the JSON Schema:

```bash
novel2script export-schema --output schemas/screenplay.schema.json
```

## Web Workbench

Start the visual workbench:

```bash
novel2script web --host 127.0.0.1 --port 8098
```

Then open:

```text
http://127.0.0.1:8098
```

The workbench supports:

- draft generation from a file path or pasted novel text
- project and version browsing
- direct YAML editing and save-as-new-version
- version diff inspection
- scene-level regeneration with extra instructions

## Local Versioning

The tool keeps two layers of versioning:

- source code versioning: Git branches, commits, and tags
- screenplay artifact versioning: `.novel2script/<project>/versions/v000x/`

Each saved version contains:

- `screenplay.yaml`
- `screenplay.json`
- `intermediates/*.json`
- `index.json`

## Validation

Run the test suite:

```bash
python -m pytest -q
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [YAML Schema](docs/YAML_SCHEMA.md)
- [Changelog](CHANGELOG.md)
