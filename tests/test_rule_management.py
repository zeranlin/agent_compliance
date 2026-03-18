from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests._bootstrap import REPO_ROOT
from agent_compliance.improvement.rule_management import load_rule_management_payload, save_rule_decision


class RuleManagementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = REPO_ROOT / "docs" / "generated" / "improvement"
        self.root.mkdir(parents=True, exist_ok=True)
        self.candidate_path = self.root / "testrules-rule-candidates.json"
        self.gate_path = self.root / "testrules-benchmark-gate.json"
        self.decision_path = self.root / "rule-decisions.json"
        self.original_decisions = self.decision_path.read_text(encoding="utf-8") if self.decision_path.exists() else None
        self.candidate_path.write_text(
            json.dumps(
                [
                    {
                        "candidate_rule_id": "CAND-TEST-001",
                        "issue_type": "other",
                        "problem_title": "测试候选规则",
                        "section_path": "评标信息",
                        "source_text": "测试原文",
                        "why_it_is_risky": "测试风险",
                        "rewrite_suggestion": "测试建议",
                        "trigger_keywords": ["测试"],
                        "primary_catalog_name": "物业管理服务",
                        "primary_domain_key": "property_service",
                        "primary_authority": "《政府采购需求管理办法》第十八条、第三十一条",
                        "secondary_authorities": ["《政府采购需求管理办法》第十四条"],
                        "applicability_logic": "资格条件应与履约能力直接相关。",
                        "human_review_reason": "法规侧复核重点：需核查是否存在法定必要性。",
                        "is_mixed_scope": False,
                    }
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.gate_path.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "candidate_rule_id": "CAND-TEST-001",
                            "issue_type": "other",
                            "status": "covered",
                            "reason": "已覆盖",
                        }
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.candidate_path.unlink(missing_ok=True)
        self.gate_path.unlink(missing_ok=True)
        if self.original_decisions is None:
            self.decision_path.unlink(missing_ok=True)
        else:
            self.decision_path.write_text(self.original_decisions, encoding="utf-8")

    def test_rule_management_loads_candidates_and_persists_decision(self) -> None:
        payload = load_rule_management_payload()
        candidate = next(item for item in payload["candidate_rules"] if item["candidate_rule_id"] == "CAND-TEST-001")
        self.assertEqual(candidate["gate_status"], "covered")
        self.assertEqual(candidate["decision"], "pending")
        self.assertEqual(candidate["primary_catalog_name"], "物业管理服务")
        self.assertEqual(candidate["primary_authority"], "《政府采购需求管理办法》第十八条、第三十一条")
        self.assertIn("formal_rule_summary", payload)
        self.assertGreater(payload["formal_rule_summary"]["by_status"]["formal_active"], 0)
        formal_rule = next(item for item in payload["formal_rules"] if item["rule_id"] == "QUAL-001")
        self.assertEqual(formal_rule["rule_status"], "formal_active")
        self.assertEqual(formal_rule["governance_tier"], "core")
        self.assertTrue(formal_rule["enabled_by_default"])
        self.assertEqual(payload["catalog_scene_summary"][0]["primary_catalog_name"], "物业管理服务")
        self.assertEqual(payload["domain_summary"][0]["primary_domain_key"], "property_service")
        self.assertEqual(payload["authority_summary"][0]["primary_authority"], "《政府采购需求管理办法》第十八条、第三十一条")

        save_rule_decision("CAND-TEST-001", "confirmed", "准备入库")

        payload = load_rule_management_payload()
        candidate = next(item for item in payload["candidate_rules"] if item["candidate_rule_id"] == "CAND-TEST-001")
        self.assertEqual(candidate["decision"], "confirmed")
        self.assertEqual(candidate["decision_note"], "准备入库")
