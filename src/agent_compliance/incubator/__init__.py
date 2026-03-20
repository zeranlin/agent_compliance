"""智能体孵化层：沉淀新智能体蓝图、脚手架与标准化生成流程。"""

from agent_compliance.incubator.lifecycle import (
    DEFAULT_INCUBATION_LIFECYCLE,
    IncubationStage,
    IncubationStageDefinition,
    default_incubation_lifecycle,
)
from agent_compliance.incubator.scaffold_generator import (
    ScaffoldPlan,
    build_scaffold_plan,
    generate_agent_scaffold,
)

__all__ = [
    "DEFAULT_INCUBATION_LIFECYCLE",
    "IncubationStage",
    "IncubationStageDefinition",
    "ScaffoldPlan",
    "build_scaffold_plan",
    "default_incubation_lifecycle",
    "generate_agent_scaffold",
]
