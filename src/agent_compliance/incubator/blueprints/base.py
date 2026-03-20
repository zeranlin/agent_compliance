from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentBlueprint:
    """定义一个新智能体最小可执行蓝图。"""

    agent_key: str
    agent_name: str
    agent_type: str
    goal: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    shared_capabilities: tuple[str, ...]
    required_files: tuple[str, ...]
    default_directories: tuple[str, ...]
    incubation_focus: tuple[str, ...]
