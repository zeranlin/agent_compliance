from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DemandResearchFinding:
    """政府采购需求调查智能体 的最小 finding 骨架。"""

    title: str
    detail: str = ""


@dataclass
class DemandResearchResult:
    """政府采购需求调查智能体 的最小结果骨架。"""

    findings: list[DemandResearchFinding] = field(default_factory=list)
