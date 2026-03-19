from __future__ import annotations

from agent_compliance.knowledge.catalog_knowledge_profile import catalog_knowledge_profiles_for_classification
from agent_compliance.knowledge.procurement_catalog import CatalogClassification
from agent_compliance.pipelines.procurement_stage_router import ProcurementStageProfile, route_procurement_stage
from agent_compliance.pipelines.rewrite_generator import (
    ACTION_DIRECT,
    ACTION_JUSTIFY,
    ACTION_REVIEW,
    ACTION_SOFTEN,
    determine_suggested_action,
)
from agent_compliance.schemas import Finding


UNCERTAIN_ISSUE_TYPES = {
    "technical_justification_needed",
    "template_mismatch",
    "other",
    "qualification_domain_mismatch",
    "scoring_content_mismatch",
    "unclear_acceptance_standard",
    "one_sided_commercial_term",
    "payment_acceptance_linkage",
}


def apply_confidence_calibrator(
    findings: list[Finding],
    *,
    classification: CatalogClassification | None = None,
    stage_profile: ProcurementStageProfile | None = None,
) -> list[Finding]:
    stage_profile = stage_profile or route_procurement_stage(findings=findings)
    for finding in findings:
        finding.confidence = calibrate_finding_confidence(
            finding,
            classification=classification,
            stage_profile=stage_profile,
        )
    return findings


def calibrate_finding_confidence(
    finding: Finding,
    *,
    classification: CatalogClassification | None = None,
    stage_profile: ProcurementStageProfile | None = None,
) -> str:
    if finding.needs_human_review and finding.issue_type in UNCERTAIN_ISSUE_TYPES:
        return _stage_adjusted_confidence(
            finding,
            "medium",
            stage_profile=stage_profile,
            classification=classification,
        )
    if finding.issue_type in {"technical_justification_needed", "template_mismatch", "other"}:
        return _stage_adjusted_confidence(
            finding,
            "medium",
            stage_profile=stage_profile,
            classification=classification,
        )
    if finding.primary_authority:
        base = "high" if finding.severity_score >= 2 else "medium"
    elif finding.severity_score >= 3:
        base = "medium"
    else:
        base = finding.confidence or "medium"
    return _stage_adjusted_confidence(
        finding,
        base,
        stage_profile=stage_profile,
        classification=classification,
    )


def _stage_adjusted_confidence(
    finding: Finding,
    base_confidence: str,
    *,
    stage_profile: ProcurementStageProfile | None = None,
    classification: CatalogClassification | None = None,
) -> str:
    stage_key = stage_profile.stage_key if stage_profile else None
    adjusted = base_confidence
    action = determine_suggested_action(finding, stage_profile=stage_profile)
    if stage_key == "pre_release_requirement_review":
        if action in {ACTION_JUSTIFY, ACTION_REVIEW} and adjusted == "low" and finding.severity_score >= 2:
            adjusted = "medium"
        if action == ACTION_JUSTIFY and adjusted == "high":
            adjusted = "medium"
        if action == ACTION_REVIEW and adjusted == "high" and finding.issue_type in UNCERTAIN_ISSUE_TYPES:
            adjusted = "medium"
        if action == ACTION_SOFTEN and adjusted == "low" and finding.severity_score >= 2:
            adjusted = "medium"
        if action == ACTION_DIRECT and finding.primary_authority and finding.severity_score >= 2:
            adjusted = "high"
    return _catalog_adjusted_confidence(finding, adjusted, classification=classification)


def _catalog_adjusted_confidence(
    finding: Finding,
    base_confidence: str,
    classification: CatalogClassification | None = None,
) -> str:
    profiles = catalog_knowledge_profiles_for_classification(classification)
    if not profiles:
        return base_confidence
    haystack = " ".join(
        [
            finding.problem_title or "",
            finding.source_text or "",
            finding.why_it_is_risky or "",
            finding.legal_or_policy_basis or "",
        ]
    )
    matched_profile = False
    for profile in profiles:
        if any(pattern and pattern in haystack for pattern in profile.high_risk_patterns):
            matched_profile = True
            break
        if finding.issue_type in profile.related_issue_types:
            matched_profile = True
            break
    if matched_profile and base_confidence == "medium" and finding.severity_score >= 2 and not finding.needs_human_review:
        return "high"
    if finding.needs_human_review and matched_profile and finding.issue_type == "technical_justification_needed":
        return "medium"
    return base_confidence
