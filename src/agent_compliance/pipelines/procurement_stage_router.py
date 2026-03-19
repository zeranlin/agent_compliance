from __future__ import annotations

from dataclasses import dataclass

from agent_compliance.schemas import Finding, NormalizedDocument


@dataclass(frozen=True)
class ProcurementStageProfile:
    stage_key: str
    stage_name: str
    stage_goal: str
    review_posture: str
    primary_users: tuple[str, ...]
    output_bias: tuple[str, ...]


DEFAULT_STAGE_PROFILE = ProcurementStageProfile(
    stage_key="pre_release_requirement_review",
    stage_name="采购需求形成与发布前审查",
    stage_goal="帮助采购人在正式发布采购需求、招标文件或磋商文件前发现高风险条款并完成改稿复核",
    review_posture="预防型审查，优先识别不宜发布、需论证、需弱化或需补边界说明的条款",
    primary_users=("采购需求编制人员", "采购复核人员", "法务与合规审核人员"),
    output_bias=("采购人改稿", "发布前复核", "风险留痕"),
)


def route_procurement_stage(
    document: NormalizedDocument | None = None,
    findings: list[Finding] | None = None,
) -> ProcurementStageProfile:
    return DEFAULT_STAGE_PROFILE
