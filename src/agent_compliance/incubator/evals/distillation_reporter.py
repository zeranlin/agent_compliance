from __future__ import annotations

from dataclasses import asdict

from agent_compliance.incubator.lifecycle import IncubationRun


def build_distillation_report(run: IncubationRun) -> dict[str, object]:
    """构建一份标准化的智能体孵化/蒸馏报告。"""

    completed_stages = sum(1 for stage in run.stages if stage.status == "completed")
    sample_set_count = sum(len(stage.sample_sets) for stage in run.stages)
    comparison_count = sum(len(stage.comparisons) for stage in run.stages)
    recommendation_count = sum(len(stage.recommendations) for stage in run.stages)

    stage_reports = []
    priority_summary: dict[str, int] = {}
    target_layer_summary: dict[str, int] = {}

    for stage in run.stages:
        for recommendation in stage.recommendations:
            priority_summary[recommendation.priority] = (
                priority_summary.get(recommendation.priority, 0) + 1
            )
            target_layer_summary[recommendation.target_layer] = (
                target_layer_summary.get(recommendation.target_layer, 0) + 1
            )

        stage_reports.append(
            {
                "stage": stage.stage.value,
                "status": stage.status,
                "notes": stage.notes,
                "outputs": tuple(stage.outputs),
                "sample_sets": [asdict(sample_set) for sample_set in stage.sample_sets],
                "comparisons": [asdict(comparison) for comparison in stage.comparisons],
                "recommendations": [
                    asdict(recommendation) for recommendation in stage.recommendations
                ],
            }
        )

    return {
        "agent_key": run.agent_key,
        "run_title": run.run_title,
        "summary": {
            "total_stages": len(run.stages),
            "completed_stages": completed_stages,
            "sample_set_count": sample_set_count,
            "comparison_count": comparison_count,
            "recommendation_count": recommendation_count,
        },
        "priority_summary": priority_summary,
        "target_layer_summary": target_layer_summary,
        "stages": stage_reports,
    }


def render_distillation_report_markdown(report: dict[str, object]) -> str:
    """把蒸馏报告渲染成便于复盘的 Markdown。"""

    summary = report["summary"]
    lines = [
        f"# {report['run_title']} 蒸馏报告",
        "",
        f"- 智能体：`{report['agent_key']}`",
        f"- 已完成阶段：`{summary['completed_stages']}/{summary['total_stages']}`",
        f"- 样例集：`{summary['sample_set_count']}`",
        f"- 对照记录：`{summary['comparison_count']}`",
        f"- 蒸馏建议：`{summary['recommendation_count']}`",
        "",
    ]

    priority_summary = report.get("priority_summary", {})
    if priority_summary:
        lines.extend(["## 建议优先级", ""])
        for priority, count in sorted(priority_summary.items()):
            lines.append(f"- `{priority}`：{count}")
        lines.append("")

    target_layer_summary = report.get("target_layer_summary", {})
    if target_layer_summary:
        lines.extend(["## 建议目标层", ""])
        for target_layer, count in sorted(target_layer_summary.items()):
            lines.append(f"- `{target_layer}`：{count}")
        lines.append("")

    lines.append("## 阶段明细")
    lines.append("")

    for stage in report["stages"]:
        lines.append(f"### {stage['stage']}")
        lines.append("")
        lines.append(f"- 状态：`{stage['status']}`")
        if stage["notes"]:
            lines.append(f"- 备注：{stage['notes']}")
        if stage["outputs"]:
            outputs = "，".join(stage["outputs"])
            lines.append(f"- 产物：{outputs}")
        if stage["sample_sets"]:
            lines.append(f"- 样例集数量：{len(stage['sample_sets'])}")
        if stage["comparisons"]:
            lines.append(f"- 对照数量：{len(stage['comparisons'])}")
        if stage["recommendations"]:
            lines.append(f"- 蒸馏建议数量：{len(stage['recommendations'])}")
        lines.append("")

    return "\n".join(lines)
