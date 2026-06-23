from __future__ import annotations

import threading
from pathlib import Path
from time import sleep

import pytest
import yaml

from ai_fiction_to_script.models.runtime import ModelRouting, ParsedChapter
from ai_fiction_to_script.models.schema import Beat, CharacterCard, Scene, ScenePlan, SceneTransition, Script, ScriptAct, SourceRef, StoryBible
from ai_fiction_to_script.services.ai_client import HybridAIClient, MockAIClient
from ai_fiction_to_script.services.cache_store import InMemoryCacheStore
from ai_fiction_to_script.services.workbench import WorkbenchService


def fitting_scene_text(chapter, request) -> str:
    source_chars = len("".join(chapter.raw_text.split()))
    if request.detail_level == "fast":
        target = round(source_chars * 0.7)
    elif request.detail_level == "detailed":
        target = round(source_chars * 1.8)
    else:
        target = round(source_chars)
    return "剧" * max(1, target)


class FittingMockAIClient(MockAIClient):
    def generate_scene(self, scene_plan, story_bible, chapter, request):
        scene = super().generate_scene(scene_plan, story_bible, chapter, request)
        return scene.model_copy(
            update={"beats": [Beat(beat_id="b001", type="action", text=fitting_scene_text(chapter, request))]}
        )

    def generate_scene_stream(self, scene_plan, story_bible, chapter, request, on_delta=None):
        return self.generate_scene(scene_plan, story_bible, chapter, request)


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


