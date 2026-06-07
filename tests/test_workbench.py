from __future__ import annotations

from pathlib import Path
from time import sleep

import pytest

from ai_fiction_to_script.models.runtime import ModelRouting
from ai_fiction_to_script.models.schema import Beat, CharacterCard, Scene, SceneTransition, Script, ScriptAct, SourceRef
from ai_fiction_to_script.services.ai_client import HybridAIClient, MockAIClient
from ai_fiction_to_script.services.cache_store import InMemoryCacheStore
from ai_fiction_to_script.services.workbench import WorkbenchService


def sample_novel_text() -> str:
    return (Path(__file__).resolve().parents[1] / "examples" / "sample_novel.txt").read_text(encoding="utf-8")


def test_workbench_uses_unicode_title_as_project_id(tmp_path) -> None:
    payload = WorkbenchService(tmp_path / ".novel2script").adapt(
        {
            "title": "中文标题项目",
            "original_author": "测试作者",
            "original_title": "中文标题原著",
            "script_type": "tv_drama",
            "tone": "balanced",
            "genre": "悬疑",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )

    assert payload["project_id"] == "中文标题项目"
    assert payload["document"]["schema_version"] == "2.0"
    assert payload["document"]["source"]["chapter_count"] == 3


def test_workbench_rejects_single_chapter_text(tmp_path) -> None:
    with pytest.raises(ValueError, match="不足 3 章"):
        WorkbenchService(tmp_path / ".novel2script").adapt(
            {
                "title": "单章项目",
                "original_author": "测试作者",
                "original_title": "单章原著",
                "script_type": "film",
                "tone": "serious",
                "genre": "悬疑",
                "novel_text": "第三章：屋顶对峙\n\n林然赶到天台，却发现真正的交易刚开始。",
                "provider": "mock",
            }
        )


def test_workbench_uses_faster_qwen_routing_for_web_requests(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")

    routing = service._web_model_routing("qwen")

    assert isinstance(routing, ModelRouting)
    assert routing.summary_model == "qwen3.6-flash"
    assert routing.planning_model == "qwen3.6-flash"
    assert routing.generation_model == "qwen3.6-flash"
    assert routing.validation_model == "qwen3.6-flash"


def test_workbench_defaults_qwen_web_requests_to_fast_scene_density(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")

    fast_request = service._build_request_from_payload(
        {
            "title": "fast-demo",
            "script_type": "short_drama",
            "provider": "qwen",
        }
    )
    balanced_request = service._build_request_from_payload(
        {
            "title": "balanced-demo",
            "script_type": "short_drama",
            "provider": "qwen",
            "speed_mode": "balanced",
        }
    )

    assert fast_request.max_scenes_per_chapter == 1
    assert fast_request.temperature == 0.2
    assert balanced_request.max_scenes_per_chapter == 2
    assert balanced_request.temperature == 0.3


def test_workbench_uses_hybrid_qwen_client_for_web_speed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "demo-key")
    service = WorkbenchService(tmp_path / ".novel2script")

    client = service._build_ai_client("qwen")

    assert isinstance(client, HybridAIClient)


def test_workbench_async_adapt_returns_preview_then_final(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": MockAIClient())

    payload = service.start_adapt_async(
        {
            "title": "异步项目",
            "original_author": "测试作者",
            "original_title": "异步原著",
            "script_type": "film",
            "tone": "serious",
            "genre": "悬疑",
            "novel_text": sample_novel_text(),
            "provider": "qwen",
            "api_key": "demo-key",
        }
    )

    assert payload["preview"]["version"]["version_id"] == "preview"
    assert payload["preview"]["document"]["schema_version"] == "2.0"
    task_id = payload["task"]["task_id"]

    for _ in range(20):
        task = service.get_task_status(task_id)
        if task["status"] == "completed":
            break
        sleep(0.05)
    else:
        raise AssertionError("async adapt task did not complete in time")

    assert task["final_version_id"] == "v0001"
    assert task["result"]["version"]["version_id"] == "v0001"
    assert [item["version_id"] for item in service.list_versions(payload["preview"]["project_id"])] == ["v0001"]


def test_workbench_fast_qwen_async_prefers_whole_script_generation(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    used_whole_script_path = {"value": False}

    class FakeFastClient:
        def generate_script_stream(self, outline, story_bible, chapters, request, on_delta=None):
            used_whole_script_path["value"] = True
            if on_delta is not None:
                on_delta('{"scenes":[', '{"scenes":[')
            scenes = []
            for scene_plan in outline.scene_plans:
                scenes.append(
                    Scene(
                        scene_id=scene_plan.scene_id,
                        title=scene_plan.title,
                        chapter_refs=scene_plan.chapter_refs,
                        time_of_day="day",
                        objective=scene_plan.objective,
                        summary=scene_plan.notes or scene_plan.objective,
                        beats=[Beat(beat_id="b001", type="action", text=scene_plan.focus_event or scene_plan.objective)],
                        transitions=SceneTransition(next_scene_hint=scene_plan.bridge_out, transition_type="cut"),
                        source_refs=[SourceRef(chapter_id=scene_plan.chapter_refs[0], excerpt_id="p001")],
                    )
                )
            return Script(acts=[ScriptAct(act_id="main", title="正文", scenes=scenes)])

        def review_document(self, document, request):
            return [], []

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": FakeFastClient())

    payload = service.start_adapt_async(
        {
            "title": "fast-whole-script",
            "original_author": "tester",
            "original_title": "fast-whole-script",
            "script_type": "film",
            "tone": "serious",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "qwen",
            "api_key": "demo-key",
            "speed_mode": "fast",
        }
    )

    task_id = payload["task"]["task_id"]
    for _ in range(20):
        task = service.get_task_status(task_id)
        if task["status"] == "completed":
            break
        sleep(0.05)
    else:
        raise AssertionError("async adapt task did not complete in time")

    assert used_whole_script_path["value"] is True
    assert task["final_version_id"] == "v0001"


def test_workbench_exports_compact_yaml_bundle_with_embedded_source_text(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    payload = service.adapt(
        {
            "title": "yaml-export-demo",
            "original_author": "tester",
            "original_title": "yaml-export-demo",
            "script_type": "film",
            "tone": "balanced",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )

    yaml_text = service.export_version_yaml(payload["project_id"], payload["version"]["version_id"])

    assert "story_bible:" not in yaml_text
    assert "outline:" not in yaml_text
    assert "quality:" not in yaml_text
    assert "extensions:" not in yaml_text
    assert "text:" in yaml_text
    assert "scenes:" in yaml_text


def test_workbench_can_regenerate_from_uploaded_yaml_bundle(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    initial = service.adapt(
        {
            "title": "yaml-regen-demo",
            "original_author": "tester",
            "original_title": "yaml-regen-demo",
            "script_type": "film",
            "tone": "balanced",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )
    bundle_yaml = service.export_version_yaml(initial["project_id"], initial["version"]["version_id"])
    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": MockAIClient())

    payload = service.start_regenerate_from_yaml_async(
        {
            "yaml_text": bundle_yaml,
            "provider": "qwen",
            "api_key": "demo-key",
            "speed_mode": "fast",
        }
    )

    task_id = payload["task"]["task_id"]
    for _ in range(20):
        task = service.get_task_status(task_id)
        if task["status"] == "completed":
            break
        sleep(0.05)
    else:
        raise AssertionError("yaml regeneration task did not complete in time")

    assert task["final_version_id"] == "v0002"
    assert task["result"]["project_id"] == initial["project_id"]


def test_workbench_async_regenerate_returns_preview_then_final(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    initial = service.adapt(
        {
            "title": "异步重生成",
            "original_author": "测试作者",
            "original_title": "异步重生成",
            "script_type": "film",
            "tone": "serious",
            "genre": "悬疑",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )
    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": MockAIClient())

    payload = service.start_regenerate_scene_async(
        project_id=initial["project_id"],
        version_id=initial["version"]["version_id"],
        scene_id=initial["scene_options"][0]["scene_id"],
        instruction="让主角更急迫",
        provider_override="qwen",
        api_key="demo-key",
        tone_override="angry",
    )

    assert payload["preview"]["version"]["version_id"] == "v0001"
    assert payload["preview"]["scene_comparison"]["instruction"] == "让主角更急迫"
    task_id = payload["task"]["task_id"]

    for _ in range(20):
        task = service.get_task_status(task_id)
        if task["status"] == "completed":
            break
        sleep(0.05)
    else:
        raise AssertionError("async regenerate task did not complete in time")

    assert task["final_version_id"] == "v0002"
    assert task["result"]["scene_comparison"]["scene_id"] == initial["scene_options"][0]["scene_id"]
    assert [item["version_id"] for item in service.list_versions(initial["project_id"])] == ["v0001", "v0002"]


def test_workbench_refreshes_stale_cached_yaml_payload(tmp_path) -> None:
    cache = InMemoryCacheStore()
    service = WorkbenchService(tmp_path / ".novel2script", cache_store=cache)
    payload = service.adapt(
        {
            "title": "缓存升级项目",
            "original_author": "测试作者",
            "original_title": "缓存升级原著",
            "script_type": "film",
            "tone": "serious",
            "genre": "悬疑",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )
    key = f"projects:{payload['project_id']}:versions:{payload['version']['version_id']}:payload"
    stale = dict(payload)
    stale["document"] = dict(stale["document"])
    stale["document"]["schema_version"] = "1.0"
    stale["yaml_text"] = stale["yaml_text"].replace('schema_version: "2.0"', "schema_version: '1.0'")
    cache.set_json(key, stale, 60)

    refreshed = service.get_version_payload(payload["project_id"], payload["version"]["version_id"])

    assert refreshed["document"]["schema_version"] == "2.0"
    assert "schema_version:" in refreshed["yaml_text"]
    assert "2.0" in refreshed["yaml_text"]


def test_workbench_regenerate_scene_sanitizes_unknown_speaker_refs(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    initial = service.adapt(
        {
            "title": "speaker-sanitize",
            "original_author": "tester",
            "original_title": "speaker-sanitize",
            "script_type": "film",
            "tone": "serious",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )

    class FakeClient:
        def generate_scene(self, scene_plan, story_bible, chapter, request):
            return Scene(
                scene_id=scene_plan.scene_id,
                title=scene_plan.title,
                chapter_refs=scene_plan.chapter_refs,
                location_ref="unknown-place",
                time_of_day="night",
                objective=scene_plan.objective,
                summary="summary",
                beats=[
                    Beat(beat_id="b001", type="dialogue", text="来客：现在开始。", speaker_ref="来客"),
                    Beat(beat_id="b002", type="action", text="The clock starts moving."),
                ],
                transitions=SceneTransition(next_scene_hint="Cut away", transition_type="cut"),
                source_refs=[SourceRef(chapter_id=scene_plan.chapter_refs[0], excerpt_id="p001")],
            )

        def review_document(self, document, request):
            return [], []

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": FakeClient())

    regenerated = service.regenerate_scene(
        project_id=initial["project_id"],
        version_id=initial["version"]["version_id"],
        scene_id=initial["scene_options"][0]["scene_id"],
        provider_override="qwen",
        api_key="demo-key",
    )

    first_scene = regenerated["document"]["script"]["acts"][0]["scenes"][0]
    first_plan = regenerated["document"]["outline"]["scene_plans"][0]
    assert first_scene["beats"][0]["speaker_ref"] is None
    assert first_scene["location_ref"] is None
    assert first_plan["title"] == first_scene["title"]


def test_workbench_rendered_screenplay_omits_act_headings_and_future_scenes(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    payload = service.adapt(
        {
            "title": "render-cleanup",
            "original_author": "tester",
            "original_title": "render-cleanup",
            "script_type": "film",
            "tone": "balanced",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )

    rendered = payload["rendered_script"]
    assert "A1 " not in rendered
    assert "A2 " not in rendered
    assert "A3 " not in rendered
    assert "戏剧目标：" not in rendered

    document = service.version_store.load_document(payload["project_id"], payload["version"]["version_id"])
    first_scene_id = document.script.acts[0].scenes[0].scene_id
    partial = service._render_screenplay_progress(document, document.script, {first_scene_id})

    assert f"[{first_scene_id}]" in partial
    assert "[s002]" not in partial


def test_workbench_render_beat_avoids_duplicate_dialogue_prefix(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    payload = service.adapt(
        {
            "title": "dialogue-cleanup",
            "original_author": "tester",
            "original_title": "dialogue-cleanup",
            "script_type": "film",
            "tone": "balanced",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )

    document = service.version_store.load_document(payload["project_id"], payload["version"]["version_id"])
    document = document.model_copy(
        update={
            "story_bible": document.story_bible.model_copy(
                update={"characters": [CharacterCard(character_id="c001", name="林默", role="protagonist")]}
            )
        }
    )
    rendered = service._render_beat(
        document,
        Beat(beat_id="b001", type="dialogue", text="林默说道：继续。", speaker_ref="c001"),
    )

    assert rendered == "林默说道：继续。"
