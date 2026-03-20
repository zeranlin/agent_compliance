from __future__ import annotations

from dataclasses import dataclass

from agent_compliance.incubator.lifecycle import ValidationComparison


@dataclass(frozen=True)
class RegressionFeedback:
    """描述一轮回归后对蒸馏建议的反馈。"""

    regression_result: str
    capability_change: str


def build_regression_feedback(
    previous: ValidationComparison | None,
    current: ValidationComparison,
) -> RegressionFeedback:
    """根据上一轮与当前对照结果，自动生成回归结论和能力变化描述。"""

    current_gap_count = len(current.gap_points)
    current_aligned_count = len(current.aligned_points)

    if previous is None:
        regression_result = (
            f"回归样例 {current.sample_id} 已记录，当前对照包含 "
            f"{current_aligned_count} 个对齐点、{current_gap_count} 个剩余差异点。"
        )
        capability_change = _capability_change_from_current(current)
        return RegressionFeedback(
            regression_result=regression_result,
            capability_change=capability_change,
        )

    previous_gap_count = len(previous.gap_points)
    previous_aligned_count = len(previous.aligned_points)

    if current_gap_count < previous_gap_count:
        regression_result = (
            f"回归样例 {current.sample_id} 的差异点已从 {previous_gap_count} 个下降到 "
            f"{current_gap_count} 个。"
        )
    elif current_gap_count > previous_gap_count:
        regression_result = (
            f"回归样例 {current.sample_id} 的差异点从 {previous_gap_count} 个上升到 "
            f"{current_gap_count} 个，当前实现仍需继续校正。"
        )
    else:
        regression_result = (
            f"回归样例 {current.sample_id} 的差异点维持在 {current_gap_count} 个，"
            "当前进入稳定性复核阶段。"
        )

    capability_change = _capability_change_from_diff(
        previous_gap_count=previous_gap_count,
        current_gap_count=current_gap_count,
        previous_aligned_count=previous_aligned_count,
        current=current,
    )
    return RegressionFeedback(
        regression_result=regression_result,
        capability_change=capability_change,
    )


def _capability_change_from_current(current: ValidationComparison) -> str:
    if current.gap_points:
        return (
            f"已补充首轮回归记录；当前已稳定覆盖 {len(current.aligned_points)} 个对齐点，"
            f"仍剩 {len(current.gap_points)} 个差异点待继续蒸馏。"
        )
    if current.aligned_points:
        return (
            f"已在回归样例 {current.sample_id} 中覆盖全部关键点，"
            "目标智能体进入稳定验证阶段。"
        )
    return f"已记录回归样例 {current.sample_id}，当前仍需补充更细的验证点。"


def _capability_change_from_diff(
    *,
    previous_gap_count: int,
    current_gap_count: int,
    previous_aligned_count: int,
    current: ValidationComparison,
) -> str:
    if current_gap_count == 0 and current.aligned_points:
        return (
            f"已在回归样例 {current.sample_id} 中覆盖全部关键点，"
            "目标智能体当前能力已达到该样例的人工基准。"
        )
    if current_gap_count < previous_gap_count:
        return (
            f"当前已新增覆盖 {max(len(current.aligned_points) - previous_aligned_count, 0)} 个对齐点，"
            f"并把剩余差异压缩到 {current_gap_count} 个。"
        )
    if current_gap_count > previous_gap_count:
        return "当前回归结果显示能力仍不稳定，新增实现尚未稳定转化为样例收益。"
    if current.aligned_points:
        return (
            f"当前已维持 {len(current.aligned_points)} 个对齐点，"
            f"但仍有 {current_gap_count} 个差异点需要继续蒸馏。"
        )
    return "当前回归结果尚未形成明确能力提升，需要继续补样例或调整实现。"


__all__ = ["RegressionFeedback", "build_regression_feedback"]
