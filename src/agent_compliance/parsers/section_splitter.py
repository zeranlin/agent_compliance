from __future__ import annotations

import re

from agent_compliance.parsers.pagination import page_hint_for_line
from agent_compliance.schemas import Clause


SECTION_PATTERNS = [
    re.compile(r"^(第[一二三四五六七八九十百]+章.*)$"),
    re.compile(r"^([一二三四五六七八九十]+、.*)$"),
    re.compile(r"^(\d+(?:\.\d+)+)\s*(.*)$"),
]

SECTION_KEYWORDS = (
    "资格要求",
    "评标信息",
    "技术要求",
    "商务要求",
    "验收条件",
    "用户需求书",
    "招标公告",
    "技术部分",
    "商务部分",
    "评分因素",
    "评分项",
)
TABLE_LABEL_KEYWORDS = ("评分项", "评分因素", "技术部分", "商务部分", "价格", "其他", "验收条件")
GENERIC_TABLE_LABELS = ("序号", "内容", "权重(%)", "评分准则")
SEMANTIC_TABLE_LABEL_RANKS = {
    "评分项": 1,
    "价格": 2,
    "技术部分": 2,
    "商务部分": 2,
    "其他": 2,
    "验收条件": 2,
    "评分因素": 3,
}


def split_into_clauses(text: str, *, page_map=None) -> list[Clause]:
    lines = text.splitlines()
    clauses: list[Clause] = []
    section_stack: list[str] = []
    current_source_section: str | None = None
    current_table_label: str | None = None

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        section_info = _match_section(line)
        if section_info:
            section_stack = _update_section_stack(section_stack, section_info)
            current_source_section = _best_source_section(section_stack)
            if not _looks_like_table_label(line):
                current_table_label = None

        if _looks_like_table_label(line):
            if _is_semantic_table_label(line):
                current_table_label = line
                section_stack = _update_table_label_stack(section_stack, line)
                current_source_section = _best_source_section(section_stack)

        clause_id = _infer_clause_id(line, line_number)
        clauses.append(
            Clause(
                clause_id=clause_id,
                text=line,
                line_start=line_number,
                line_end=line_number,
                source_section=current_source_section,
                section_path="-".join(section_stack) if section_stack else current_source_section,
                table_or_item_label=_infer_table_label(current_table_label, line),
                page_hint=page_hint_for_line(line_number, page_map or []),
            )
        )

    return clauses


def _match_section(line: str) -> tuple[int, str] | None:
    chapter_match = SECTION_PATTERNS[0].match(line)
    if chapter_match:
        return (1, chapter_match.group(1))
    cn_match = SECTION_PATTERNS[1].match(line)
    if cn_match and len(line) <= 40 and "。" not in line and "，" not in line and "；" not in line:
        return (2, cn_match.group(1))
    numeric_match = SECTION_PATTERNS[2].match(line)
    if numeric_match and len(line) <= 80 and "。" not in line:
        level = min(numeric_match.group(1).count(".") + 2, 5)
        return (level, line)
    if _looks_like_table_label(line):
        return None
    if any(keyword in line for keyword in SECTION_KEYWORDS) and len(line) <= 40 and "。" not in line and "；" not in line:
        return (3, line)
    return None


def _update_section_stack(section_stack: list[str], section_info: tuple[int, str]) -> list[str]:
    level, title = section_info
    normalized = title.strip("：: ")
    stack = section_stack[: max(level - 1, 0)]
    stack.append(normalized)
    return stack


def _update_table_label_stack(section_stack: list[str], line: str) -> list[str]:
    normalized = line.strip("：: ")
    rank = SEMANTIC_TABLE_LABEL_RANKS.get(normalized)
    if rank is None:
        return section_stack
    if section_stack and section_stack[-1] == normalized:
        return section_stack
    stack: list[str] = []
    for item in section_stack:
        item_rank = SEMANTIC_TABLE_LABEL_RANKS.get(item)
        if item_rank is not None and item_rank >= rank:
            continue
        stack.append(item)
    stack.append(normalized)
    return stack


def _best_source_section(section_stack: list[str]) -> str | None:
    if not section_stack:
        return None
    for item in reversed(section_stack):
        if any(keyword in item for keyword in SECTION_KEYWORDS):
            return item
    return section_stack[-1]


def _looks_like_table_label(line: str) -> bool:
    normalized = line.strip("：: ")
    if any(keyword == normalized for keyword in TABLE_LABEL_KEYWORDS):
        return True
    if normalized in GENERIC_TABLE_LABELS:
        return True
    if len(normalized) <= 12 and re.fullmatch(r"(序号|内容|评分项|评分因素|权重\(%\)|评分准则)", normalized):
        return True
    return False


def _is_semantic_table_label(line: str) -> bool:
    normalized = line.strip("：: ")
    return normalized in SEMANTIC_TABLE_LABEL_RANKS


def _infer_table_label(current_table_label: str | None, line: str) -> str | None:
    if line == current_table_label:
        return current_table_label
    if current_table_label and not _match_section(line):
        return current_table_label
    return current_table_label if _looks_like_table_label(line) else None


def _infer_clause_id(line: str, line_number: int) -> str:
    match = re.match(r"^([^\s]{1,40})", line)
    if match:
        return match.group(1)
    return f"L-{line_number:04d}"
