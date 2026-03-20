from __future__ import annotations

from agent_compliance.incubator.lifecycle import (
    DistillationRecommendation,
    ValidationComparison,
)


def build_distillation_recommendations(
    comparisons: tuple[ValidationComparison, ...],
) -> tuple[DistillationRecommendation, ...]:
    """根据对照差异生成第一版蒸馏建议。"""

    recommendations: list[DistillationRecommendation] = []
    for comparison in comparisons:
        for gap_point in comparison.gap_points:
            recommendations.append(_recommendation_from_gap(comparison, gap_point))
    return tuple(recommendations)


def summarize_validation_gaps(
    comparisons: tuple[ValidationComparison, ...],
) -> dict[str, object]:
    """汇总一组对照差异。"""

    gap_points = [gap for comparison in comparisons for gap in comparison.gap_points]
    return {
        "comparison_count": len(comparisons),
        "gap_count": len(gap_points),
        "gap_points": tuple(gap_points),
        "sample_ids": tuple(comparison.sample_id for comparison in comparisons),
    }


def _recommendation_from_gap(
    comparison: ValidationComparison,
    gap_point: str,
) -> DistillationRecommendation:
    lower_gap = gap_point.lower()
    if "评分" in gap_point or "scoring" in lower_gap:
        return DistillationRecommendation(
            title="增强评分语义引擎",
            target_layer="scoring_semantic_consistency_engine",
            action=f"围绕样例 {comparison.sample_id} 补充评分相关差异：{gap_point}",
            rationale="人工或强通用智能体已识别评分差异，目标智能体仍需增强。",
            priority="P0",
        )
    if "商务" in gap_point or "验收" in gap_point or "commercial" in lower_gap:
        return DistillationRecommendation(
            title="增强商务链路引擎",
            target_layer="commercial_lifecycle_analyzer",
            action=f"围绕样例 {comparison.sample_id} 补充商务/验收差异：{gap_point}",
            rationale="商务与验收链路存在结构性差异，需继续压实主问题收束。",
            priority="P0",
        )
    if "混合" in gap_point or "边界" in gap_point or "scope" in lower_gap:
        return DistillationRecommendation(
            title="增强边界识别引擎",
            target_layer="mixed_scope_boundary_engine",
            action=f"围绕样例 {comparison.sample_id} 补充边界差异：{gap_point}",
            rationale="边界类问题仍是目标智能体与人工结果差异的高发点。",
            priority="P1",
        )
    if "仲裁" in gap_point or "归并" in gap_point or "arbiter" in lower_gap:
        return DistillationRecommendation(
            title="增强仲裁归并层",
            target_layer="finding_arbiter",
            action=f"围绕样例 {comparison.sample_id} 补充仲裁差异：{gap_point}",
            rationale="问题上浮、去重与收束仍需继续校正。",
            priority="P1",
        )
    return DistillationRecommendation(
        title="补充通用蒸馏增强",
        target_layer="review_pipeline",
        action=f"围绕样例 {comparison.sample_id} 补充差异：{gap_point}",
        rationale="当前差异尚未命中专项规则，先按通用增强入口沉淀。",
        priority="P2",
    )
