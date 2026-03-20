from __future__ import annotations

import unittest

from agent_compliance.incubator.blueprints import (
    BUDGET_AGENT_BLUEPRINT,
    COMPARISON_EVAL_AGENT_TEMPLATE,
    DEMAND_RESEARCH_AGENT_BLUEPRINT,
    REVIEW_AGENT_BLUEPRINT,
    SPECIAL_CHECKS_AGENT_BLUEPRINT,
    get_blueprint_template,
    list_blueprints,
    list_blueprint_templates,
)


class BlueprintTemplateTests(unittest.TestCase):
    def test_list_blueprint_templates_returns_all_registered_types(self) -> None:
        template_keys = {template.template_key for template in list_blueprint_templates()}
        self.assertEqual(
            template_keys,
            {"review", "budget_analysis", "demand_research", "comparison_eval"},
        )

    def test_concrete_blueprints_keep_template_identity(self) -> None:
        self.assertEqual(REVIEW_AGENT_BLUEPRINT.template_key, "review")
        self.assertEqual(BUDGET_AGENT_BLUEPRINT.template_key, "budget_analysis")
        self.assertEqual(DEMAND_RESEARCH_AGENT_BLUEPRINT.template_key, "demand_research")
        self.assertEqual(SPECIAL_CHECKS_AGENT_BLUEPRINT.template_key, "review")
        self.assertIn("web shell", REVIEW_AGENT_BLUEPRINT.shared_capabilities)
        self.assertIn("rules/__init__.py", BUDGET_AGENT_BLUEPRINT.required_files)

    def test_list_blueprints_includes_special_checks_agent(self) -> None:
        blueprint_keys = {blueprint.agent_key for blueprint in list_blueprints()}
        self.assertIn("special_checks", blueprint_keys)

    def test_get_blueprint_template_returns_template_definition(self) -> None:
        template = get_blueprint_template("comparison_eval")
        self.assertEqual(template.template_name, "对比评估型智能体模板")
        self.assertEqual(template.agent_type, COMPARISON_EVAL_AGENT_TEMPLATE.agent_type)


if __name__ == "__main__":
    unittest.main()
