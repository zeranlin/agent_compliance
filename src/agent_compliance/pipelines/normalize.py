from __future__ import annotations

import json
from pathlib import Path

from agent_compliance.cache.file_cache import sha256_file
from agent_compliance.config import detect_paths
from agent_compliance.parsers.section_splitter import split_into_clauses
from agent_compliance.parsers.text_extractor import extract_text
from agent_compliance.schemas import NormalizedDocument


def run_normalize(source_path: Path) -> NormalizedDocument:
    paths = detect_paths()
    paths.normalized_root.mkdir(parents=True, exist_ok=True)

    text = extract_text(source_path)
    file_hash = sha256_file(source_path)
    stem = source_path.stem
    normalized_text_path = paths.normalized_root / f"{stem}-{file_hash[:12]}.txt"
    normalized_json_path = paths.normalized_root / f"{stem}-{file_hash[:12]}.json"

    normalized_text_path.write_text(text, encoding="utf-8")
    clauses = split_into_clauses(text)
    document = NormalizedDocument(
        source_path=str(source_path),
        document_name=source_path.name,
        file_hash=file_hash,
        normalized_text_path=str(normalized_text_path),
        clause_count=len(clauses),
        clauses=clauses,
    )
    normalized_json_path.write_text(
        json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return document
