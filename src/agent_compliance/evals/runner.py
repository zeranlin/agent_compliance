from __future__ import annotations

from pathlib import Path
import re

from agent_compliance.config import detect_paths


def list_benchmark_cases() -> list[dict[str, object]]:
    paths = detect_paths()
    cases_root = paths.repo_root / "docs" / "evals" / "cases"
    cases: list[dict[str, object]] = []
    for path in sorted(cases_root.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        title = _extract_title(content) or path.stem
        case_ids = _extract_case_ids(content)
        cases.append(
            {
                "path": str(path),
                "title": title,
                "case_count": len(case_ids),
                "case_ids": case_ids,
            }
        )
    return cases


def benchmark_summary() -> dict[str, str]:
    paths = detect_paths()
    benchmark_path = paths.repo_root / "docs" / "evals" / "cases" / "starter-benchmark-set.md"
    rubric_path = paths.repo_root / "docs" / "evals" / "rubrics" / "review-rubric.md"
    cases = list_benchmark_cases()
    return {
        "benchmark_path": str(benchmark_path),
        "rubric_path": str(rubric_path),
        "case_files": len(cases),
        "case_count": sum(int(item["case_count"]) for item in cases),
        "cases": cases,
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
