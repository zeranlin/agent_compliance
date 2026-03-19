from __future__ import annotations

from agent_compliance.knowledge.catalog_knowledge_profile import catalog_knowledge_profiles_for_classification
from agent_compliance.knowledge.procurement_catalog import CatalogClassification
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
) -> list[Finding]:
    for finding in findings:
        finding.confidence = calibrate_finding_confidence(finding, classification=classification)
    return findings


def calibrate_finding_confidence(
    finding: Finding,
    *,
    classification: CatalogClassification | None = None,
) -> str:
    if finding.needs_human_review and finding.issue_type in UNCERTAIN_ISSUE_TYPES:
        return "medium"
    if finding.issue_type in {"technical_justification_needed", "template_mismatch", "other"}:
        return "medium"
    if finding.primary_authority:
        base = "high" if finding.severity_score >= 2 else "medium"
    elif finding.severity_score >= 3:
        base = "medium"
    else:
        base = finding.confidence or "medium"
    return _catalog_adjusted_confidence(finding, base, classification=classification)


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
