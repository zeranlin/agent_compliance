from __future__ import annotations

from pathlib import Path

from agent_compliance.incubator.comparison_builder import build_validation_comparison_from_files
from agent_compliance.incubator.lifecycle import ValidationComparison
from agent_compliance.incubator.sample_registry import SampleManifest


HUMAN_BASELINE_FILENAME = "human_baseline.txt"
STRONG_AGENT_RESULT_FILENAME = "strong_agent_result.txt"
TARGET_AGENT_RESULT_FILENAME = "target_agent_result.txt"
SUMMARY_FILENAME = "summary.txt"


def collect_validation_comparisons_from_root(
    root_dir: Path,
    *,
    sample_ids: tuple[str, ...] = (),
) -> tuple[ValidationComparison, ...]:
    """从标准目录结构自动采集对照结果。

    目录约定：
    - <root>/<sample_id>/human_baseline.txt
    - <root>/<sample_id>/strong_agent_result.txt
    - <root>/<sample_id>/target_agent_result.txt
    - <root>/<sample_id>/summary.txt  (可选)
    """

    if not root_dir.exists():
        raise FileNotFoundError(root_dir)
    if not root_dir.is_dir():
        raise NotADirectoryError(root_dir)

    candidate_ids = sample_ids or _discover_sample_ids(root_dir)
    comparisons: list[ValidationComparison] = []
    for sample_id in candidate_ids:
        comparison = _load_single_comparison(root_dir, sample_id)
        if comparison is not None:
            comparisons.append(comparison)
    return tuple(comparisons)


def collect_validation_comparisons_from_manifest(
    root_dir: Path,
    manifest: SampleManifest,
) -> tuple[ValidationComparison, ...]:
    """按样例清单中声明的 sample_id，从标准目录采集对照结果。"""

    return collect_validation_comparisons_from_root(
        root_dir,
        sample_ids=manifest.sample_ids,
    )


def _discover_sample_ids(root_dir: Path) -> tuple[str, ...]:
    sample_ids: list[str] = []
    for child in sorted(root_dir.iterdir()):
        if child.is_dir():
            sample_ids.append(child.name)
    return tuple(sample_ids)


def _load_single_comparison(root_dir: Path, sample_id: str) -> ValidationComparison | None:
    sample_dir = root_dir / sample_id
    if not sample_dir.is_dir():
        return None

    human_path = sample_dir / HUMAN_BASELINE_FILENAME
    strong_path = sample_dir / STRONG_AGENT_RESULT_FILENAME
    target_path = sample_dir / TARGET_AGENT_RESULT_FILENAME
    if not (human_path.exists() and strong_path.exists() and target_path.exists()):
        return None

    summary_path = sample_dir / SUMMARY_FILENAME
    summary = ""
    if summary_path.exists():
        summary = summary_path.read_text(encoding="utf-8").strip()

    return build_validation_comparison_from_files(
        sample_id=sample_id,
        human_baseline_path=human_path,
        strong_agent_result_path=strong_path,
        target_agent_result_path=target_path,
        summary=summary,
    )


__all__ = [
    "HUMAN_BASELINE_FILENAME",
    "STRONG_AGENT_RESULT_FILENAME",
    "TARGET_AGENT_RESULT_FILENAME",
    "SUMMARY_FILENAME",
    "collect_validation_comparisons_from_manifest",
    "collect_validation_comparisons_from_root",
]
