# Screenplay YAML Schema Design

This document defines the project screenplay YAML contract and explains why the schema is structured this way.

## Goal

The schema is designed for novel authors who want a fast, editable first screenplay draft from at least 3 source chapters. It must support:

- Editable screenplay text in YAML.
- Traceability from scenes back to source chapters.
- Programmatic validation before export or regeneration.
- Iterative rewriting of individual scenes without regenerating the whole project.

## Top-Level Shape

```yaml
schema_version: "2.0"
meta: {}
source: {}
adaptation: {}
story_bible: {}
outline: {}
script: {}
quality: {}
extensions: {}
```

## Field Design

`meta` identifies the project, source work, target format, language, tone, provider, and model. It exists so exported YAML files remain self-describing outside the application.

`source` stores source chapter metadata, not the whole novel body by default. This keeps normal exports compact while preserving chapter IDs for traceability.

`adaptation` records the creative brief: target format, compression policy, pacing policy, structure type, and style guide. This makes later regeneration deterministic enough to stay aligned with the author's intent.

`story_bible` contains reusable story facts: logline, synopsis, themes, characters, locations, timeline, and props. This separates story understanding from screenplay wording, so editors can adjust core facts independently from scenes.

`outline` contains act and scene plans. It is the planning layer between source understanding and generated screenplay text.

`script` contains the actual screenplay draft. It is organized as acts, scenes, and beats. Beat types are limited to `action`, `dialogue`, `transition`, and `narration` so the output stays easy to edit and validate.

`quality` stores confidence, warnings, revision suggestions, and continuity checks. AI-generated drafts need explicit review signals rather than hiding uncertainty.

`extensions` is reserved for product features that should not break the core schema. Current examples include ingestion metadata, production notes, and regeneration bundles.

## Reference Rules

The schema uses stable IDs instead of names for cross references:

- `chapter_id` links scenes and source references to original chapters.
- `character_id` links dialogue beats to speakers.
- `location_id` links scenes to story locations.
- `scene_id` links outline plans to final script scenes.

Stable IDs are required because names can be duplicated, renamed, or translated during adaptation.

## Minimum Valid Draft

A valid generated draft must contain:

- `source.chapter_count >= 3`
- At least 3 `source.chapters`
- At least one `outline.act`
- At least one `outline.scene_plan`
- At least one `script.act`
- Valid references from scenes and beats back to source chapters, characters, and locations

## Implementation

- Pydantic schema: `src/ai_fiction_to_script/models/schema.py`
- Runtime request models: `src/ai_fiction_to_script/models/runtime.py`
- JSON Schema export command:

```powershell
python -m ai_fiction_to_script.cli export-schema --output schemas/screenplay.schema.json
```

## Why YAML

YAML is used because authors and editors can read and modify it directly, while the application can still validate it through a strict Pydantic/JSON Schema model. This balances human editability with machine reliability.
