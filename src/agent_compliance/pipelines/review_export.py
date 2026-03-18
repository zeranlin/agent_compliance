from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from agent_compliance.schemas import Finding, ReviewResult


def export_review_bytes(
    review: ReviewResult,
    *,
    export_format: str,
    mode: str,
    document_payload: dict[str, Any] | None = None,
) -> tuple[bytes, str, str]:
    normalized_format = export_format.lower()
    normalized_mode = "summary" if mode == "summary" else "full"
    if normalized_format == "json":
        payload = build_export_payload(review, mode=normalized_mode, document_payload=document_payload)
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return content, "application/json; charset=utf-8", build_export_filename(review.document_name, normalized_mode, "json")
    if normalized_format == "markdown":
        content = render_export_markdown(review, mode=normalized_mode, document_payload=document_payload).encode("utf-8")
        return content, "text/markdown; charset=utf-8", build_export_filename(review.document_name, normalized_mode, "md")
    raise ValueError(f"不支持的导出格式：{export_format}")


def build_export_payload(
    review: ReviewResult,
    *,
    mode: str,
    document_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    findings = _pick_findings(review.findings, mode)
    summary = {
        "overall_risk_summary": review.overall_risk_summary,
        "finding_count": len(findings),
        "high_risk_count": sum(1 for item in findings if item.risk_level == "high"),
        "medium_risk_count": sum(1 for item in findings if item.risk_level == "medium"),
        "low_risk_count": sum(1 for item in findings if item.risk_level == "low"),
    }
    document = {
        "document_name": review.document_name,
        "source_path": (document_payload or {}).get("source_path"),
        "normalized_text_path": (document_payload or {}).get("normalized_text_path"),
        "review_scope": review.review_scope,
        "jurisdiction": review.jurisdiction,
    }
    return {
        "document": document,
        "review_summary": summary,
        "export_meta": {
            "export_format": "json",
            "export_mode": mode,
            "export_timestamp": datetime.now().isoformat(timespec="seconds"),
            "generated_by": "agent_compliance.review_export",
        },
        "findings": [_serialize_finding(item, mode=mode) for item in findings],
        "items_for_human_review": review.items_for_human_review,
        "review_limitations": review.review_limitations,
    }


def render_export_markdown(
    review: ReviewResult,
    *,
    mode: str,
    document_payload: dict[str, Any] | None = None,
) -> str:
    findings = _pick_findings(review.findings, mode)
    lines = [
        f"# {review.document_name} 审查结果导出",
        "",
        "## 文件信息",
        "",
        f"- 审查范围：`{review.review_scope}`",
        f"- 审查时间：`{review.review_timestamp}`",
        f"- 导出模式：`{'主问题版' if mode == 'summary' else '完整明细版'}`",
    ]
    if document_payload:
        lines.append(f"- 原文件：`{document_payload.get('source_path', '')}`")
    lines.extend(
        [
            "",
            "## 风险摘要",
            "",
            f"- 风险摘要：{review.overall_risk_summary}",
            f"- 问题数量：`{len(findings)}`",
            "",
            "## 问题清单",
            "",
        ]
    )

    for finding in findings:
        lines.extend(
            [
                f"### {finding.finding_id} {finding.problem_title}",
                f"- 章节：`{_chapter_group(finding)}`",
                f"- 风险等级：`{finding.risk_level}`",
                f"- 置信度：`{finding.confidence}`",
                f"- 合规判断：`{finding.compliance_judgment}`",
                f"- 位置：`{_full_location(finding)}`",
                f"- 问题类型：`{finding.issue_type}`",
                f"- 代表性证据：`{finding.source_text}`" if mode == "summary" else f"- 原文摘录：`{finding.source_text}`",
                f"- 风险说明：{finding.why_it_is_risky}",
                f"- 法规依据：{finding.legal_or_policy_basis or finding.primary_authority or '暂无'}",
                f"- 适用逻辑：{finding.applicability_logic or finding.human_review_reason or '暂无'}",
                f"- 修改建议：{finding.rewrite_suggestion}",
                "",
            ]
        )

    if review.items_for_human_review:
        lines.extend(["## 需人工复核", ""])
        for item in review.items_for_human_review:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def build_export_filename(document_name: str, mode: str, extension: str) -> str:
    stem = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", document_name).strip("._") or "review-export"
    stem = re.sub(r"\.(docx|pdf|txt|md|json)$", "", stem, flags=re.IGNORECASE)
    suffix = "summary" if mode == "summary" else "full"
    return f"{stem}-{suffix}.{extension}"


def _pick_findings(findings: list[Finding], mode: str) -> list[Finding]:
    if mode != "summary":
        return findings
    return [item for item in findings if _is_main_issue(item)]


def _is_main_issue(finding: Finding) -> bool:
    return finding.finding_origin == "analyzer" or (
        finding.finding_origin == "llm_added" and bool(re.search(r"章节|主问题", finding.problem_title or ""))
    )


def _chapter_group(finding: Finding) -> str:
    text = " ".join(
        part for part in [finding.problem_title, finding.section_path, finding.source_section] if part
    )
    if re.search(r"资格|申请人的资格要求|准入门槛", text):
        return "资格"
    if re.search(r"评分|评标信息|演示|品牌档次|认证评分|商务评分", text):
        return "评分"
    if re.search(r"技术|标准|检测报告|证明材料", text):
        return "技术"
    return "商务/验收"


def _full_location(finding: Finding) -> str:
    parts: list[str] = []
    if finding.section_path:
        parts.append(finding.section_path)
    elif finding.source_section:
        parts.append(finding.source_section)
    if finding.table_or_item_label:
        parts.append(finding.table_or_item_label)
    if finding.page_hint:
        parts.append(finding.page_hint)
    if finding.text_line_start and finding.text_line_end:
        if finding.text_line_start == finding.text_line_end:
            parts.append(f"行 {finding.text_line_start}")
        else:
            parts.append(f"行 {finding.text_line_start}-{finding.text_line_end}")
    return " | ".join(part for part in parts if part) or "未定位"


def _serialize_finding(finding: Finding, *, mode: str) -> dict[str, Any]:
    base = finding.to_dict()
    if mode == "summary":
        return {
            "finding_id": base["finding_id"],
            "problem_title": base["problem_title"],
            "chapter_group": _chapter_group(finding),
            "risk_level": base["risk_level"],
            "confidence": base["confidence"],
            "compliance_judgment": base["compliance_judgment"],
            "source_section": base["source_section"],
            "section_path": base["section_path"],
            "table_or_item_label": base["table_or_item_label"],
            "page_hint": base["page_hint"],
            "text_line_start": base["text_line_start"],
            "text_line_end": base["text_line_end"],
            "representative_evidence": base["source_text"],
            "why_it_is_risky": base["why_it_is_risky"],
            "legal_or_policy_basis": base["legal_or_policy_basis"],
            "primary_authority": base.get("primary_authority"),
            "secondary_authorities": base.get("secondary_authorities"),
            "applicability_logic": base.get("applicability_logic"),
            "rewrite_suggestion": base["rewrite_suggestion"],
            "needs_human_review": base["needs_human_review"],
            "human_review_reason": base["human_review_reason"],
            "issue_type": base["issue_type"],
            "finding_origin": base.get("finding_origin", "rule"),
        }
    return base
