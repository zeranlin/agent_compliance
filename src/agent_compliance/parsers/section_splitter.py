from __future__ import annotations

import re

from agent_compliance.schemas import Clause


SECTION_PATTERNS = [re.compile(r"^第.+章"), re.compile(r"^[一二三四五六七八九十]+、")]

SECTION_KEYWORDS = ("资格要求", "评标信息", "技术要求", "商务要求", "验收条件", "用户需求书", "招标公告")


def split_into_clauses(text: str) -> list[Clause]:
    lines = text.splitlines()
    clauses: list[Clause] = []
    current_section: str | None = None

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        if _looks_like_section(line):
            current_section = line

        clause_id = _infer_clause_id(line, line_number)
        clauses.append(
            Clause(
                clause_id=clause_id,
                text=line,
                line_start=line_number,
                line_end=line_number,
                section_path=current_section,
            )
        )

    return clauses


def _looks_like_section(line: str) -> bool:
    if any(pattern.match(line) for pattern in SECTION_PATTERNS):
        return True
    if any(keyword in line for keyword in SECTION_KEYWORDS) and len(line) <= 40 and "。" not in line and "；" not in line:
        return True
    return False


def _infer_clause_id(line: str, line_number: int) -> str:
    match = re.match(r"^([^\s]{1,30})", line)
    if match:
        return match.group(1)
    return f"L-{line_number:04d}"
