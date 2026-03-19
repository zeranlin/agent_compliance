from __future__ import annotations

from pathlib import Path
import re
import json

from agent_compliance.config import detect_paths
from agent_compliance.evals.benchmark_regression_reporter import build_benchmark_regression_report


def list_benchmark_cases() -> list[dict[str, object]]:
    paths = detect_paths()
    cases_root = paths.repo_root / "docs" / "evals" / "cases"
    cases: list[dict[str, object]] = []
    for path in sorted(cases_root.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        title = _extract_title(content) or path.stem
        case_ids = _extract_case_ids(content)
        issue_types = _extract_issue_types(content)
        cases.append(
            {
                "path": str(path),
                "title": title,
                "case_count": len(case_ids),
                "case_ids": case_ids,
                "issue_types": issue_types,
            }
        )
    return cases


def benchmark_summary() -> dict[str, str]:
    paths = detect_paths()
    benchmark_path = paths.repo_root / "docs" / "evals" / "cases" / "starter-benchmark-set.md"
    rubric_path = paths.repo_root / "docs" / "evals" / "rubrics" / "review-rubric.md"
    cases = list_benchmark_cases()
    latest_gate = _latest_benchmark_gate(paths.repo_root / "docs" / "generated" / "improvement")
    return {
        "benchmark_path": str(benchmark_path),
        "rubric_path": str(rubric_path),
        "case_files": len(cases),
        "case_count": sum(int(item["case_count"]) for item in cases),
        "issue_types_covered": sorted({issue for item in cases for issue in item.get("issue_types", [])}),
        "cases": cases,
        "latest_benchmark_gate": latest_gate,
        "benchmark_regression_report": build_benchmark_regression_report(latest_gate),
        "status": "当前可读取本地 benchmark 样本清单与案例数量，后续版本继续接入自动跑分。",
    }


def _extract_title(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _extract_case_ids(content: str) -> list[str]:
    explicit = re.findall(r"`case_id`:\s*`([^`]+)`", content)
    if explicit:
        return explicit
    headings = re.findall(r"^###\s+(.+)$", content, flags=re.MULTILINE)
    return [heading.strip() for heading in headings]


def _extract_issue_types(content: str) -> list[str]:
    grouped = re.findall(r"`expected_issue_types`:\s*([^\\n]+)", content)
    if grouped:
        discovered: list[str] = []
        for chunk in grouped:
            discovered.extend(re.findall(r"`([^`]+)`", chunk))
        if discovered:
            return sorted(set(discovered))
    explicit = re.findall(r"`expected_issue_type`:\s*`([^`]+)`", content)
    if explicit:
        return sorted(set(explicit))
    discovered = re.findall(
        r"`(geographic_restriction|personnel_restriction|excessive_supplier_qualification|qualification_domain_mismatch|irrelevant_certification_or_award|duplicative_scoring_advantage|scoring_content_mismatch|ambiguous_requirement|excessive_scoring_weight|post_award_proof_substitution|narrow_technical_parameter|technical_justification_needed|unclear_acceptance_standard|one_sided_commercial_term|payment_acceptance_linkage|other|scoring_structure_imbalance|template_mismatch)`",
        content,
    )
    return sorted(set(discovered))


def _latest_benchmark_gate(improvement_root: Path) -> dict[str, object] | None:
    gates = sorted(improvement_root.glob("*-benchmark-gate.json"))
    if not gates:
        return None
    latest = gates[-1]
    payload = json.loads(latest.read_text(encoding="utf-8"))
    return {
        "path": str(latest),
        "status": payload.get("status"),
        "candidate_count": payload.get("candidate_count", 0),
        "covered_count": payload.get("covered_count", 0),
        "needs_benchmark_count": payload.get("needs_benchmark_count", 0),
    }
