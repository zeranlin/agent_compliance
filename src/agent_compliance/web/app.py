from __future__ import annotations

import json
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agent_compliance.cache.review_cache import (
    REVIEW_CACHE_VERSION,
    build_review_cache_key,
    load_review_cache,
    reference_snapshot_id,
    save_review_cache,
)
from agent_compliance.config import LLMConfig, detect_llm_config, detect_paths
from agent_compliance.pipelines.llm_enhance import enhance_review_result
from agent_compliance.pipelines.normalize import run_normalize
from agent_compliance.pipelines.render import write_review_outputs
from agent_compliance.pipelines.review import build_review_result
from agent_compliance.pipelines.rule_scan import run_rule_scan
from agent_compliance.rules.base import RULE_SET_VERSION


def run_web_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), ReviewWebHandler)
    print(f"Web UI running at http://{host}:{port}")
    server.serve_forever()


class ReviewWebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if urlparse(self.path).path == "/":
            self._send_html(_index_html())
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/review":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        try:
            fields = _parse_multipart(self.headers, self.rfile.read(int(self.headers.get("Content-Length", "0"))))
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
        source_path = _persist_upload(upload["filename"], upload["content"])
        normalized = run_normalize(source_path)
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
        llm_config = _web_llm_config(use_llm)
        review = enhance_review_result(review, llm_config)
        json_path, md_path = write_review_outputs(review, normalized.file_hash[:12])

        self._send_json(
            {
                "cache": {"enabled": use_cache, "used": cache_used, "key": cache_key},
                "llm": {
                    "enabled": llm_config.enabled,
                    "base_url": llm_config.base_url,
                    "model": llm_config.model,
                },
                "review": review.to_dict(),
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
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        fields[name] = {
            "filename": filename or "",
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
        enabled=use_llm and config.enabled,
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )


def _flag_value(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "on", "yes"}


def _index_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>采购审查工作台</title>
  <style>
    :root {
      --bg: #f3efe6;
      --panel: #fffaf0;
      --ink: #1d2a2f;
      --accent: #b5522d;
      --muted: #6d6b66;
      --line: #d8cbb2;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Source Han Serif SC", "Songti SC", serif;
      background:
        radial-gradient(circle at top left, rgba(181,82,45,.12), transparent 30%),
        linear-gradient(180deg, #f7f2e8 0%, var(--bg) 100%);
      color: var(--ink);
    }
    .wrap { max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }
    .hero { display: grid; gap: 18px; margin-bottom: 24px; }
    .hero h1 { margin: 0; font-size: clamp(32px, 5vw, 58px); line-height: .95; letter-spacing: -.04em; }
    .hero p { margin: 0; max-width: 760px; color: var(--muted); font-size: 17px; line-height: 1.6; }
    .panel { background: rgba(255,250,240,.92); border: 1px solid var(--line); border-radius: 22px; box-shadow: 0 20px 60px rgba(72,54,31,.08); }
    .controls, .summary, .findings { padding: 22px; margin-bottom: 20px; }
    .row { display: flex; flex-wrap: wrap; gap: 14px 22px; align-items: center; }
    .file { padding: 14px; border: 1px dashed var(--line); border-radius: 16px; width: min(100%, 420px); background: rgba(255,255,255,.65); }
    label.toggle { display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: 14px; }
    button { border: 0; background: var(--accent); color: white; padding: 12px 18px; border-radius: 999px; font-size: 15px; cursor: pointer; }
    button:disabled { opacity: .45; cursor: wait; }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-top: 16px; }
    .stat { padding: 14px; border-radius: 16px; background: rgba(255,255,255,.7); border: 1px solid var(--line); }
    .stat b { display: block; font-size: 28px; margin-top: 6px; }
    .finding { padding: 18px 0; border-top: 1px solid var(--line); }
    .finding:first-child { border-top: 0; padding-top: 0; }
    .meta { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 10px; color: var(--muted); font-size: 13px; }
    .tag { padding: 4px 8px; border-radius: 999px; background: rgba(181,82,45,.12); color: var(--accent); }
    .finding p { margin: 8px 0; line-height: 1.7; }
    .hidden { display: none; }
    .status { color: var(--muted); font-size: 14px; }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>采购审查工作台</h1>
      <p>本地上传采购文件，直接运行离线审查。默认走规则与本地检索链路，可按需打开本地大模型兜底增强。</p>
    </section>
    <form id="review-form" class="panel controls">
      <div class="row"><input class="file" type="file" name="file" accept=".docx,.doc,.pdf,.txt,.md,.rtf" required /></div>
      <div class="row">
        <label class="toggle"><input type="checkbox" name="use_cache" /> 启用结果缓存</label>
        <label class="toggle"><input type="checkbox" name="use_llm" /> 启用本地模型兜底</label>
      </div>
      <div class="row"><button type="submit" id="submit-btn">开始审查</button><span class="status" id="status">等待上传文件</span></div>
    </form>
    <section id="summary" class="panel summary hidden"></section>
    <section id="findings" class="panel findings hidden"></section>
  </div>
  <script>
    const form = document.getElementById('review-form');
    const submitBtn = document.getElementById('submit-btn');
    const statusNode = document.getElementById('status');
    const summaryNode = document.getElementById('summary');
    const findingsNode = document.getElementById('findings');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      submitBtn.disabled = true;
      statusNode.textContent = '正在审查，请稍候...';
      summaryNode.classList.add('hidden');
      findingsNode.classList.add('hidden');
      try {
        const formData = new FormData(form);
        const response = await fetch('/api/review', { method: 'POST', body: formData });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '审查失败');
        renderSummary(payload);
        renderFindings(payload.review.findings);
        statusNode.textContent = '审查完成';
      } catch (error) {
        statusNode.textContent = `失败：${error.message}`;
      } finally {
        submitBtn.disabled = false;
      }
    });
    function renderSummary(payload) {
      const review = payload.review;
      const high = review.findings.filter(item => item.risk_level === 'high').length;
      const medium = review.findings.filter(item => item.risk_level === 'medium').length;
      summaryNode.innerHTML = `
        <h2>审查摘要</h2>
        <p>${review.overall_risk_summary}</p>
        <div class="summary-grid">
          <div class="stat">发现项<b>${review.findings.length}</b></div>
          <div class="stat">高风险<b>${high}</b></div>
          <div class="stat">中风险<b>${medium}</b></div>
          <div class="stat">模型<b>${payload.llm.enabled ? payload.llm.model : '关闭'}</b></div>
          <div class="stat">缓存<b>${payload.cache.enabled ? (payload.cache.used ? '命中' : '启用') : '关闭'}</b></div>
        </div>`;
      summaryNode.classList.remove('hidden');
    }
    function renderFindings(findings) {
      findingsNode.innerHTML = `<h2>Findings</h2>${findings.map(renderFinding).join('')}`;
      findingsNode.classList.remove('hidden');
    }
    function renderFinding(finding) {
      return `<article class="finding">
        <h3>${finding.finding_id} ${finding.problem_title}</h3>
        <div class="meta">
          <span class="tag">${finding.risk_level}</span>
          <span>${finding.issue_type}</span>
          <span>${finding.section_path || ''}</span>
          <span>${finding.page_hint || ''}</span>
        </div>
        <p><strong>代表性摘录：</strong>${escapeHtml(finding.source_text)}</p>
        <p><strong>风险说明：</strong>${escapeHtml(finding.why_it_is_risky)}</p>
        <p><strong>依据：</strong>${escapeHtml(finding.legal_or_policy_basis || '—')}</p>
        <p><strong>修改建议：</strong>${escapeHtml(finding.rewrite_suggestion)}</p>
      </article>`;
    }
    function escapeHtml(text) {
      return String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }
  </script>
</body>
</html>"""
