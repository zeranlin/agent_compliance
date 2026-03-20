from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator.comparison_collector import (
    collect_validation_comparisons_from_manifest,
    collect_validation_comparisons_from_root,
)
from agent_compliance.incubator.sample_registry import build_sample_manifest


class ComparisonCollectorTests(unittest.TestCase):
    def test_collect_from_root_discovers_standard_sample_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sample_dir(
                root / "case-001",
                human="输出项目概述\n输出技术需求框架",
                strong="建议输出结构化需求骨架。",
                target="输出项目概述",
            )
            self._write_sample_dir(
                root / "case-002",
                human="输出项目概述\n输出验收需求框架",
                strong="建议输出验收要求。",
                target="输出项目概述\n输出验收需求框架",
                summary="case-002 summary",
            )

            comparisons = collect_validation_comparisons_from_root(root)

            self.assertEqual(len(comparisons), 2)
            self.assertEqual(comparisons[0].sample_id, "case-001")
            self.assertEqual(comparisons[1].summary, "case-002 summary")

    def test_collect_from_manifest_only_reads_declared_sample_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sample_dir(
                root / "positive-a",
                human="输出项目概述\n输出技术需求框架",
                strong="建议输出结构化需求骨架。",
                target="输出项目概述",
            )
            self._write_sample_dir(
                root / "ignored-case",
                human="输出项目概述\n输出验收需求框架",
                strong="建议输出验收要求。",
                target="输出项目概述",
            )
            manifest = build_sample_manifest(
                "第一批需求调查样例",
                positive_paths=("samples/positive/positive-a.docx",),
            )

            comparisons = collect_validation_comparisons_from_manifest(root, manifest)

            self.assertEqual(len(comparisons), 1)
            self.assertEqual(comparisons[0].sample_id, "positive-a")

    def _write_sample_dir(
        self,
        sample_dir: Path,
        *,
        human: str,
        strong: str,
        target: str,
        summary: str | None = None,
    ) -> None:
        sample_dir.mkdir(parents=True, exist_ok=True)
        (sample_dir / "human_baseline.txt").write_text(human, encoding="utf-8")
        (sample_dir / "strong_agent_result.txt").write_text(strong, encoding="utf-8")
        (sample_dir / "target_agent_result.txt").write_text(target, encoding="utf-8")
        if summary is not None:
            (sample_dir / "summary.txt").write_text(summary, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
