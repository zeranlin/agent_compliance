from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator.sample_registry import (
    build_sample_manifest,
    load_sample_manifest,
    serialize_sample_manifest,
    summarize_sample_manifest,
    write_sample_manifest,
)


class SampleRegistryTests(unittest.TestCase):
    def test_build_manifest_groups_assets_by_label(self) -> None:
        manifest = build_sample_manifest(
            "第一批预算样例",
            positive_paths=("samples/positive/a.docx",),
            negative_paths=("samples/negative/b.docx",),
            boundary_paths=("samples/boundary/c.docx",),
        )

        self.assertEqual(manifest.positive_examples, ("a",))
        self.assertEqual(manifest.negative_examples, ("b",))
        self.assertEqual(manifest.boundary_examples, ("c",))

    def test_manifest_can_convert_to_sample_set_and_summary(self) -> None:
        manifest = build_sample_manifest(
            "第一批合规样例",
            positive_paths=("samples/positive/one.docx", "samples/positive/two.docx"),
            negative_paths=("samples/negative/three.docx",),
            version="v2",
            agent_key="compliance_review",
            benchmark_refs=("bench-001",),
            change_summary="补入一条负样例",
        )

        sample_set = manifest.to_sample_set()
        summary = summarize_sample_manifest(manifest)

        self.assertEqual(sample_set.name, "第一批合规样例@v2")
        self.assertEqual(sample_set.positive_examples, ("one", "two"))
        self.assertEqual(sample_set.benchmark_refs, ("bench-001",))
        self.assertEqual(summary["version"], "v2")
        self.assertEqual(summary["agent_key"], "compliance_review")
        self.assertEqual(summary["positive_count"], 2)
        self.assertEqual(summary["negative_count"], 1)
        self.assertEqual(summary["change_summary"], "补入一条负样例")

    def test_manifest_can_round_trip_as_versioned_asset(self) -> None:
        manifest = build_sample_manifest(
            "第一批预算样例",
            positive_paths=("samples/positive/a.docx",),
            version="v3",
            agent_key="budget_demand",
            change_summary="追加正样例并绑定预算 benchmark",
            benchmark_refs=("budget-bench-001",),
        )

        serialized = serialize_sample_manifest(manifest)
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = write_sample_manifest(Path(temp_dir), manifest)
            loaded = load_sample_manifest(manifest_path)

        self.assertEqual(serialized["version"], "v3")
        self.assertEqual(loaded.version, "v3")
        self.assertEqual(loaded.agent_key, "budget_demand")
        self.assertEqual(loaded.benchmark_refs, ("budget-bench-001",))
        self.assertEqual(loaded.change_summary, "追加正样例并绑定预算 benchmark")


if __name__ == "__main__":
    unittest.main()
