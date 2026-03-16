from __future__ import annotations

import json
from pathlib import Path

from agent_compliance.config import detect_paths
from agent_compliance.schemas import ReviewResult


def write_review_outputs(review: ReviewResult, output_stem: str) -> tuple[Path, Path]:
    paths = detect_paths()
    paths.review_root.mkdir(parents=True, exist_ok=True)

    json_path = paths.review_root / f"{output_stem}-findings.json"
    md_path = paths.review_root / f"{output_stem}-review.md"

    json_path.write_text(
        json.dumps(review.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(_render_markdown(review), encoding="utf-8")
    return json_path, md_path


def _render_markdown(review: ReviewResult) -> str:
    lines = [
        f"# {review.document_name} 本地审查结果",
        "",
        "## 审查摘要",
        "",
        f"- 审查范围：`{review.review_scope}`",
        f"- 审查时间：`{review.review_timestamp}`",
        f"- 风险摘要：{review.overall_risk_summary}",
        "",
        "## Findings",
        "",
    ]

    for finding in review.findings:
        lines.extend(
            [
                f"### {finding.finding_id} {finding.problem_title}",
                f"- 问题类型：`{finding.issue_type}`",
                f"- 条款编号：`{finding.clause_id}`",
                f"- 位置：`{finding.section_path}`",
                f"- 页码提示：`{finding.page_hint}`",
                f"- 表格/评分项：`{finding.table_or_item_label}`",
                f"- 辅助行号：`{finding.text_line_start}-{finding.text_line_end}`",
                f"- 风险等级：`{finding.risk_level}`",
                f"- 合规判断：`{finding.compliance_judgment}`",
                f"- 原文摘录：`{finding.source_text}`",
                f"- 风险说明：{finding.why_it_is_risky}",
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
