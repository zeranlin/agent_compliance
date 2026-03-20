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
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      font-size: 15px;
      color: var(--ink);
      background: #fff;
    }
    textarea {
      min-height: 84px;
      resize: vertical;
      line-height: 1.6;
      font-family: inherit;
    }
    .button-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .subform {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fbfdff;
      padding: 14px;
      display: grid;
      gap: 12px;
    }
    .subform h3 {
      margin: 0;
      font-size: 18px;
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
    .section-block {
      display: grid;
      gap: 12px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }
    .trend-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .mini-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      background: #fbfdff;
      display: grid;
      gap: 6px;
    }
    .mini-card strong {
      font-size: 14px;
    }
    .recommendation-list {
      display: grid;
      gap: 10px;
      max-height: 320px;
      overflow: auto;
    }
    .recommendation-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fbfdff;
      padding: 12px 14px;
      display: grid;
      gap: 8px;
    }
    .rec-head {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
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
      .trend-grid {
        grid-template-columns: 1fr;
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
        <a href="/incubator/definition">需求定义层</a>
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
        <div class="subform">
          <div>
            <h3>补充样例与对照</h3>
            <p>选中一个已有 run 后，可以在这里补样例清单，或直接填写人工/强通用智能体/目标智能体三方结果，继续推进对照验证和蒸馏建议生成。</p>
          </div>
          <label>
            样例清单名称
            <input id="manifest-name-input" placeholder="例如：第一批采购需求样例" />
          </label>
          <label>
            正样例路径（每行一个）
            <textarea id="positive-paths-input" placeholder="/path/to/positive-a.docx&#10;/path/to/positive-b.docx"></textarea>
          </label>
          <label>
            负样例路径（每行一个）
            <textarea id="negative-paths-input" placeholder="/path/to/negative-a.docx"></textarea>
          </label>
          <label>
            边界样例路径（每行一个）
            <textarea id="boundary-paths-input" placeholder="/path/to/boundary-a.docx"></textarea>
          </label>
          <label>
            对照样例 ID
            <input id="comparison-sample-id-input" placeholder="例如：case-001" />
          </label>
          <label>
            人工基准
            <textarea id="human-baseline-input" placeholder="人工结果要点，一行一条。"></textarea>
          </label>
          <label>
            强通用智能体结果
            <textarea id="strong-agent-result-input" placeholder="强通用智能体结果要点，一行一条。"></textarea>
          </label>
          <label>
            目标智能体结果
            <textarea id="target-agent-result-input" placeholder="当前目标智能体结果要点，一行一条。"></textarea>
          </label>
          <label>
            对照摘要（可选）
            <textarea id="comparison-summary-input" placeholder="例如：当前目标智能体仍漏掉评分结构和边界条款。"></textarea>
          </label>
          <div class="button-row">
            <button id="continue-run-btn" type="button">补充并续跑</button>
          </div>
        </div>
        <div class="subform">
          <div>
            <h3>更新蒸馏建议状态</h3>
            <p>选中一个已有 run 后，可以把某条蒸馏建议直接更新为 accepted / implemented / validated，并补回归结果与能力变化。</p>
          </div>
          <label>
            蒸馏建议
            <select id="recommendation-select">
              <option value="">请先选择右侧 run</option>
            </select>
          </label>
          <label>
            所属阶段
            <select id="recommendation-stage-select">
              <option value="distillation_iteration">distillation_iteration</option>
              <option value="productization">productization</option>
            </select>
          </label>
          <label>
            建议状态
            <select id="recommendation-status-select">
              <option value="accepted">accepted</option>
              <option value="implemented">implemented</option>
              <option value="validated">validated</option>
              <option value="dropped">dropped</option>
            </select>
          </label>
          <label>
            备注
            <textarea id="recommendation-notes-input" placeholder="例如：已补规则扫描第一版。"></textarea>
          </label>
          <label>
            回归结果（可选）
            <textarea id="recommendation-regression-input" placeholder="例如：评分样例回归通过。"></textarea>
          </label>
          <label>
            能力变化（可选）
            <textarea id="recommendation-change-input" placeholder="例如：已稳定输出评分主问题。"></textarea>
          </label>
          <div class="button-row">
            <button id="update-recommendation-btn" type="button">更新建议状态</button>
          </div>
        </div>
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
    const manifestNameNode = document.getElementById('manifest-name-input');
    const positivePathsNode = document.getElementById('positive-paths-input');
    const negativePathsNode = document.getElementById('negative-paths-input');
    const boundaryPathsNode = document.getElementById('boundary-paths-input');
    const comparisonSampleIdNode = document.getElementById('comparison-sample-id-input');
    const humanBaselineNode = document.getElementById('human-baseline-input');
    const strongAgentResultNode = document.getElementById('strong-agent-result-input');
    const targetAgentResultNode = document.getElementById('target-agent-result-input');
    const comparisonSummaryNode = document.getElementById('comparison-summary-input');
    const recommendationSelectNode = document.getElementById('recommendation-select');
    const recommendationStageSelectNode = document.getElementById('recommendation-stage-select');
    const recommendationStatusSelectNode = document.getElementById('recommendation-status-select');
    const recommendationNotesNode = document.getElementById('recommendation-notes-input');
    const recommendationRegressionNode = document.getElementById('recommendation-regression-input');
    const recommendationChangeNode = document.getElementById('recommendation-change-input');
    const statusNode = document.getElementById('incubator-status');
    const runListNode = document.getElementById('run-list');
    const runDetailNode = document.getElementById('run-detail');
    let blueprints = [];
    let runs = [];
    let selectedRunPath = null;
    let selectedRun = null;

    loadBlueprints();
    loadRuns();

    document.getElementById('start-run-btn').addEventListener('click', startIncubationRun);
    document.getElementById('refresh-runs-btn').addEventListener('click', loadRuns);
    document.getElementById('continue-run-btn').addEventListener('click', continueIncubationRun);
    document.getElementById('update-recommendation-btn').addEventListener('click', updateRecommendationStatus);
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
        selectedRun = run;
        const summary = summarizeRun(run);
        syncRecommendationOptions(run);
        const trend = await loadRunTrend(payload.run_manifest, payload.agent_key);
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
          ${renderTrendBlock(trend)}
          ${renderRecommendationBlock(run)}
          <div>
            <h2 style="font-size:20px; margin-bottom:8px;">蒸馏报告</h2>
            <div class="viewer">${escapeHtml(payload.report_markdown || '暂无 Markdown 报告。')}</div>
          </div>
        `;
      } catch (error) {
        runDetailNode.innerHTML = `<div class="empty">读取 run 详情失败：${escapeHtml(error.message)}</div>`;
      }
    }

    async function updateRecommendationStatus() {
      if (!selectedRunPath) {
        statusNode.textContent = '请先选择一个已有 run。';
        return;
      }
      if (!recommendationSelectNode.value) {
        statusNode.textContent = '请先选择一条蒸馏建议。';
        return;
      }
      statusNode.textContent = '正在更新蒸馏建议状态...';
      try {
        const response = await fetch('/api/incubator/recommendation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            run_manifest: selectedRunPath,
            recommendation_key: recommendationSelectNode.value,
            stage: recommendationStageSelectNode.value,
            status: recommendationStatusSelectNode.value,
            notes: recommendationNotesNode.value.trim(),
            regression_result: recommendationRegressionNode.value.trim(),
            capability_change: recommendationChangeNode.value.trim(),
          }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '更新蒸馏建议失败');
        statusNode.textContent = `已更新建议：${payload.recommendation_key} -> ${payload.status}`;
        await loadRuns();
        if (payload.run_manifest) {
          await showRunDetail(payload.run_manifest);
        }
      } catch (error) {
        statusNode.textContent = `更新蒸馏建议失败：${error.message}`;
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

    async function continueIncubationRun() {
      if (!selectedRunPath) {
        statusNode.textContent = '请先在左侧选择一个已有 run。';
        return;
      }
      statusNode.textContent = '正在补充样例与对照，并续跑当前 run...';
      try {
        const response = await fetch('/api/incubator/continue', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            run_manifest: selectedRunPath,
            manifest_name: manifestNameNode.value.trim(),
            positive_paths: positivePathsNode.value,
            negative_paths: negativePathsNode.value,
            boundary_paths: boundaryPathsNode.value,
            comparison_sample_id: comparisonSampleIdNode.value.trim(),
            human_baseline: humanBaselineNode.value,
            strong_agent_result: strongAgentResultNode.value,
            target_agent_result: targetAgentResultNode.value,
            comparison_summary: comparisonSummaryNode.value,
          }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '续跑孵化失败');
        statusNode.textContent = `已续跑：${payload.run_title}；样例补充=${payload.continued.sample_manifest_added ? '是' : '否'}，对照补充=${payload.continued.comparison_added ? '是' : '否'}。`;
        await loadRuns();
        if (payload.outputs && payload.outputs.run_manifest) {
          await showRunDetail(payload.outputs.run_manifest);
        }
      } catch (error) {
        statusNode.textContent = `续跑孵化失败：${error.message}`;
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

    function syncRecommendationOptions(run) {
      const recommendations = collectRecommendations(run);
      recommendationSelectNode.innerHTML = recommendations.length
        ? recommendations.map((item) => (
            `<option value="${escapeHtml(item.recommendation_key)}">${escapeHtml(item.title)} · ${escapeHtml(item.status)} · ${escapeHtml(item.target_layer)}</option>`
          )).join('')
        : '<option value="">当前 run 暂无蒸馏建议</option>';
      if (!recommendations.length) return;
      recommendationSelectNode.onchange = () => {
        const selected = recommendations.find((item) => item.recommendation_key === recommendationSelectNode.value);
        if (!selected) return;
        recommendationStageSelectNode.value = selected.stage;
        recommendationStatusSelectNode.value = selected.status === 'proposed' ? 'accepted' : selected.status;
        recommendationNotesNode.value = selected.resolution_notes || '';
        recommendationRegressionNode.value = selected.regression_result || '';
        recommendationChangeNode.value = selected.capability_change || '';
      };
      recommendationSelectNode.dispatchEvent(new Event('change'));
    }

    function collectRecommendations(run) {
      const stages = Array.isArray(run.stages) ? run.stages : [];
      return stages.flatMap((stage) => (
        (stage.recommendations || []).map((recommendation) => ({
          ...recommendation,
          stage: stage.stage,
        }))
      ));
    }

    async function loadRunTrend(runManifest, agentKey) {
      try {
        const response = await fetch(`/api/incubator/run-compare?path=${encodeURIComponent(runManifest)}&agent_key=${encodeURIComponent(agentKey || '')}`);
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '读取趋势失败');
        return payload.report || null;
      } catch (error) {
        return { error: error.message };
      }
    }

    function renderTrendBlock(report) {
      if (!report) return '';
      if (report.error) {
        return `<section class="section-block"><h2 style="font-size:20px; margin:0;">趋势摘要</h2><div class="empty">读取趋势失败：${escapeHtml(report.error)}</div></section>`;
      }
      const trajectory = report.trajectory || {};
      const trend = report.trend || {};
      const dominantLayers = (trajectory.dominant_target_layers || []).map((item) => `${item.name}(${item.count})`).join('，') || '暂无';
      return `
        <section class="section-block">
          <h2 style="font-size:20px; margin:0;">趋势摘要</h2>
          <div class="trend-grid">
            <div class="mini-card">
              <strong>gap 走势</strong>
              <div>${escapeHtml(trajectory.gap_trend || '暂无')}</div>
            </div>
            <div class="mini-card">
              <strong>能力增强走势</strong>
              <div>${escapeHtml(trajectory.validated_change_trend || '暂无')}</div>
            </div>
            <div class="mini-card">
              <strong>重点目标层</strong>
              <div>${escapeHtml(dominantLayers)}</div>
            </div>
          </div>
          <div class="summary-strip">
            <span class="pill">run ${escapeHtml(report.run_count || 0)}</span>
            <span class="pill warn">gap 序列 ${escapeHtml(JSON.stringify(trend.gap_series || []))}</span>
            <span class="pill ok">能力变化序列 ${escapeHtml(JSON.stringify(trend.validated_change_series || []))}</span>
          </div>
        </section>
      `;
    }

    function renderRecommendationBlock(run) {
      const recommendations = collectRecommendations(run);
      if (!recommendations.length) {
        return `<section class="section-block"><h2 style="font-size:20px; margin:0;">蒸馏建议</h2><div class="empty">当前 run 暂无蒸馏建议。</div></section>`;
      }
      return `
        <section class="section-block">
          <h2 style="font-size:20px; margin:0;">蒸馏建议</h2>
          <div class="recommendation-list">
            ${recommendations.map((item) => `
              <article class="recommendation-card">
                <div class="rec-head">
                  <span class="pill">${escapeHtml(item.stage)}</span>
                  <span class="pill warn">${escapeHtml(item.priority || 'P1')}</span>
                  <span class="pill ok">${escapeHtml(item.status || 'proposed')}</span>
                </div>
                <strong>${escapeHtml(item.title || item.recommendation_key)}</strong>
                <div>${escapeHtml(item.action || '')}</div>
                <div style="color:var(--muted);">${escapeHtml(item.rationale || '')}</div>
              </article>
            `).join('')}
          </div>
        </section>
      `;
    }

    function escapeHtml(text) {
      return String(text || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }
  </script>
</body>
</html>"""
