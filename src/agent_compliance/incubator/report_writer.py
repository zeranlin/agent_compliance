from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DistillationArtifactPaths:
    """描述一次蒸馏报告落盘结果。"""

    target_dir: Path
    json_path: Path
    markdown_path: Path


def write_distillation_report(
    output_dir: Path,
    agent_key: str,
    run_key: str,
    report: dict[str, object],
    report_markdown: str,
) -> DistillationArtifactPaths:
    """把蒸馏报告写入标准 JSON 和 Markdown 产物。"""

    target_dir = output_dir / agent_key
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / f"{run_key}-distillation-report.json"
    markdown_path = target_dir / f"{run_key}-distillation-report.md"

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(report_markdown, encoding="utf-8")

    return DistillationArtifactPaths(
        target_dir=target_dir,
        json_path=json_path,
        markdown_path=markdown_path,
    )
