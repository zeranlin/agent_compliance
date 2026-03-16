from __future__ import annotations

import json
import subprocess
from email.parser import BytesParser
from email.policy import default
from html import escape as html_escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from agent_compliance.cache.review_cache import (
    REVIEW_CACHE_VERSION,
    build_review_cache_key,
    load_review_cache,
    reference_snapshot_id,
    save_review_cache,
)
from agent_compliance.config import LLMConfig, detect_llm_config, detect_paths
from agent_compliance.improvement.rule_management import load_rule_management_payload, save_rule_decision
from agent_compliance.parsers.pagination import page_hint_for_line
from agent_compliance.pipelines.llm_enhance import enhance_review_result
from agent_compliance.pipelines.llm_review import apply_llm_review_tasks
from agent_compliance.pipelines.normalize import run_normalize
from agent_compliance.pipelines.render import write_review_outputs
from agent_compliance.pipelines.review import build_review_result
from agent_compliance.pipelines.rule_scan import run_rule_scan
from agent_compliance.rules.base import RULE_SET_VERSION
from agent_compliance.schemas import NormalizedDocument


def run_web_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), ReviewWebHandler)
    print(f"Web UI running at http://{host}:{port}")
    server.serve_forever()


class ReviewWebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(_index_html())
            return
        if path == "/api/rules":
            self._send_json(load_rule_management_payload())
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/open-source":
            self._handle_open_source()
            return
        if path == "/api/rules/decision":
            self._handle_rule_decision()
            return
        if path != "/api/review":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            fields = _parse_multipart(self.headers, body)
        except Exception as exc:
            self._send_json({"error": f"请求解析失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)
            return

        upload = fields.get("file")
        if not upload or not upload.get("filename"):
            self._send_json({"error": "缺少上传文件"}, status=HTTPStatus.BAD_REQUEST)
            return

        use_llm = _flag_value(fields.get("use_llm", {}).get("value"))
        use_cache = _flag_value(fields.get("use_cache", {}).get("value"))
        paths = detect_paths()
        source_path = _persist_upload(str(upload["filename"]), bytes(upload["content"]))
        normalized = run_normalize(source_path)
        review, llm_artifacts, cache_key, cache_used = _run_review(normalized, use_cache=use_cache, use_llm=use_llm, paths=paths)
        json_path, md_path = write_review_outputs(review, normalized.file_hash[:12])

        self._send_json(
            {
                "cache": {"enabled": use_cache, "used": cache_used, "key": cache_key},
                "llm": {
                    "enabled": _web_llm_config(use_llm).enabled,
                    "base_url": detect_llm_config().base_url,
                    "model": detect_llm_config().model,
                },
                "document": _build_document_payload(normalized),
                "review": review.to_dict(),
                "llm_review": llm_artifacts.to_dict(),
                "outputs": {"json": str(json_path), "markdown": str(md_path)},
            }
        )

    def log_message(self, format: str, *args) -> None:
        return

    def _send_html(self, html: str, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_open_source(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            path = Path(payload.get("path", ""))
            if not path.exists():
                self._send_json({"error": "原文件不存在"}, status=HTTPStatus.BAD_REQUEST)
                return
            subprocess.run(["open", str(path)], check=True)
            self._send_json({"ok": True})
        except Exception as exc:
            self._send_json({"error": f"打开原文件失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)

    def _handle_rule_decision(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            candidate_rule_id = str(payload.get("candidate_rule_id", "")).strip()
            decision = str(payload.get("decision", "")).strip()
            note = str(payload.get("note", "")).strip()
            if not candidate_rule_id:
                self._send_json({"error": "缺少 candidate_rule_id"}, status=HTTPStatus.BAD_REQUEST)
                return
            save_rule_decision(candidate_rule_id, decision, note)
            self._send_json(load_rule_management_payload())
        except Exception as exc:
            self._send_json({"error": f"保存规则决策失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)


def _run_review(
    normalized: NormalizedDocument,
    *,
    use_cache: bool,
    use_llm: bool,
    paths,
) -> tuple[Any, str, bool]:
    reference_snapshot = reference_snapshot_id(paths.repo_root / "docs" / "references")
    cache_key = build_review_cache_key(
        file_hash=normalized.file_hash,
        rule_set_version=RULE_SET_VERSION,
        reference_snapshot=reference_snapshot,
        review_pipeline_version=REVIEW_CACHE_VERSION,
    )
    review = load_review_cache(cache_key) if use_cache else None
    cache_used = review is not None
    if review is None:
        hits = run_rule_scan(normalized)
        review = build_review_result(normalized, hits)
        if use_cache:
            save_review_cache(
                cache_key,
                review,
                metadata={
                    "file_hash": normalized.file_hash,
                    "rule_set_version": RULE_SET_VERSION,
                    "reference_snapshot": reference_snapshot,
                    "review_pipeline_version": REVIEW_CACHE_VERSION,
                },
            )
    review = enhance_review_result(review, _web_llm_config(use_llm))
    review, llm_artifacts = apply_llm_review_tasks(
        normalized,
        review,
        _web_llm_config(use_llm),
        output_stem=normalized.file_hash[:12],
    )
    return review, llm_artifacts, cache_key, cache_used


def _parse_multipart(headers, body: bytes) -> dict[str, dict[str, bytes | str]]:
    content_type = headers.get("Content-Type", "")
    if not content_type.startswith("multipart/form-data"):
        raise ValueError("仅支持 multipart/form-data")

    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    fields: dict[str, dict[str, bytes | str]] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        fields[name] = {
            "filename": part.get_filename() or "",
            "content": payload,
            "value": payload.decode("utf-8", errors="ignore"),
        }
    return fields


def _persist_upload(filename: str, content: bytes) -> Path:
    paths = detect_paths()
    paths.uploads_root.mkdir(parents=True, exist_ok=True)
    target = paths.uploads_root / Path(filename).name
    target.write_bytes(content)
    return target


def _web_llm_config(use_llm: bool) -> LLMConfig:
    config = detect_llm_config()
    return LLMConfig(
        enabled=bool(use_llm or config.enabled),
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )


def _flag_value(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "on", "yes"}


def _build_document_payload(normalized: NormalizedDocument) -> dict[str, Any]:
    text = Path(normalized.normalized_text_path).read_text(encoding="utf-8")
    lines = [
        {
            "number": number,
            "text": raw_line,
            "page_hint": page_hint_for_line(number, normalized.page_map),
        }
        for number, raw_line in enumerate(text.splitlines(), start=1)
    ]
    payload = {
        "source_path": normalized.source_path,
        "normalized_text_path": normalized.normalized_text_path,
        "line_count": len(lines),
        "lines": lines,
        "render_mode": "text",
        "blocks": [],
    }
    suffix = Path(normalized.source_path).suffix.lower()
    if suffix == ".docx":
        blocks = _build_docx_blocks(Path(normalized.source_path), lines)
        if blocks:
            payload["render_mode"] = "docx_blocks"
            payload["blocks"] = blocks
    return payload


def _build_docx_blocks(source_path: Path, lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        with ZipFile(source_path) as archive:
            document_xml = archive.read("word/document.xml")
    except Exception:
        return []

    root = ET.fromstring(document_xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    body = root.find("w:body", ns)
    if body is None:
        return []

    normalized_lines = [str(item["text"]) for item in lines]
    search_cursor = 0
    blocks: list[dict[str, Any]] = []
    block_index = 1

    for child in body:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = _docx_paragraph_text(child, ns)
            if not text.strip():
                continue
            start_line, end_line, search_cursor = _locate_block_lines(text, normalized_lines, search_cursor)
            blocks.append(
                {
                    "block_id": f"block-{block_index}",
                    "kind": "paragraph",
                    "html": f"<p>{html_escape(text)}</p>",
                    "start_line": start_line,
                    "end_line": end_line,
                    "page_hint": page_hint_for_line(start_line, []) if False else None,
                }
            )
            block_index += 1
        elif tag == "tbl":
            rows = _docx_table_rows(child, ns)
            if not rows:
                continue
            table_text = "\n".join(" | ".join(cell for cell in row if cell) for row in rows if any(cell for cell in row))
            start_line, end_line, search_cursor = _locate_block_lines(table_text, normalized_lines, search_cursor)
            rows_html = []
            for row in rows:
                cells_html = "".join(f"<td>{html_escape(cell)}</td>" for cell in row)
                rows_html.append(f"<tr>{cells_html}</tr>")
            blocks.append(
                {
                    "block_id": f"block-{block_index}",
                    "kind": "table",
                    "html": f"<table><tbody>{''.join(rows_html)}</tbody></table>",
                    "start_line": start_line,
                    "end_line": end_line,
                    "page_hint": None,
                }
            )
            block_index += 1
    return blocks


def _docx_paragraph_text(paragraph: ET.Element, ns: dict[str, str]) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "t" and node.text:
            parts.append(node.text)
        elif tag == "tab":
            parts.append("    ")
        elif tag in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts).strip()


def _docx_table_rows(table: ET.Element, ns: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall("w:tr", ns):
        cells: list[str] = []
        for cell in row.findall("w:tc", ns):
            paragraphs = [_docx_paragraph_text(paragraph, ns) for paragraph in cell.findall("w:p", ns)]
            cell_text = "\n".join(part for part in paragraphs if part).strip()
            cells.append(cell_text)
        if cells:
            rows.append(cells)
    return rows


def _locate_block_lines(block_text: str, normalized_lines: list[str], cursor: int) -> tuple[int, int, int]:
    target_parts = [part.strip() for part in block_text.splitlines() if part.strip()]
    if not target_parts:
        fallback = min(cursor + 1, max(len(normalized_lines), 1))
        return fallback, fallback, fallback

    start_index = None
    search_text = target_parts[0]
    for idx in range(cursor, len(normalized_lines)):
        candidate = normalized_lines[idx].strip()
        if not candidate:
            continue
        if search_text in candidate or candidate in search_text:
            start_index = idx
            break
    if start_index is None:
        for idx, candidate_line in enumerate(normalized_lines):
            candidate = candidate_line.strip()
            if candidate and (search_text in candidate or candidate in search_text):
                start_index = idx
                break

    if start_index is None:
        fallback = min(cursor + 1, max(len(normalized_lines), 1))
        return fallback, fallback, fallback

    end_index = start_index
    part_cursor = start_index
    for part in target_parts[1:]:
        for idx in range(part_cursor + 1, len(normalized_lines)):
            candidate = normalized_lines[idx].strip()
            if candidate and (part in candidate or candidate in part):
                end_index = idx
                part_cursor = idx
                break

    return start_index + 1, end_index + 1, max(end_index + 1, cursor)


def _index_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>采购审查工作台</title>
  <style>
    :root {
      --bg: #f4efe5;
      --panel: #fffdf8;
      --line: #ddd2c2;
      --ink: #20252b;
      --muted: #6c675e;
      --accent: #9d4a24;
      --high: #a33d22;
      --medium: #8f6714;
      --active: #fff2dd;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
    }
    .app {
      max-width: 1500px;
      margin: 0 auto;
      padding: 20px;
    }
    .hero {
      margin-bottom: 16px;
    }
    .hero h1 {
      margin: 0 0 8px;
      font-size: 30px;
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 12px 30px rgba(52, 41, 29, 0.06);
    }
    .toolbar {
      padding: 16px;
      margin-bottom: 16px;
      display: grid;
      gap: 12px;
    }
    .toolbar-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px 16px;
      align-items: center;
    }
    button {
      border: 0;
      border-radius: 10px;
      background: var(--accent);
      color: #fff;
      padding: 10px 16px;
      font-size: 14px;
      cursor: pointer;
    }
    button.secondary {
      background: #fff;
      color: var(--ink);
      border: 1px solid var(--line);
    }
    button:disabled {
      opacity: .5;
      cursor: wait;
    }
    label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 14px;
    }
    .status {
      color: var(--muted);
      font-size: 14px;
    }
    .summary {
      display: none;
      margin-bottom: 16px;
      padding: 16px;
    }
    .summary h2 {
      margin: 0 0 10px;
      font-size: 20px;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }
    .stat {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
      background: #fff;
    }
    .stat .label {
      color: var(--muted);
      font-size: 12px;
    }
    .stat .value {
      margin-top: 8px;
      font-size: 18px;
      font-weight: 700;
      line-height: 1.5;
      word-break: break-word;
    }
    .workspace {
      display: none;
      grid-template-columns: 420px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    .rules-panel {
      display: none;
      margin-top: 16px;
      padding: 16px;
    }
    .rules-grid {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      gap: 16px;
      margin-top: 12px;
    }
    .rules-col {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      min-height: 420px;
      overflow: hidden;
    }
    .rules-col-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 6px;
    }
    .rules-col-head h3 {
      margin: 0;
      font-size: 18px;
    }
    .rules-toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-top: 8px;
    }
    .rules-list {
      padding: 12px;
      display: grid;
      gap: 10px;
      max-height: 560px;
      overflow: auto;
    }
    .rule-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
      background: #fffdfa;
      display: grid;
      gap: 8px;
      cursor: pointer;
    }
    .rule-card.active {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(157, 74, 36, 0.12);
      background: #fff8f1;
    }
    .rule-card-title {
      font-size: 15px;
      font-weight: 700;
      line-height: 1.5;
    }
    .rule-card-meta {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
      word-break: break-word;
    }
    .rule-detail {
      padding: 16px;
      display: grid;
      gap: 12px;
    }
    .rule-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .rule-note {
      width: 100%;
      min-height: 70px;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--line);
      font: inherit;
      resize: vertical;
    }
    .issues,
    .document {
      min-height: 580px;
    }
    .issues-head,
    .document-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 8px;
    }
    .issues-head h2,
    .document-head h2 {
      margin: 0;
      font-size: 20px;
    }
    .meta {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
      word-break: break-word;
    }
    .issues-list {
      padding: 12px;
      display: grid;
      gap: 10px;
      max-height: calc(100vh - 250px);
      overflow: auto;
    }
    .issue-item {
      width: 100%;
      background: #fff;
      color: var(--ink);
      border: 1px solid var(--line);
      border-radius: 12px;
      display: grid;
      overflow: hidden;
    }
    .issue-item.active {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(157, 74, 36, 0.12);
      background: #fff8f1;
    }
    .issue-summary {
      width: 100%;
      border: 0;
      background: transparent;
      color: inherit;
      text-align: left;
      padding: 14px;
      display: grid;
      gap: 8px;
      cursor: pointer;
    }
    .issue-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: space-between;
    }
    .issue-action-buttons {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .issue-mini-btn {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--ink);
      padding: 6px 10px;
      font-size: 12px;
      cursor: pointer;
    }
    .issue-detail {
      display: none;
      padding: 0 14px 14px;
      border-top: 1px solid #f1eadf;
      background: rgba(255, 252, 247, 0.92);
    }
    .issue-item.expanded .issue-detail {
      display: grid;
      gap: 10px;
    }
    .detail-pair {
      display: grid;
      gap: 4px;
    }
    .detail-label {
      color: var(--muted);
      font-size: 12px;
    }
    .detail-value {
      color: var(--ink);
      font-size: 13px;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .issue-top {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 12px;
      background: #f5ede2;
      color: var(--accent);
    }
    .badge.high {
      background: rgba(163, 61, 34, 0.1);
      color: var(--high);
    }
    .badge.medium {
      background: rgba(143, 103, 20, 0.12);
      color: var(--medium);
    }
    .badge.origin-llm {
      background: rgba(40, 88, 162, 0.12);
      color: #2858a2;
    }
    .badge.origin-rule {
      background: rgba(61, 120, 74, 0.12);
      color: #2f6f42;
    }
    .issues-filters {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .filter-chip {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--muted);
      padding: 6px 10px;
      font-size: 12px;
      cursor: pointer;
    }
    .filter-chip.active {
      border-color: var(--accent);
      color: var(--accent);
      background: #fff5ea;
    }
    .issue-title {
      font-size: 16px;
      font-weight: 700;
      line-height: 1.5;
    }
    .issue-meta,
    .issue-snippet {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .issue-snippet {
      color: var(--ink);
    }
    .issue-toggle-text {
      color: var(--muted);
      font-size: 12px;
    }
    .document-body {
      max-height: calc(100vh - 250px);
      overflow: auto;
      padding: 8px 0;
      background: #fff;
    }
    .doc-block {
      margin: 12px 16px;
      padding: 10px 12px;
      border: 1px solid transparent;
      border-radius: 10px;
      background: #fff;
    }
    .doc-block.active {
      background: var(--active);
      border-color: #f0c98a;
    }
    .doc-block p {
      margin: 0;
      line-height: 1.8;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .doc-block table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      background: #fff;
    }
    .doc-block td {
      border: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.7;
      font-size: 14px;
    }
    .doc-block-meta {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .doc-line {
      display: grid;
      grid-template-columns: 72px minmax(0, 1fr);
      gap: 12px;
      padding: 8px 16px;
      border-top: 1px solid #f1eadf;
      align-items: start;
    }
    .doc-line:first-child {
      border-top: 0;
    }
    .doc-line.active {
      background: var(--active);
      border-top-color: #f0c98a;
      border-bottom: 1px solid #f0c98a;
    }
    .doc-line-number {
      text-align: right;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .doc-line-text {
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.7;
      font-size: 14px;
    }
    .empty {
      padding: 20px 16px;
      color: var(--muted);
      line-height: 1.7;
    }
    @media (max-width: 1080px) {
      .workspace {
        grid-template-columns: 1fr;
      }
      .rules-grid {
        grid-template-columns: 1fr;
      }
      .issues-list,
      .document-body {
        max-height: none;
      }
      .summary-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <section class="hero">
      <h1>采购审查工作台</h1>
      <p>上传采购文件后，页面会渲染文件正文并生成审查问题清单。点击任意问题，右侧正文会自动定位到对应位置并高亮，方便快速复核。</p>
    </section>

    <form id="review-form" class="panel toolbar">
      <div class="toolbar-row">
        <input type="file" name="file" accept=".docx,.doc,.pdf,.txt,.md,.rtf" required />
        <button type="submit" id="submit-btn">上传并审查</button>
        <button type="button" id="open-source-btn" class="secondary" disabled>打开原文件</button>
      </div>
      <div class="toolbar-row">
        <label><input type="checkbox" name="use_cache" /> 启用缓存</label>
        <label><input type="checkbox" name="use_llm" /> 启用本地模型</label>
      </div>
      <div id="status" class="status">等待上传文件</div>
    </form>

    <section id="summary" class="panel summary"></section>

    <section id="workspace" class="workspace">
      <section class="panel issues">
        <div id="issues-head" class="issues-head"></div>
        <div id="issues-list" class="issues-list"></div>
      </section>
      <section class="panel document">
        <div id="document-head" class="document-head"></div>
        <div id="document-body" class="document-body"></div>
      </section>
    </section>
    <section id="rules-panel" class="panel rules-panel">
      <h2>规则管理</h2>
      <div id="rules-summary" class="meta">正在加载规则候选...</div>
      <div class="rules-grid">
        <section class="rules-col">
          <div id="rules-col-head" class="rules-col-head"></div>
          <div id="rules-list" class="rules-list"></div>
        </section>
        <section class="rules-col">
          <div class="rules-col-head">
            <h3>规则详情</h3>
            <div class="meta">查看候选规则、benchmark gate 状态，并记录是否确认入库。</div>
          </div>
          <div id="rule-detail" class="rule-detail"></div>
        </section>
      </div>
    </section>
  </div>

  <script>
    const form = document.getElementById('review-form');
    const submitBtn = document.getElementById('submit-btn');
    const openSourceBtn = document.getElementById('open-source-btn');
    const statusNode = document.getElementById('status');
    const summaryNode = document.getElementById('summary');
    const workspaceNode = document.getElementById('workspace');
    const issuesHeadNode = document.getElementById('issues-head');
    const issuesListNode = document.getElementById('issues-list');
    const documentHeadNode = document.getElementById('document-head');
    const documentBodyNode = document.getElementById('document-body');
    const rulesPanelNode = document.getElementById('rules-panel');
    const rulesSummaryNode = document.getElementById('rules-summary');
    const rulesColHeadNode = document.getElementById('rules-col-head');
    const rulesListNode = document.getElementById('rules-list');
    const ruleDetailNode = document.getElementById('rule-detail');

    let latestDocument = null;
    let latestFindings = [];
    let currentFindingFilter = 'all';
    let latestRulePayload = { formal_rules: [], candidate_rules: [], decision_summary: {} };
    let currentRuleFilter = 'pending';
    let selectedCandidateId = '';

    loadRuleManagement();

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      submitBtn.disabled = true;
      openSourceBtn.disabled = true;
      statusNode.textContent = '正在审查，请稍候...';
      summaryNode.style.display = 'none';
      workspaceNode.style.display = 'none';
      try {
        const formData = new FormData(form);
        const response = await fetch('/api/review', { method: 'POST', body: formData });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '审查失败');
        latestDocument = payload.document;
        latestFindings = payload.review.findings;
        currentFindingFilter = 'all';
        renderSummary(payload);
        renderIssues(payload.review.findings);
        renderDocument(payload.document);
        await loadRuleManagement();
        if (payload.review.findings.length) {
          selectFinding(payload.review.findings[0].finding_id);
        }
        openSourceBtn.disabled = !payload.document || !payload.document.source_path;
        statusNode.textContent = '审查完成';
      } catch (error) {
        statusNode.textContent = `失败：${error.message}`;
      } finally {
        submitBtn.disabled = false;
      }
    });

    openSourceBtn.addEventListener('click', openSourceFile);

    function renderSummary(payload) {
      const review = payload.review;
      const highCount = review.findings.filter((item) => item.risk_level === 'high').length;
      const mediumCount = review.findings.filter((item) => item.risk_level === 'medium').length;
      const llmAddedCount = review.findings.filter((item) => item.finding_origin === 'llm_added').length;
      const ruleCount = review.findings.filter((item) => item.finding_origin !== 'llm_added').length;
      summaryNode.innerHTML = `
        <h2>审查摘要</h2>
        <div>${escapeHtml(review.overall_risk_summary)}</div>
        <div class="summary-grid">
          <div class="stat"><div class="label">文件</div><div class="value">${escapeHtml(review.document_name)}</div></div>
          <div class="stat"><div class="label">发现项</div><div class="value">${review.findings.length}</div></div>
          <div class="stat"><div class="label">规则命中</div><div class="value">${ruleCount}</div></div>
          <div class="stat"><div class="label">模型新增</div><div class="value">${llmAddedCount}</div></div>
          <div class="stat"><div class="label">高风险</div><div class="value">${highCount}</div></div>
          <div class="stat"><div class="label">中风险</div><div class="value">${mediumCount}</div></div>
          <div class="stat"><div class="label">缓存 / 模型</div><div class="value">${payload.cache.enabled ? '缓存开' : '缓存关'} / ${payload.llm.enabled ? '模型开' : '模型关'}</div></div>
        </div>`;
      summaryNode.style.display = 'block';
    }

    async function loadRuleManagement() {
      try {
        const response = await fetch('/api/rules');
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '规则管理加载失败');
        latestRulePayload = payload;
        if (!selectedCandidateId && payload.candidate_rules.length) {
          selectedCandidateId = payload.candidate_rules[0].candidate_rule_id;
        }
        renderRules(payload);
      } catch (error) {
        rulesPanelNode.style.display = 'block';
        rulesSummaryNode.textContent = `规则管理加载失败：${error.message}`;
      }
    }

    function renderRules(payload) {
      const summary = payload.decision_summary || {};
      rulesSummaryNode.textContent = `正式规则 ${payload.formal_rules.length} 条；候选规则 ${payload.candidate_rules.length} 条；待确认 ${summary.pending || 0} 条；已确认 ${summary.confirmed || 0} 条。`;
      rulesColHeadNode.innerHTML = `
        <h3>候选规则</h3>
        <div class="meta">候选规则来自模型新增问题和 benchmark gate 结果。确认入库表示进入本地规则候选确认状态，不会自动改代码。</div>
        <div class="rules-toolbar">
          <button type="button" class="filter-chip ${currentRuleFilter === 'pending' ? 'active' : ''}" data-rule-filter="pending">待确认</button>
          <button type="button" class="filter-chip ${currentRuleFilter === 'confirmed' ? 'active' : ''}" data-rule-filter="confirmed">已确认</button>
          <button type="button" class="filter-chip ${currentRuleFilter === 'all' ? 'active' : ''}" data-rule-filter="all">全部</button>
        </div>`;
      rulesColHeadNode.querySelectorAll('[data-rule-filter]').forEach((node) => {
        node.addEventListener('click', () => {
          currentRuleFilter = node.dataset.ruleFilter;
          renderRules(latestRulePayload);
        });
      });
      const candidates = applyRuleFilter(payload.candidate_rules || []);
      rulesListNode.innerHTML = candidates.length
        ? candidates.map((item) => renderRuleCard(item)).join('')
        : '<div class="empty">当前没有符合筛选条件的候选规则。</div>';
      rulesListNode.querySelectorAll('.rule-card').forEach((node) => {
        node.addEventListener('click', () => {
          selectedCandidateId = node.dataset.candidateId;
          renderRules(latestRulePayload);
        });
      });
      const selected = candidates.find((item) => item.candidate_rule_id === selectedCandidateId) || candidates[0] || null;
      if (selected) selectedCandidateId = selected.candidate_rule_id;
      renderRuleDetail(selected);
      rulesPanelNode.style.display = 'block';
    }

    function renderRuleCard(item) {
      const active = item.candidate_rule_id === selectedCandidateId ? 'active' : '';
      return `<article class="rule-card ${active}" data-candidate-id="${escapeHtml(item.candidate_rule_id)}">
        <div class="rule-card-title">${escapeHtml(item.problem_title)}</div>
        <div class="rule-card-meta">候选ID：${escapeHtml(item.candidate_rule_id)}</div>
        <div class="rule-card-meta">问题类型：${escapeHtml(item.issue_type)} ｜ gate：${escapeHtml(item.gate_status)} ｜ 状态：${escapeHtml(decisionLabelText(item.decision))}</div>
        <div class="rule-card-meta">${escapeHtml(item.source_text || '')}</div>
      </article>`;
    }

    function renderRuleDetail(item) {
      if (!item) {
        ruleDetailNode.innerHTML = '<div class="empty">当前没有可查看的候选规则。</div>';
        return;
      }
      ruleDetailNode.innerHTML = `
        <div class="detail-pair"><div class="detail-label">候选规则ID</div><div class="detail-value">${escapeHtml(item.candidate_rule_id)}</div></div>
        <div class="detail-pair"><div class="detail-label">问题标题</div><div class="detail-value">${escapeHtml(item.problem_title)}</div></div>
        <div class="detail-pair"><div class="detail-label">问题类型</div><div class="detail-value">${escapeHtml(item.issue_type)}</div></div>
        <div class="detail-pair"><div class="detail-label">来源位置</div><div class="detail-value">${escapeHtml(item.section_path || '')}</div></div>
        <div class="detail-pair"><div class="detail-label">原文摘录</div><div class="detail-value">${escapeHtml(item.source_text || '')}</div></div>
        <div class="detail-pair"><div class="detail-label">风险说明</div><div class="detail-value">${escapeHtml(item.why_it_is_risky || '')}</div></div>
        <div class="detail-pair"><div class="detail-label">建议改写</div><div class="detail-value">${escapeHtml(item.rewrite_suggestion || '')}</div></div>
        <div class="detail-pair"><div class="detail-label">触发关键词</div><div class="detail-value">${escapeHtml((item.trigger_keywords || []).join('，'))}</div></div>
        <div class="detail-pair"><div class="detail-label">benchmark gate</div><div class="detail-value">${escapeHtml(item.gate_status)} ｜ ${escapeHtml(item.gate_reason || '')}</div></div>
        <div class="detail-pair"><div class="detail-label">当前状态</div><div class="detail-value">${escapeHtml(decisionLabelText(item.decision))}</div></div>
        <div class="detail-pair">
          <div class="detail-label">备注</div>
          <textarea id="rule-note" class="rule-note" placeholder="可选：记录为什么确认、暂缓或忽略">${escapeHtml(item.decision_note || '')}</textarea>
        </div>
        <div class="rule-actions">
          <button type="button" data-rule-action="confirmed">确认入库</button>
          <button type="button" class="secondary" data-rule-action="deferred">暂缓</button>
          <button type="button" class="secondary" data-rule-action="ignored">忽略</button>
        </div>`;
      ruleDetailNode.querySelectorAll('[data-rule-action]').forEach((node) => {
        node.addEventListener('click', async () => {
          await saveRuleDecision(item.candidate_rule_id, node.dataset.ruleAction);
        });
      });
    }

    async function saveRuleDecision(candidateRuleId, decision) {
      const noteNode = document.getElementById('rule-note');
      const note = noteNode ? noteNode.value : '';
      try {
        const response = await fetch('/api/rules/decision', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ candidate_rule_id: candidateRuleId, decision, note }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '规则决策保存失败');
        latestRulePayload = payload;
        selectedCandidateId = candidateRuleId;
        renderRules(payload);
        statusNode.textContent = `规则候选已更新为：${decisionLabelText(decision)}`;
      } catch (error) {
        statusNode.textContent = `保存规则决策失败：${error.message}`;
      }
    }

    function renderIssues(findings) {
      const filtered = applyFindingFilter(findings, currentFindingFilter);
      const llmCount = findings.filter((item) => item.finding_origin === 'llm_added').length;
      const ruleCount = findings.filter((item) => item.finding_origin !== 'llm_added').length;
      issuesHeadNode.innerHTML = `
        <h2>审查问题清单</h2>
        <div class="meta">共 ${findings.length} 条问题，其中规则命中 ${ruleCount} 条、模型新增 ${llmCount} 条。点击“定位正文”会跳到对应位置，点击“展开详情”可查看依据、判断和建议。</div>
        <div class="issues-filters">
          <button type="button" class="filter-chip ${currentFindingFilter === 'all' ? 'active' : ''}" data-filter="all">全部</button>
          <button type="button" class="filter-chip ${currentFindingFilter === 'rule' ? 'active' : ''}" data-filter="rule">规则</button>
          <button type="button" class="filter-chip ${currentFindingFilter === 'llm' ? 'active' : ''}" data-filter="llm">模型新增</button>
        </div>`;
      issuesListNode.innerHTML = filtered.length
        ? filtered.map((finding, index) => renderIssueItem(finding, index + 1)).join('')
        : '<div class="empty">当前没有识别出需要提示的问题。</div>';
      issuesHeadNode.querySelectorAll('.filter-chip').forEach((node) => {
        node.addEventListener('click', () => {
          currentFindingFilter = node.dataset.filter;
          renderIssues(latestFindings);
        });
      });
      issuesListNode.querySelectorAll('.issue-summary').forEach((node) => {
        node.addEventListener('click', () => {
          const card = node.closest('.issue-item');
          selectFinding(card.dataset.findingId);
        });
      });
      issuesListNode.querySelectorAll('.issue-locate-btn').forEach((node) => {
        node.addEventListener('click', (event) => {
          event.stopPropagation();
          const card = node.closest('.issue-item');
          selectFinding(card.dataset.findingId);
        });
      });
      issuesListNode.querySelectorAll('.issue-toggle-btn').forEach((node) => {
        node.addEventListener('click', (event) => {
          event.stopPropagation();
          const card = node.closest('.issue-item');
          card.classList.toggle('expanded');
          node.querySelector('.issue-toggle-text').textContent = card.classList.contains('expanded') ? '收起详情' : '展开详情';
        });
      });
      workspaceNode.style.display = 'grid';
    }

    function renderIssueItem(finding, index) {
      const originLabel = finding.finding_origin === 'llm_added' ? '模型新增' : '规则命中';
      const originClass = finding.finding_origin === 'llm_added' ? 'origin-llm' : 'origin-rule';
      return `<article class="issue-item" data-finding-id="${escapeHtml(finding.finding_id)}">
        <button type="button" class="issue-summary">
          <div class="issue-top">
            <span>问题 ${index}</span>
            <span class="badge ${escapeHtml(finding.risk_level)}">${escapeHtml(riskLabel(finding.risk_level))}</span>
            <span class="badge">${escapeHtml(finding.issue_type)}</span>
            <span class="badge ${originClass}">${originLabel}</span>
          </div>
          <div class="issue-title">${escapeHtml(finding.problem_title)}</div>
          <div class="issue-meta">位置：${escapeHtml(finding.section_path || finding.source_section || '待补充')} ｜ 行号：${escapeHtml(formatLineRange(finding.text_line_start, finding.text_line_end))}</div>
          <div class="issue-snippet">${escapeHtml(finding.source_text)}</div>
          <div class="issue-actions">
            <div class="issue-action-buttons">
              <button type="button" class="issue-mini-btn issue-locate-btn">定位正文</button>
              <button type="button" class="issue-mini-btn issue-toggle-btn"><span class="issue-toggle-text">展开详情</span></button>
            </div>
          </div>
        </button>
        <div class="issue-detail">
          <div class="detail-pair">
            <div class="detail-label">合规判断</div>
            <div class="detail-value">${escapeHtml(finding.compliance_judgment)}</div>
          </div>
          <div class="detail-pair">
            <div class="detail-label">页码提示</div>
            <div class="detail-value">${escapeHtml(finding.page_hint || '待人工翻页复核')}</div>
          </div>
          <div class="detail-pair">
            <div class="detail-label">来源</div>
            <div class="detail-value">${escapeHtml(originLabel)}</div>
          </div>
          <div class="detail-pair">
            <div class="detail-label">风险说明</div>
            <div class="detail-value">${escapeHtml(finding.why_it_is_risky)}</div>
          </div>
          <div class="detail-pair">
            <div class="detail-label">依据</div>
            <div class="detail-value">${escapeHtml(finding.legal_or_policy_basis || '当前离线链路未单独拆出更细依据，请结合正式审查结果复核。')}</div>
          </div>
          <div class="detail-pair">
            <div class="detail-label">修改建议</div>
            <div class="detail-value">${escapeHtml(finding.rewrite_suggestion)}</div>
          </div>
        </div>
      </article>`;
    }

    function renderDocument(documentPayload) {
      documentHeadNode.innerHTML = `
        <h2>文件正文</h2>
        <div class="meta">原文件：${escapeHtml(documentPayload.source_path)}</div>
        <div class="meta">稳定文本：${escapeHtml(documentPayload.normalized_text_path)}</div>
        <div class="meta">总行数：${documentPayload.line_count} ｜ 渲染模式：${documentPayload.render_mode === 'docx_blocks' ? 'DOCX 原文结构' : '稳定文本'}</div>`;
      documentBodyNode.innerHTML = documentPayload.render_mode === 'docx_blocks'
        ? documentPayload.blocks.map((block) => renderDocumentBlock(block)).join('')
        : documentPayload.lines.map((line) => renderDocumentLine(line)).join('');
      workspaceNode.style.display = 'grid';
    }

    function renderDocumentBlock(block) {
      const meta = `行号：${formatLineRange(block.start_line, block.end_line)}`;
      return `<div class="doc-block" id="${escapeHtml(block.block_id)}" data-start-line="${block.start_line}" data-end-line="${block.end_line}">
        ${block.html}
        <div class="doc-block-meta">${escapeHtml(meta)}</div>
      </div>`;
    }

    function renderDocumentLine(line) {
      return `<div class="doc-line" id="doc-line-${line.number}">
        <div class="doc-line-number">${String(line.number).padStart(4, '0')}${line.page_hint ? `<br>${escapeHtml(line.page_hint)}` : ''}</div>
        <div class="doc-line-text">${escapeHtml(line.text || ' ')}</div>
      </div>`;
    }

    function selectFinding(findingId) {
      const finding = latestFindings.find((item) => item.finding_id === findingId);
      if (!finding) return;
      issuesListNode.querySelectorAll('.issue-item').forEach((node) => {
        node.classList.toggle('active', node.dataset.findingId === findingId);
      });
      highlightDocumentRange(finding.text_line_start, finding.text_line_end);
    }

    function highlightDocumentRange(start, end) {
      documentBodyNode.querySelectorAll('.active').forEach((node) => node.classList.remove('active'));
      let target = null;
      if (latestDocument && latestDocument.render_mode === 'docx_blocks') {
        documentBodyNode.querySelectorAll('.doc-block').forEach((node) => {
          const blockStart = Number(node.dataset.startLine);
          const blockEnd = Number(node.dataset.endLine);
          const overlaps = blockStart <= end && blockEnd >= start;
          if (overlaps) {
            node.classList.add('active');
            if (!target) target = node;
          }
        });
      } else {
        for (let line = start; line <= end; line += 1) {
          const node = document.getElementById(`doc-line-${line}`);
          if (node) {
            node.classList.add('active');
            if (!target) target = node;
          }
        }
      }
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    async function openSourceFile() {
      if (!latestDocument || !latestDocument.source_path) return;
      try {
        const response = await fetch('/api/open-source', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: latestDocument.source_path }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '打开失败');
      } catch (error) {
        statusNode.textContent = `打开原文件失败：${error.message}`;
      }
    }

    function formatLineRange(start, end) {
      if (!start && !end) return '—';
      if (!end || start === end) return String(start).padStart(4, '0');
      return `${String(start).padStart(4, '0')}-${String(end).padStart(4, '0')}`;
    }

    function riskLabel(level) {
      return ({ high: '高风险', medium: '中风险', low: '低风险' }[level] || level || '未标注');
    }

    function applyFindingFilter(findings, filter) {
      if (filter === 'llm') {
        return findings.filter((item) => item.finding_origin === 'llm_added');
      }
      if (filter === 'rule') {
        return findings.filter((item) => item.finding_origin !== 'llm_added');
      }
      return findings;
    }

    function applyRuleFilter(candidates) {
      if (currentRuleFilter === 'all') return candidates;
      return candidates.filter((item) => item.decision === currentRuleFilter);
    }

    function decisionLabelText(decision) {
      return ({ pending: '待确认', confirmed: '已确认入库', deferred: '暂缓', ignored: '忽略' }[decision] || decision || '待确认');
    }

    function escapeHtml(text) {
      return String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }
  </script>
</body>
</html>"""
