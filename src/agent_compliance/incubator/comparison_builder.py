from __future__ import annotations

from pathlib import Path
import re

from agent_compliance.incubator.lifecycle import ValidationComparison


def build_validation_comparison(
    *,
    sample_id: str,
    human_baseline: str,
    strong_agent_result: str,
    target_agent_result: str,
    summary: str = "",
) -> ValidationComparison:
    """根据三方文本结果自动构造最小对照对象。"""

    baseline_points = _extract_points(human_baseline) or _extract_points(strong_agent_result)
    target_points = _extract_points(target_agent_result)

    aligned_points = tuple(
        point for point in baseline_points if _has_similar_point(point, target_points)
    )
    gap_points = tuple(
        point for point in baseline_points if not _has_similar_point(point, target_points)
    )

    generated_summary = summary or _build_summary(sample_id, aligned_points, gap_points)
    return ValidationComparison(
        sample_id=sample_id,
        human_baseline=human_baseline.strip(),
        strong_agent_result=strong_agent_result.strip(),
        target_agent_result=target_agent_result.strip(),
        aligned_points=aligned_points,
        gap_points=gap_points,
        summary=generated_summary,
    )


def build_validation_comparison_from_files(
    *,
    sample_id: str,
    human_baseline_path: Path,
    strong_agent_result_path: Path,
    target_agent_result_path: Path,
    summary: str = "",
) -> ValidationComparison:
    """从三份标准文本文件构造对照对象。"""

    return build_validation_comparison(
        sample_id=sample_id,
        human_baseline=human_baseline_path.read_text(encoding="utf-8"),
        strong_agent_result=strong_agent_result_path.read_text(encoding="utf-8"),
        target_agent_result=target_agent_result_path.read_text(encoding="utf-8"),
        summary=summary,
    )


def _extract_points(text: str) -> tuple[str, ...]:
    points: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = re.sub(r"^[\-\*\d\.\)\(（）、\s]+", "", line).strip()
        if len(normalized) < 6:
            continue
        points.append(normalized)
    return tuple(dict.fromkeys(points))


def _has_similar_point(point: str, candidates: tuple[str, ...]) -> bool:
    point_tokens = _tokens(point)
    if not point_tokens:
        return False
    for candidate in candidates:
        candidate_tokens = _tokens(candidate)
        if len(point_tokens & candidate_tokens) >= 2:
            return True
    return False


def _tokens(text: str) -> set[str]:
    normalized_tokens: set[str] = set()
    for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", text):
        lowered = token.lower()
        normalized_tokens.add(lowered)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) >= 2:
            normalized_tokens.update(token[i : i + 2] for i in range(len(token) - 1))
    return normalized_tokens


def _build_summary(
    sample_id: str,
    aligned_points: tuple[str, ...],
    gap_points: tuple[str, ...],
) -> str:
    if gap_points:
        return f"样例 {sample_id} 当前仍有 {len(gap_points)} 个关键差异点未被目标智能体覆盖。"
    if aligned_points:
        return f"样例 {sample_id} 的关键点已被目标智能体初步覆盖，可进入下一轮细化。"
    return f"样例 {sample_id} 已生成自动对照结果，当前仍需补充更细的评测点。"
