from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_compliance.incubator.blueprints.base import AgentBlueprint


@dataclass(frozen=True)
class ScaffoldPlan:
    """描述一次脚手架生成的目标位置与文件集合。"""

    agent_key: str
    target_root: Path
    directories: tuple[Path, ...]
    files: tuple[Path, ...]


def build_scaffold_plan(base_dir: Path, blueprint: AgentBlueprint) -> ScaffoldPlan:
    """根据蓝图构造最小智能体脚手架计划。"""

    target_root = base_dir / blueprint.agent_key
    directories = tuple(target_root / name for name in blueprint.default_directories)
    files = tuple(target_root / relative_path for relative_path in blueprint.required_files)
    return ScaffoldPlan(
        agent_key=blueprint.agent_key,
        target_root=target_root,
        directories=directories,
        files=files,
    )


def generate_agent_scaffold(
    base_dir: Path,
    blueprint: AgentBlueprint,
    *,
    overwrite: bool = False,
) -> ScaffoldPlan:
    """按蓝图生成最小智能体骨架。"""

    plan = build_scaffold_plan(base_dir, blueprint)
    plan.target_root.mkdir(parents=True, exist_ok=True)
    for directory in plan.directories:
        directory.mkdir(parents=True, exist_ok=True)

    for file_path in plan.files:
        if file_path.exists() and not overwrite:
            continue
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(_render_stub(file_path, blueprint), encoding="utf-8")

    return plan


def _render_stub(file_path: Path, blueprint: AgentBlueprint) -> str:
    name = file_path.name
    if name == "__init__.py":
        return _render_init_stub(blueprint)
    if name == "schemas.py":
        return _render_schemas_stub(blueprint)
    if name == "pipeline.py":
        return _render_pipeline_stub(blueprint)
    if name == "service.py":
        return _render_service_stub(blueprint)
    return _render_generic_stub(blueprint)


def _render_init_stub(blueprint: AgentBlueprint) -> str:
    return (
        '"""'
        f"{blueprint.agent_name} 包骨架。"
        '"""\n'
    )


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


def _render_generic_stub(blueprint: AgentBlueprint) -> str:
    return (
        '"""'
        f"{blueprint.agent_name} 自动生成骨架文件。"
        '"""\n'
    )


def _pascal_case(value: str) -> str:
    return "".join(part.capitalize() for part in value.split("_"))
