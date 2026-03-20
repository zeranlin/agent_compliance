from __future__ import annotations


def incubator_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>智能体孵化与蒸馏工厂控制台</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --panel: #ffffff;
      --line: #d5dfec;
      --ink: #1f2937;
      --muted: #5e6b7a;
      --accent: #1f5f8b;
      --accent-soft: #eef5fb;
      --ok: #eaf7ef;
      --warn: #fff5e7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #eef4fb 0%, var(--bg) 100%);
    }
    a { color: var(--accent); text-decoration: none; }
    .app {
      max-width: 1500px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      gap: 16px;
    }
    .hero, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 10px 24px rgba(31, 95, 139, 0.08);
    }
    .hero {
      padding: 24px 28px;
      display: grid;
      gap: 10px;
    }
    .hero h1 {
      margin: 0;
      font-size: 34px;
      line-height: 1.15;
    }
    .hero .meta {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--accent);
      font-weight: 700;
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
      font-size: 17px;
    }
    .hero-actions {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      font-weight: 600;
    }
    .layout {
      display: grid;
      grid-template-columns: 380px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    .panel {
      padding: 20px;
      display: grid;
      gap: 16px;
    }
    .panel h2 {
      margin: 0;
      font-size: 24px;
    }
    .panel p {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }
    label {
      display: grid;
      gap: 6px;
      font-size: 14px;
      font-weight: 600;
      color: var(--muted);
    }
    input, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      font-size: 15px;
      color: var(--ink);
      background: #fff;
    }
    .button-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    button {
      border: none;
      border-radius: 12px;
      padding: 11px 16px;
      background: var(--accent);
      color: #fff;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary {
      background: #fff;
      color: var(--accent);
      border: 1px solid var(--line);
    }
    .status {
      padding: 12px 14px;
      border-radius: 12px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 600;
      min-height: 48px;
    }
    .run-list {
      display: grid;
      gap: 10px;
      max-height: 720px;
      overflow: auto;
      padding-right: 4px;
    }
    .run-card {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: #fbfdff;
      cursor: pointer;
      display: grid;
      gap: 8px;
    }
    .run-card.active {
      border-color: #8eb7d8;
      background: #eef6fd;
      box-shadow: inset 0 0 0 1px #c8ddef;
    }
    .run-card h3 {
      margin: 0;
      font-size: 17px;
      line-height: 1.4;
    }
    .run-meta, .summary-strip {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
      font-weight: 700;
    }
    .pill.ok {
      background: var(--ok);
      color: #16774e;
    }
    .pill.warn {
      background: var(--warn);
      color: #996000;
    }
    .detail-head {
      display: grid;
      gap: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--line);
    }
    .detail-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      background: #fbfdff;
      display: grid;
      gap: 6px;
    }
    .metric .label {
      font-size: 13px;
      color: var(--muted);
      font-weight: 600;
    }
    .metric .value {
      font-size: 28px;
      font-weight: 800;
      line-height: 1;
    }
    .viewer {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      background: #fcfdff;
      white-space: pre-wrap;
      line-height: 1.65;
      max-height: 540px;
      overflow: auto;
      font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
      font-size: 13px;
    }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 14px;
      padding: 24px;
      text-align: center;
      color: var(--muted);
      background: #fbfdff;
    }
    @media (max-width: 1100px) {
      .layout {
        grid-template-columns: 1fr;
      }
      .detail-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 720px) {
      .app { padding: 14px; }
      .hero h1 { font-size: 28px; }
      .detail-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <section class="hero">
      <div class="meta">Incubator Console</div>
      <h1>智能体孵化与蒸馏工厂控制台</h1>
      <p>这个页面只做一件事：启动一轮标准孵化，并查看落盘的 run manifest 与蒸馏报告。它不负责复杂设计，只服务方法层验证和复盘。</p>
      <div class="hero-actions">
        <a href="/review-check">采购需求合规性检查智能体</a>
        <a href="/review-next">增强审查页</a>
        <a href="/rules">规则管理页</a>
      </div>
    </section>
    <section class="layout">
      <section class="panel">
        <div>
          <h2>启动一轮孵化</h2>
          <p>先选蓝图，再给一轮 run 起一个标题。当前页面只做首轮骨架孵化与查看；样例登记、对照验证和蒸馏建议执行仍走命令行续跑。</p>
        </div>
        <label>
          智能体蓝图
          <select id="blueprint-select"></select>
        </label>
        <label>
          运行标题
          <input id="run-title-input" placeholder="例如：政府采购预算需求智能体 第一轮孵化" />
        </label>
        <div class="button-row">
          <button id="start-run-btn" type="button">启动孵化</button>
          <button id="refresh-runs-btn" class="secondary" type="button">刷新运行列表</button>
        </div>
        <div id="incubator-status" class="status">等待选择蓝图并启动一轮孵化。</div>
        <div>
          <h2 style="font-size:20px;">历史 runs</h2>
          <p>点击左侧任一 run，可直接查看 run manifest 摘要和蒸馏报告正文。</p>
        </div>
        <div id="run-list" class="run-list"></div>
      </section>
      <section class="panel">
        <div id="run-detail" class="empty">右侧会显示当前选中 run 的摘要、产物路径和蒸馏报告。</div>
      </section>
    </section>
  </div>
  <script>
    const blueprintNode = document.getElementById('blueprint-select');
    const runTitleNode = document.getElementById('run-title-input');
    const statusNode = document.getElementById('incubator-status');
    const runListNode = document.getElementById('run-list');
    const runDetailNode = document.getElementById('run-detail');
    let blueprints = [];
    let runs = [];
    let selectedRunPath = null;

    loadBlueprints();
    loadRuns();

    document.getElementById('start-run-btn').addEventListener('click', startIncubationRun);
    document.getElementById('refresh-runs-btn').addEventListener('click', loadRuns);
    blueprintNode.addEventListener('change', applyDefaultRunTitle);

    async function loadBlueprints() {
      try {
        const response = await fetch('/api/incubator/blueprints');
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '加载蓝图失败');
        blueprints = payload.blueprints || [];
        blueprintNode.innerHTML = blueprints.map((item) => (
          `<option value="${escapeHtml(item.agent_key)}">${escapeHtml(item.agent_name)} · ${escapeHtml(item.agent_type)}</option>`
        )).join('');
        applyDefaultRunTitle();
      } catch (error) {
        statusNode.textContent = `加载蓝图失败：${error.message}`;
      }
    }

    function applyDefaultRunTitle() {
      if (runTitleNode.value.trim()) return;
      const selected = blueprints.find((item) => item.agent_key === blueprintNode.value);
      if (!selected) return;
      runTitleNode.value = `${selected.agent_name} 第一轮孵化`;
    }

    async function loadRuns() {
      try {
        const response = await fetch('/api/incubator/runs');
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '加载运行列表失败');
        runs = payload.runs || [];
        renderRunList();
        if (selectedRunPath) {
          const matched = runs.find((item) => item.run_manifest === selectedRunPath);
          if (matched) {
            await showRunDetail(selectedRunPath);
            return;
          }
        }
        if (runs.length) {
          await showRunDetail(runs[0].run_manifest);
        } else {
          runDetailNode.innerHTML = '<div class="empty">当前还没有 incubator run。先启动一轮孵化即可。</div>';
        }
      } catch (error) {
        statusNode.textContent = `加载运行列表失败：${error.message}`;
      }
    }

    function renderRunList() {
      runListNode.innerHTML = runs.length ? runs.map((item) => {
        const summary = item.summary || {};
        const active = item.run_manifest === selectedRunPath ? 'active' : '';
        return `
          <article class="run-card ${active}" data-run-path="${escapeHtml(item.run_manifest)}">
            <h3>${escapeHtml(item.run_title)}</h3>
            <div class="summary-strip">
              <span class="pill">${escapeHtml(item.agent_key)}</span>
              <span class="pill ok">阶段 ${summary.completed_stages || 0}/${summary.total_stages || 0}</span>
              <span class="pill warn">建议 ${summary.recommendation_count || 0}</span>
            </div>
            <div class="run-meta">
              <span>${escapeHtml(item.updated_at || '')}</span>
            </div>
          </article>
        `;
      }).join('') : '<div class="empty">当前还没有 run。</div>';
      runListNode.querySelectorAll('.run-card').forEach((node) => {
        node.addEventListener('click', () => showRunDetail(node.dataset.runPath));
      });
    }

    async function showRunDetail(path) {
      selectedRunPath = path;
      renderRunList();
      try {
        const response = await fetch(`/api/incubator/run?path=${encodeURIComponent(path)}`);
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '读取 run 详情失败');
        const run = payload.run || {};
        const summary = summarizeRun(run);
        runDetailNode.innerHTML = `
          <div class="detail-head">
            <h2>${escapeHtml(payload.run_title || '')}</h2>
            <p>${escapeHtml(payload.agent_key || '')} · run manifest：${escapeHtml(payload.run_manifest || '')}</p>
            <div class="summary-strip">
              <span class="pill">${escapeHtml(payload.report_markdown_path || '无 Markdown 报告')}</span>
            </div>
          </div>
          <div class="detail-grid">
            <div class="metric"><div class="label">已完成阶段</div><div class="value">${summary.completedStages}</div></div>
            <div class="metric"><div class="label">样例集</div><div class="value">${summary.sampleSets}</div></div>
            <div class="metric"><div class="label">对照结果</div><div class="value">${summary.comparisons}</div></div>
            <div class="metric"><div class="label">蒸馏建议</div><div class="value">${summary.recommendations}</div></div>
          </div>
          <div>
            <h2 style="font-size:20px; margin-bottom:8px;">蒸馏报告</h2>
            <div class="viewer">${escapeHtml(payload.report_markdown || '暂无 Markdown 报告。')}</div>
          </div>
        `;
      } catch (error) {
        runDetailNode.innerHTML = `<div class="empty">读取 run 详情失败：${escapeHtml(error.message)}</div>`;
      }
    }

    async function startIncubationRun() {
      const agentKey = blueprintNode.value;
      const runTitle = runTitleNode.value.trim();
      if (!agentKey) {
        statusNode.textContent = '请先选择一个蓝图。';
        return;
      }
      statusNode.textContent = '正在启动一轮标准孵化，请稍候...';
      try {
        const response = await fetch('/api/incubator/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_key: agentKey, run_title: runTitle }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '启动孵化失败');
        statusNode.textContent = `已启动：${payload.run_title}；当前完成的是首轮骨架孵化。样例准备、对照验证、蒸馏迭代和产品化阶段需在后续续跑中继续完成。`;
        await loadRuns();
        if (payload.outputs && payload.outputs.run_manifest) {
          await showRunDetail(payload.outputs.run_manifest);
        }
      } catch (error) {
        statusNode.textContent = `启动孵化失败：${error.message}`;
      }
    }

    function summarizeRun(run) {
      const stages = Array.isArray(run.stages) ? run.stages : [];
      return {
        completedStages: stages.filter((item) => item.status === 'completed').length,
        sampleSets: stages.reduce((sum, item) => sum + ((item.sample_sets || []).length), 0),
        comparisons: stages.reduce((sum, item) => sum + ((item.comparisons || []).length), 0),
        recommendations: stages.reduce((sum, item) => sum + ((item.recommendations || []).length), 0),
      };
    }

    function escapeHtml(text) {
      return String(text || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }
  </script>
</body>
</html>"""
