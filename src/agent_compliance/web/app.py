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
        if path == "/review-next":
            self._send_html(_review_next_html())
            return
        if path == "/rules":
            self._send_html(_rules_html())
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
    .issues-summary-bar {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin-top: 6px;
    }
    .issues-stat {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 10px 12px;
      display: grid;
      gap: 4px;
    }
    .issues-stat-label {
      color: var(--muted);
      font-size: 12px;
    }
    .issues-stat-value {
      font-size: 20px;
      font-weight: 700;
      line-height: 1.1;
    }
    .issues-stat-value.high {
      color: var(--high);
    }
    .issues-stat-value.medium {
      color: var(--medium);
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
    .issue-item.high {
      border-left: 5px solid var(--high);
      background: linear-gradient(90deg, rgba(163, 61, 34, 0.05), #fff 14%);
    }
    .issue-item.medium {
      border-left: 5px solid var(--medium);
      background: linear-gradient(90deg, rgba(143, 103, 20, 0.05), #fff 14%);
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
    .issue-title-row {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      justify-content: space-between;
    }
    .issue-rank {
      min-width: 34px;
      height: 34px;
      border-radius: 10px;
      background: #f5ede2;
      color: var(--accent);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      flex: 0 0 auto;
    }
    .issue-rank.high {
      background: rgba(163, 61, 34, 0.12);
      color: var(--high);
    }
    .issue-rank.medium {
      background: rgba(143, 103, 20, 0.12);
      color: var(--medium);
    }
    .issue-main {
      display: grid;
      gap: 6px;
      min-width: 0;
      flex: 1 1 auto;
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
      background: #fffaf3;
      border-radius: 10px;
      padding: 9px 10px;
    }
    .issue-toggle-text {
      color: var(--muted);
      font-size: 12px;
    }
    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 12px;
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
      .issues-summary-bar,
      .detail-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <section class="hero">
      <h1>采购审查工作台</h1>
      <p>上传采购文件后，页面会渲染文件正文并生成审查问题清单。点击任意问题，右侧正文会自动定位到对应位置并高亮，方便快速复核。</p>
      <p><a href="/rules">打开规则管理页面</a></p>
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
    let latestDocument = null;
    let latestFindings = [];
    let currentFindingFilter = 'all';

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


    function renderIssues(findings) {
      const sortedFindings = sortFindings(findings);
      const filtered = applyFindingFilter(sortedFindings, currentFindingFilter);
      const llmCount = findings.filter((item) => item.finding_origin === 'llm_added').length;
      const ruleCount = findings.filter((item) => item.finding_origin !== 'llm_added').length;
      const highCount = findings.filter((item) => item.risk_level === 'high').length;
      const mediumCount = findings.filter((item) => item.risk_level === 'medium').length;
      issuesHeadNode.innerHTML = `
        <h2>审查问题清单</h2>
        <div class="meta">共 ${findings.length} 条问题，其中规则命中 ${ruleCount} 条、模型新增 ${llmCount} 条。清单已按风险等级排序，高风险优先显示。点击“定位正文”会跳到对应位置，点击“展开详情”可查看依据、判断和建议。</div>
        <div class="issues-summary-bar">
          <div class="issues-stat"><div class="issues-stat-label">高风险</div><div class="issues-stat-value high">${highCount}</div></div>
          <div class="issues-stat"><div class="issues-stat-label">中风险</div><div class="issues-stat-value medium">${mediumCount}</div></div>
          <div class="issues-stat"><div class="issues-stat-label">规则命中</div><div class="issues-stat-value">${ruleCount}</div></div>
          <div class="issues-stat"><div class="issues-stat-label">模型新增</div><div class="issues-stat-value">${llmCount}</div></div>
        </div>
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
      return `<article class="issue-item ${escapeHtml(finding.risk_level || '')}" data-finding-id="${escapeHtml(finding.finding_id)}">
        <button type="button" class="issue-summary">
          <div class="issue-top">
            <span>问题 ${index}</span>
            <span class="badge ${escapeHtml(finding.risk_level)}">${escapeHtml(riskLabel(finding.risk_level))}</span>
            <span class="badge">${escapeHtml(finding.issue_type)}</span>
            <span class="badge ${originClass}">${originLabel}</span>
          </div>
          <div class="issue-title-row">
            <div class="issue-rank ${escapeHtml(finding.risk_level || '')}">${String(index).padStart(2, '0')}</div>
            <div class="issue-main">
              <div class="issue-title">${escapeHtml(finding.problem_title)}</div>
              <div class="issue-meta">位置：${escapeHtml(finding.section_path || finding.source_section || '待补充')}</div>
              <div class="issue-meta">页码：${escapeHtml(finding.page_hint || '待人工翻页复核')} ｜ 行号：${escapeHtml(formatLineRange(finding.text_line_start, finding.text_line_end))}</div>
            </div>
          </div>
          <div class="issue-snippet">${escapeHtml(finding.source_text)}</div>
          <div class="issue-actions">
            <div class="issue-action-buttons">
              <button type="button" class="issue-mini-btn issue-locate-btn">定位正文</button>
              <button type="button" class="issue-mini-btn issue-toggle-btn"><span class="issue-toggle-text">展开详情</span></button>
            </div>
          </div>
        </button>
        <div class="issue-detail">
          <div class="detail-grid">
            <div class="detail-pair">
              <div class="detail-label">合规判断</div>
              <div class="detail-value">${escapeHtml(finding.compliance_judgment)}</div>
            </div>
            <div class="detail-pair">
              <div class="detail-label">来源</div>
              <div class="detail-value">${escapeHtml(originLabel)}</div>
            </div>
            <div class="detail-pair">
              <div class="detail-label">条款编号</div>
              <div class="detail-value">${escapeHtml(finding.clause_id || '待补充')}</div>
            </div>
            <div class="detail-pair">
              <div class="detail-label">表格/评分项</div>
              <div class="detail-value">${escapeHtml(finding.table_or_item_label || '—')}</div>
            </div>
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

    function sortFindings(findings) {
      const priority = { high: 0, medium: 1, low: 2, none: 3 };
      return [...findings].sort((left, right) => {
        const levelDiff = (priority[left.risk_level] ?? 9) - (priority[right.risk_level] ?? 9);
        if (levelDiff !== 0) return levelDiff;
        const lineDiff = (left.text_line_start || 0) - (right.text_line_start || 0);
        if (lineDiff !== 0) return lineDiff;
        return String(left.finding_id).localeCompare(String(right.finding_id));
      });
    }

    function escapeHtml(text) {
      return String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }
  </script>
</body>
</html>"""


def _review_next_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>审查工作台 V2</title>
  <style>
    :root {
      --bg: #f4efe7;
      --paper: #fffdf8;
      --ink: #1f1a17;
      --muted: #6c625b;
      --line: #d8cdc1;
      --accent: #9c5b2e;
      --accent-soft: #efe1d3;
      --high: #aa2e25;
      --high-soft: #f7ddd7;
      --medium: #9a6a14;
      --medium-soft: #f7ebcd;
      --rule: #275d8a;
      --rule-soft: #dbe8f5;
      --llm: #6e3ea4;
      --llm-soft: #ece0fa;
      --analyzer: #20644a;
      --analyzer-soft: #d9efe5;
      --doc-bg-top: #eef6ff;
      --doc-bg-bottom: #e3efff;
      --doc-border: #c9dbf4;
      --problem-ink: #a53026;
      --problem-bg: #fde8e4;
      --shadow: 0 18px 40px rgba(67, 45, 22, 0.08);
      --radius: 18px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "PingFang SC", "Noto Sans SC", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.85), transparent 34%),
        linear-gradient(180deg, #f7f2ea 0%, var(--bg) 100%);
      color: var(--ink);
    }
    .shell {
      max-width: 1500px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 18px;
      margin-bottom: 18px;
    }
    .hero-card, .panel {
      background: rgba(255,253,248,0.94);
      border: 1px solid rgba(216,205,193,0.92);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }
    .hero-card {
      padding: 22px 24px;
      overflow: hidden;
      position: relative;
    }
    .hero-card::after {
      content: "";
      position: absolute;
      inset: auto -60px -80px auto;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(156,91,46,0.18), rgba(156,91,46,0));
      pointer-events: none;
    }
    .eyebrow {
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 8px;
      font-weight: 700;
    }
    h1, h2, h3, p { margin: 0; }
    .hero-card h1 {
      font-size: 30px;
      line-height: 1.2;
      margin-bottom: 10px;
    }
    .hero-card p {
      color: var(--muted);
      line-height: 1.6;
      max-width: 760px;
    }
    .hero-actions {
      display: flex;
      gap: 12px;
      margin-top: 16px;
      flex-wrap: wrap;
    }
    .hero-actions a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 700;
    }
    .upload-card {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    form {
      display: grid;
      gap: 12px;
    }
    input[type="file"] {
      width: 100%;
      border: 1px dashed var(--line);
      background: #fff;
      border-radius: 14px;
      padding: 14px;
    }
    .switches {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .switch {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border-radius: 999px;
      background: #fff;
      border: 1px solid var(--line);
      font-size: 13px;
      color: var(--muted);
    }
    button {
      appearance: none;
      border: none;
      border-radius: 14px;
      padding: 12px 16px;
      background: linear-gradient(135deg, #b86a34, #8c4b22);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary {
      background: #fff;
      color: var(--accent);
      border: 1px solid var(--line);
    }
    .meta {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .metric {
      padding: 16px;
      border-radius: 16px;
      background: rgba(255,253,248,0.94);
      border: 1px solid rgba(216,205,193,0.92);
      box-shadow: var(--shadow);
    }
    .metric-label {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 10px;
    }
    .metric strong {
      display: block;
      font-size: 28px;
      line-height: 1;
    }
    .workspace {
      display: grid;
      grid-template-columns: 380px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }
    .panel { min-height: 720px; }
    .left-pane {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      position: sticky;
      top: 14px;
      align-self: start;
      max-height: calc(100vh - 28px);
    }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .toolbar button {
      padding: 8px 12px;
      border-radius: 999px;
      background: #fff;
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }
    .toolbar button.is-active {
      background: var(--accent-soft);
      color: var(--accent);
      border-color: rgba(156,91,46,0.28);
    }
    .issue-list {
      display: grid;
      gap: 10px;
      flex: 1 1 auto;
      min-height: 0;
      overflow: auto;
      padding-right: 4px;
    }
    .issue-group {
      display: grid;
      gap: 10px;
    }
    .issue-group-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 8px 10px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.76);
      border: 1px solid rgba(199, 214, 236, 0.92);
      position: sticky;
      top: 0;
      z-index: 1;
      backdrop-filter: blur(8px);
    }
    .issue-group-title {
      display: grid;
      gap: 2px;
    }
    .issue-group-title strong {
      font-size: 13px;
    }
    .issue-group-title span {
      color: var(--muted);
      font-size: 11px;
      line-height: 1.45;
    }
    .issue-group-count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 28px;
      height: 28px;
      padding: 0 8px;
      border-radius: 999px;
      background: #e9f2ff;
      color: #2f5f96;
      font-size: 12px;
      font-weight: 800;
      flex-shrink: 0;
    }
    .issue-card {
      border-radius: 16px;
      border: 1px solid var(--line);
      background: #fff;
      padding: 14px;
      cursor: pointer;
      transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
    }
    .issue-card:hover {
      transform: translateY(-1px);
      box-shadow: 0 10px 24px rgba(59, 38, 19, 0.08);
    }
    .issue-card.is-active {
      border-color: rgba(156,91,46,0.44);
      box-shadow: 0 12px 28px rgba(59, 38, 19, 0.12);
      background: #fffaf2;
    }
    .issue-card.high { border-left: 6px solid var(--high); }
    .issue-card.medium { border-left: 6px solid var(--medium); }
    .issue-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
      align-items: start;
    }
    .issue-title {
      font-size: 15px;
      line-height: 1.5;
      font-weight: 700;
    }
    .issue-excerpt {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
      margin-top: 8px;
    }
    .badge-row, .mini-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .badge, .mini-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 12px;
      font-weight: 700;
    }
    .badge.high { background: var(--high-soft); color: var(--high); }
    .badge.medium { background: var(--medium-soft); color: var(--medium); }
    .badge.main { background: var(--analyzer-soft); color: var(--analyzer); }
    .badge.origin-rule { background: var(--rule-soft); color: var(--rule); }
    .badge.origin-llm { background: var(--llm-soft); color: var(--llm); }
    .mini-pill {
      background: #f5efe8;
      color: var(--muted);
      font-weight: 600;
    }
    .detail-pane {
      display: grid;
      grid-template-rows: minmax(0, 4fr) auto auto;
      min-height: 780px;
      max-height: calc(100vh - 28px);
    }
    .detail-head, .detail-body, .document-pane {
      padding: 14px 16px;
    }
    .document-pane {
      border-bottom: 1px solid var(--line);
      min-height: 560px;
      background:
        linear-gradient(180deg, var(--doc-bg-top) 0%, var(--doc-bg-bottom) 100%);
    }
    .document-tools {
      display: grid;
      gap: 10px;
      padding: 12px 16px 0;
      background: linear-gradient(180deg, rgba(231, 242, 255, 0.92), rgba(231, 242, 255, 0.72));
      border-bottom: 1px solid rgba(167, 191, 222, 0.5);
    }
    .document-toolbar-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: space-between;
    }
    .document-toolbar-row .toolbar {
      gap: 8px;
    }
    .document-toolbar-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .document-mode-note {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .chapter-nav {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      padding-bottom: 4px;
    }
    .chapter-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      border: 1px solid rgba(126, 153, 186, 0.34);
      background: rgba(255, 255, 255, 0.78);
      color: #315476;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }
    .chapter-chip.is-active {
      background: #e2eefc;
      border-color: rgba(73, 120, 175, 0.44);
      color: #274c72;
      box-shadow: inset 0 0 0 1px rgba(73, 120, 175, 0.14);
    }
    .chapter-chip .count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      border-radius: 999px;
      background: rgba(73, 120, 175, 0.12);
      color: inherit;
      font-size: 11px;
      font-weight: 800;
    }
    .detail-head {
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      background: rgba(255,250,243,0.88);
      padding-top: 8px;
      padding-bottom: 8px;
    }
    .detail-body {
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 6px;
      background: #fffaf3;
      padding-top: 8px;
      padding-bottom: 10px;
    }
    .detail-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 6px;
    }
    .learning-card {
      border: 1px solid rgba(125, 156, 196, 0.25);
      background: rgba(242, 248, 255, 0.92);
      border-radius: 12px;
      padding: 10px 12px;
      display: grid;
      gap: 8px;
    }
    .learning-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }
    .learning-head strong {
      font-size: 12px;
      line-height: 1.4;
    }
    .learning-meta {
      color: var(--muted);
      font-size: 11px;
      line-height: 1.6;
    }
    .learning-section {
      display: grid;
      gap: 4px;
    }
    .learning-section h3 {
      margin: 0;
      font-size: 11px;
      color: var(--accent);
    }
    .learning-list {
      margin: 0;
      padding-left: 16px;
      font-size: 12px;
      line-height: 1.65;
    }
    .learning-list li + li {
      margin-top: 3px;
    }
    .detail-item {
      padding: 8px 10px;
      border-radius: 10px;
      background: #fff;
      border: 1px solid var(--line);
      font-size: 12px;
      line-height: 1.55;
    }
    .detail-item strong {
      display: block;
      margin-bottom: 3px;
      font-size: 10px;
      color: var(--muted);
      letter-spacing: 0.02em;
    }
    .document-pane {
      min-height: 0;
      overflow: auto;
      background: linear-gradient(180deg, var(--doc-bg-top) 0%, var(--doc-bg-bottom) 100%);
      scroll-behavior: smooth;
      padding: 18px 22px 24px;
    }
    .doc-layout {
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    .doc-outline {
      position: sticky;
      top: 10px;
      align-self: start;
      display: grid;
      gap: 8px;
      padding: 10px;
      border-radius: 14px;
      background: rgba(236, 245, 255, 0.92);
      border: 1px solid rgba(168, 193, 224, 0.52);
      box-shadow: 0 8px 18px rgba(53, 91, 136, 0.08);
    }
    .doc-outline-title {
      color: #35587d;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }
    .doc-outline button {
      width: 100%;
      text-align: left;
      border-radius: 12px;
      border: 1px solid rgba(140, 169, 203, 0.3);
      background: rgba(255, 255, 255, 0.88);
      color: #35587d;
      padding: 8px 10px;
      font-size: 12px;
      font-weight: 700;
      line-height: 1.45;
      cursor: pointer;
    }
    .doc-outline button.is-active {
      background: #dfeeff;
      border-color: rgba(73, 120, 175, 0.42);
      color: #254a72;
    }
    .doc-outline button .count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 18px;
      height: 18px;
      margin-left: 6px;
      padding: 0 5px;
      border-radius: 999px;
      background: rgba(73, 120, 175, 0.12);
      font-size: 11px;
      font-weight: 800;
    }
    .doc-block {
      border: 0;
      background: transparent;
      border-radius: 0;
      padding: 0;
      margin: 0;
    }
    .doc-block.chapter-anchor {
      margin: 18px 0 8px;
      padding-top: 10px;
      border-top: 1px solid rgba(124, 168, 223, 0.28);
      background: transparent;
    }
    .chapter-anchor-title {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: #36587c;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }
    .doc-block p {
      margin: 0;
      line-height: 2.02;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 15px;
    }
    .doc-block table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      background: rgba(255,255,255,0.78);
      margin: 6px 0 14px;
    }
    .doc-block td {
      border: 1px solid rgba(178, 199, 225, 0.42);
      padding: 9px 10px;
      vertical-align: top;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.78;
      font-size: 14px;
    }
    .doc-block.is-target {
      background: linear-gradient(90deg, rgba(124,168,223,0.08), rgba(124,168,223,0.02) 45%, rgba(124,168,223,0));
    }
    .doc-block.is-target .problem-fragment {
      color: var(--problem-ink);
      background: linear-gradient(180deg, rgba(253,232,228,0.92), rgba(253,232,228,0.7));
      border-radius: 8px;
      padding: 6px 8px;
      border-left: 4px solid rgba(165,48,38,0.4);
    }
    .doc-block.is-target .problem-fragment table {
      background: transparent;
    }
    .doc-block.is-target .problem-fragment td {
      color: var(--problem-ink);
      background: rgba(253,232,228,0.52);
      border-color: rgba(165,48,38,0.22);
    }
    .doc-line {
      display: grid;
      grid-template-columns: 72px 1fr;
      gap: 12px;
      align-items: start;
      padding: 8px 0;
      border-top: 1px dashed rgba(216,205,193,0.45);
      font-size: 15px;
      line-height: 1.8;
    }
    .doc-line:first-child { border-top: none; }
    .doc-line.target {
      background: linear-gradient(90deg, rgba(124,168,223,0.22), rgba(124,168,223,0));
      border-radius: 10px;
      padding-left: 8px;
      padding-right: 8px;
    }
    .doc-line.target .problem-text {
      color: var(--problem-ink);
      background: var(--problem-bg);
      border-radius: 8px;
      padding: 4px 8px;
      display: inline-block;
      border: 1px solid rgba(165,48,38,0.18);
    }
    .line-no {
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }
    .doc-reading-surface {
      background: rgba(255, 255, 255, 0.86);
      border: 1px solid rgba(176, 198, 224, 0.38);
      border-radius: 18px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
      padding: 10px 16px 18px;
    }
    .context-toggle.is-hidden {
      display: none;
    }
    #detail-title {
      font-size: 14px;
      line-height: 1.4;
      margin-right: auto;
    }
    #detail-excerpt {
      font-size: 10px;
      line-height: 1.5;
      display: none;
    }
    #detail-badges {
      justify-content: flex-end;
    }
    .badge.compact {
      padding: 4px 8px;
      font-size: 11px;
    }
    .empty {
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 16px;
      padding: 20px;
      text-align: center;
      background: rgba(255,255,255,0.62);
    }
    @media (max-width: 1180px) {
      .hero, .workspace, .summary-grid, .detail-grid { grid-template-columns: 1fr; }
      .left-pane {
        position: static;
        max-height: none;
      }
      .detail-pane {
        max-height: none;
        min-height: 0;
      }
      .issue-list { max-height: none; }
      .document-pane { min-height: 360px; }
      .doc-layout {
        grid-template-columns: 1fr;
      }
      .doc-outline {
        position: static;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-card">
        <div class="eyebrow">Gov Compliance Review</div>
        <h1>审查工作台 V2</h1>
        <p>这是一页专门用来看“主问题化、章节化、仲裁化”升级效果的新页面。它会优先展示章节级主问题、来源链路和仲裁收束效果，而不是只展示扁平 findings 列表。</p>
        <div class="hero-actions">
          <a href="/">旧版审查页</a>
          <a href="/rules">规则管理页</a>
        </div>
      </div>
      <div class="hero-card upload-card">
        <div>
          <div class="eyebrow">Run Review</div>
          <h2>上传文件并验证新链路</h2>
        </div>
        <form id="review-form">
          <input id="file-input" type="file" name="file" accept=".docx,.pdf,.txt" required />
          <div class="switches">
            <label class="switch"><input type="checkbox" name="use_llm" checked /> 启用本地模型</label>
            <label class="switch"><input type="checkbox" name="use_cache" /> 启用缓存</label>
          </div>
          <div class="switches">
            <button type="submit">开始审查</button>
            <button type="button" class="secondary" id="open-source-btn" disabled>打开原文件</button>
          </div>
        </form>
        <div id="run-meta" class="meta">上传后会同时返回文档原文、主问题视图、明细视图和来源链路信息。</div>
      </div>
    </section>

    <section id="summary-grid" class="summary-grid">
      <div class="metric"><div class="metric-label">当前状态</div><strong>待运行</strong></div>
      <div class="metric"><div class="metric-label">主问题</div><strong>0</strong></div>
      <div class="metric"><div class="metric-label">保留明细</div><strong>0</strong></div>
      <div class="metric"><div class="metric-label">模型新增</div><strong>0</strong></div>
      <div class="metric"><div class="metric-label">高风险</div><strong>0</strong></div>
      <div class="metric"><div class="metric-label">中风险</div><strong>0</strong></div>
    </section>

    <section class="workspace">
      <aside class="panel left-pane">
        <div>
          <div class="eyebrow">Issue Navigator</div>
          <h2>问题清单</h2>
          <p class="meta">默认优先看章节级主问题。切换视图后，可以对照明细问题和模型新增问题。</p>
        </div>
        <div class="toolbar" id="view-toolbar">
          <button type="button" data-view="main" class="is-active">主问题视图</button>
          <button type="button" data-view="all">全部问题</button>
          <button type="button" data-view="llm">模型新增</button>
        </div>
        <div class="toolbar" id="risk-toolbar">
          <button type="button" data-risk="all" class="is-active">全部风险</button>
          <button type="button" data-risk="high">高风险</button>
          <button type="button" data-risk="medium">中风险</button>
        </div>
        <div id="issue-list" class="issue-list">
          <div class="empty">上传文件后，这里会优先显示章节级主问题。</div>
        </div>
      </aside>

      <section class="panel detail-pane">
        <div class="document-tools">
          <div class="document-toolbar-row">
            <div class="document-toolbar-actions">
              <div class="toolbar" id="document-mode-toolbar">
                <button type="button" data-document-mode="context" class="is-active">附近上下文</button>
                <button type="button" data-document-mode="chapter">查看整章</button>
              </div>
              <button type="button" id="context-toggle" class="secondary context-toggle is-hidden">展开更多上下文</button>
            </div>
            <div id="document-mode-note" class="document-mode-note">默认只看当前问题附近上下文，方便快速定位和比对。</div>
          </div>
          <div id="chapter-nav" class="chapter-nav"></div>
        </div>
        <div id="document-pane" class="document-pane">
          <div class="empty">上传文件后，这里会渲染文档原文，并跟随问题卡片定位到对应位置。</div>
        </div>
        <div class="detail-head">
          <div class="eyebrow">Focused Review</div>
          <h2 id="detail-title">尚未选择问题</h2>
          <div id="detail-badges" class="badge-row"></div>
          <p id="detail-excerpt" class="meta">这里只保留当前问题的风险描述和建议改写，避免和左侧清单重复。</p>
        </div>
        <div class="detail-body">
          <div id="detail-grid" class="detail-grid">
            <div class="detail-item"><strong>风险说明</strong><div>待运行</div></div>
            <div class="detail-item"><strong>建议改写</strong><div>待运行</div></div>
          </div>
          <div id="learning-card" class="learning-card">
            <div class="learning-head">
              <strong>Difference Learning</strong>
              <span class="badge compact">待运行</span>
            </div>
            <div class="learning-meta">启用本地模型后，这里会显示本轮自动沉淀的规则、主题分析器、LLM prompt 和 benchmark 优化建议。</div>
          </div>
        </div>
      </section>
    </section>
  </div>

  <script>
    const state = {
      payload: null,
      findings: [],
      filtered: [],
      selectedFindingId: null,
      viewMode: 'main',
      riskMode: 'all',
      sectionMode: 'all',
      documentMode: 'context',
      activeChapterKey: 'all',
      contextExpanded: false,
    };

    const form = document.getElementById('review-form');
    const openSourceBtn = document.getElementById('open-source-btn');
    const runMetaNode = document.getElementById('run-meta');
    const summaryGridNode = document.getElementById('summary-grid');
    const issueListNode = document.getElementById('issue-list');
    const detailTitleNode = document.getElementById('detail-title');
    const detailBadgesNode = document.getElementById('detail-badges');
    const detailExcerptNode = document.getElementById('detail-excerpt');
    const detailGridNode = document.getElementById('detail-grid');
    const documentPaneNode = document.getElementById('document-pane');
    const learningCardNode = document.getElementById('learning-card');
    const chapterNavNode = document.getElementById('chapter-nav');
    const documentModeNoteNode = document.getElementById('document-mode-note');
    const contextToggleNode = document.getElementById('context-toggle');

    form.addEventListener('submit', submitReview);
    openSourceBtn.addEventListener('click', openSourceFile);
    document.getElementById('view-toolbar').querySelectorAll('[data-view]').forEach((node) => {
      node.addEventListener('click', () => {
        state.viewMode = node.dataset.view;
        render();
      });
    });
    document.getElementById('risk-toolbar').querySelectorAll('[data-risk]').forEach((node) => {
      node.addEventListener('click', () => {
        state.riskMode = node.dataset.risk;
        render();
      });
    });
    document.getElementById('document-mode-toolbar').querySelectorAll('[data-document-mode]').forEach((node) => {
      node.addEventListener('click', () => {
        state.documentMode = node.dataset.documentMode;
        if (state.documentMode !== 'context') {
          state.contextExpanded = false;
        }
        renderDocumentModeState();
        renderDocument();
      });
    });
    contextToggleNode.addEventListener('click', () => {
      state.contextExpanded = !state.contextExpanded;
      renderDocumentModeState();
      renderDocument();
    });
    const sectionToolbarNode = document.createElement('div');
    sectionToolbarNode.className = 'toolbar';
    sectionToolbarNode.id = 'section-toolbar';
    sectionToolbarNode.innerHTML = `
      <button type="button" data-section="all" class="is-active">全部章节</button>
      <button type="button" data-section="qualification">资格</button>
      <button type="button" data-section="scoring">评分</button>
      <button type="button" data-section="technical">技术</button>
      <button type="button" data-section="commercial">商务/验收</button>
    `;
    document.querySelector('.left-pane').insertBefore(sectionToolbarNode, issueListNode);
    sectionToolbarNode.querySelectorAll('[data-section]').forEach((node) => {
      node.addEventListener('click', () => {
        state.sectionMode = node.dataset.section;
        render();
      });
    });

    async function submitReview(event) {
      event.preventDefault();
      const formData = new FormData(form);
      runMetaNode.textContent = '正在执行审查，请稍候...';
      issueListNode.innerHTML = '<div class="empty">正在生成主问题视图...</div>';
      try {
        const response = await fetch('/api/review', { method: 'POST', body: formData });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || '审查失败');
        }
        state.payload = payload;
        state.findings = payload.review.findings || [];
        state.selectedFindingId = null;
        state.activeChapterKey = 'all';
        state.documentMode = 'context';
        state.contextExpanded = false;
        openSourceBtn.disabled = !payload.document || !payload.document.source_path;
        runMetaNode.textContent = `已完成审查：${payload.review.document_name}；缓存 ${payload.cache.used ? '命中' : '未命中'}；本地模型 ${payload.llm.enabled ? '已启用' : '未启用'}。`;
        render();
      } catch (error) {
        runMetaNode.textContent = `审查失败：${error.message}`;
        issueListNode.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
      }
    }

    async function openSourceFile() {
      const sourcePath = state.payload && state.payload.document ? state.payload.document.source_path : '';
      if (!sourcePath) return;
      await fetch('/api/open-source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: sourcePath }),
      });
    }

    function render() {
      renderToolbarState();
      renderSummary();
      renderIssues();
      renderDetail();
      renderDocument();
    }

    function renderToolbarState() {
      document.querySelectorAll('#view-toolbar [data-view]').forEach((node) => {
        node.classList.toggle('is-active', node.dataset.view === state.viewMode);
      });
      document.querySelectorAll('#risk-toolbar [data-risk]').forEach((node) => {
        node.classList.toggle('is-active', node.dataset.risk === state.riskMode);
      });
      document.querySelectorAll('#section-toolbar [data-section]').forEach((node) => {
        node.classList.toggle('is-active', node.dataset.section === state.sectionMode);
      });
      renderDocumentModeState();
    }

    function renderDocumentModeState() {
      document.querySelectorAll('#document-mode-toolbar [data-document-mode]').forEach((node) => {
        node.classList.toggle('is-active', node.dataset.documentMode === state.documentMode);
      });
      documentModeNoteNode.textContent = state.documentMode === 'chapter'
        ? '当前显示选中问题所在章节的连续正文，适合整体判断本章条款结构。'
        : (state.contextExpanded
          ? '当前显示扩展后的上下文，适合在定位后继续比对前后条款。'
          : '当前仅显示选中问题附近少量上下文，适合快速定位和核对风险点。');
      contextToggleNode.classList.toggle('is-hidden', state.documentMode !== 'context');
      contextToggleNode.textContent = state.contextExpanded ? '收起上下文' : '展开更多上下文';
    }

    function renderSummary() {
      const findings = state.findings;
      const metrics = summarizeFindings(findings);
      const sectionMetrics = summarizeBySection(findings);
      summaryGridNode.innerHTML = `
        ${renderMetric('当前状态', state.payload ? '已完成' : '待运行')}
        ${renderMetric('主问题', metrics.main)}
        ${renderMetric('保留明细', metrics.detail)}
        ${renderMetric('模型新增', metrics.llm)}
        ${renderMetric('高风险', metrics.high)}
        ${renderMetric('中风险', metrics.medium)}
        ${renderMetric('资格主问题', sectionMetrics.qualification)}
        ${renderMetric('评分主问题', sectionMetrics.scoring)}
        ${renderMetric('技术主问题', sectionMetrics.technical)}
        ${renderMetric('商务/验收主问题', sectionMetrics.commercial)}
      `;
    }

    function renderMetric(label, value) {
      return `<div class="metric"><div class="metric-label">${escapeHtml(label)}</div><strong>${escapeHtml(String(value))}</strong></div>`;
    }

    function summarizeFindings(findings) {
      return {
        main: findings.filter(isMainIssue).length,
        detail: findings.filter((item) => !isMainIssue(item)).length,
        llm: findings.filter((item) => item.finding_origin === 'llm_added').length,
        high: findings.filter((item) => item.risk_level === 'high').length,
        medium: findings.filter((item) => item.risk_level === 'medium').length,
      };
    }

    function summarizeBySection(findings) {
      const mainFindings = findings.filter(isMainIssue);
      return {
        qualification: mainFindings.filter((item) => classifySection(item) === 'qualification').length,
        scoring: mainFindings.filter((item) => classifySection(item) === 'scoring').length,
        technical: mainFindings.filter((item) => classifySection(item) === 'technical').length,
        commercial: mainFindings.filter((item) => classifySection(item) === 'commercial').length,
      };
    }

    function applyFilters(findings) {
      let items = findings.slice();
      if (state.viewMode === 'main') {
        items = items.filter(isMainIssue);
      } else if (state.viewMode === 'llm') {
        items = items.filter((item) => item.finding_origin === 'llm_added');
      }
      if (state.riskMode !== 'all') {
        items = items.filter((item) => item.risk_level === state.riskMode);
      }
      if (state.sectionMode !== 'all') {
        items = items.filter((item) => classifySection(item) === state.sectionMode);
      }
      return items;
    }

    function renderIssues() {
      const filtered = applyFilters(state.findings);
      state.filtered = filtered;
      if (!state.selectedFindingId && filtered.length) {
        state.selectedFindingId = filtered[0].finding_id;
      }
      if (!filtered.some((item) => item.finding_id === state.selectedFindingId) && filtered.length) {
        state.selectedFindingId = filtered[0].finding_id;
      }
      if (!filtered.length) {
        issueListNode.innerHTML = '<div class="empty">当前筛选条件下没有问题。</div>';
        return;
      }
      issueListNode.innerHTML = renderIssueGroups(filtered);
      issueListNode.querySelectorAll('.issue-card').forEach((node) => {
        node.addEventListener('click', () => {
          state.selectedFindingId = node.dataset.findingId;
          const finding = state.findings.find((item) => item.finding_id === state.selectedFindingId);
          state.activeChapterKey = finding ? chapterKeyForFinding(finding) : state.activeChapterKey;
          state.contextExpanded = false;
          renderIssues();
          renderDetail();
          renderDocument();
        });
      });
    }

    function renderIssueGroups(findings) {
      const sectionOrder = ['qualification', 'scoring', 'technical', 'commercial'];
      const grouped = new Map(sectionOrder.map((section) => [section, []]));
      findings.forEach((finding) => {
        const section = classifySection(finding);
        if (!grouped.has(section)) grouped.set(section, []);
        grouped.get(section).push(finding);
      });
      return Array.from(grouped.entries())
        .filter(([, items]) => items.length)
        .map(([section, items]) => `
          <section class="issue-group">
            <div class="issue-group-head">
              <div class="issue-group-title">
                <strong>${escapeHtml(sectionLabelFromKey(section))}</strong>
                <span>${escapeHtml(sectionDescription(section))}</span>
              </div>
              <span class="issue-group-count">${escapeHtml(String(items.length))}</span>
            </div>
            ${items.map(renderIssueCard).join('')}
          </section>
        `)
        .join('');
    }

    function renderIssueCard(finding) {
      const active = finding.finding_id === state.selectedFindingId;
      const badges = [
        `<span class="badge ${escapeHtml(finding.risk_level)}">${riskLabel(finding.risk_level)}</span>`,
        isMainIssue(finding) ? '<span class="badge main">章节主问题</span>' : '',
        `<span class="badge">${escapeHtml(sectionLabel(finding))}</span>`,
        `<span class="badge">${escapeHtml(subthemeLabel(finding))}</span>`,
        `<span class="badge ${originBadgeClass(finding)}">${escapeHtml(originLabel(finding))}</span>`,
      ].join('');
      return `
        <article class="issue-card ${escapeHtml(finding.risk_level)} ${active ? 'is-active' : ''}" data-finding-id="${escapeHtml(finding.finding_id)}">
          <div class="issue-head">
            <div class="issue-title">${escapeHtml(finding.problem_title)}</div>
          </div>
          <div class="badge-row">${badges}</div>
          <div class="mini-meta" style="margin-top:10px;">
            <span class="mini-pill">位置 ${escapeHtml(compactLocation(finding))}</span>
            <span class="mini-pill">来源 ${escapeHtml(sourceChain(finding))}</span>
          </div>
          <div class="issue-excerpt"><strong>代表性证据：</strong>${escapeHtml(finding.source_text || '无原文摘录')}</div>
        </article>
      `;
    }

    function renderDetail() {
      const finding = state.filtered.find((item) => item.finding_id === state.selectedFindingId) || state.findings.find((item) => item.finding_id === state.selectedFindingId);
      if (!finding) {
        detailTitleNode.textContent = '尚未选择问题';
        detailBadgesNode.innerHTML = '';
        detailExcerptNode.textContent = '这里只保留当前问题的风险描述和建议改写，避免和左侧清单重复。';
        detailGridNode.innerHTML = '<div class="detail-item"><strong>状态</strong><div>暂无内容</div></div>';
        renderDifferenceLearning();
        return;
      }
      detailTitleNode.textContent = finding.problem_title;
      detailBadgesNode.innerHTML = `
        <span class="badge compact ${escapeHtml(finding.risk_level)}">${riskLabel(finding.risk_level)}</span>
        ${isMainIssue(finding) ? '<span class="badge compact main">章节主问题</span>' : ''}
        <span class="badge compact">${escapeHtml(sectionLabel(finding))}</span>
        <span class="badge compact">${escapeHtml(subthemeLabel(finding))}</span>
        <span class="badge compact ${originBadgeClass(finding)}">${escapeHtml(originLabel(finding))}</span>
      `;
      detailExcerptNode.textContent = '';
      detailGridNode.innerHTML = `
        <div class="detail-item"><strong>代表性证据</strong><div>${escapeHtml(finding.source_text || '暂无')}</div></div>
        <div class="detail-item"><strong>风险说明</strong><div>${escapeHtml(finding.why_it_is_risky || '暂无')}</div></div>
        <div class="detail-item"><strong>建议改写</strong><div>${escapeHtml(finding.rewrite_suggestion || '暂无')}</div></div>
      `;
      renderDifferenceLearning(finding);
    }

    function renderDocument() {
      const documentPayload = state.payload ? state.payload.document : null;
      if (!documentPayload) {
        documentPaneNode.innerHTML = '<div class="empty">上传文件后，这里会渲染文档原文，并联动定位。</div>';
        chapterNavNode.innerHTML = '';
        return;
      }
      const finding = state.filtered.find((item) => item.finding_id === state.selectedFindingId) || state.findings.find((item) => item.finding_id === state.selectedFindingId);
      const start = finding ? finding.text_line_start : -1;
      const end = finding ? finding.text_line_end : -1;
      const chapterKey = finding ? chapterKeyForFinding(finding) : 'all';
      if (!state.activeChapterKey || state.activeChapterKey === 'all') {
        state.activeChapterKey = chapterKey;
      }
      const chapterNav = buildChapterNav(documentPayload, state.findings);
      chapterNavNode.innerHTML = chapterNav.map((item) => `
        <button type="button" class="chapter-chip ${item.key === effectiveChapterKey(chapterKey) ? 'is-active' : ''}" data-chapter-key="${escapeHtml(item.key)}">
          <span>${escapeHtml(item.label)}</span>
          <span class="count">${escapeHtml(String(item.count))}</span>
        </button>
      `).join('');
      chapterNavNode.querySelectorAll('[data-chapter-key]').forEach((node) => {
        node.addEventListener('click', () => {
          state.activeChapterKey = node.dataset.chapterKey;
          state.documentMode = 'chapter';
          renderDocumentModeState();
          renderDocument();
        });
      });
      const blocks = buildVisibleBlocks(documentPayload, finding, effectiveChapterKey(chapterKey));
      const outlineItems = chapterNav.map((item) => `
        <button type="button" class="${item.key === effectiveChapterKey(chapterKey) ? 'is-active' : ''}" data-outline-key="${escapeHtml(item.key)}">
          <span>${escapeHtml(item.label)}</span><span class="count">${escapeHtml(String(item.count))}</span>
        </button>
      `).join('');
      documentPaneNode.innerHTML = blocks.length
        ? `<div class="doc-layout"><aside class="doc-outline"><div class="doc-outline-title">章节目录</div>${outlineItems}</aside><div class="doc-reading-surface">${blocks.map((block, index) => renderBlock(block, index, start, end)).join('')}</div></div>`
        : '<div class="empty">当前章节暂无可展示正文。</div>';
      documentPaneNode.querySelectorAll('[data-outline-key]').forEach((node) => {
        node.addEventListener('click', () => {
          state.activeChapterKey = node.dataset.outlineKey;
          state.documentMode = 'chapter';
          state.contextExpanded = false;
          renderDocumentModeState();
          renderDocument();
        });
      });
      if (finding) {
        const node = documentPaneNode.querySelector('[data-target-block="true"]') || documentPaneNode.querySelector('.doc-line.target');
        if (node) scrollDocumentPaneToNode(node);
      }
    }

    function effectiveChapterKey(findingChapterKey) {
      if (state.documentMode === 'context') return findingChapterKey || state.activeChapterKey || 'all';
      return state.activeChapterKey && state.activeChapterKey !== 'all'
        ? state.activeChapterKey
        : (findingChapterKey || 'all');
    }

    function buildVisibleBlocks(documentPayload, finding, chapterKey) {
      const hasBlocks = documentPayload.blocks && documentPayload.blocks.length;
      const blocks = hasBlocks ? documentPayload.blocks.slice() : [{ kind: 'text', lines: documentPayload.lines || [], start_line: 1, end_line: documentPayload.line_count || 1 }];
      const normalizedBlocks = addChapterAnchors(blocks);
      if (!finding) return normalizedBlocks;
      if (state.documentMode === 'chapter') {
        return normalizedBlocks.filter((block) => block.chapter_key === chapterKey || block.kind === 'chapter-anchor' && block.chapter_key === chapterKey);
      }
      const targetIndex = normalizedBlocks.findIndex((block) => block.kind !== 'chapter-anchor' && blockIntersectsFinding(block, finding));
      if (targetIndex === -1) return normalizedBlocks.filter((block) => block.chapter_key === chapterKey);
      const keep = new Set();
      const radius = state.contextExpanded ? 3 : 1;
      for (let index = Math.max(0, targetIndex - radius); index <= Math.min(normalizedBlocks.length - 1, targetIndex + radius); index += 1) {
        keep.add(index);
      }
      for (let index = targetIndex; index >= 0; index -= 1) {
        if (normalizedBlocks[index].kind === 'chapter-anchor') {
          keep.add(index);
          break;
        }
      }
      return normalizedBlocks.filter((_, index) => keep.has(index));
    }

    function addChapterAnchors(blocks) {
      const output = [];
      let currentChapterKey = 'all';
      let currentChapterLabel = '文档正文';
      blocks.forEach((block, index) => {
        const detected = detectChapterForBlock(block, index);
        if (detected && detected.key !== currentChapterKey) {
          currentChapterKey = detected.key;
          currentChapterLabel = detected.label;
          output.push({
            kind: 'chapter-anchor',
            block_id: `anchor-${index}-${detected.key}`,
            chapter_key: currentChapterKey,
            chapter_label: currentChapterLabel,
            start_line: block.start_line,
            end_line: block.start_line,
            html: `<div class="chapter-anchor-title">${escapeHtml(currentChapterLabel)}</div>`,
          });
        }
        output.push({ ...block, chapter_key: currentChapterKey, chapter_label: currentChapterLabel });
      });
      return output;
    }

    function detectChapterForBlock(block, index) {
      const text = blockText(block);
      if (/第一章\s*招标公告|申请人的资格要求/.test(text)) return { key: 'qualification', label: '资格条件' };
      if (/评标信息|评审因素|评分项|样品|产品设计方案|技术保障措施/.test(text)) return { key: 'scoring', label: '评分标准' };
      if (/第三章\s*用户需求书-四、技术要求|四、技术要求|技术要求/.test(text)) return { key: 'technical', label: '技术要求' };
      if (/五、商务要求|履约担保|付款方式|安装、调试和验收|关于违约|关于安全/.test(text)) return { key: 'commercial', label: '商务与验收' };
      if (index === 0) return { key: 'qualification', label: '资格条件' };
      return null;
    }

    function buildChapterNav(documentPayload, findings) {
      const counts = { qualification: 0, scoring: 0, technical: 0, commercial: 0 };
      findings.forEach((finding) => {
        counts[chapterKeyForFinding(finding)] = (counts[chapterKeyForFinding(finding)] || 0) + 1;
      });
      const detected = new Set(['qualification', 'scoring', 'technical', 'commercial']);
      return Array.from(detected).map((key) => ({
        key,
        label: sectionLabelFromKey(key),
        count: counts[key] || 0,
      }));
    }

    function chapterKeyForFinding(finding) {
      return classifySection(finding);
    }

    function blockIntersectsFinding(block, finding) {
      const start = Number(block.start_line || 0);
      const end = Number(block.end_line || start);
      return start <= finding.text_line_end && end >= finding.text_line_start;
    }

    function blockText(block) {
      if (block.html) {
        return String(block.html).replace(/<[^>]+>/g, ' ');
      }
      const blockLines = block.lines || [];
      return blockLines.map((line) => line.text || '').join(' ');
    }

    function renderBlock(block, index, start, end) {
      if (block.kind === 'chapter-anchor') {
        return `
          <section class="doc-block chapter-anchor" data-target-block="false" data-start-line="${block.start_line}" data-end-line="${block.end_line}">
            ${block.html}
          </section>
        `;
      }
      const blockLines = block.lines || [];
      const blockStart = Number(block.start_line || (blockLines[0] ? blockLines[0].number : 0));
      const blockEnd = Number(block.end_line || (blockLines.length ? blockLines[blockLines.length - 1].number : 0));
      const hasTarget = blockLines.length
        ? blockLines.some((line) => line.number >= start && line.number <= end)
        : (blockStart <= end && blockEnd >= start);
      const content = block.html
        ? `<div class="${hasTarget ? 'problem-fragment' : ''}">${block.html}</div>${hasTarget ? `<div class="mini-meta" style="margin-top:8px;"><span class="mini-pill">行 ${escapeHtml(String(blockStart))}-${escapeHtml(String(blockEnd))}</span></div>` : ''}`
        : (blockLines || []).map((line) => renderLine(line, start, end)).join('');
      return `
        <section class="doc-block ${hasTarget ? 'is-target' : ''}" data-target-block="${hasTarget ? 'true' : 'false'}" data-start-line="${blockStart}" data-end-line="${blockEnd}">
          ${content}
        </section>
      `;
    }

    function renderLine(line, start, end) {
      const target = line.number >= start && line.number <= end;
      return `
        <div class="doc-line ${target ? 'target' : ''}">
          <div class="line-no">L${escapeHtml(String(line.number))}</div>
          <div>${target ? `<span class="problem-text">${escapeHtml(line.text || '')}</span>` : escapeHtml(line.text || '')}</div>
        </div>
      `;
    }

    function scrollDocumentPaneToNode(node) {
      const paneRect = documentPaneNode.getBoundingClientRect();
      const nodeRect = node.getBoundingClientRect();
      const offset = nodeRect.top - paneRect.top + documentPaneNode.scrollTop - 80;
      documentPaneNode.scrollTo({ top: Math.max(offset, 0), behavior: 'smooth' });
    }

    function isMainIssue(finding) {
      return finding.finding_origin === 'analyzer' || (finding.finding_origin === 'llm_added' && /章节|主问题/.test(finding.problem_title || ''));
    }

    function originLabel(finding) {
      if (finding.finding_origin === 'llm_added') return '全文辅助扫描';
      if (finding.finding_origin === 'analyzer') return '结构分析 / 仲裁保留';
      return '规则命中';
    }

    function originBadgeClass(finding) {
      if (finding.finding_origin === 'llm_added') return 'origin-llm';
      if (finding.finding_origin === 'analyzer') return 'main';
      return 'origin-rule';
    }

    function sourceChain(finding) {
      if (finding.finding_origin === 'analyzer') return '规则命中 → 结构分析 → 仲裁保留';
      if (finding.finding_origin === 'llm_added') return '全文辅助扫描 → 仲裁判断';
      return '规则命中';
    }

    function classifySection(finding) {
      const text = [finding.problem_title, finding.section_path, finding.source_section].filter(Boolean).join(' ');
      if (/资格|申请人的资格要求|准入门槛/.test(text)) return 'qualification';
      if (/评分|评标信息|演示|品牌档次|认证评分|商务评分/.test(text)) return 'scoring';
      if (/技术|标准|检测报告|证明材料/.test(text)) return 'technical';
      return 'commercial';
    }

    function sectionLabel(finding) {
      return sectionLabelFromKey(classifySection(finding));
    }

    function sectionLabelFromKey(sectionKey) {
      const mapping = {
        qualification: '资格',
        scoring: '评分',
        technical: '技术',
        commercial: '商务/验收',
      };
      return mapping[sectionKey] || '其它';
    }

    function sectionDescription(sectionKey) {
      const mapping = {
        qualification: '一般门槛、属地场所、经营年限和错位资质会优先归并在这里。',
        scoring: '品牌、认证、演示和主观评分等结构性问题会集中展示。',
        technical: '标准错位、证明形式和技术必要性边界问题会集中展示。',
        commercial: '资金占用、验收费转嫁、责任失衡和验收边界问题会集中展示。',
      };
      return mapping[sectionKey] || '当前筛选条件下的问题会按章节归在这里。';
    }

    function subthemeLabel(finding) {
      const title = finding.problem_title || '';
      if (/一般财务和规模/.test(title)) return '财务/规模';
      if (/经营年限|属地场所|单项业绩/.test(title)) return '年限/场所/业绩';
      if (/行业资质|专门许可/.test(title)) return '错位资质';
      if (/品牌档次/.test(title)) return '品牌评分';
      if (/认证评分/.test(title)) return '错位认证';
      if (/证书认证或模板内容/.test(title)) return '评分错位';
      if (/标准或规范/.test(title)) return '标准错位';
      if (/证明材料形式/.test(title)) return '证明形式';
      if (/资金占用/.test(title)) return '资金占用';
      if (/交货期限/.test(title)) return '交期异常';
      if (/费用整体转嫁/.test(title)) return '验收费转嫁';
      if (/责任和违约后果/.test(title)) return '责任失衡';
      if (/验收程序|最终确认边界/.test(title)) return '验收边界';
      if (/属地倾斜/.test(title)) return '属地倾斜';
      if (/模板残留|义务外扩/.test(title)) return '模板残留';
      if (/行业适配性不足/.test(title)) return '行业适配';
      return finding.issue_type || '综合';
    }

    function riskLabel(level) {
      if (level === 'high') return '高风险';
      if (level === 'medium') return '中风险';
      return level || '未知';
    }

    function compactLocation(finding) {
      const section = finding.section_path || finding.source_section || '未定位章节';
      return `${section} / L${finding.text_line_start}`;
    }

    function renderDifferenceLearning(finding = null) {
      const learning = state.payload && state.payload.llm_review ? state.payload.llm_review.difference_learning : null;
      if (!learning || learning.status === 'llm_disabled') {
        learningCardNode.innerHTML = `
          <div class="learning-head">
            <strong>Difference Learning</strong>
            <span class="badge compact">未启用</span>
          </div>
          <div class="learning-meta">启用本地模型后，这里会显示本轮自动沉淀的规则、主题分析器、LLM prompt 和 benchmark 优化建议。</div>
        `;
        return;
      }
      const suggestions = learning.suggestions || {};
      const relatedIssueType = finding ? finding.issue_type : '';
      const badgeText = learning.added_finding_count ? `新增问题 ${learning.added_finding_count}` : '无新增问题';
      learningCardNode.innerHTML = `
        <div class="learning-head">
          <strong>Difference Learning</strong>
          <span class="badge compact">${escapeHtml(badgeText)}</span>
        </div>
        <div class="learning-meta">本轮自动把模型新增问题沉淀为后续增强建议。${relatedIssueType ? ` 当前选中问题类型：${escapeHtml(relatedIssueType)}` : ''}</div>
        ${renderLearningSection('规则建议', suggestions.rules || [], relatedIssueType)}
        ${renderLearningSection('分析器建议', suggestions.theme_analyzers || [], relatedIssueType)}
        ${renderLearningSection('LLM Prompt 建议', suggestions.llm_prompts || [], relatedIssueType)}
        ${renderLearningSection('Benchmark 建议', suggestions.benchmark || [], relatedIssueType)}
      `;
    }

    function renderLearningSection(label, items, relatedIssueType) {
      const filtered = relatedIssueType
        ? items.filter((item) => String(item.target || '').includes(relatedIssueType) || String(item.suggestion || '').includes(relatedIssueType))
        : items;
      const chosen = filtered.length ? filtered : items;
      if (!chosen.length) return '';
      return `
        <section class="learning-section">
          <h3>${escapeHtml(label)}</h3>
          <ul class="learning-list">
            ${chosen.slice(0, 3).map((item) => `<li><strong>${escapeHtml(String(item.target || 'system'))}</strong>：${escapeHtml(String(item.suggestion || ''))}</li>`).join('')}
          </ul>
        </section>
      `;
    }

    function fullLocation(finding) {
      const parts = [];
      if (finding.section_path) parts.push(finding.section_path);
      if (finding.page_hint) parts.push(finding.page_hint);
      parts.push(`行 ${finding.text_line_start}-${finding.text_line_end}`);
      return parts.join(' | ');
    }

    function escapeHtml(text) {
      return String(text || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }
  </script>
</body>
</html>"""


def _rules_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>规则管理</title>
  <style>
    :root {
      --bg: #f4efe5;
      --panel: #fffdf8;
      --line: #ddd2c2;
      --ink: #20252b;
      --muted: #6c675e;
      --accent: #9d4a24;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
    }
    .app { max-width: 1400px; margin: 0 auto; padding: 20px; }
    .hero h1 { margin: 0 0 8px; font-size: 30px; }
    .hero p { margin: 0 0 8px; color: var(--muted); line-height: 1.6; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 12px 30px rgba(52, 41, 29, 0.06);
      padding: 16px;
    }
    .meta { color: var(--muted); font-size: 13px; line-height: 1.6; word-break: break-word; }
    .rules-grid {
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      gap: 16px;
      margin-top: 16px;
    }
    .rules-col {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      overflow: hidden;
    }
    .rules-col-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 6px;
    }
    .rules-col-head h2, .rules-col-head h3 { margin: 0; }
    .rules-toolbar, .rule-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .rules-list {
      padding: 12px;
      display: grid;
      gap: 10px;
      max-height: 70vh;
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
    .rule-card-title { font-size: 15px; font-weight: 700; line-height: 1.5; }
    .rule-card-meta, .detail-label { color: var(--muted); font-size: 12px; line-height: 1.6; }
    .detail-value {
      color: var(--ink);
      font-size: 13px;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .detail-pair { display: grid; gap: 4px; }
    .rule-detail { padding: 16px; display: grid; gap: 12px; }
    .rule-note {
      width: 100%;
      min-height: 80px;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--line);
      font: inherit;
      resize: vertical;
    }
    .filter-chip, button {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--ink);
      padding: 8px 12px;
      font-size: 12px;
      cursor: pointer;
    }
    button.primary, .filter-chip.active {
      border-color: var(--accent);
      color: var(--accent);
      background: #fff5ea;
    }
    .empty { padding: 20px 16px; color: var(--muted); line-height: 1.7; }
    @media (max-width: 1080px) {
      .rules-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <section class="hero">
      <h1>规则管理</h1>
      <p>这里单独管理模型新增候选规则、benchmark gate 状态和入库确认决策。</p>
      <p><a href="/">返回审查工作台</a></p>
    </section>

    <section class="panel">
      <div id="rules-summary" class="meta">正在加载规则候选...</div>
      <div class="rules-grid">
        <section class="rules-col">
          <div id="rules-col-head" class="rules-col-head"></div>
          <div id="rules-list" class="rules-list"></div>
        </section>
        <section class="rules-col">
          <div class="rules-col-head">
            <h3>规则详情</h3>
            <div class="meta">查看候选规则、gate 状态，并记录确认入库、暂缓或忽略决策。</div>
          </div>
          <div id="rule-detail" class="rule-detail"></div>
        </section>
      </div>
    </section>
  </div>

  <script>
    const rulesSummaryNode = document.getElementById('rules-summary');
    const rulesColHeadNode = document.getElementById('rules-col-head');
    const rulesListNode = document.getElementById('rules-list');
    const ruleDetailNode = document.getElementById('rule-detail');

    let latestRulePayload = { formal_rules: [], candidate_rules: [], decision_summary: {} };
    let currentRuleFilter = 'pending';
    let selectedCandidateId = '';

    loadRuleManagement();

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
        rulesSummaryNode.textContent = `规则管理加载失败：${error.message}`;
      }
    }

    function renderRules(payload) {
      const summary = payload.decision_summary || {};
      rulesSummaryNode.textContent = `正式规则 ${payload.formal_rules.length} 条；候选规则 ${payload.candidate_rules.length} 条；待确认 ${summary.pending || 0} 条；已确认 ${summary.confirmed || 0} 条。`;
      rulesColHeadNode.innerHTML = `
        <h2>候选规则</h2>
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
          <button type="button" class="primary" data-rule-action="confirmed">确认入库</button>
          <button type="button" data-rule-action="deferred">暂缓</button>
          <button type="button" data-rule-action="ignored">忽略</button>
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
