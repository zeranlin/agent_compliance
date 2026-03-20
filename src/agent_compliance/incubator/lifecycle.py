from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class SampleSet:
    """描述一组用于孵化或蒸馏的样例资产。"""

    name: str
    positive_examples: tuple[str, ...] = ()
    negative_examples: tuple[str, ...] = ()
    boundary_examples: tuple[str, ...] = ()
    benchmark_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationComparison:
    """记录一次人工、强通用智能体与目标智能体的对照结果。"""

    sample_id: str
    human_baseline: str
    strong_agent_result: str
    target_agent_result: str
    aligned_points: tuple[str, ...] = ()
    gap_points: tuple[str, ...] = ()
    summary: str = ""


@dataclass(frozen=True)
class DistillationRecommendation:
    """描述一条蒸馏增强建议。"""

    recommendation_key: str
    title: str
    target_layer: str
    action: str
    rationale: str
    priority: str = "P1"
    status: str = "proposed"
    resolution_notes: str = ""
    regression_result: str = ""
    capability_change: str = ""


@dataclass
class IncubationStageRecord:
    """记录某个孵化阶段的执行情况。"""

    stage: IncubationStage
    status: str = "pending"
    notes: str = ""
    outputs: list[str] = field(default_factory=list)
    sample_sets: list[SampleSet] = field(default_factory=list)
    comparisons: list[ValidationComparison] = field(default_factory=list)
    recommendations: list[DistillationRecommendation] = field(default_factory=list)


@dataclass
class IncubationRun:
    """记录一次目标智能体孵化/蒸馏闭环。"""

    agent_key: str
    run_title: str
    stages: list[IncubationStageRecord]

    def get_stage(self, stage: IncubationStage) -> IncubationStageRecord:
        for record in self.stages:
            if record.stage == stage:
                return record
        raise KeyError(stage)

    def set_stage_status(self, stage: IncubationStage, status: str, notes: str = "") -> None:
        record = self.get_stage(stage)
        record.status = status
        if notes:
            record.notes = notes

    def add_stage_output(self, stage: IncubationStage, output: str) -> None:
        self.get_stage(stage).outputs.append(output)

    def add_sample_set(self, stage: IncubationStage, sample_set: SampleSet) -> None:
        self.get_stage(stage).sample_sets.append(sample_set)

    def add_comparison(self, stage: IncubationStage, comparison: ValidationComparison) -> None:
        self.get_stage(stage).comparisons.append(comparison)

    def add_recommendation(
        self,
        stage: IncubationStage,
        recommendation: DistillationRecommendation,
    ) -> None:
        self.get_stage(stage).recommendations.append(recommendation)

    def update_recommendation_status(
        self,
        stage: IncubationStage,
        recommendation_key: str,
        status: str,
        notes: str = "",
        regression_result: str = "",
        capability_change: str = "",
    ) -> None:
        recommendations = self.get_stage(stage).recommendations
        for index, recommendation in enumerate(recommendations):
            if recommendation.recommendation_key == recommendation_key:
                recommendations[index] = DistillationRecommendation(
                    recommendation_key=recommendation.recommendation_key,
                    title=recommendation.title,
                    target_layer=recommendation.target_layer,
                    action=recommendation.action,
                    rationale=recommendation.rationale,
                    priority=recommendation.priority,
                    status=status,
                    resolution_notes=notes or recommendation.resolution_notes,
                    regression_result=regression_result or recommendation.regression_result,
                    capability_change=capability_change or recommendation.capability_change,
                )
                return
        raise KeyError(recommendation_key)


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


def create_incubation_run(agent_key: str, run_title: str) -> IncubationRun:
    """根据默认生命周期生成一条新的孵化记录。"""

    return IncubationRun(
        agent_key=agent_key,
        run_title=run_title,
        stages=[
            IncubationStageRecord(stage=definition.stage)
            for definition in DEFAULT_INCUBATION_LIFECYCLE
        ],
    )
