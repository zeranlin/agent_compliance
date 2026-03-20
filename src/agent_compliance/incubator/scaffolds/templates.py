from __future__ import annotations

from pathlib import Path

from agent_compliance.incubator.blueprints.base import AgentBlueprint


def render_scaffold_file(file_path: Path, blueprint: AgentBlueprint) -> str | None:
    """按文件名渲染标准脚手架内容。"""

    name = file_path.name
    if name == "__init__.py":
        return _render_init_stub(blueprint)
    if name == "schemas.py":
        return _render_schemas_stub(blueprint)
    if name == "pipeline.py":
        return _render_pipeline_stub(blueprint)
    if name == "service.py":
        return _render_service_stub(blueprint)
    if name == "product_outline.md":
        return _render_product_outline_stub(blueprint)
    if name == "README.md" and file_path.parent.name == "evals":
        return _render_eval_readme_stub(blueprint)
    if name == "test_agent_smoke.py":
        return _render_test_stub(blueprint)
    return None


def _render_init_stub(blueprint: AgentBlueprint) -> str:
    return f'"""{blueprint.agent_name} 包骨架。"""\n'


def _render_schemas_stub(blueprint: AgentBlueprint) -> str:
    class_name = _pascal_case(blueprint.agent_key)
    return f'''from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class {class_name}Finding:
    """{blueprint.agent_name} 的最小 finding 骨架。"""

    title: str
    detail: str = ""


@dataclass
class {class_name}Result:
    """{blueprint.agent_name} 的最小结果骨架。"""

    findings: list[{class_name}Finding] = field(default_factory=list)
'''


def _render_pipeline_stub(blueprint: AgentBlueprint) -> str:
    return f'''from __future__ import annotations


def run_pipeline(input_path: str) -> dict[str, object]:
    """{blueprint.agent_name} 的最小 pipeline 入口。"""

    return {{
        "agent_key": "{blueprint.agent_key}",
        "input_path": input_path,
        "status": "bootstrap",
    }}
'''


def _render_service_stub(blueprint: AgentBlueprint) -> str:
    return f'''from __future__ import annotations

from agent_compliance.agents.{blueprint.agent_key}.pipeline import run_pipeline


def review(input_path: str) -> dict[str, object]:
    """{blueprint.agent_name} 的最小 service 入口。"""

    return run_pipeline(input_path)
'''


def _render_product_outline_stub(blueprint: AgentBlueprint) -> str:
    inputs = "\n".join(f"- {item}" for item in blueprint.inputs)
    outputs = "\n".join(f"- {item}" for item in blueprint.outputs)
    focus = "\n".join(f"- {item}" for item in blueprint.incubation_focus)
    return f"""# {blueprint.agent_name} Product Outline

## Goal
{blueprint.goal}

## Agent Metadata
- agent_key: `{blueprint.agent_key}`
- template_key: `{blueprint.template_key}`
- agent_type: `{blueprint.agent_type}`
- template_label: `{blueprint.template_key} scaffold`

## Inputs
{inputs}

## Outputs
{outputs}

## First Incubation Focus
{focus}

## Notes
- This file is a scaffold draft for early incubation.
- Move the stable version into `docs/product-specs/` when the agent enters productization.
"""


def _render_eval_readme_stub(blueprint: AgentBlueprint) -> str:
    return f"""# {blueprint.agent_name} Eval Skeleton

This directory is the default evaluation scaffold for `{blueprint.agent_key}`.

Suggested next files:
- `positive-samples.json`
- `negative-samples.json`
- `comparison-notes.md`
- `benchmark-config.json`

Current incubation focus:
{chr(10).join(f"- {item}" for item in blueprint.incubation_focus)}
"""


def _render_test_stub(blueprint: AgentBlueprint) -> str:
    return f'''from __future__ import annotations

import unittest

from agent_compliance.agents.{blueprint.agent_key}.pipeline import run_pipeline


class { _pascal_case(blueprint.agent_key) }SmokeTests(unittest.TestCase):
    def test_pipeline_returns_bootstrap_payload(self) -> None:
        result = run_pipeline("sample-input")
        self.assertEqual(result["agent_key"], "{blueprint.agent_key}")
        self.assertEqual(result["status"], "bootstrap")


if __name__ == "__main__":
    unittest.main()
'''


def _pascal_case(value: str) -> str:
    return "".join(part.capitalize() for part in value.split("_"))
