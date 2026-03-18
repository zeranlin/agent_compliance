from __future__ import annotations

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


def apply_confidence_calibrator(findings: list[Finding]) -> list[Finding]:
    for finding in findings:
        finding.confidence = calibrate_finding_confidence(finding)
    return findings


def calibrate_finding_confidence(finding: Finding) -> str:
    if finding.needs_human_review and finding.issue_type in UNCERTAIN_ISSUE_TYPES:
        return "medium"
    if finding.issue_type in {"technical_justification_needed", "template_mismatch", "other"}:
        return "medium"
    if finding.primary_authority:
        return "high" if finding.severity_score >= 2 else "medium"
    if finding.severity_score >= 3:
        return "medium"
    return finding.confidence or "medium"
