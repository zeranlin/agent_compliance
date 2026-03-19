from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest

from agent_compliance.cache.file_cache import sha256_file
from agent_compliance.cache.review_cache import (
    REVIEW_CACHE_VERSION,
    build_review_cache_key,
    cache_path_for_key,
    reference_snapshot_id,
)
from agent_compliance.config import detect_paths
from agent_compliance.rules.base import RULE_SET_VERSION
from tests._bootstrap import REPO_ROOT
from agent_compliance.evals.runner import benchmark_summary


class CliSmokeTest(unittest.TestCase):
    def test_benchmark_paths_point_inside_repo(self) -> None:
        summary = benchmark_summary()
        self.assertTrue(Path(summary["benchmark_path"]).exists())
        self.assertTrue(Path(summary["rubric_path"]).exists())
        self.assertIn("issue_types_covered", summary)
        self.assertIn("geographic_restriction", summary["issue_types_covered"])
        self.assertIn("benchmark_regression_report", summary)
        self.assertEqual(summary["benchmark_regression_report"]["stage_name"], "采购需求形成与发布前审查")

    def test_rule_scan_returns_json(self) -> None:
        sample = "供应商须在采购人所在地行政区域内设有分公司，否则投标无效。"
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
            handle.write(sample)
            temp_path = Path(handle.name)

        result = subprocess.run(
            [sys.executable, "-m", "agent_compliance", "scan-rules", str(temp_path), "--json"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "PYTHONPATH": str(REPO_ROOT / "src")},
        )
        self.assertIn("rule_hits", result.stdout)

    def test_web_command_is_available(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent_compliance", "web", "--help"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "PYTHONPATH": str(REPO_ROOT / "src")},
        )
        self.assertIn("Run local review web UI", result.stdout)

    def test_review_uses_cache_on_second_run(self) -> None:
        sample = "\n".join(
            [
                "第一章 招标公告",
                "评标信息",
                "技术部分",
                "评分因素",
                "若供应商提供守合同重信用企业，可得10分。",
            ]
        )
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
            handle.write(sample)
            temp_path = Path(handle.name)

        env = {**dict(os.environ), "PYTHONPATH": str(REPO_ROOT / "src")}
        paths = detect_paths()
        cache_key = build_review_cache_key(
            file_hash=sha256_file(temp_path),
            rule_set_version=RULE_SET_VERSION,
            reference_snapshot=reference_snapshot_id(paths.repo_root / "docs" / "references"),
            review_pipeline_version=REVIEW_CACHE_VERSION,
        )
        cache_path = cache_path_for_key(cache_key)
        if cache_path.exists():
            cache_path.unlink()

        first = subprocess.run(
            [sys.executable, "-m", "agent_compliance", "review", str(temp_path), "--json", "--use-cache", "--refresh-cache"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        second = subprocess.run(
            [sys.executable, "-m", "agent_compliance", "review", str(temp_path), "--json", "--use-cache"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        first_payload = json.loads(first.stdout)
        second_payload = json.loads(second.stdout)
        self.assertTrue(first_payload["cache"]["enabled"])
        self.assertFalse(first_payload["cache"]["used"])
        self.assertTrue(second_payload["cache"]["enabled"])
        self.assertTrue(second_payload["cache"]["used"])
        self.assertTrue(cache_path.exists())

        Path(first_payload["outputs"]["json"]).unlink(missing_ok=True)
        Path(first_payload["outputs"]["markdown"]).unlink(missing_ok=True)
        Path(second_payload["outputs"]["json"]).unlink(missing_ok=True)
        Path(second_payload["outputs"]["markdown"]).unlink(missing_ok=True)
        cache_path.unlink(missing_ok=True)
        temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
