from __future__ import annotations

from ai_fiction_to_script.models.schema import ContinuityChecks, QualityReport, ScreenplayDocument


class QualityChecker:
    def review(self, document: ScreenplayDocument) -> QualityReport:
        warnings: list[str] = []
        suggestions: list[str] = []
        character_ids = {item.character_id for item in document.story_bible.characters}
        location_ids = {item.location_id for item in document.story_bible.locations}
        chapter_ids = {item.chapter_id for item in document.source.chapters}

        character_consistency = True
        timeline_consistency = True
        location_consistency = True
        reference_consistency = True

        if document.source.chapter_count != len(document.source.chapters):
            warnings.append("source.chapter_count 与 source.chapters 数量不一致。")
            reference_consistency = False

        outline_scene_total = sum(act.scene_count for act in document.outline.acts)
        script_scene_total = sum(len(act.scenes) for act in document.script.acts)
        if outline_scene_total != script_scene_total:
            warnings.append("outline 中声明的场景数量与 script 中实际场景数量不一致。")
            timeline_consistency = False

        for act in document.script.acts:
            if not act.scenes:
                warnings.append(f"{act.title} 没有任何场景。")
            for scene in act.scenes:
                if not scene.beats:
                    warnings.append(f"{scene.scene_id} 缺少 beats。")
                if scene.location_ref and scene.location_ref not in location_ids:
                    warnings.append(f"{scene.scene_id} 的 location_ref 未在 story_bible.locations 中定义。")
                    location_consistency = False
                if any(chapter_ref not in chapter_ids for chapter_ref in scene.chapter_refs):
                    warnings.append(f"{scene.scene_id} 的 chapter_refs 存在无效引用。")
                    reference_consistency = False
                for beat in scene.beats:
                    if beat.type == "dialogue" and beat.speaker_ref and beat.speaker_ref not in character_ids:
                        warnings.append(f"{scene.scene_id}/{beat.beat_id} 的 speaker_ref 未在角色表中定义。")
                        character_consistency = False
                    if beat.type == "dialogue" and not beat.speaker_ref:
                        warnings.append(f"{scene.scene_id}/{beat.beat_id} 为对白节拍但缺少 speaker_ref。")
                        character_consistency = False
                if scene.transitions is None:
                    suggestions.append(f"可为 {scene.scene_id} 增加转场提示，降低场景跳跃感。")

        confidence = max(0.45, 1.0 - 0.06 * len(warnings) - 0.02 * len(suggestions))
        return QualityReport(
            confidence=round(confidence, 2),
            warnings=warnings,
            revision_suggestions=suggestions,
            continuity_checks=ContinuityChecks(
                character_consistency=character_consistency,
                timeline_consistency=timeline_consistency,
                location_consistency=location_consistency,
                reference_consistency=reference_consistency,
            ),
        )

