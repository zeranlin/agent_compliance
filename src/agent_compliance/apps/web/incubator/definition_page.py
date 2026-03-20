from __future__ import annotations


def incubator_definition_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>需求定义层 · 智能体孵化与蒸馏工厂</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --panel: #ffffff;
      --line: #d5dfec;
      --ink: #1f2937;
      --muted: #5e6b7a;
      --accent: #1f5f8b;
      --accent-soft: #eef5fb;
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
      max-width: 1480px;
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
    .hero h1 { margin: 0; font-size: 34px; line-height: 1.15; }
    .meta {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--accent);
      font-weight: 700;
    }
    .hero p, .panel p {
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
      font-size: 16px;
    }
    .hero-actions {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      font-weight: 600;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 760px) minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    .panel {
      padding: 20px;
      display: grid;
      gap: 16px;
    }
    .panel h2 { margin: 0; font-size: 24px; }
    .section {
      border-top: 1px solid var(--line);
      padding-top: 14px;
      display: grid;
      gap: 12px;
    }
    label {
      display: grid;
      gap: 6px;
      font-size: 14px;
      font-weight: 700;
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
      font-family: inherit;
    }
    textarea {
      min-height: 96px;
      resize: vertical;
      line-height: 1.6;
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
    .status {
      padding: 12px 14px;
      border-radius: 12px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 600;
      min-height: 48px;
    }
    .tips {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fbfdff;
      padding: 14px;
      display: grid;
      gap: 8px;
    }
    .tips h3 { margin: 0; font-size: 18px; }
    .tips ul { margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.7; }
    .output-paths {
      display: grid;
      gap: 8px;
    }
    .viewer {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      background: #fcfdff;
      white-space: pre-wrap;
      line-height: 1.65;
      min-height: 420px;
      overflow: auto;
      font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
      font-size: 13px;
    }
    .summary-card {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: #fbfdff;
      display: grid;
      gap: 10px;
    }
    .summary-card h3 { margin: 0; font-size: 19px; }
    .summary-card ul { margin: 0; padding-left: 18px; }
    @media (max-width: 1100px) {
      .layout { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <section class="hero">
      <div class="meta">Requirement Definition</div>
      <h1>需求定义层</h1>
      <p>这一步只做一件事：把业务方“想要一个什么智能体”的自然语言需求，整理成可进入孵化工厂的业务蓝图确认稿。先定义清楚，再进入样例、设计和蒸馏。</p>
      <div class="hero-actions">
        <a href="/incubator">返回孵化控制台</a>
        <a href="/review-check">采购需求合规性检查智能体</a>
      </div>
    </section>
    <section class="layout">
      <section class="panel">
        <div>
          <h2>填写第一层需求</h2>
          <p>先把业务目标、输入输出、成功标准和不做事项说清楚。页面会自动生成“需求定义确认稿”，供你后续进入样例准备和蓝图设计。</p>
        </div>
        <label>
          智能体类型模板
          <select id="template-select"></select>
        </label>
        <label>
          智能体名称
          <input id="agent-name-input" placeholder="例如：政府采购采购需求调查智能体" />
        </label>
        <label>
          业务需求
          <textarea id="business-need-input" placeholder="例如：我要一个合规性检查智能体，用来对政府采购采购需求文档发布前进行风险检查。"></textarea>
        </label>
        <label>
          使用场景
          <textarea id="usage-scenario-input" placeholder="例如：采购人准备发布采购文件前，先做内部复核。"></textarea>
        </label>
        <label>
          用户角色（每行一个）
          <textarea id="user-roles-input" placeholder="采购人&#10;法务复核人员&#10;代理机构"></textarea>
        </label>
        <label>
          输入项（每行一个）
          <textarea id="input-documents-input" placeholder="采购需求文档&#10;招标文件&#10;预算说明"></textarea>
        </label>
        <label>
          目标输出（每行一个）
          <textarea id="expected-outputs-input" placeholder="风险问题清单&#10;法规依据&#10;建议改写"></textarea>
        </label>
        <label>
          成功标准（每行一个）
          <textarea id="success-criteria-input" placeholder="能稳定输出主问题&#10;能带出证据位置&#10;结果可供人工改稿"></textarea>
        </label>
        <label>
          不做什么（每行一个，可选）
          <textarea id="non-goals-input" placeholder="不直接替代正式裁判&#10;不自动代替法务签发"></textarea>
        </label>
        <label>
          约束条件（每行一个，可选）
          <textarea id="constraints-input" placeholder="需支持本地离线运行&#10;需保留结构化导出"></textarea>
        </label>
        <button id="generate-definition-btn" type="button">生成需求定义确认稿</button>
        <div id="definition-status" class="status">先填完左侧内容，再生成第一层确认稿。</div>
        <div class="tips">
          <h3>这一页要达成什么</h3>
          <ul>
            <li>把业务需求翻成可执行的产品定义。</li>
            <li>明确第一版的能力边界和不做事项。</li>
            <li>生成可落盘、可复用、可进入后续孵化步骤的确认稿。</li>
          </ul>
        </div>
      </section>
      <section class="panel">
        <div>
          <h2>确认稿预览</h2>
          <p>右侧会显示自动生成的产品定义、能力边界和第一版目标。确认这一步清楚之后，再进入样例准备和蓝图设计。</p>
        </div>
        <div id="definition-summary" class="summary-card">
          <h3>尚未生成确认稿</h3>
          <p>生成后，这里会先给出结构化摘要。</p>
        </div>
        <div class="output-paths" id="definition-outputs"></div>
        <div id="definition-viewer" class="viewer">生成后，这里会显示需求定义确认稿 Markdown。</div>
      </section>
    </section>
  </div>
  <script>
    const templateNode = document.getElementById('template-select');
    const agentNameNode = document.getElementById('agent-name-input');
    const businessNeedNode = document.getElementById('business-need-input');
    const usageScenarioNode = document.getElementById('usage-scenario-input');
    const userRolesNode = document.getElementById('user-roles-input');
    const inputDocumentsNode = document.getElementById('input-documents-input');
    const expectedOutputsNode = document.getElementById('expected-outputs-input');
    const successCriteriaNode = document.getElementById('success-criteria-input');
    const nonGoalsNode = document.getElementById('non-goals-input');
    const constraintsNode = document.getElementById('constraints-input');
    const statusNode = document.getElementById('definition-status');
    const summaryNode = document.getElementById('definition-summary');
    const outputsNode = document.getElementById('definition-outputs');
    const viewerNode = document.getElementById('definition-viewer');

    loadTemplates();
    document.getElementById('generate-definition-btn').addEventListener('click', generateDefinitionDraft);
    templateNode.addEventListener('change', applyTemplateHint);

    async function loadTemplates() {
      try {
        const response = await fetch('/api/incubator/blueprint-templates');
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '加载模板失败');
        const templates = payload.templates || [];
        templateNode.innerHTML = templates.map((item) => (
          `<option value="${escapeHtml(item.template_key)}">${escapeHtml(item.template_name)} · ${escapeHtml(item.agent_type)}</option>`
        )).join('');
        applyTemplateHint();
      } catch (error) {
        statusNode.textContent = `加载模板失败：${error.message}`;
      }
    }

    function applyTemplateHint() {
      const templateKey = templateNode.value;
      if (agentNameNode.value.trim()) return;
      const hints = {
        review: '政府采购合规性检查智能体',
        budget_analysis: '政府采购预算需求智能体',
        demand_research: '政府采购需求调查智能体',
        comparison_eval: '政府采购对比评估智能体',
      };
      agentNameNode.value = hints[templateKey] || '';
    }

    async function generateDefinitionDraft() {
      statusNode.textContent = '正在生成需求定义确认稿...';
      try {
        const response = await fetch('/api/incubator/definition', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            template_key: templateNode.value,
            agent_name: agentNameNode.value.trim(),
            business_need: businessNeedNode.value.trim(),
            usage_scenario: usageScenarioNode.value.trim(),
            user_roles: userRolesNode.value,
            input_documents: inputDocumentsNode.value,
            expected_outputs: expectedOutputsNode.value,
            success_criteria: successCriteriaNode.value,
            non_goals: nonGoalsNode.value,
            constraints: constraintsNode.value,
          }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '生成失败');
        const draft = payload.draft || {};
        summaryNode.innerHTML = `
          <h3>${escapeHtml(draft.agent_name || '需求定义确认稿')}</h3>
          <p><strong>产品定义：</strong>${escapeHtml(draft.product_definition || '')}</p>
          <p><strong>第一版目标：</strong>${escapeHtml(draft.first_version_goal || '')}</p>
          <div>
            <strong>能力边界：</strong>
            <ul>${(draft.capability_boundary || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
          </div>
        `;
        outputsNode.innerHTML = `
          <div><strong>JSON：</strong>${escapeHtml(payload.outputs?.json || '')}</div>
          <div><strong>Markdown：</strong>${escapeHtml(payload.outputs?.markdown || '')}</div>
        `;
        viewerNode.textContent = payload.preview_markdown || '';
        statusNode.textContent = '需求定义确认稿已生成。建议确认这一步后，再进入样例准备和蓝图设计。';
      } catch (error) {
        statusNode.textContent = `生成需求定义确认稿失败：${error.message}`;
      }
    }

    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }
  </script>
</body>
</html>
"""


__all__ = ["incubator_definition_html"]
