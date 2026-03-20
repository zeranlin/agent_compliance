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

    def test_incubate_agent_command_can_resume_existing_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
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
                        "--json",
                    ]
                )
            first_payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)

            comparisons_path = temp_path / "comparisons.json"
            comparisons_path.write_text(
                json.dumps(
                    [
                        {
                            "sample_id": "case-002",
                            "human_baseline": "人工抓到商务问题",
                            "strong_agent_result": "强智能体抓到商务问题",
                            "target_agent_result": "目标智能体漏判",
                            "gap_points": ["商务链条归并过宽"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            resume_stdout = StringIO()
            with redirect_stdout(resume_stdout):
                resume_exit_code = main(
                    [
                        "incubate-agent",
                        "budget_demand",
                        "--output-dir",
                        str(temp_path / "outputs"),
                        "--resume-run",
                        first_payload["outputs"]["run_manifest"],
                        "--comparisons-json",
                        str(comparisons_path),
                        "--json",
                    ]
                )

            resume_payload = json.loads(resume_stdout.getvalue())
            self.assertEqual(resume_exit_code, 0)
            self.assertIsNone(resume_payload["scaffold_root"])
            self.assertEqual(
                Path(resume_payload["outputs"]["run_manifest"]).name,
                Path(first_payload["outputs"]["run_manifest"]).name,
            )

    def test_incubate_agent_command_can_build_auto_comparison_from_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            human_path = temp_path / "human.txt"
            strong_path = temp_path / "strong.txt"
            target_path = temp_path / "target.txt"
            human_path.write_text(
                "输出项目概述\n输出技术需求框架\n输出待人工补充项",
                encoding="utf-8",
            )
            strong_path.write_text(
                "建议先形成结构化需求初稿骨架和待补充项。",
                encoding="utf-8",
            )
            target_path.write_text(
                "输出项目概述\n输出待人工补充项",
                encoding="utf-8",
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "incubate-agent",
                        "demand_research",
                        "--agents-dir",
                        str(temp_path / "agents"),
                        "--output-dir",
                        str(temp_path / "outputs"),
                        "--sample-id",
                        "demand-case-001",
                        "--human-baseline-file",
                        str(human_path),
                        "--strong-agent-result-file",
                        str(strong_path),
                        "--target-agent-result-file",
                        str(target_path),
                        "--json",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            report_json = json.loads(Path(payload["outputs"]["json"]).read_text(encoding="utf-8"))
            self.assertEqual(report_json["summary"]["comparison_count"], 1)
            self.assertGreaterEqual(report_json["summary"]["recommendation_count"], 1)

    def test_compare_incubation_runs_command_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            first_stdout = StringIO()
            with redirect_stdout(first_stdout):
                main(
                    [
                        "incubate-agent",
                        "budget_demand",
                        "--agents-dir",
                        str(temp_path / "agents"),
                        "--output-dir",
                        str(temp_path / "outputs"),
                        "--json",
                    ]
                )
            first_payload = json.loads(first_stdout.getvalue())

            comparisons_path = temp_path / "comparisons.json"
            comparisons_path.write_text(
                json.dumps(
                    [
                        {
                            "sample_id": "case-003",
                            "human_baseline": "人工抓到预算边界问题",
                            "strong_agent_result": "强智能体抓到预算边界问题",
                            "target_agent_result": "目标智能体漏判",
                            "gap_points": ["预算边界未覆盖"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            second_stdout = StringIO()
            with redirect_stdout(second_stdout):
                main(
                    [
                        "incubate-agent",
                        "budget_demand",
                        "--output-dir",
                        str(temp_path / "outputs"),
                        "--resume-run",
                        first_payload["outputs"]["run_manifest"],
                        "--comparisons-json",
                        str(comparisons_path),
                        "--json",
                    ]
                )
            second_payload = json.loads(second_stdout.getvalue())

            compare_stdout = StringIO()
            with redirect_stdout(compare_stdout):
                exit_code = main(
                    [
                        "compare-incubation-runs",
                        first_payload["outputs"]["run_manifest"],
                        second_payload["outputs"]["run_manifest"],
                        "--json",
                    ]
                )

            compare_payload = json.loads(compare_stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(compare_payload["run_count"], 2)
            self.assertEqual(compare_payload["agent_key"], "budget_demand")

    def test_update_incubation_recommendation_command_updates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            comparisons_path = temp_path / "comparisons.json"
            comparisons_path.write_text(
                json.dumps(
                    [
                        {
                            "sample_id": "case-004",
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

            first_stdout = StringIO()
            with redirect_stdout(first_stdout):
                main(
                    [
                        "incubate-agent",
                        "budget_demand",
                        "--agents-dir",
                        str(temp_path / "agents"),
                        "--output-dir",
                        str(temp_path / "outputs"),
                        "--comparisons-json",
                        str(comparisons_path),
                        "--json",
                    ]
                )
            payload = json.loads(first_stdout.getvalue())
            run_manifest = Path(payload["outputs"]["run_manifest"])
            report_json = Path(payload["outputs"]["json"])
            report = json.loads(report_json.read_text(encoding="utf-8"))
            recommendation_key = report["stages"][5]["recommendations"][0]["recommendation_key"]

            update_stdout = StringIO()
            with redirect_stdout(update_stdout):
                exit_code = main(
                    [
                        "update-incubation-recommendation",
                        str(run_manifest),
                        recommendation_key,
                        "--status",
                        "implemented",
                        "--notes",
                        "已完成首轮实现",
                        "--json",
                    ]
                )

            update_payload = json.loads(update_stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(update_payload["status"], "implemented")

            updated_run = json.loads(run_manifest.read_text(encoding="utf-8"))
            recommendation = updated_run["stages"][5]["recommendations"][0]
            self.assertEqual(recommendation["status"], "implemented")
            self.assertEqual(recommendation["resolution_notes"], "已完成首轮实现")


if __name__ == "__main__":
    unittest.main()
