from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from agent_compliance.apps.cli import main


class IncubatorCliTests(unittest.TestCase):
    def test_incubate_agent_command_bootstraps_agent_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            comparisons_path = temp_path / "comparisons.json"
            comparisons_path.write_text(
                json.dumps(
                    [
                        {
                            "sample_id": "case-001",
                            "human_baseline": "人工抓到评分问题",
                            "strong_agent_result": "强智能体抓到评分问题",
                            "target_agent_result": "目标智能体漏判",
                            "gap_points": ["评分结构失衡未上浮"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "incubate-agent",
                        "budget_demand",
                        "--agents-dir",
                        str(temp_path / "agents"),
                        "--output-dir",
                        str(temp_path / "outputs"),
                        "--positive-sample",
                        "samples/positive/a.docx",
                        "--comparisons-json",
                        str(comparisons_path),
                        "--json",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["agent_key"], "budget_demand")
            self.assertTrue((temp_path / "agents" / "budget_demand").exists())
            self.assertTrue(Path(payload["outputs"]["run_manifest"]).exists())
            self.assertTrue(Path(payload["outputs"]["json"]).exists())
            self.assertTrue(Path(payload["outputs"]["markdown"]).exists())


if __name__ == "__main__":
    unittest.main()
