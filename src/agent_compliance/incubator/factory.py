from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_compliance.incubator.blueprints.base import AgentBlueprint
from agent_compliance.incubator.blueprints.registry import get_blueprint
from agent_compliance.incubator.distillation_engine import (
    build_distillation_recommendations,
)
from agent_compliance.incubator.evals import (
    build_distillation_report,
    render_distillation_report_markdown,
)
from agent_compliance.incubator.lifecycle import (
    IncubationRun,
    IncubationStage,
    ValidationComparison,
    create_incubation_run,
)
from agent_compliance.incubator.sample_registry import SampleManifest
from agent_compliance.incubator.scaffold_generator import (
    ScaffoldPlan,
    generate_agent_scaffold,
)


@dataclass(frozen=True)
class FactoryBootstrapResult:
    """描述一次智能体工厂启动结果。"""

    blueprint: AgentBlueprint
    scaffold_plan: ScaffoldPlan | None
    run: IncubationRun
    report: dict[str, object]
    report_markdown: str


def bootstrap_agent_factory(
    agents_dir: Path,
    agent_key: str,
    *,
    run_title: str | None = None,
    sample_manifest: SampleManifest | None = None,
    comparisons: tuple[ValidationComparison, ...] = (),
    overwrite: bool = False,
) -> FactoryBootstrapResult:
    """按标准蓝图启动一个新的智能体孵化回合。"""

    blueprint = get_blueprint(agent_key)
    plan = generate_agent_scaffold(agents_dir, blueprint, overwrite=overwrite)

    run = create_incubation_run(
        agent_key=blueprint.agent_key,
        run_title=run_title or f"{blueprint.agent_name} 第一轮孵化",
    )
    _initialize_run(
        run,
        blueprint,
        plan,
        sample_manifest=sample_manifest,
        comparisons=comparisons,
    )

    report = build_distillation_report(run)
    report_markdown = render_distillation_report_markdown(report)
    return FactoryBootstrapResult(
        blueprint=blueprint,
        scaffold_plan=plan,
        run=run,
        report=report,
        report_markdown=report_markdown,
    )


def resume_agent_factory(
    run: IncubationRun,
    *,
    sample_manifest: SampleManifest | None = None,
    comparisons: tuple[ValidationComparison, ...] = (),
) -> FactoryBootstrapResult:
    """基于已有 run manifest 继续推进一轮孵化。"""

    blueprint = get_blueprint(run.agent_key)
    _merge_follow_up_inputs(
        run,
        sample_manifest=sample_manifest,
        comparisons=comparisons,
    )
    report = build_distillation_report(run)
    report_markdown = render_distillation_report_markdown(report)
    return FactoryBootstrapResult(
        blueprint=blueprint,
        scaffold_plan=None,
        run=run,
        report=report,
        report_markdown=report_markdown,
    )


def _initialize_run(
    run: IncubationRun,
    blueprint: AgentBlueprint,
    plan: ScaffoldPlan,
    *,
    sample_manifest: SampleManifest | None,
    comparisons: tuple[ValidationComparison, ...],
) -> None:
    run.set_stage_status(
        IncubationStage.REQUIREMENT_DEFINITION,
        "completed",
        f"已按 {blueprint.agent_name} 蓝图建立第一版目标定义。",
    )
    run.add_stage_output(IncubationStage.REQUIREMENT_DEFINITION, blueprint.goal)

    run.set_stage_status(
        IncubationStage.STRONG_AGENT_DESIGN,
        "completed",
        "已选择标准蓝图并确认共享底座与孵化重点。",
    )
    run.add_stage_output(
        IncubationStage.STRONG_AGENT_DESIGN,
        f"共享底座：{', '.join(blueprint.shared_capabilities)}",
    )
    run.add_stage_output(
        IncubationStage.STRONG_AGENT_DESIGN,
        f"孵化重点：{', '.join(blueprint.incubation_focus)}",
    )

    run.set_stage_status(
        IncubationStage.TARGET_AGENT_BOOTSTRAP,
        "completed",
        f"已生成最小骨架：{plan.target_root}",
    )
    for file_path in plan.files:
        run.add_stage_output(
            IncubationStage.TARGET_AGENT_BOOTSTRAP,
            str(file_path.relative_to(plan.target_root.parent)),
        )

    if sample_manifest is not None:
        run.set_stage_status(
            IncubationStage.SAMPLE_PREPARATION,
            "completed",
            f"已登记样例清单：{sample_manifest.name}@{sample_manifest.version}",
        )
        run.add_sample_set(
            IncubationStage.SAMPLE_PREPARATION,
            sample_manifest.to_sample_set(),
        )
        run.add_stage_output(
            IncubationStage.SAMPLE_PREPARATION,
            (
                f"正样例 {len(sample_manifest.positive_examples)} / "
                f"负样例 {len(sample_manifest.negative_examples)} / "
                f"边界样例 {len(sample_manifest.boundary_examples)}"
            ),
        )
        if sample_manifest.change_summary:
            run.add_stage_output(
                IncubationStage.SAMPLE_PREPARATION,
                f"版本说明：{sample_manifest.change_summary}",
            )

    if comparisons:
        _apply_comparisons_and_recommendations(run, comparisons)


def _merge_follow_up_inputs(
    run: IncubationRun,
    *,
    sample_manifest: SampleManifest | None,
    comparisons: tuple[ValidationComparison, ...],
) -> None:
    if sample_manifest is not None:
        run.set_stage_status(
            IncubationStage.SAMPLE_PREPARATION,
            "completed",
            f"已补充样例清单：{sample_manifest.name}@{sample_manifest.version}",
        )
        run.add_sample_set(
            IncubationStage.SAMPLE_PREPARATION,
            sample_manifest.to_sample_set(),
        )
        run.add_stage_output(
            IncubationStage.SAMPLE_PREPARATION,
            (
                f"补充正样例 {len(sample_manifest.positive_examples)} / "
                f"负样例 {len(sample_manifest.negative_examples)} / "
                f"边界样例 {len(sample_manifest.boundary_examples)}"
            ),
        )
        if sample_manifest.change_summary:
            run.add_stage_output(
                IncubationStage.SAMPLE_PREPARATION,
                f"版本说明：{sample_manifest.change_summary}",
            )

    if comparisons:
        _apply_comparisons_and_recommendations(run, comparisons)


def _apply_comparisons_and_recommendations(
    run: IncubationRun,
    comparisons: tuple[ValidationComparison, ...],
) -> None:
    run.set_stage_status(
        IncubationStage.PARITY_VALIDATION,
        "completed",
        f"已记录 {len(comparisons)} 条对照结果。",
    )
    for comparison in comparisons:
        run.add_comparison(IncubationStage.PARITY_VALIDATION, comparison)

    recommendations = build_distillation_recommendations(comparisons)
    if recommendations:
        run.set_stage_status(
            IncubationStage.DISTILLATION_ITERATION,
            "in_progress",
            f"已根据对照差异生成 {len(recommendations)} 条初步蒸馏建议。",
        )
        for recommendation in recommendations:
            run.add_recommendation(
                IncubationStage.DISTILLATION_ITERATION,
                recommendation,
            )
