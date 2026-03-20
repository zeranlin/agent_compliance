from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_compliance.incubator.blueprints.base import AgentBlueprint
from agent_compliance.incubator.scaffolds import render_scaffold_file


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
    rendered = render_scaffold_file(file_path, blueprint)
    if rendered is not None:
        return rendered
    return _render_generic_stub(blueprint)


def _render_generic_stub(blueprint: AgentBlueprint) -> str:
    return (
        '"""'
        f"{blueprint.agent_name} 自动生成骨架文件。"
        '"""\n'
    )
