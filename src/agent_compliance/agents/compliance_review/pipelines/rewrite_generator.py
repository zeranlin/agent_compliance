from __future__ import annotations

from agent_compliance.agents.compliance_review.pipelines.procurement_stage_router import ProcurementStageProfile, route_procurement_stage
from agent_compliance.core.schemas import Finding


ACTION_DIRECT = "direct_modify"
ACTION_SOFTEN = "soften_expression"
ACTION_JUSTIFY = "justify_necessity"
ACTION_REVIEW = "procurement_legal_review"

ACTION_PREFIXES = {
    ACTION_DIRECT: "建议直接修改：",
    ACTION_SOFTEN: "建议弱化表述：",
    ACTION_JUSTIFY: "建议补充必要性论证：",
    ACTION_REVIEW: "建议采购/法务复核：",
}


def apply_rewrite_generator(
    findings: list[Finding],
    *,
    stage_profile: ProcurementStageProfile | None = None,
) -> list[Finding]:
    stage_profile = stage_profile or route_procurement_stage(findings=findings)
    for finding in findings:
        action = determine_suggested_action(finding, stage_profile=stage_profile)
        prefix = ACTION_PREFIXES[action]
        if finding.rewrite_suggestion and not _has_action_prefix(finding.rewrite_suggestion):
            finding.rewrite_suggestion = f"{prefix}{finding.rewrite_suggestion}"
        if action in {ACTION_REVIEW, ACTION_JUSTIFY} and not finding.human_review_reason:
            finding.human_review_reason = _default_review_reason(finding, stage_profile=stage_profile)
    return findings


def determine_suggested_action(
    finding: Finding,
    *,
    stage_profile: ProcurementStageProfile | None = None,
) -> str:
    stage_profile = stage_profile or route_procurement_stage(findings=[finding])
    text = " ".join(filter(None, [finding.problem_title, finding.why_it_is_risky, finding.legal_or_policy_basis]))
    if finding.needs_human_review:
        if finding.issue_type == "technical_justification_needed" or "论证" in text:
            return ACTION_JUSTIFY
        return ACTION_REVIEW
    if finding.issue_type == "technical_justification_needed" or "论证" in text:
        return ACTION_JUSTIFY
    if any(
        marker in text
        for marker in ("主观", "高分", "过严", "边界", "弱化", "不宜继续", "压降", "量化锚点", "开放式")
    ):
        return ACTION_SOFTEN
    if stage_profile.stage_key == "pre_release_requirement_review" and finding.issue_type in {
        "ambiguous_requirement",
        "unclear_acceptance_standard",
        "payment_acceptance_linkage",
        "template_mismatch",
        "other",
    }:
        return ACTION_SOFTEN
    return ACTION_DIRECT


def _has_action_prefix(text: str) -> bool:
    return any(text.startswith(prefix) for prefix in ACTION_PREFIXES.values())


def _default_review_reason(
    finding: Finding,
    *,
    stage_profile: ProcurementStageProfile | None = None,
) -> str:
    stage_profile = stage_profile or route_procurement_stage(findings=[finding])
    if stage_profile.stage_key == "pre_release_requirement_review":
        if finding.issue_type == "technical_justification_needed":
            return "发布前建议结合使用场景、市场可得性和必要性说明补充论证后再决定是否保留。"
        return "发布前建议由采购与法务结合项目边界、履约安排和法规适用性进一步复核。"
    return "建议结合采购场景和法规适用性进一步复核。"
