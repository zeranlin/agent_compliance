from __future__ import annotations

import unittest

from agent_compliance.incubator.sample_registry import (
    build_sample_manifest,
    summarize_sample_manifest,
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
        )

        sample_set = manifest.to_sample_set(benchmark_refs=("bench-001",))
        summary = summarize_sample_manifest(manifest)

        self.assertEqual(sample_set.name, "第一批合规样例")
        self.assertEqual(sample_set.positive_examples, ("one", "two"))
        self.assertEqual(sample_set.benchmark_refs, ("bench-001",))
        self.assertEqual(summary["positive_count"], 2)
        self.assertEqual(summary["negative_count"], 1)


if __name__ == "__main__":
    unittest.main()
