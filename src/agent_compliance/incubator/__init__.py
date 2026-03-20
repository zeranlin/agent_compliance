"""智能体孵化层：沉淀新智能体蓝图、脚手架与标准化生成流程。"""

from agent_compliance.incubator.blueprints import (
    AgentBlueprint,
    BUDGET_AGENT_BLUEPRINT,
    DEMAND_RESEARCH_AGENT_BLUEPRINT,
    REVIEW_AGENT_BLUEPRINT,
    budget_agent_blueprint,
    demand_research_agent_blueprint,
    get_blueprint,
    list_blueprints,
    review_agent_blueprint,
)
from agent_compliance.incubator.lifecycle import (
    DEFAULT_INCUBATION_LIFECYCLE,
    DistillationRecommendation,
    IncubationStage,
    IncubationStageDefinition,
    IncubationRun,
    IncubationStageRecord,
    SampleSet,
    ValidationComparison,
    create_incubation_run,
    default_incubation_lifecycle,
)
from agent_compliance.incubator.evals import (
    build_distillation_report,
    render_distillation_report_markdown,
)
from agent_compliance.incubator.distillation_engine import (
    build_distillation_recommendations,
    summarize_validation_gaps,
)
from agent_compliance.incubator.factory import (
    FactoryBootstrapResult,
    bootstrap_agent_factory,
    resume_agent_factory,
)
from agent_compliance.incubator.sample_registry import (
    SampleAsset,
    SampleManifest,
    build_sample_manifest,
    summarize_sample_manifest,
)
from agent_compliance.incubator.report_writer import (
    DistillationArtifactPaths,
    write_distillation_report,
)
from agent_compliance.incubator.run_store import (
    IncubationRunPaths,
    load_incubation_run,
    serialize_incubation_run,
    write_incubation_run,
)
from agent_compliance.incubator.scaffold_generator import (
    ScaffoldPlan,
    build_scaffold_plan,
    generate_agent_scaffold,
)

__all__ = [
    "DEFAULT_INCUBATION_LIFECYCLE",
    "AgentBlueprint",
    "BUDGET_AGENT_BLUEPRINT",
    "DEMAND_RESEARCH_AGENT_BLUEPRINT",
    "DistillationRecommendation",
    "DistillationArtifactPaths",
    "FactoryBootstrapResult",
    "IncubationStage",
    "IncubationStageDefinition",
    "IncubationRun",
    "IncubationRunPaths",
    "IncubationStageRecord",
    "REVIEW_AGENT_BLUEPRINT",
    "SampleSet",
    "ScaffoldPlan",
    "SampleAsset",
    "ValidationComparison",
    "SampleManifest",
    "build_scaffold_plan",
    "build_distillation_report",
    "build_distillation_recommendations",
    "build_sample_manifest",
    "bootstrap_agent_factory",
    "budget_agent_blueprint",
    "demand_research_agent_blueprint",
    "create_incubation_run",
    "default_incubation_lifecycle",
    "generate_agent_scaffold",
    "get_blueprint",
    "list_blueprints",
    "load_incubation_run",
    "render_distillation_report_markdown",
    "resume_agent_factory",
    "review_agent_blueprint",
    "serialize_incubation_run",
    "summarize_sample_manifest",
    "summarize_validation_gaps",
    "write_distillation_report",
    "write_incubation_run",
]
