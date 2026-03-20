from __future__ import annotations

from collections import Counter

from agent_compliance.incubator.lifecycle import IncubationRun


def build_run_comparison_report(runs: tuple[IncubationRun, ...]) -> dict[str, object]:
    """比较同一智能体多轮孵化 run 的收敛情况。"""

    if not runs:
        raise ValueError("at least one incubation run is required")

    agent_keys = {run.agent_key for run in runs}
    if len(agent_keys) != 1:
        raise ValueError("all runs must belong to the same agent_key")

    run_summaries = []
    gap_counts: list[int] = []
    recommendation_counts: list[int] = []
    completed_stage_counts: list[int] = []
    all_gap_points: list[str] = []
    all_target_layers: list[str] = []
    validated_change_counts: list[int] = []
    recommendation_status_series: list[dict[str, int]] = []

    for run in runs:
        comparisons = [comparison for stage in run.stages for comparison in stage.comparisons]
        recommendations = [
            recommendation for stage in run.stages for recommendation in stage.recommendations
        ]
        gap_points = [gap for comparison in comparisons for gap in comparison.gap_points]
        aligned_points = [
            aligned for comparison in comparisons for aligned in comparison.aligned_points
        ]
        completed_stages = sum(1 for stage in run.stages if stage.status == "completed")
        validated_changes = sum(
            1
            for recommendation in recommendations
            if recommendation.regression_result or recommendation.capability_change
        )
        gap_counts.append(len(gap_points))
        recommendation_counts.append(len(recommendations))
        completed_stage_counts.append(completed_stages)
        validated_change_counts.append(validated_changes)
        recommendation_status_series.append(
            dict(Counter(recommendation.status for recommendation in recommendations))
        )
        all_gap_points.extend(gap_points)
        all_target_layers.extend(recommendation.target_layer for recommendation in recommendations)

        run_summaries.append(
            {
                "run_title": run.run_title,
                "completed_stages": completed_stages,
                "comparison_count": len(comparisons),
                "gap_count": len(gap_points),
                "aligned_count": len(aligned_points),
                "recommendation_count": len(recommendations),
                "validated_change_count": validated_changes,
                "recommendation_status_summary": dict(
                    Counter(recommendation.status for recommendation in recommendations)
                ),
                "target_layers": tuple(recommendation.target_layer for recommendation in recommendations),
            }
        )

    trend = {
        "gap_delta": gap_counts[-1] - gap_counts[0],
        "recommendation_delta": recommendation_counts[-1] - recommendation_counts[0],
        "completed_stage_delta": completed_stage_counts[-1] - completed_stage_counts[0],
        "validated_change_delta": validated_change_counts[-1] - validated_change_counts[0],
        "is_gap_converging": gap_counts[-1] <= gap_counts[0],
        "gap_series": tuple(gap_counts),
        "recommendation_series": tuple(recommendation_counts),
        "completed_stage_series": tuple(completed_stage_counts),
        "validated_change_series": tuple(validated_change_counts),
    }

    trajectory = {
        "gap_trend": _describe_gap_trend(gap_counts),
        "validated_change_trend": _describe_validated_change_trend(validated_change_counts),
        "dominant_target_layers": _top_items(Counter(all_target_layers)),
        "recommendation_status_series": tuple(recommendation_status_series),
    }

    recurring_gap_points = {
        gap: count for gap, count in Counter(all_gap_points).items() if count > 1
    }
    recurring_target_layers = {
        layer: count for layer, count in Counter(all_target_layers).items() if count > 1
    }

    return {
        "agent_key": runs[0].agent_key,
        "run_count": len(runs),
        "runs": run_summaries,
        "trend": trend,
        "trajectory": trajectory,
        "recurring_gap_points": recurring_gap_points,
        "recurring_target_layers": recurring_target_layers,
    }


def render_run_comparison_markdown(report: dict[str, object]) -> str:
    """把多轮 run 对比渲染成 Markdown。"""

    lines = [
        f"# {report['agent_key']} 多轮孵化对比报告",
        "",
        f"- 对比轮次：`{report['run_count']}`",
        f"- gap 变化：`{report['trend']['gap_delta']}`",
        f"- 建议变化：`{report['trend']['recommendation_delta']}`",
        f"- 完成阶段变化：`{report['trend']['completed_stage_delta']}`",
        f"- 已记录回归/能力变化：`{report['trend']['validated_change_delta']}`",
        f"- gap 是否收敛：`{report['trend']['is_gap_converging']}`",
        "",
        "## 趋势摘要",
        "",
        f"- gap 走势：{report['trajectory']['gap_trend']}",
        f"- 能力增强走势：{report['trajectory']['validated_change_trend']}",
        f"- gap 序列：`{list(report['trend']['gap_series'])}`",
        f"- 建议序列：`{list(report['trend']['recommendation_series'])}`",
        f"- 回归/能力变化序列：`{list(report['trend']['validated_change_series'])}`",
        "",
        "## 各轮摘要",
        "",
    ]

    for run in report["runs"]:
        lines.extend(
            [
                f"### {run['run_title']}",
                "",
                f"- 已完成阶段：`{run['completed_stages']}`",
                f"- 对照记录：`{run['comparison_count']}`",
                f"- gap 数量：`{run['gap_count']}`",
                f"- 已对齐点：`{run['aligned_count']}`",
                f"- 蒸馏建议：`{run['recommendation_count']}`",
                f"- 已记录回归/能力变化：`{run['validated_change_count']}`",
                f"- 建议状态：`{run['recommendation_status_summary']}`",
                "",
            ]
        )

    recurring_gaps = report.get("recurring_gap_points", {})
    if recurring_gaps:
        lines.extend(["## 重复出现的 gap", ""])
        for gap, count in sorted(recurring_gaps.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{gap}`：{count}")
        lines.append("")

    recurring_layers = report.get("recurring_target_layers", {})
    if recurring_layers:
        lines.extend(["## 重复成为增强重点的目标层", ""])
        for layer, count in sorted(recurring_layers.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{layer}`：{count}")
        lines.append("")

    return "\n".join(lines)


def _describe_gap_trend(gap_counts: list[int]) -> str:
    if len(gap_counts) <= 1:
        return "当前仅有一轮 run，尚不足以判断长期收敛趋势。"
    if all(next_count <= current for current, next_count in zip(gap_counts, gap_counts[1:])):
        if gap_counts[-1] < gap_counts[0]:
            return "gap 在多轮孵化中持续下降，目标智能体正在收敛。"
        return "gap 维持稳定，当前进入平台期。"
    if gap_counts[-1] < gap_counts[0]:
        return "gap 整体下降，但中间仍有波动，当前属于不稳定收敛。"
    return "gap 未呈现下降趋势，仍需继续补样例或调整蒸馏策略。"


def _describe_validated_change_trend(validated_change_counts: list[int]) -> str:
    if len(validated_change_counts) <= 1:
        return "当前仅记录一轮能力变化，后续需继续补回归结果。"
    if validated_change_counts[-1] > validated_change_counts[0]:
        return "已记录的回归收益在增加，说明蒸馏建议正在逐步转化为能力。"
    if validated_change_counts[-1] == validated_change_counts[0]:
        return "已记录的回归收益暂时持平，需继续推进建议落地和验证。"
    return "已记录的回归收益出现回落，需复核建议执行和回归口径。"


def _top_items(counter: Counter[str], limit: int = 3) -> tuple[dict[str, object], ...]:
    return tuple(
        {"name": name, "count": count}
        for name, count in counter.most_common(limit)
    )
