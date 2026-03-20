from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_compliance.incubator.blueprints.base import AgentBlueprint
from agent_compliance.incubator.blueprints.registry import get_blueprint
from agent_compliance.incubator.evals import (
    build_distillation_report,
    render_distillation_report_markdown,
)
from agent_compliance.incubator.lifecycle import (
    IncubationRun,
    IncubationStage,
    create_incubation_run,
)
from agent_compliance.incubator.scaffold_generator import (
    ScaffoldPlan,
    generate_agent_scaffold,
)


@dataclass(frozen=True)
class FactoryBootstrapResult:
    """描述一次智能体工厂启动结果。"""

    blueprint: AgentBlueprint
    scaffold_plan: ScaffoldPlan
    run: IncubationRun
    report: dict[str, object]
    report_markdown: str


def bootstrap_agent_factory(
    agents_dir: Path,
    agent_key: str,
    *,
    run_title: str | None = None,
    overwrite: bool = False,
) -> FactoryBootstrapResult:
    """按标准蓝图启动一个新的智能体孵化回合。"""

    blueprint = get_blueprint(agent_key)
    plan = generate_agent_scaffold(agents_dir, blueprint, overwrite=overwrite)

    run = create_incubation_run(
        agent_key=blueprint.agent_key,
        run_title=run_title or f"{blueprint.agent_name} 第一轮孵化",
    )
    _initialize_run(run, blueprint, plan)

    report = build_distillation_report(run)
    report_markdown = render_distillation_report_markdown(report)
    return FactoryBootstrapResult(
        blueprint=blueprint,
        scaffold_plan=plan,
        run=run,
        report=report,
        report_markdown=report_markdown,
    )


def _initialize_run(
    run: IncubationRun,
    blueprint: AgentBlueprint,
    plan: ScaffoldPlan,
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
