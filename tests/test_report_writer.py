from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator import (
    build_distillation_report,
    create_incubation_run,
    render_distillation_report_markdown,
)
from agent_compliance.incubator.report_writer import write_distillation_report


class ReportWriterTests(unittest.TestCase):
    def test_write_distillation_report_persists_json_and_markdown(self) -> None:
        run = create_incubation_run("compliance_review", "合规智能体蒸馏")
        report = build_distillation_report(run)
        markdown = render_distillation_report_markdown(report)

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_distillation_report(
                Path(temp_dir),
                "compliance_review",
                "run-001",
                report,
                markdown,
            )
            self.assertTrue(paths.json_path.exists())
            self.assertTrue(paths.markdown_path.exists())
            self.assertIn("合规智能体蒸馏", paths.markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
