from __future__ import annotations

import re

from agent_compliance.core.schemas import PageSpan


PAGE_MARKER_PATTERN = re.compile(r"^\[\[PAGE:(\d+)\]\]$")
DEFAULT_LINES_PER_PAGE = 45


def build_page_map(text: str, *, lines_per_page: int = DEFAULT_LINES_PER_PAGE) -> list[PageSpan]:
    explicit = _build_explicit_page_map(text)
    if explicit:
        return explicit
    return _build_estimated_page_map(text, lines_per_page=lines_per_page)


def page_hint_for_line(line_number: int, page_map: list[PageSpan]) -> str | None:
    for span in page_map:
        if span.line_start <= line_number <= span.line_end:
            suffix = "（估算）" if span.is_estimated else ""
            return f"第{span.page_number}页{suffix}"
    return None


def _build_explicit_page_map(text: str) -> list[PageSpan]:
    lines = text.splitlines()
    spans: list[PageSpan] = []
    current_page = 1
    current_start = 1
    saw_marker = False

    for line_number, raw_line in enumerate(lines, start=1):
        match = PAGE_MARKER_PATTERN.match(raw_line.strip())
        if not match:
            continue
        saw_marker = True
        marker_page = int(match.group(1))
        if line_number > current_start:
            spans.append(
                PageSpan(
                    page_number=current_page,
                    line_start=current_start,
                    line_end=line_number - 1,
                    is_estimated=False,
                )
            )
        current_page = marker_page
        current_start = line_number + 1

    if not saw_marker:
        return []

    if current_start <= len(lines):
        spans.append(
            PageSpan(
                page_number=current_page,
                line_start=current_start,
                line_end=len(lines),
                is_estimated=False,
            )
        )
    return spans


def _build_estimated_page_map(text: str, *, lines_per_page: int) -> list[PageSpan]:
    total_lines = max(len(text.splitlines()), 1)
    spans: list[PageSpan] = []
    page_number = 1
    for line_start in range(1, total_lines + 1, lines_per_page):
        line_end = min(line_start + lines_per_page - 1, total_lines)
        spans.append(
            PageSpan(
                page_number=page_number,
                line_start=line_start,
                line_end=line_end,
                is_estimated=True,
            )
        )
        page_number += 1
    return spans