def test_workbench_maps_qwen_web_detail_levels_to_scene_density(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")

    standard_request = service._build_request_from_payload(
        {
            "title": "standard-demo",
            "script_type": "short_drama",
            "provider": "qwen",
        }
    )
    fast_request = service._build_request_from_payload(
        {
            "title": "fast-demo",
            "script_type": "short_drama",
            "provider": "qwen",
            "detail_level": "fast",
        }
    )
    detailed_request = service._build_request_from_payload(
        {
            "title": "detailed-demo",
            "script_type": "short_drama",
            "provider": "qwen",
            "detail_level": "detailed",
        }
    )

    assert standard_request.detail_level == "standard"
    assert standard_request.max_scenes_per_chapter == 1
    assert standard_request.max_beats_per_scene == 10
    assert standard_request.chapter_context_chars == 1200
    assert fast_request.max_scenes_per_chapter == 1
    assert fast_request.max_beats_per_scene == 6
    assert fast_request.chapter_context_chars == 600
    assert fast_request.temperature == 0.2
    assert detailed_request.detail_level == "detailed"
    assert detailed_request.max_scenes_per_chapter == 1
    assert detailed_request.max_beats_per_scene == 12
    assert detailed_request.chapter_context_chars == 1600
    assert detailed_request.temperature == 0.3


def test_workbench_detail_length_check_does_not_pad_scene_body(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    chapter = ParsedChapter(
        chapter_id="ch01",
        title="第一章",
        raw_text="一" * 1000,
        raw_text_ref="memory://chapter-1",
    )
    scene_plan = ScenePlan(scene_id="s001", act_id="main", title="第一章", objective="推进剧情", chapter_refs=["ch01"])
    scene = Scene(
        scene_id="s001",
        title="第一章",
        chapter_refs=["ch01"],
        time_of_day="day",
        objective="推进剧情",
        summary="summary",
        beats=[Beat(beat_id="b001", type="action", text="短")],
        source_refs=[SourceRef(chapter_id="ch01", excerpt_id="p001")],
    )
    story_bible = StoryBible(logline="logline", synopsis="synopsis")

    fast_request = service._build_request_from_payload({"title": "fast-demo", "provider": "qwen", "detail_level": "fast"})
    standard_request = service._build_request_from_payload({"title": "standard-demo", "provider": "qwen", "detail_level": "standard"})
    detailed_request = service._build_request_from_payload({"title": "detailed-demo", "provider": "qwen", "detail_level": "detailed"})

    class SameShortClient:
        def generate_scene(self, *_args, **_kwargs):
            return scene

    fast_scene, _ = service._generate_scene_with_length_warning(SameShortClient(), scene_plan, story_bible, chapter, fast_request)
    standard_scene, standard_warning = service._generate_scene_with_length_warning(
        SameShortClient(), scene_plan, story_bible, chapter, standard_request
    )
    detailed_scene, detailed_warning = service._generate_scene_with_length_warning(
        SameShortClient(), scene_plan, story_bible, chapter, detailed_request
    )

    fast_chars = service._scene_body_char_count(fast_scene)
    standard_chars = service._scene_body_char_count(standard_scene)
    detailed_chars = service._scene_body_char_count(detailed_scene)

    assert fast_chars < 200
    assert standard_chars < 200
    assert detailed_chars < 200
    assert standard_chars == detailed_chars == fast_chars
    assert "未达到目标字数范围" in standard_warning
    assert "未达到目标字数范围" in detailed_warning


def test_workbench_qwen_result_does_not_leak_generation_instructions_into_body(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    chapter = ParsedChapter(
        chapter_id="ch01",
        title="第一章",
        raw_text="一" * 1000,
        raw_text_ref="memory://chapter-1",
    )
    scene_plan = ScenePlan(scene_id="s001", act_id="main", title="第一章", objective="推进剧情", chapter_refs=["ch01"])
    scene = Scene(
        scene_id="s001",
        title="第一章",
        chapter_refs=["ch01"],
        time_of_day="day",
        objective="推进剧情",
        summary="summary",
        beats=[Beat(beat_id="b001", type="action", text="原始短稿")],
        source_refs=[SourceRef(chapter_id="ch01", excerpt_id="p001")],
    )
    story_bible = StoryBible(logline="logline", synopsis="synopsis")
    request = service._build_request_from_payload(
        {
            "title": "style-demo",
            "provider": "qwen",
            "script_type": "audio_drama",
            "tone": "dark",
            "detail_level": "detailed",
        }
    )

    class SameShortClient:
        def generate_scene(self, *_args, **_kwargs):
            return scene

    styled_scene, warning = service._generate_scene_with_length_warning(
        SameShortClient(),
        scene_plan,
        story_bible,
        chapter,
        request,
    )
    body = "\n".join(beat.text for beat in styled_scene.beats)

    assert "广播剧处理" not in body
    assert "语气执行" not in body
    assert "详细度执行" not in body
    assert "原始短稿" in body
    assert "细节扩写" not in body
    assert "情绪补足" not in body
    assert "环境与反应" not in body
    assert "未达到目标字数范围" in warning


def test_workbench_generation_settings_are_recorded_without_becoming_scene_text(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    chapter = ParsedChapter(
        chapter_id="ch01",
        title="第一章",
        raw_text="一" * 600,
        raw_text_ref="memory://chapter-1",
    )
    scene_plan = ScenePlan(scene_id="s001", act_id="main", title="第一章", objective="推进剧情", chapter_refs=["ch01"])
    scene = Scene(
        scene_id="s001",
        title="第一章",
        chapter_refs=["ch01"],
        time_of_day="day",
        objective="推进剧情",
        summary="同一个冲突",
        beats=[Beat(beat_id="b001", type="action", text="同一个模型原始输出")],
        source_refs=[SourceRef(chapter_id="ch01", excerpt_id="p001")],
    )
    story_bible = StoryBible(logline="logline", synopsis="synopsis")

    class SameClient:
        def generate_scene(self, *_args, **_kwargs):
            return scene

    request = service._build_request_from_payload(
        {"title": "b", "provider": "qwen", "script_type": "audio_drama", "tone": "humorous", "detail_level": "standard"}
    )

    generated_scene, _ = service._generate_scene_with_length_warning(SameClient(), scene_plan, story_bible, chapter, request)
    body = "\n".join(beat.text for beat in generated_scene.beats)

    assert "广播剧处理" not in body
    assert "语气执行" not in body
    assert "详细度执行" not in body
    assert "同一个模型原始输出" in body


def test_workbench_version_summary_falls_back_to_saved_request(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    payload = service.adapt(
        {
            "title": "summary-fallback-demo",
            "original_author": "tester",
            "original_title": "summary-fallback-demo",
            "script_type": "audio_drama",
            "tone": "dark",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
            "detail_level": "detailed",
        }
    )

    document = service.version_store.load_document(payload["project_id"], payload["version"]["version_id"])
    document = document.model_copy(update={"extensions": {}})
    saved = service.version_store.save(
        payload["project_id"],
        document,
        intermediates=service._build_intermediates_from_document(
            payload["project_id"],
            payload["version"]["version_id"],
            document,
            service._load_request(payload["project_id"], payload["version"]["version_id"], document),
        ),
        note="summary fallback",
    )
    service._invalidate_project_cache(payload["project_id"])

    projects = service.list_projects()
    versions = next(project["versions"] for project in projects if project["project_id"] == payload["project_id"])
    summary = next(version["generation_summary"] for version in versions if version["version_id"] == saved.version_id)

    assert summary["script_type_label"] == "广播剧剧本"
    assert summary["tone_label"] == "暗黑"
    assert summary["detail_label"] == "详写"


def test_workbench_infers_genre_when_payload_genre_is_empty(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")

    request = service._build_request_from_payload(
        {
            "title": "genre-demo",
            "script_type": "film",
            "provider": "qwen",
            "novel_text": "调查员追查失踪案件，线索指向一个隐藏多年的秘密。真相即将揭开。",
        }
    )

    assert "悬疑" in request.genre


def test_workbench_uses_hybrid_qwen_client_for_web_speed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "demo-key")
    service = WorkbenchService(tmp_path / ".novel2script")

    client = service._build_ai_client("qwen")

    assert isinstance(client, HybridAIClient)


def test_workbench_qwen_hybrid_uses_qwen_for_review(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "demo-key")
    service = WorkbenchService(tmp_path / ".novel2script")

    client = service._build_ai_client("qwen")

    assert isinstance(client, HybridAIClient)
    assert client._reviewer_client is client._generator_client
    assert isinstance(client._planner_client, MockAIClient)


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


def test_workbench_fast_qwen_async_uses_chapter_generation_for_strict_length(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    used_whole_script_path = {"value": False}
    generated_scenes: list[str] = []

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

        def generate_scene_stream(self, scene_plan, story_bible, chapter, request, on_delta=None):
            generated_scenes.append(scene_plan.scene_id)
            return Scene(
                scene_id=scene_plan.scene_id,
                title=scene_plan.title,
                chapter_refs=scene_plan.chapter_refs,
                time_of_day="day",
                objective=scene_plan.objective,
                summary=scene_plan.notes or scene_plan.objective,
                beats=[Beat(beat_id="b001", type="action", text=fitting_scene_text(chapter, request))],
                transitions=SceneTransition(next_scene_hint=scene_plan.bridge_out, transition_type="cut"),
                source_refs=[SourceRef(chapter_id=scene_plan.chapter_refs[0], excerpt_id="p001")],
            )

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

    assert used_whole_script_path["value"] is False
    assert generated_scenes == ["s001", "s002", "s003"]
    assert task["final_version_id"] == "v0001"


def test_workbench_fast_qwen_falls_back_to_chapter_generation_when_whole_script_times_out(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")

    class TimeoutThenChapterClient(FittingMockAIClient):
        def generate_script_stream(self, outline, story_bible, chapters, request, on_delta=None):
            raise ValueError("simulated whole-script timeout")

        def generate_scene_stream(self, scene_plan, story_bible, chapter, request, on_delta=None):
            return self.generate_scene(scene_plan, story_bible, chapter, request)

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": TimeoutThenChapterClient())

    payload = service.start_adapt_async(
        {
            "title": "fast-fallback",
            "original_author": "tester",
            "original_title": "fast-fallback",
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

    assert task["status"] == "completed"
    assert task["final_version_id"] == "v0001"
    assert len(task["result"]["document"]["script"]["acts"][0]["scenes"]) == 3


def test_workbench_standard_qwen_async_generates_progressively_by_chapter(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    used_whole_script_path = {"value": False}

    class FakeStandardClient(MockAIClient):
        def generate_script_stream(self, outline, story_bible, chapters, request, on_delta=None):
            used_whole_script_path["value"] = True
            return super().generate_script_stream(outline, story_bible, chapters, request, on_delta=on_delta)

        def generate_scene_stream(self, scene_plan, story_bible, chapter, request, on_delta=None):
            if on_delta is not None:
                on_delta(f"CHAPTER_UNIT {scene_plan.scene_id} | {scene_plan.title}", "")
            return self.generate_scene(scene_plan, story_bible, chapter, request)

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": FakeStandardClient())

    payload = service.start_adapt_async(
        {
            "title": "standard-progressive",
            "original_author": "tester",
            "original_title": "standard-progressive",
            "script_type": "film",
            "tone": "serious",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "qwen",
            "api_key": "demo-key",
            "detail_level": "standard",
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

    assert used_whole_script_path["value"] is False
    assert task["final_version_id"] == "v0001"


def test_workbench_async_final_document_records_selected_generation_settings(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")

    class FittingClient(FittingMockAIClient):
        def review_document(self, document, request):
            return [], []

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": FittingClient())

    payload = service.start_adapt_async(
        {
            "title": "settings-record-demo",
            "original_author": "tester",
            "original_title": "settings-record-demo",
            "script_type": "audio_drama",
            "tone": "dark",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "qwen",
            "api_key": "demo-key",
            "detail_level": "detailed",
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

    document = task["result"]["document"]
    assert document["meta"]["target_format"] == "audio_drama"
    assert document["meta"]["tone"] == "dark"
    assert document["extensions"]["generation_settings"]["detail_level"] == "detailed"
    assert "广播剧剧本" in task["result"]["rendered_script"]
    assert "暗黑" in task["result"]["rendered_script"]
    assert "详写" in task["result"]["rendered_script"]


def test_workbench_continues_when_one_chapter_generation_fails(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")

    class PartiallyFailingClient(MockAIClient):
        def generate_scene_stream(self, scene_plan, story_bible, chapter, request, on_delta=None):
            if scene_plan.scene_id == "s002":
                raise ValueError("simulated chapter timeout")
            return self.generate_scene(scene_plan, story_bible, chapter, request)

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": PartiallyFailingClient())

    payload = service.start_adapt_async(
        {
            "title": "partial-failure",
            "original_author": "tester",
            "original_title": "partial-failure",
            "script_type": "film",
            "tone": "serious",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "qwen",
            "api_key": "demo-key",
            "detail_level": "standard",
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

    assert task["status"] == "completed"
    document = task["result"]["document"]
    assert len(document["script"]["acts"][0]["scenes"]) == document["source"]["chapter_count"]
    assert any("s002" in warning and "simulated chapter timeout" in warning for warning in document["quality"]["warnings"])


def test_workbench_collapses_multiple_scenes_per_chapter_before_saving(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    payload = service.adapt(
        {
            "title": "collapse-demo",
            "original_author": "tester",
            "original_title": "collapse-demo",
            "script_type": "film",
            "tone": "balanced",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )
    document = service.version_store.load_document(payload["project_id"], payload["version"]["version_id"])
    first_scene = document.script.acts[0].scenes[0]
    extra_scene = first_scene.model_copy(
        update={
            "scene_id": "s999",
            "title": "extra",
            "beats": [Beat(beat_id="b001", type="action", text="extra beat")],
        }
    )
    expanded_script = Script(
        acts=[
            ScriptAct(
                act_id="main",
                title="正文",
                scenes=[first_scene, extra_scene, *document.script.acts[0].scenes[1:]],
            )
        ]
    )
    expanded_document = document.model_copy(update={"script": expanded_script})

    collapsed = service._collapse_document_to_chapter_units(expanded_document)

    assert len(collapsed.script.acts[0].scenes) == collapsed.source.chapter_count
    assert [scene.chapter_refs for scene in collapsed.script.acts[0].scenes] == [["ch01"], ["ch02"], ["ch03"]]
    assert any(beat.text == "extra beat" for beat in collapsed.script.acts[0].scenes[0].beats)


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

    bundle = yaml.safe_load(yaml_text)

    assert bundle["schema_version"] == "2.0"
    assert "meta" in bundle
    assert "source" in bundle
    assert "adaptation" in bundle
    assert "story_bible" in bundle
    assert "outline" in bundle
    assert "script" in bundle
    assert "quality" in bundle
    assert "extensions" in bundle
    assert "regeneration_bundle" in bundle["extensions"]
    assert "source_chapters" in bundle["extensions"]["regeneration_bundle"]
    assert "characters" not in bundle
    assert "scenes" not in bundle
    assert bundle["script"]["acts"][0]["scenes"][0]["beats"]


def test_workbench_exported_yaml_demotes_narrative_dialogue_to_action(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    payload = service.adapt(
        {
            "title": "yaml-sanitize-demo",
            "original_author": "tester",
            "original_title": "yaml-sanitize-demo",
            "script_type": "film",
            "tone": "balanced",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )
    document = service.version_store.load_document(payload["project_id"], payload["version"]["version_id"])
    first_character_id = document.story_bible.characters[0].character_id
    first_scene = document.script.acts[0].scenes[0]
    rewritten_scene = first_scene.model_copy(
        update={
            "beats": [
                Beat(
                    beat_id="b001",
                    type="dialogue",
                    text="林默没有回答，只是盯着那枚怀表。",
                    speaker_ref=first_character_id,
                )
            ]
        }
    )
    rewritten_script = Script(
        acts=[ScriptAct(act_id=document.script.acts[0].act_id, title=document.script.acts[0].title, scenes=[rewritten_scene])]
    )
    rewritten_document = document.model_copy(update={"script": rewritten_script})
    saved = service.version_store.save(
        payload["project_id"],
        rewritten_document,
        intermediates={"chapters": service.version_store.load_intermediate(payload["project_id"], payload["version"]["version_id"], "chapters")},
        note="sanitize",
    )

    exported = yaml.safe_load(service.export_version_yaml(payload["project_id"], saved.version_id))
    first_line = exported["script"]["acts"][0]["scenes"][0]["beats"][0]

    assert first_line["type"] == "action"
    assert first_line.get("speaker_ref") is None
    assert "没有回答" in first_line["text"]


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
    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": FittingMockAIClient())

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


def test_workbench_can_regenerate_from_screenplay_yaml_without_source_chapters(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": FittingMockAIClient())
    bundle_yaml = yaml.safe_dump(
        {
            "schema_version": "2.0",
            "meta": {
                "project_id": "yaml-blueprint-demo",
                "title": "yaml-blueprint-demo",
                "original_author": "tester",
                "original_novel_title": "yaml-blueprint-demo",
                "target_format": "film",
                "language": "zh-CN",
                "genre": ["mystery"],
                "tone": "serious",
                "created_at": "2026-06-07T00:00:00+00:00",
                "model_provider": "qwen",
                "model_name": "qwen3.6-flash",
            },
            "source": {
                "chapter_count": 3,
                "chapters": [
                    {"chapter_id": "ch01", "title": "第一章", "raw_text_ref": "memory://ch01", "summary": "暴雨夜，神秘来客进入古董店。", "excerpt_count": 2},
                    {"chapter_id": "ch02", "title": "第二章", "raw_text_ref": "memory://ch02", "summary": "林默彻夜翻阅古籍。", "excerpt_count": 2},
                    {"chapter_id": "ch03", "title": "第三章", "raw_text_ref": "memory://ch03", "summary": "怀表归位，怨灵消散。", "excerpt_count": 2},
                ],
            },
            "adaptation": {
                "adaptation_goal": "将小说改编为可编辑剧本初稿",
                "compression_strategy": "merge_minor_events",
                "pacing_policy": "preserve_key_conflicts",
                "structure_type": "continuous_sequence",
                "style_guide": {
                    "dialogue_style": "自然克制",
                    "narration_style": "简洁清晰",
                    "pacing_style": "快速推进",
                },
            },
            "story_bible": {
                "logline": "林默被卷入怀表异变。",
                "synopsis": "来客带来怀表，林默查清来历并完成封印。",
                "theme": ["时间", "执念"],
                "characters": [
                    {"character_id": "c001", "name": "林默", "role": "protagonist", "traits": [], "relations": []},
                    {"character_id": "c002", "name": "来客", "role": "supporting", "traits": [], "relations": []},
                ],
                "locations": [
                    {"location_id": "l001", "name": "旧时光古董店"},
                    {"location_id": "l002", "name": "废弃钟楼"},
                ],
                "timeline": [],
                "props": ["怀表"],
            },
            "outline": {
                "structure_type": "continuous_sequence",
                "acts": [{"act_id": "main", "name": "正文", "purpose": "推进主线", "scene_count": 3}],
                "scene_plans": [
                    {"scene_id": "s001", "act_id": "main", "title": "雨夜来客", "objective": "来客把怀表交给林默", "chapter_refs": ["ch01"]},
                    {"scene_id": "s002", "act_id": "main", "title": "齿轮下的秘密", "objective": "林默查清怀表来历", "chapter_refs": ["ch02"]},
                    {"scene_id": "s003", "act_id": "main", "title": "午夜的钟声", "objective": "林默完成封印", "chapter_refs": ["ch03"]},
                ],
            },
            "script": {
                "acts": [
                    {
                        "act_id": "main",
                        "title": "正文",
                        "scenes": [
                            {
                                "scene_id": "s001",
                                "title": "雨夜来客",
                                "chapter_refs": ["ch01"],
                                "location_ref": "l001",
                                "time_of_day": "深夜",
                                "objective": "来客把怀表交给林默",
                                "summary": "暴雨夜，神秘来客进入古董店。",
                                "beats": [
                                    {"beat_id": "b001", "type": "action", "text": "暴雨敲打古董店木门。"},
                                    {"beat_id": "b002", "type": "dialogue", "text": "帮我修好它。", "speaker_ref": "c002"},
                                ],
                                "source_refs": [{"chapter_id": "ch01", "excerpt_id": "p001"}],
                            },
                            {
                                "scene_id": "s002",
                                "title": "齿轮下的秘密",
                                "chapter_refs": ["ch02"],
                                "location_ref": "l001",
                                "time_of_day": "凌晨",
                                "objective": "林默查清怀表来历",
                                "summary": "林默彻夜翻阅古籍。",
                                "beats": [
                                    {"beat_id": "b001", "type": "action", "text": "林默翻开残卷，核对怀表刻痕。"},
                                    {"beat_id": "b002", "type": "dialogue", "text": "第三个节点失控了。", "speaker_ref": "c001"},
                                ],
                                "source_refs": [{"chapter_id": "ch02", "excerpt_id": "p001"}],
                            },
                            {
                                "scene_id": "s003",
                                "title": "午夜的钟声",
                                "chapter_refs": ["ch03"],
                                "location_ref": "l002",
                                "time_of_day": "午夜",
                                "objective": "林默完成封印",
                                "summary": "怀表归位，怨灵消散。",
                                "beats": [
                                    {"beat_id": "b001", "type": "action", "text": "林默把怀表压进钟摆机关。"},
                                    {"beat_id": "b002", "type": "dialogue", "text": "时间到了，该走了。", "speaker_ref": "c001"},
                                ],
                                "source_refs": [{"chapter_id": "ch03", "excerpt_id": "p001"}],
                            },
                        ],
                    }
                ]
            },
            "quality": {"confidence": 0.9, "warnings": [], "revision_suggestions": [], "continuity_checks": {}},
            "extensions": {
                "regeneration_bundle": {
                    "source_chapters": [
                        {"chapter_id": "ch01", "title": "第一章", "text": "暴雨敲打古董店木门。 来客：帮我修好它。"},
                        {"chapter_id": "ch02", "title": "第二章", "text": "林默翻开残卷，核对怀表刻痕。 林默：第三个节点失控了。"},
                        {"chapter_id": "ch03", "title": "第三章", "text": "林默把怀表压进钟摆机关。 林默：时间到了，该走了。"},
                    ]
                }
            },
        },
        allow_unicode=True,
        sort_keys=False,
    )

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
        raise AssertionError("screenplay yaml regeneration task did not complete in time")

    assert task["final_version_id"] == "v0001"
    assert task["result"]["project_id"] == "yaml-blueprint-demo"


def test_workbench_yaml_regeneration_preserves_requested_detail_level(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    raw_payload = {
        "meta": {
            "title": "yaml-detail",
            "original_novel_title": "yaml-detail",
            "original_author": "tester",
            "target_format": "film",
            "tone": "balanced",
        },
        "extensions": {
            "regeneration_bundle": {
                "source_chapters": [
                    {"chapter_id": "ch01", "title": "第一章", "text": "第一章正文"},
                    {"chapter_id": "ch02", "title": "第二章", "text": "第二章正文"},
                    {"chapter_id": "ch03", "title": "第三章", "text": "第三章正文"},
                ]
            }
        },
    }

    bundle_payload = service._build_payload_from_yaml_bundle(
        yaml.safe_dump(raw_payload, allow_unicode=True),
        {"detail_level": "detailed"},
    )
    request = service._build_request_from_payload(bundle_payload)

    assert request.detail_level == "detailed"
    assert request.max_beats_per_scene == 12


def test_workbench_regenerate_scene_normalizes_audio_drama_markup(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    initial = service.adapt(
        {
            "title": "regen-format-demo",
            "original_author": "tester",
            "original_title": "regen-format-demo",
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
                location_ref=None,
                time_of_day="night",
                objective=scene_plan.objective,
                summary="summary",
                beats=[
                    Beat(beat_id="b001", type="action", text="[SFX] 暴雨砸在玻璃上。"),
                    Beat(beat_id="b002", type="dialogue", text="[VO/林默] 我不会退。"),
                    Beat(beat_id="b003", type="action", text=fitting_scene_text(chapter, request)),
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

    rendered = regenerated["scene_comparison"]["after"]["rendered"]

    assert "[VO" not in rendered
    assert "[SFX" not in rendered
    assert "林默：我不会退。" in rendered
    assert "暴雨砸在玻璃上。" in rendered


def test_workbench_regenerate_scene_applies_requested_detail_level(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    initial = service.adapt(
        {
            "title": "regen-detail-demo",
            "original_author": "tester",
            "original_title": "regen-detail-demo",
            "script_type": "film",
            "tone": "serious",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
            "detail_level": "fast",
        }
    )
    captured: dict[str, object] = {}

    class CapturingClient(MockAIClient):
        def generate_scene(self, scene_plan, story_bible, chapter, request):
            captured["detail_level"] = request.detail_level
            captured["max_beats_per_scene"] = request.max_beats_per_scene
            captured["chapter_context_chars"] = request.chapter_context_chars
            scene = super().generate_scene(scene_plan, story_bible, chapter, request)
            return scene.model_copy(
                update={
                    "beats": [Beat(beat_id="b001", type="action", text=fitting_scene_text(chapter, request))]
                }
            )

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": CapturingClient())

    service.regenerate_scene(
        project_id=initial["project_id"],
        version_id=initial["version"]["version_id"],
        scene_id=initial["scene_options"][0]["scene_id"],
        provider_override="qwen",
        api_key="demo-key",
        detail_level="detailed",
    )

    assert captured == {
        "detail_level": "detailed",
        "max_beats_per_scene": 12,
        "chapter_context_chars": 1600,
    }


def test_workbench_regenerate_scene_keeps_single_result_when_length_budget_is_not_met(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    initial = service.adapt(
        {
            "title": "strict-length-demo",
            "original_author": "tester",
            "original_title": "strict-length-demo",
            "script_type": "film",
            "tone": "serious",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )
    attempts = {"count": 0}

    class RetryingClient:
        def generate_scene(self, scene_plan, story_bible, chapter, request):
            attempts["count"] += 1
            text = "短" if attempts["count"] == 1 else fitting_scene_text(chapter, request)
            return Scene(
                scene_id=scene_plan.scene_id,
                title=scene_plan.title,
                chapter_refs=scene_plan.chapter_refs,
                time_of_day="day",
                objective=scene_plan.objective,
                summary="summary",
                beats=[Beat(beat_id="b001", type="action", text=text)],
                transitions=SceneTransition(next_scene_hint="Cut away", transition_type="cut"),
                source_refs=[SourceRef(chapter_id=scene_plan.chapter_refs[0], excerpt_id="p001")],
            )

        def review_document(self, document, request):
            return [], []

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": RetryingClient())

    regenerated = service.regenerate_scene(
        project_id=initial["project_id"],
        version_id=initial["version"]["version_id"],
        scene_id=initial["scene_options"][0]["scene_id"],
        provider_override="qwen",
        api_key="demo-key",
    )

    assert attempts["count"] == 1
    assert any(beat["text"] == "短" for beat in regenerated["scene_comparison"]["after"]["scene"]["beats"])
    assert any("未达到目标字数范围" in warning for warning in regenerated["document"]["quality"]["warnings"])


def test_workbench_regenerate_scene_saves_short_result_with_length_warning(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    initial = service.adapt(
        {
            "title": "strict-length-failure",
            "original_author": "tester",
            "original_title": "strict-length-failure",
            "script_type": "film",
            "tone": "serious",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )

    class ShortClient:
        def generate_scene(self, scene_plan, story_bible, chapter, request):
            return Scene(
                scene_id=scene_plan.scene_id,
                title=scene_plan.title,
                chapter_refs=scene_plan.chapter_refs,
                time_of_day="day",
                objective=scene_plan.objective,
                summary="summary",
                beats=[Beat(beat_id="b001", type="action", text="短")],
                transitions=SceneTransition(next_scene_hint="Cut away", transition_type="cut"),
                source_refs=[SourceRef(chapter_id=scene_plan.chapter_refs[0], excerpt_id="p001")],
            )

        def review_document(self, document, request):
            return [], []

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": ShortClient())

    regenerated = service.regenerate_scene(
        project_id=initial["project_id"],
        version_id=initial["version"]["version_id"],
        scene_id=initial["scene_options"][0]["scene_id"],
        provider_override="qwen",
        api_key="demo-key",
    )

    assert any(beat["text"] == "短" for beat in regenerated["scene_comparison"]["after"]["scene"]["beats"])
    assert any("未达到目标字数范围" in warning for warning in regenerated["document"]["quality"]["warnings"])


def test_workbench_async_adapt_completes_with_warning_when_qwen_scene_length_budget_is_not_met(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")

    class ShortClient:
        def generate_scene_stream(self, scene_plan, story_bible, chapter, request, on_delta=None):
            return Scene(
                scene_id=scene_plan.scene_id,
                title=scene_plan.title,
                chapter_refs=scene_plan.chapter_refs,
                time_of_day="day",
                objective=scene_plan.objective,
                summary="summary",
                beats=[Beat(beat_id="b001", type="action", text="短")],
                transitions=SceneTransition(next_scene_hint="Cut away", transition_type="cut"),
                source_refs=[SourceRef(chapter_id=scene_plan.chapter_refs[0], excerpt_id="p001")],
            )

        def review_document(self, document, request):
            return [], []

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": ShortClient())

    payload = service.start_adapt_async(
        {
            "title": "strict-async-failure",
            "original_author": "tester",
            "original_title": "strict-async-failure",
            "script_type": "film",
            "tone": "serious",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "qwen",
            "api_key": "demo-key",
            "detail_level": "standard",
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

    assert task["result"]["version"]["version_id"] == "v0001"
    assert any("未达到目标字数范围" in warning for warning in task["result"]["document"]["quality"]["warnings"])


def test_workbench_async_adapt_publishes_progress_before_scene_finishes(monkeypatch, tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    release_generation = threading.Event()

    class BlockingClient:
        def generate_scene_stream(self, scene_plan, story_bible, chapter, request, on_delta=None):
            release_generation.wait(timeout=5)
            return Scene(
                scene_id=scene_plan.scene_id,
                title=scene_plan.title,
                chapter_refs=scene_plan.chapter_refs,
                time_of_day="day",
                objective=scene_plan.objective,
                summary="summary",
                beats=[Beat(beat_id="b001", type="action", text=fitting_scene_text(chapter, request))],
                transitions=SceneTransition(next_scene_hint="Cut away", transition_type="cut"),
                source_refs=[SourceRef(chapter_id=scene_plan.chapter_refs[0], excerpt_id="p001")],
            )

        def review_document(self, document, request):
            return [], []

    monkeypatch.setattr(service, "_build_ai_client", lambda provider, api_key="": BlockingClient())

    payload = service.start_adapt_async(
        {
            "title": "progress-before-finish",
            "original_author": "tester",
            "original_title": "progress-before-finish",
            "script_type": "film",
            "tone": "serious",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "qwen",
            "api_key": "demo-key",
            "detail_level": "standard",
        }
    )

    task_id = payload["task"]["task_id"]
    try:
        for _ in range(20):
            task = service.get_task_status(task_id)
            rendered = task.get("result", {}).get("rendered_script", "")
            if "正在连接模型并生成当前章节剧本" in rendered:
                break
            sleep(0.05)
        else:
            raise AssertionError("task did not publish generation progress before completion")
    finally:
        release_generation.set()

    for _ in range(20):
        task = service.get_task_status(task_id)
        if task["status"] == "completed":
            break
        sleep(0.05)
    else:
        raise AssertionError("async adapt task did not complete after release")


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
                    Beat(beat_id="b003", type="action", text=fitting_scene_text(chapter, request)),
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


def test_workbench_render_scene_keeps_narrative_beats_as_separate_paragraphs(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    payload = service.adapt(
        {
            "title": "render-merge-demo",
            "original_author": "tester",
            "original_title": "render-merge-demo",
            "script_type": "film",
            "tone": "balanced",
            "genre": "mystery",
            "novel_text": sample_novel_text(),
            "provider": "mock",
        }
    )
    document = service.version_store.load_document(payload["project_id"], payload["version"]["version_id"])
    scene = document.script.acts[0].scenes[0].model_copy(
        update={
            "beats": [
                Beat(beat_id="b001", type="action", text="第一段动作"),
                Beat(beat_id="b002", type="narration", text="第二段旁白"),
                Beat(beat_id="b003", type="dialogue", speaker_ref=None, text="角色：一句对白"),
                Beat(beat_id="b004", type="action", text="第三段动作"),
            ]
        }
    )

    rendered = service._render_scene(document, scene)

    assert "第一段动作\n第二段旁白\n角色：一句对白\n第三段动作" in rendered


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


def test_workbench_render_beat_removes_event_marker_prefix_from_dialogue(tmp_path) -> None:
    service = WorkbenchService(tmp_path / ".novel2script")
    payload = service.adapt(
        {
            "title": "event-marker-cleanup",
            "original_author": "tester",
            "original_title": "event-marker-cleanup",
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
                update={"characters": [CharacterCard(character_id="c001", name="陈母", role="supporting")]}
            )
        }
    )

    rendered = service._render_beat(
        document,
        Beat(beat_id="b001", type="dialogue", text="E067: 陈母\n知律。", speaker_ref="c001"),
    )

    assert rendered == "陈母：知律。"
