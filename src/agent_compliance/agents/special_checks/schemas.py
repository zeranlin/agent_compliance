from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpecialChecksFinding:
    """政府采购四类专项检查智能体 的最小 finding 骨架。"""

    title: str
    detail: str = ""


@dataclass
class SpecialChecksResult:
    """政府采购四类专项检查智能体 的最小结果骨架。"""

    findings: list[SpecialChecksFinding] = field(default_factory=list)
