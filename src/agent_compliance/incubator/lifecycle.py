from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IncubationStage(str, Enum):
    """标准化智能体孵化阶段。"""

    REQUIREMENT_DEFINITION = "requirement_definition"
    SAMPLE_PREPARATION = "sample_preparation"
    STRONG_AGENT_DESIGN = "strong_agent_design"
    TARGET_AGENT_BOOTSTRAP = "target_agent_bootstrap"
    PARITY_VALIDATION = "parity_validation"
    DISTILLATION_ITERATION = "distillation_iteration"
    PRODUCTIZATION = "productization"


@dataclass(frozen=True)
class IncubationStageDefinition:
    """描述一个孵化阶段的目标与产物。"""

    stage: IncubationStage
    title: str
    goal: str
    outputs: tuple[str, ...]


DEFAULT_INCUBATION_LIFECYCLE: tuple[IncubationStageDefinition, ...] = (
    IncubationStageDefinition(
        stage=IncubationStage.REQUIREMENT_DEFINITION,
        title="业务需求定义",
        goal="明确智能体定位、边界、输入输出和成功标准。",
        outputs=("产品定位", "范围边界", "第一版目标能力清单"),
    ),
    IncubationStageDefinition(
        stage=IncubationStage.SAMPLE_PREPARATION,
        title="样例资产准备",
        goal="沉淀正样例、负样例、边界样例和人工基准。",
        outputs=("benchmark 样本", "标签定义", "覆盖说明"),
    ),
    IncubationStageDefinition(
        stage=IncubationStage.STRONG_AGENT_DESIGN,
        title="强通用智能体设计",
        goal="设计目标智能体主链、schema、规则、分析器和评测方式。",
        outputs=("主链方案", "schema", "初版规则与 analyzer"),
    ),
    IncubationStageDefinition(
        stage=IncubationStage.TARGET_AGENT_BOOTSTRAP,
        title="本地目标智能体生成",
        goal="起最小骨架并形成可运行的本地目标智能体。",
        outputs=("pipeline.py", "schemas.py", "service.py", "脚手架目录"),
    ),
    IncubationStageDefinition(
        stage=IncubationStage.PARITY_VALIDATION,
        title="对照验证",
        goal="对比人工、强通用智能体与目标智能体输出差异。",
        outputs=("差异报告", "缺口清单", "增强优先级"),
    ),
    IncubationStageDefinition(
        stage=IncubationStage.DISTILLATION_ITERATION,
        title="持续蒸馏",
        goal="把差异转成规则、analyzer、仲裁和结构层增强。",
        outputs=("增强实现", "回归结果", "能力变化记录"),
    ),
    IncubationStageDefinition(
        stage=IncubationStage.PRODUCTIZATION,
        title="最终固化发布",
        goal="将目标智能体固化为可部署、可评测、可销售的产品线。",
        outputs=("正式规则集", "正式导出", "发布口径", "运维方式"),
    ),
)


def default_incubation_lifecycle() -> tuple[IncubationStageDefinition, ...]:
    """返回默认孵化生命周期。"""

    return DEFAULT_INCUBATION_LIFECYCLE
