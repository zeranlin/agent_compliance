from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pdfplumber


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = REPO_ROOT / "data" / "procurement-catalog" / "raw" / "full-catalog-2022" / "source.pdf"
OUTPUT_JSON = REPO_ROOT / "data" / "procurement-catalog" / "catalogs-full.json"

HEADER_PREFIX = "编 码 品目名称"
ROOT_PATTERN = re.compile(r"^([ABC])\s+(\S+)$")
CODE_PATTERN = re.compile(r"^([ABC]\d{8})\s+(.+)$")
DESCRIPTION_SPLIT_PATTERN = re.compile(
    r"(?P<name>.+?)(?P<desc>(包括|用于|具有|含|指|不包括|是指|即|其中|含有|适用于).*)$"
)


@dataclass
class CatalogEntry:
    catalog_code: str
    catalog_name: str
    category_letter: str
    category_type: str
    level: int
    parent_code: str | None
    description: str
    source_page: int
    extraction_status: str


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def category_type_for_letter(letter: str) -> str:
    return {"A": "goods", "B": "engineering", "C": "service"}.get(letter, "mixed")


def infer_level(code: str) -> int:
    groups = [code[1:3], code[3:5], code[5:7], code[7:9]]
    return sum(1 for group in groups if group != "00")


def infer_parent_code(code: str) -> str | None:
    groups = [code[1:3], code[3:5], code[5:7], code[7:9]]
    level = infer_level(code)
    if level <= 1:
        return code[0]
    last_non_zero = max(index for index, group in enumerate(groups) if group != "00")
    parent_groups = groups[:]
    parent_groups[last_non_zero] = "00"
    return f"{code[0]}{''.join(parent_groups)}"


def split_name_and_description(rest: str) -> tuple[str, str]:
    match = DESCRIPTION_SPLIT_PATTERN.match(rest)
    if not match:
        return rest.strip(), ""
    return match.group("name").strip(), match.group("desc").strip()


def extract_catalog_entries() -> list[CatalogEntry]:
    entries: list[CatalogEntry] = []
    current_entry: CatalogEntry | None = None
    started = False

    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            lines = [normalize_line(line) for line in text.splitlines() if normalize_line(line)]
            if not lines:
                continue

            for line in lines:
                if line.isdigit():
                    continue
                if line.startswith(HEADER_PREFIX):
                    continue
                if not started:
                    if page_index >= 10 and line == "A 货物":
                        started = True
                    else:
                        continue

                root_match = ROOT_PATTERN.match(line)
                if root_match:
                    if current_entry is not None:
                        entries.append(current_entry)
                        current_entry = None
                    letter, name = root_match.groups()
                    entries.append(
                        CatalogEntry(
                            catalog_code=letter,
                            catalog_name=name,
                            category_letter=letter,
                            category_type=category_type_for_letter(letter),
                            level=0,
                            parent_code=None,
                            description="",
                            source_page=page_index,
                            extraction_status="parsed",
                        )
                    )
                    continue

                code_match = CODE_PATTERN.match(line)
                if code_match:
                    if current_entry is not None:
                        entries.append(current_entry)
                    code, rest = code_match.groups()
                    name, description = split_name_and_description(rest)
                    current_entry = CatalogEntry(
                        catalog_code=code,
                        catalog_name=name,
                        category_letter=code[0],
                        category_type=category_type_for_letter(code[0]),
                        level=infer_level(code),
                        parent_code=infer_parent_code(code),
                        description=description,
                        source_page=page_index,
                        extraction_status="parsed_partial_desc" if description else "parsed",
                    )
                    continue

                if current_entry is None:
                    continue

                # 第一版全量骨架优先保证编码、名称、层级和父子关系稳定。
                # 多行说明在 PDF 中存在列顺序串位，后续再做精细抽取。
                continue

    if current_entry is not None:
        entries.append(current_entry)

    deduped: dict[str, CatalogEntry] = {}
    for entry in entries:
        existing = deduped.get(entry.catalog_code)
        if existing is None or len(entry.description) > len(existing.description):
            deduped[entry.catalog_code] = entry
    return [deduped[key] for key in sorted(deduped.keys())]


def main() -> None:
    entries = extract_catalog_entries()
    payload = {
        "source_id": "PROCUREMENT-CATALOG-2022-FULL",
        "entry_count": len(entries),
        "extraction_status": "skeleton_generated",
        "description": "基于 2022 版《政府采购品目分类目录》PDF 抽取的第一版全量目录骨架，优先保证编码、名称、层级和父子关系可用。",
        "entries": [asdict(entry) for entry in entries],
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT_JSON}")
    print(f"entries={len(entries)}")


if __name__ == "__main__":
    main()
