from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401

from agent_compliance.incubator.evals.benchmark_regression_reporter import build_benchmark_regression_report


class BenchmarkRegressionReporterTest(unittest.TestCase):
    def test_report_handles_missing_gate(self) -> None:
        report = build_benchmark_regression_report(None)
        self.assertEqual(report["status"], "no_gate")
        self.assertEqual(report["stage_name"], "采购需求形成与发布前审查")
        self.assertTrue(report["gaps"])

    def test_report_summarizes_pre_release_strengths_and_gaps(self) -> None:
        report = build_benchmark_regression_report(
            {
                "status": "needs_attention",
                "candidate_count": 3,
                "covered_count": 2,
                "needs_benchmark_count": 1,
                "catalog_scene_summary": [{"primary_catalog_name": "物业管理服务", "candidate_count": 2}],
                "domain_summary": [{"primary_domain_key": "property_management_service", "candidate_count": 2}],
                "authority_summary": [{"primary_authority": "《政府采购需求管理办法》第十八条、第三十一条", "candidate_count": 2}],
                "profile_risk_summary": [{"risk_pattern": "付款条件与履约评价结果深度绑定", "candidate_count": 1}],
            }
        )
        self.assertEqual(report["stage_name"], "采购需求形成与发布前审查")
        self.assertIn("3 条候选规则", report["summary"])
        self.assertTrue(any("物业管理服务" in item for item in report["strengths"]))
        self.assertTrue(any("缺少 benchmark" in item or "待补 benchmark" in item for item in report["gaps"]))
        self.assertTrue(any("property_management_service" in item for item in report["next_actions"]))


if __name__ == "__main__":
    unittest.main()
