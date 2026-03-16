from __future__ import annotations

from pathlib import Path

from agent_compliance.config import detect_paths


def benchmark_summary() -> dict[str, str]:
    paths = detect_paths()
    benchmark_path = paths.repo_root / "docs" / "evals" / "cases" / "starter-benchmark-set.md"
    rubric_path = paths.repo_root / "docs" / "evals" / "rubrics" / "review-rubric.md"
    return {
        "benchmark_path": str(benchmark_path),
        "rubric_path": str(rubric_path),
        "status": "第一阶段仅提供评测入口说明，后续版本接入自动跑分。",
    }
