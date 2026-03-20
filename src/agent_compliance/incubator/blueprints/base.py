from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentBlueprintTemplate:
    """定义一类智能体的标准模板。"""

    template_key: str
    template_name: str
    agent_type: str
    default_inputs: tuple[str, ...]
    default_outputs: tuple[str, ...]
    shared_capabilities: tuple[str, ...]
    required_files: tuple[str, ...]
    default_directories: tuple[str, ...]
    incubation_focus: tuple[str, ...]


@dataclass(frozen=True)
class AgentBlueprint:
    """定义一个新智能体最小可执行蓝图。"""

    agent_key: str
    agent_name: str
    template_key: str
    agent_type: str
    goal: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    shared_capabilities: tuple[str, ...]
    required_files: tuple[str, ...]
    default_directories: tuple[str, ...]
    incubation_focus: tuple[str, ...]


def create_agent_blueprint(
    *,
    template: AgentBlueprintTemplate,
    agent_key: str,
    agent_name: str,
    goal: str,
    inputs: tuple[str, ...] = (),
    outputs: tuple[str, ...] = (),
    incubation_focus: tuple[str, ...] = (),
) -> AgentBlueprint:
    """基于模板生成一条具体智能体蓝图。"""

    return AgentBlueprint(
        agent_key=agent_key,
        agent_name=agent_name,
        template_key=template.template_key,
        agent_type=template.agent_type,
        goal=goal,
        inputs=inputs or template.default_inputs,
        outputs=outputs or template.default_outputs,
        shared_capabilities=template.shared_capabilities,
        required_files=template.required_files,
        default_directories=template.default_directories,
        incubation_focus=incubation_focus or template.incubation_focus,
    )
