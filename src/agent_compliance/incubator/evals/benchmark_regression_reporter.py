from __future__ import annotations

from typing import Any

from agent_compliance.agents.compliance_review.pipelines.procurement_stage_router import ProcurementStageProfile, route_procurement_stage


def build_benchmark_regression_report(
    benchmark_gate: dict[str, Any] | None,
    *,
    stage_profile: ProcurementStageProfile | None = None,
) -> dict[str, Any]:
    stage_profile = stage_profile or route_procurement_stage()
    if not benchmark_gate:
        return {
            "stage_key": stage_profile.stage_key,
            "stage_name": stage_profile.stage_name,
            "status": "no_gate",
            "summary": "当前还没有可用的 benchmark gate 结果，暂不能判断发布前审查场景下的提升与缺口。",
            "strengths": [],
            "gaps": ["缺少 benchmark gate 结果，无法按发布前审查场景解释当前收益与缺口。"],
            "next_actions": ["先运行启用本地模型的审查任务，生成规则候选和 benchmark gate，再进行回归解释。"],
        }

    covered_count = int(benchmark_gate.get("covered_count", 0) or 0)
    needs_count = int(benchmark_gate.get("needs_benchmark_count", 0) or 0)
    candidate_count = int(benchmark_gate.get("candidate_count", 0) or 0)
    status = str(benchmark_gate.get("status") or "ok")

    scene_summary = benchmark_gate.get("catalog_scene_summary", []) or []
    domain_summary = benchmark_gate.get("domain_summary", []) or []
    authority_summary = benchmark_gate.get("authority_summary", []) or []
    profile_risk_summary = benchmark_gate.get("profile_risk_summary", []) or []

    strengths: list[str] = []
    gaps: list[str] = []
    next_actions: list[str] = []

    if covered_count > 0:
        strengths.append(f"已有 {covered_count} 条候选规则在 benchmark 中找到对应问题类型，说明发布前审查的高频风险开始形成可复用覆盖。")
    if authority_summary:
        top_authority = authority_summary[0]
        strengths.append(
            f"法规依据已开始进入 benchmark 总结，当前最集中的主依据是“{top_authority.get('primary_authority', '未知依据')}”。"
        )
    if scene_summary:
        top_scene = scene_summary[0]
        strengths.append(
            f"候选规则已经能按品目场景汇总，当前最集中的审查场景是“{top_scene.get('primary_catalog_name', '未知品目')}”。"
        )

    if needs_count > 0:
        gaps.append(f"仍有 {needs_count} 条候选规则缺少 benchmark 样本支撑，发布前审查场景下的能力提升还没有完全被验证。")
        next_actions.append("优先补齐缺少 benchmark 的候选规则样本，避免发布前高风险条款只靠一次性命中而没有回归支撑。")
    if domain_summary:
        top_domain = domain_summary[0]
        next_actions.append(
            f"继续优先回归“{top_domain.get('primary_domain_key', 'unknown')}”场景，验证该领域在发布前审查阶段的主问题召回和误报边界。"
        )
    if profile_risk_summary:
        top_pattern = profile_risk_summary[0]
        next_actions.append(
            f"围绕高频画像风险“{top_pattern.get('risk_pattern', '未知模式')}”补充案例和 benchmark，提升采购人发布前复核时的稳定解释能力。"
        )
    if not next_actions:
        next_actions.append("继续按品目场景扩充 benchmark 样本，并对照人工审查结果验证主问题收束和改稿建议质量。")

    if not gaps and status == "ok" and candidate_count:
        summary = (
            f"当前 benchmark gate 显示 {candidate_count} 条候选规则已全部具备发布前审查场景下的基础覆盖，"
            "说明近期新增能力已经开始形成可回归验证的稳定闭环。"
        )
    else:
        summary = (
            f"当前 benchmark gate 共记录 {candidate_count} 条候选规则，其中 {covered_count} 条已覆盖、"
            f"{needs_count} 条仍待补 benchmark。系统已经能从发布前审查视角说明部分收益，但能力闭环仍需继续补样本和回归。"
        )

    return {
        "stage_key": stage_profile.stage_key,
        "stage_name": stage_profile.stage_name,
        "status": status,
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "next_actions": next_actions,
    }
