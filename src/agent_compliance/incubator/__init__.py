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
    IncubationEvent,
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
    build_run_comparison_report,
    render_distillation_report_markdown,
    render_run_comparison_markdown,
)
from agent_compliance.incubator.distillation_engine import (
    build_distillation_recommendations,
    summarize_validation_gaps,
)
from agent_compliance.incubator.comparison_builder import (
    build_validation_comparison,
    build_validation_comparison_from_files,
)
from agent_compliance.incubator.comparison_collector import (
    collect_validation_comparisons_from_manifest,
    collect_validation_comparisons_from_root,
)
from agent_compliance.incubator.regression_runner import (
    RegressionFeedback,
    build_regression_feedback,
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
    deserialize_sample_manifest,
    load_sample_manifest,
    serialize_sample_manifest,
    summarize_sample_manifest,
    write_sample_manifest,
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
    "IncubationEvent",
    "FactoryBootstrapResult",
    "IncubationStage",
    "IncubationStageDefinition",
    "IncubationRun",
    "IncubationRunPaths",
    "IncubationStageRecord",
    "RegressionFeedback",
    "REVIEW_AGENT_BLUEPRINT",
    "SampleSet",
    "ScaffoldPlan",
    "SampleAsset",
    "ValidationComparison",
    "SampleManifest",
    "build_scaffold_plan",
    "build_distillation_report",
    "build_run_comparison_report",
    "build_distillation_recommendations",
    "build_sample_manifest",
    "bootstrap_agent_factory",
    "build_regression_feedback",
    "build_validation_comparison",
    "build_validation_comparison_from_files",
    "collect_validation_comparisons_from_manifest",
    "collect_validation_comparisons_from_root",
    "budget_agent_blueprint",
    "deserialize_sample_manifest",
    "demand_research_agent_blueprint",
    "create_incubation_run",
    "default_incubation_lifecycle",
    "generate_agent_scaffold",
    "get_blueprint",
    "list_blueprints",
    "load_sample_manifest",
    "load_incubation_run",
    "render_distillation_report_markdown",
    "render_run_comparison_markdown",
    "resume_agent_factory",
    "review_agent_blueprint",
    "serialize_incubation_run",
    "serialize_sample_manifest",
    "summarize_sample_manifest",
    "summarize_validation_gaps",
    "write_distillation_report",
    "write_incubation_run",
    "write_sample_manifest",
]
