def review_home_html() -> str:
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
      <p><a href="/review-check">打开采购人审查页</a> · <a href="/review-next">打开增强审查页</a> · <a href="/rules">打开规则管理页面</a> · <a href="/incubator">打开孵化工厂控制台</a></p>
    </section>

    <form id="review-form" class="panel toolbar">
      <div class="toolbar-row">
        <input type="file" name="file" accept=".docx,.doc,.pdf,.txt,.md,.rtf" required />
        <button type="submit" id="submit-btn">上传并审查</button>
        <button type="button" id="open-source-btn" class="secondary" disabled>打开原文件</button>
      </div>
      <div class="toolbar-row">
        <label><input type="checkbox" name="use_cache" /> 启用缓存</label>
        <label><input type="checkbox" name="use_llm" /> 启用大模型（混合审查）</label>
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
        const treatmentDiff = treatmentPriority(left).rank - treatmentPriority(right).rank;
        if (treatmentDiff !== 0) return treatmentDiff;
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
