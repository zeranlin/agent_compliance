from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import tempfile
import unittest

from tests._bootstrap import REPO_ROOT
from agent_compliance.evals.runner import benchmark_summary


class CliSmokeTest(unittest.TestCase):
    def test_benchmark_paths_point_inside_repo(self) -> None:
        summary = benchmark_summary()
        self.assertTrue(Path(summary["benchmark_path"]).exists())
        self.assertTrue(Path(summary["rubric_path"]).exists())

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


if __name__ == "__main__":
    unittest.main()
