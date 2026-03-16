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
      --bg: #efe8da;
      --panel: #fffaf1;
      --panel-strong: #fffdf8;
      --ink: #1f2528;
      --accent: #a34727;
      --muted: #6f675b;
      --line: #d6c6ab;
      --warn: #a33a1e;
      --medium: #9b6a12;
      --chip-bg: rgba(163,71,39,.1);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Source Han Serif SC", "Songti SC", serif;
      background:
        radial-gradient(circle at top left, rgba(163,71,39,.16), transparent 28%),
        radial-gradient(circle at top right, rgba(62,88,99,.08), transparent 26%),
        linear-gradient(180deg, #f6f0e4 0%, var(--bg) 100%);
      color: var(--ink);
    }
    .wrap { max-width: 1240px; margin: 0 auto; padding: 30px 18px 60px; }
    .hero { display: grid; gap: 16px; margin-bottom: 22px; }
    .eyebrow { color: var(--accent); text-transform: uppercase; letter-spacing: .12em; font-size: 12px; }
    .hero h1 { margin: 0; font-size: clamp(34px, 5vw, 62px); line-height: .95; letter-spacing: -.04em; }
    .hero p { margin: 0; max-width: 860px; color: var(--muted); font-size: 17px; line-height: 1.7; }
    .layout { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 18px; align-items: start; }
    .panel { background: rgba(255,250,241,.94); border: 1px solid var(--line); border-radius: 24px; box-shadow: 0 20px 60px rgba(72,54,31,.08); }
    .controls, .summary, .findings { padding: 22px; }
    .controls { position: sticky; top: 18px; }
    .row { display: flex; flex-wrap: wrap; gap: 12px 18px; align-items: center; }
    .stack { display: grid; gap: 12px; }
    .file { padding: 14px; border: 1px dashed var(--line); border-radius: 16px; width: 100%; background: rgba(255,255,255,.7); }
    label.toggle { display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: 14px; }
    button { border: 0; background: var(--accent); color: white; padding: 12px 18px; border-radius: 999px; font-size: 15px; cursor: pointer; }
    button:disabled { opacity: .45; cursor: wait; }
    .status { color: var(--muted); font-size: 14px; line-height: 1.6; }
    .summary { display: grid; gap: 18px; margin-bottom: 18px; }
    .summary-head { display: grid; gap: 10px; }
    .summary-head h2, .findings h2, .controls h2 { margin: 0; font-size: 24px; }
    .summary-head p { margin: 0; color: var(--muted); line-height: 1.7; }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; }
    .stat { padding: 16px; border-radius: 18px; background: rgba(255,255,255,.72); border: 1px solid var(--line); }
    .stat span { color: var(--muted); font-size: 13px; }
    .stat b { display: block; font-size: 30px; margin-top: 10px; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between; margin-bottom: 18px; }
    .toolbar-left, .toolbar-right { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    .select, .search {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 10px 14px;
      background: rgba(255,255,255,.76);
      color: var(--ink);
      font: inherit;
    }
    .search { min-width: 220px; }
    .finding-list { display: grid; gap: 16px; }
    .finding-card {
      border: 1px solid var(--line);
      border-radius: 24px;
      background: var(--panel-strong);
      overflow: hidden;
    }
    .finding-header {
      display: grid;
      gap: 10px;
      padding: 20px 22px 16px;
      border-bottom: 1px solid rgba(214,198,171,.75);
      background: linear-gradient(180deg, rgba(255,255,255,.76), rgba(255,248,238,.92));
    }
    .finding-index {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
    }
    .pill {
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--chip-bg);
      color: var(--accent);
      font-size: 12px;
    }
    .pill.high { background: rgba(163,58,30,.12); color: var(--warn); }
    .pill.medium { background: rgba(155,106,18,.13); color: var(--medium); }
    .finding-header h3 {
      margin: 0;
      font-size: 24px;
      line-height: 1.35;
    }
    .finding-detail {
      padding: 20px 22px 22px;
      display: grid;
      gap: 16px;
    }
    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px 18px;
    }
    .detail-item {
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(247,241,230,.72);
      border: 1px solid rgba(214,198,171,.72);
    }
    .detail-item.full { grid-column: 1 / -1; }
    .detail-item dt {
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }
    .detail-item dd {
      margin: 0;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .quote {
      margin: 0;
      padding: 14px 16px;
      border-left: 4px solid var(--accent);
      border-radius: 0 16px 16px 0;
      background: rgba(163,71,39,.06);
      line-height: 1.8;
    }
    .muted { color: var(--muted); }
    .hidden { display: none; }
    @media (max-width: 920px) {
      .layout { grid-template-columns: 1fr; }
      .controls { position: static; }
      .detail-grid { grid-template-columns: 1fr; }
      .search { min-width: 0; width: 100%; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">Local Review Console</div>
      <h1>采购审查工作台</h1>
      <p>本地上传采购文件，直接运行离线审查。默认走规则与本地检索链路，可按需打开本地大模型兜底增强。</p>
    </section>
    <div class="layout">
      <form id="review-form" class="panel controls stack">
        <div class="stack">
          <h2>审查设置</h2>
          <div class="status">上传采购文件后，结果会按正式审查意见的字段顺序展开，便于逐条复核。</div>
        </div>
        <div class="row"><input class="file" type="file" name="file" accept=".docx,.doc,.pdf,.txt,.md,.rtf" required /></div>
        <div class="stack">
          <label class="toggle"><input type="checkbox" name="use_cache" /> 启用结果缓存</label>
          <label class="toggle"><input type="checkbox" name="use_llm" /> 启用本地模型兜底</label>
        </div>
        <div class="row"><button type="submit" id="submit-btn">开始审查</button></div>
        <div class="status" id="status">等待上传文件</div>
      </form>
      <main>
        <section id="summary" class="panel summary hidden"></section>
        <section id="findings" class="panel findings hidden"></section>
      </main>
    </div>
  </div>
  <script>
    const form = document.getElementById('review-form');
    const submitBtn = document.getElementById('submit-btn');
    const statusNode = document.getElementById('status');
    const summaryNode = document.getElementById('summary');
    const findingsNode = document.getElementById('findings');
    let latestFindings = [];
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
        latestFindings = payload.review.findings;
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
        <div class="summary-head">
          <h2>审查摘要</h2>
          <p>${escapeHtml(review.overall_risk_summary)}</p>
          <p class="muted">文件：${escapeHtml(review.document_name)} ｜ 审查范围：${escapeHtml(review.review_scope)} ｜ 审查时间：${escapeHtml(review.review_timestamp)}</p>
        </div>
        <div class="summary-grid">
          <div class="stat"><span>发现项</span><b>${review.findings.length}</b></div>
          <div class="stat"><span>高风险</span><b>${high}</b></div>
          <div class="stat"><span>中风险</span><b>${medium}</b></div>
          <div class="stat"><span>模型</span><b>${payload.llm.enabled ? escapeHtml(payload.llm.model) : '关闭'}</b></div>
          <div class="stat"><span>缓存</span><b>${payload.cache.enabled ? (payload.cache.used ? '命中' : '启用') : '关闭'}</b></div>
        </div>`;
      summaryNode.classList.remove('hidden');
    }
    function renderFindings(findings) {
      findingsNode.innerHTML = `
        <div class="toolbar">
          <div class="toolbar-left">
            <h2>主要问题</h2>
          </div>
          <div class="toolbar-right">
            <select id="risk-filter" class="select">
              <option value="all">全部风险等级</option>
              <option value="high">仅看高风险</option>
              <option value="medium">仅看中风险</option>
            </select>
            <input id="finding-search" class="search" type="search" placeholder="搜索标题、位置、原文摘录" />
          </div>
        </div>
        <div id="finding-list" class="finding-list"></div>`;
      document.getElementById('risk-filter').addEventListener('change', applyFindingFilters);
      document.getElementById('finding-search').addEventListener('input', applyFindingFilters);
      latestFindings = findings;
      applyFindingFilters();
      findingsNode.classList.remove('hidden');
    }
    function applyFindingFilters() {
      const risk = document.getElementById('risk-filter')?.value || 'all';
      const keyword = (document.getElementById('finding-search')?.value || '').trim().toLowerCase();
      const filtered = latestFindings.filter((finding) => {
        const matchRisk = risk === 'all' || finding.risk_level === risk;
        const haystack = [
          finding.problem_title,
          finding.section_path,
          finding.source_text,
          finding.issue_type,
          finding.clause_id,
        ].join(' ').toLowerCase();
        const matchKeyword = !keyword || haystack.includes(keyword);
        return matchRisk && matchKeyword;
      });
      const listNode = document.getElementById('finding-list');
      listNode.innerHTML = filtered.length
        ? filtered.map((finding, index) => renderFinding(finding, index + 1)).join('')
        : '<div class="muted">当前筛选条件下没有匹配的 finding。</div>';
    }
    function renderFinding(finding, index) {
      const basis = formatParagraphs(finding.legal_or_policy_basis || '当前离线链路未单独拆出更细依据，请结合正式 Markdown 结果复核。');
      const logic = formatParagraphs([finding.why_it_is_risky, finding.impact_on_competition_or_performance].filter(Boolean).join('\\n'));
      return `<article class="finding-card">
        <div class="finding-header">
          <div class="finding-index">
            <span>主要问题 ${index}</span>
            <span class="pill ${escapeHtml(finding.risk_level)}">${riskLabel(finding.risk_level)}</span>
            <span class="pill">${escapeHtml(finding.compliance_judgment)}</span>
          </div>
          <h3>${escapeHtml(finding.problem_title)}</h3>
        </div>
        <div class="finding-detail">
          <dl class="detail-grid">
            <div class="detail-item full"><dt>位置</dt><dd>${escapeHtml(finding.section_path || finding.source_section || '待补充')}</dd></div>
            <div class="detail-item"><dt>页码提示</dt><dd>${escapeHtml(finding.page_hint || 'Word 原件待人工翻页复核')}</dd></div>
            <div class="detail-item"><dt>条款编号</dt><dd>${escapeHtml(finding.clause_id || '待补充')}</dd></div>
            <div class="detail-item"><dt>辅助行号</dt><dd>${escapeHtml(formatLineRange(finding.text_line_start, finding.text_line_end))}</dd></div>
            <div class="detail-item"><dt>风险类型</dt><dd>${escapeHtml(finding.issue_type)}</dd></div>
            <div class="detail-item"><dt>风险等级</dt><dd>${escapeHtml(riskLabel(finding.risk_level))}</dd></div>
            <div class="detail-item"><dt>合规判断</dt><dd>${escapeHtml(finding.compliance_judgment)}</dd></div>
            <div class="detail-item"><dt>表格/评分项</dt><dd>${escapeHtml(finding.table_or_item_label || finding.source_section || '—')}</dd></div>
            <div class="detail-item full"><dt>原文摘录</dt><dd><blockquote class="quote">${escapeHtml(finding.source_text)}</blockquote></dd></div>
            <div class="detail-item full"><dt>依据</dt><dd>${basis}</dd></div>
            <div class="detail-item full"><dt>适用逻辑</dt><dd>${logic}</dd></div>
            <div class="detail-item full"><dt>修改建议</dt><dd>${formatParagraphs(finding.rewrite_suggestion)}</dd></div>
            <div class="detail-item full"><dt>建议替代表述</dt><dd>${formatParagraphs(finding.rewrite_suggestion)}</dd></div>
          </dl>
        </div>
      </article>`;
    }
    function formatLineRange(start, end) {
      if (!start && !end) return '—';
      if (start === end || !end) return String(start).padStart(4, '0');
      return `${String(start).padStart(4, '0')}-${String(end).padStart(4, '0')}`;
    }
    function riskLabel(level) {
      return ({ high: '高', medium: '中', low: '低' }[level] || level || '未标注');
    }
    function formatParagraphs(text) {
      return escapeHtml(String(text || '—'))
        .split('\\n')
        .filter(Boolean)
        .map(line => `<div>${line}</div>`)
        .join('');
    }
    function escapeHtml(text) {
      return String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }
  </script>
</body>
</html>"""
