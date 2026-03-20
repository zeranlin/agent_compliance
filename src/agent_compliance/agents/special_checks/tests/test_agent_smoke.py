from __future__ import annotations

import unittest

from agent_compliance.agents.special_checks.pipeline import run_pipeline


class SpecialChecksSmokeTests(unittest.TestCase):
    def test_pipeline_returns_bootstrap_payload(self) -> None:
        result = run_pipeline("sample-input")
        self.assertEqual(result["agent_key"], "special_checks")
        self.assertEqual(result["status"], "bootstrap")


if __name__ == "__main__":
    unittest.main()
