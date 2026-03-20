from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_compliance.incubator.evals import build_distillation_report
from agent_compliance.incubator.lifecycle import IncubationRun


@dataclass(frozen=True)
class ProductizationArtifactPaths:
    """描述一次产品化固化模板输出路径。"""

    target_dir: Path
    json_path: Path
    markdown_path: Path


def build_productization_package(run: IncubationRun) -> dict[str, object]:
    """根据一轮孵化 run 生成产品化固化模板。"""

    report = build_distillation_report(run)
    summary = report["summary"]
    readiness_level = _readiness_level(summary)
    return {
        "agent_key": run.agent_key,
        "run_title": run.run_title,
        "readiness_level": readiness_level,
        "summary": summary,
        "release_checklist": _build_release_checklist(summary, report),
        "ops_guidance": _build_ops_guidance(readiness_level),
        "delivery_template": _build_delivery_template(run.agent_key, readiness_level),
        "acceptance_template": _build_acceptance_template(readiness_level),
    }


def render_productization_markdown(package: dict[str, object]) -> str:
    """把产品化固化模板渲染成 Markdown。"""

    lines = [
        f"# {package['run_title']} 产品化固化模板",
        "",
        f"- 智能体：`{package['agent_key']}`",
        f"- 当前准备度：`{package['readiness_level']}`",
        "",
        "## 发布 Checklist",
        "",
    ]
    for item in package["release_checklist"]:
        lines.append(f"- [{_checkbox(item['done'])}] {item['title']}：{item['notes']}")
    lines.extend(["", "## 运维口径", ""])
    for item in package["ops_guidance"]:
        lines.append(f"- **{item['title']}**：{item['content']}")
    lines.extend(["", "## 交付模板", ""])
    for item in package["delivery_template"]:
        lines.append(f"- **{item['title']}**：{item['content']}")
    lines.extend(["", "## 验收模板", ""])
    for item in package["acceptance_template"]:
        lines.append(f"- **{item['title']}**：{item['content']}")
    lines.append("")
    return "\n".join(lines)


def write_productization_package(
    output_dir: Path,
    agent_key: str,
    run_key: str,
    package: dict[str, object],
    markdown: str,
) -> ProductizationArtifactPaths:
    """把产品化固化模板写成标准 JSON 和 Markdown 产物。"""

    target_dir = output_dir / agent_key
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / f"{run_key}-productization.json"
    markdown_path = target_dir / f"{run_key}-productization.md"
    json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    return ProductizationArtifactPaths(
        target_dir=target_dir,
        json_path=json_path,
        markdown_path=markdown_path,
    )


def _readiness_level(summary: dict[str, object]) -> str:
    completed = int(summary.get("completed_stages", 0))
    validated = int(summary.get("validated_change_count", 0))
    if completed >= 5 and validated >= 1:
        return "pilot_ready"
    if completed >= 4:
        return "incubation_ready"
    return "not_ready"


def _build_release_checklist(summary: dict[str, object], report: dict[str, object]) -> list[dict[str, object]]:
    completed = int(summary.get("completed_stages", 0))
    comparisons = int(summary.get("comparison_count", 0))
    validated = int(summary.get("validated_change_count", 0))
    recommendation_status = report.get("recommendation_status_summary", {})
    validated_recommendations = int(recommendation_status.get("validated", 0))
    return [
        {
            "title": "已完成首轮骨架孵化",
            "done": completed >= 4,
            "notes": f"当前已完成阶段 {completed}/{summary.get('total_stages', 0)}。",
        },
        {
            "title": "已具备对照验证记录",
            "done": comparisons > 0,
            "notes": f"当前累计对照记录 {comparisons} 条。",
        },
        {
            "title": "已形成可验证能力变化",
            "done": validated > 0,
            "notes": f"当前已记录回归/能力变化 {validated} 条。",
        },
        {
            "title": "已有 validated 蒸馏建议",
            "done": validated_recommendations > 0,
            "notes": f"当前 validated 建议 {validated_recommendations} 条。",
        },
    ]


def _build_ops_guidance(readiness_level: str) -> list[dict[str, str]]:
    return [
        {
            "title": "运行口径",
            "content": "继续以 run manifest 为唯一追踪基线，所有续跑、建议状态和回归结果都应写回同一条 run。",
        },
        {
            "title": "建议部署方式",
            "content": "在本地或灰度环境先运行，不建议在未达到 pilot_ready 前作为正式默认能力发布。",
        },
        {
            "title": "当前准备度判断",
            "content": f"本轮 run 当前处于 {readiness_level}，建议结合 validated_change_count 和多轮趋势再决定是否进入正式产品化发布。",
        },
        {
            "title": "运维关注点",
            "content": "重点关注样例版本、对照口径是否变动，以及建议状态与回归结果是否持续同步。",
        },
    ]


def _build_delivery_template(agent_key: str, readiness_level: str) -> list[dict[str, str]]:
    return [
        {
            "title": "交付范围",
            "content": f"交付 `{agent_key}` 的当前骨架、run manifest、蒸馏报告、产品化固化模板；当前准备度为 {readiness_level}。",
        },
        {
            "title": "建议附带材料",
            "content": "附带样例清单版本、最近一轮 run 对比结果、关键 validated 建议和代表性回归结论。",
        },
        {
            "title": "对外说明口径",
            "content": "明确当前能力是孵化中、灰度验证中还是已进入 pilot_ready，不混淆为完全成熟产品。",
        },
    ]


def _build_acceptance_template(readiness_level: str) -> list[dict[str, str]]:
    return [
        {
            "title": "最小验收项",
            "content": "能按蓝图起骨架、能记录 run、能补 comparison、能输出蒸馏建议、能回挂回归结果。",
        },
        {
            "title": "建议验收证据",
            "content": "提供至少一条 run manifest、一份蒸馏报告、一份产品化固化模板，以及一条 validated 建议的回归结果。",
        },
        {
            "title": "当前验收口径",
            "content": f"若当前准备度仍为 {readiness_level}，验收应以方法层和闭环完整性为主，不应按正式量产能力验收。",
        },
    ]


def _checkbox(done: bool) -> str:
    return "x" if done else " "


__all__ = [
    "ProductizationArtifactPaths",
    "build_productization_package",
    "render_productization_markdown",
    "write_productization_package",
]
