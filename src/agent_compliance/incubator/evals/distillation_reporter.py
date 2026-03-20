from __future__ import annotations

from dataclasses import asdict

from agent_compliance.incubator.lifecycle import IncubationRun, default_incubation_lifecycle


_STAGE_TITLES = {
    definition.stage.value: definition.title
    for definition in default_incubation_lifecycle()
}

_PENDING_HINTS = {
    "sample_preparation": "尚未补充正样例、负样例或边界样例。",
    "parity_validation": "尚未提供人工基准、强通用智能体结果和目标智能体结果的对照。",
    "distillation_iteration": "尚未基于对照差异生成或执行蒸馏建议。",
    "productization": "尚未完成稳定回归、发布口径和固化发布准备。",
}

_IN_PROGRESS_HINTS = {
    "distillation_iteration": "已进入蒸馏迭代，可继续实现建议并回挂回归结果。",
}


def build_distillation_report(run: IncubationRun) -> dict[str, object]:
    """构建一份标准化的智能体孵化/蒸馏报告。"""

    completed_stages = sum(1 for stage in run.stages if stage.status == "completed")
    sample_set_count = sum(len(stage.sample_sets) for stage in run.stages)
    comparison_count = sum(len(stage.comparisons) for stage in run.stages)
    recommendation_count = sum(len(stage.recommendations) for stage in run.stages)
    event_count = sum(len(stage.events) for stage in run.stages)

    stage_reports = []
    priority_summary: dict[str, int] = {}
    target_layer_summary: dict[str, int] = {}
    recommendation_status_summary: dict[str, int] = {}
    validated_change_count = 0

    for stage in run.stages:
        for recommendation in stage.recommendations:
            priority_summary[recommendation.priority] = (
                priority_summary.get(recommendation.priority, 0) + 1
            )
            target_layer_summary[recommendation.target_layer] = (
                target_layer_summary.get(recommendation.target_layer, 0) + 1
            )
            recommendation_status_summary[recommendation.status] = (
                recommendation_status_summary.get(recommendation.status, 0) + 1
            )
            if recommendation.regression_result or recommendation.capability_change:
                validated_change_count += 1

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
                "events": [asdict(event) for event in stage.events],
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
            "validated_change_count": validated_change_count,
            "event_count": event_count,
        },
        "priority_summary": priority_summary,
        "target_layer_summary": target_layer_summary,
        "recommendation_status_summary": recommendation_status_summary,
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
        f"- 已记录回归/能力变化：`{summary['validated_change_count']}`",
        f"- 执行痕迹：`{summary['event_count']}`",
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

    recommendation_status_summary = report.get("recommendation_status_summary", {})
    if recommendation_status_summary:
        lines.extend(["## 建议执行状态", ""])
        for status, count in sorted(recommendation_status_summary.items()):
            lines.append(f"- `{status}`：{count}")
        lines.append("")

    lines.append("## 阶段明细")
    lines.append("")

    for stage in report["stages"]:
        lines.append(f"### {stage['stage']}")
        lines.append("")
        stage_key = stage["stage"]
        stage_title = _STAGE_TITLES.get(stage_key)
        if stage_title:
            lines.append(f"- 阶段名称：{stage_title}")
        lines.append(f"- 状态：`{stage['status']}`")
        if stage["notes"]:
            lines.append(f"- 备注：{stage['notes']}")
        elif stage["status"] == "pending" and stage_key in _PENDING_HINTS:
            lines.append(f"- 说明：{_PENDING_HINTS[stage_key]}")
        elif stage["status"] == "in_progress" and stage_key in _IN_PROGRESS_HINTS:
            lines.append(f"- 说明：{_IN_PROGRESS_HINTS[stage_key]}")
        if stage["outputs"]:
            outputs = "，".join(stage["outputs"])
            lines.append(f"- 产物：{outputs}")
        if stage["sample_sets"]:
            lines.append(f"- 样例集数量：{len(stage['sample_sets'])}")
        if stage["comparisons"]:
            lines.append(f"- 对照数量：{len(stage['comparisons'])}")
        if stage["recommendations"]:
            lines.append(f"- 蒸馏建议数量：{len(stage['recommendations'])}")
            regression_notes = [
                recommendation
                for recommendation in stage["recommendations"]
                if recommendation.get("regression_result") or recommendation.get("capability_change")
            ]
            if regression_notes:
                lines.append(f"- 已记录回归结果数量：{len(regression_notes)}")
        if stage["events"]:
            lines.append(f"- 执行事件数量：{len(stage['events'])}")
            latest_events = stage["events"][-3:]
            for event in latest_events:
                lines.append(f"  - `{event['timestamp']}` {event['summary']}")
        lines.append("")

    return "\n".join(lines)
