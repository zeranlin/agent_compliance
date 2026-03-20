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
      --warm: #fff8ef;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #eef4fb 0%, var(--bg) 100%);
    }
    a { color: var(--accent); text-decoration: none; }
    .app { max-width: 1480px; margin: 0 auto; padding: 24px; display: grid; gap: 16px; }
    .hero, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 10px 24px rgba(31, 95, 139, 0.08);
    }
    .hero { padding: 24px 28px; display: grid; gap: 10px; }
    .hero h1, .panel h2, .panel h3 { margin: 0; }
    .hero h1 { font-size: 34px; line-height: 1.15; }
    .meta {
      font-size: 12px; text-transform: uppercase; letter-spacing: .14em; color: var(--accent); font-weight: 700;
    }
    .hero p, .panel p { margin: 0; color: var(--muted); line-height: 1.7; font-size: 16px; }
    .hero-actions { display: flex; gap: 14px; flex-wrap: wrap; font-weight: 600; }
    .layout { display: grid; grid-template-columns: minmax(0, 780px) minmax(0, 1fr); gap: 16px; align-items: start; }
    .panel { padding: 20px; display: grid; gap: 16px; }
    label { display: grid; gap: 6px; font-size: 14px; font-weight: 700; color: var(--muted); }
    input, textarea {
      width: 100%; border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; font-size: 15px;
      color: var(--ink); background: #fff; font-family: inherit;
    }
    textarea { min-height: 96px; resize: vertical; line-height: 1.6; }
    button {
      border: none; border-radius: 12px; padding: 11px 16px; background: var(--accent); color: #fff; font-size: 15px;
      font-weight: 700; cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--accent); border: 1px solid var(--line); }
    .button-row { display: flex; gap: 12px; flex-wrap: wrap; }
    .status {
      padding: 12px 14px; border-radius: 12px; background: var(--accent-soft); color: var(--accent); font-weight: 600; min-height: 48px;
    }
    .card {
      border: 1px solid var(--line); border-radius: 14px; padding: 14px; background: #fbfdff; display: grid; gap: 10px;
    }
    .card.warm { background: var(--warm); }
    .card ul, .card ol { margin: 0; padding-left: 20px; color: var(--muted); line-height: 1.7; }
    .split { display: grid; gap: 12px; }
    .viewer {
      border: 1px solid var(--line); border-radius: 14px; padding: 16px; background: #fcfdff; white-space: pre-wrap; line-height: 1.65;
      min-height: 360px; overflow: auto; font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; font-size: 13px;
    }
    .hidden { display: none; }
    @media (max-width: 1100px) { .layout { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="app">
    <section class="hero">
      <div class="meta">Requirement Definition</div>
      <h1>需求定义层</h1>
      <p>这一步先不要求业务方自己选智能体类型。你先告诉工厂“想做什么”，系统会先辅助分析整体处理流程、推断更合适的智能体路线、列出待补充信息，再生成正式的需求定义确认稿。</p>
      <div class="hero-actions">
        <a href="/incubator">返回孵化控制台</a>
        <a href="/review-check">采购需求合规性检查智能体</a>
      </div>
    </section>
    <section class="layout">
      <section class="panel">
        <div>
          <h2>第一步：先说你想做什么</h2>
          <p>先说目标，不需要自己选模板。系统会先给出 6 步处理流程和待补充问题，再进入正式确认稿。</p>
        </div>
        <label>
          智能体名称（可先不填）
          <input id="agent-name-input" placeholder="例如：政府采购采购需求调查智能体" />
        </label>
        <label>
          核心业务需求
          <textarea id="business-need-input" placeholder="例如：我要一个合规性检查智能体，用来对政府采购采购需求文档发布前进行风险检查。"></textarea>
        </label>
        <label>
          已知使用场景（可先写一句）
          <textarea id="usage-scenario-input" placeholder="例如：采购人准备发布采购文件前，先做内部复核。"></textarea>
        </label>
        <div class="button-row">
          <button id="analyze-btn" type="button">先分析需求</button>
        </div>
        <div id="definition-status" class="status">先输入业务需求，系统会先帮你分析处理流程和待补充信息。</div>
        <div class="card warm">
          <h3>这一页的目标</h3>
          <ul>
            <li>先把模糊业务需求翻成一条可执行路线。</li>
            <li>先列出你还需要补什么，而不是一开始就让你选技术模板。</li>
            <li>确认补充信息后，再生成标准需求定义确认稿。</li>
          </ul>
        </div>
        <div id="confirmation-form" class="split hidden">
          <div>
            <h3>第二步：确认并补充信息</h3>
            <p>下面这些内容是系统根据你的需求自动推断出的默认项。你确认或改写之后，再生成正式确认稿。</p>
          </div>
          <label>
            用户角色（每行一个）
            <textarea id="user-roles-input"></textarea>
          </label>
          <label>
            输入项（每行一个）
            <textarea id="input-documents-input"></textarea>
          </label>
          <label>
            目标输出（每行一个）
            <textarea id="expected-outputs-input"></textarea>
          </label>
          <label>
            成功标准（每行一个）
            <textarea id="success-criteria-input"></textarea>
          </label>
          <label>
            不做什么（每行一个，可选）
            <textarea id="non-goals-input"></textarea>
          </label>
          <label>
            约束条件（每行一个，可选）
            <textarea id="constraints-input" placeholder="例如：需支持本地离线运行&#10;需保留结构化导出"></textarea>
          </label>
          <div class="button-row">
            <button id="generate-btn" type="button">生成需求定义确认稿</button>
          </div>
        </div>
      </section>
      <section class="panel">
        <div>
          <h2>分析结果与确认稿</h2>
          <p>右侧会先显示系统建议的处理流程、推断的智能体路线和待补充问题；确认后，再显示正式确认稿。</p>
        </div>
        <div id="analysis-summary" class="card">
          <h3>尚未开始分析</h3>
          <p>先点击“先分析需求”，这里会显示系统给你的处理流程和待补充问题。</p>
        </div>
        <div id="process-card" class="card hidden"></div>
        <div id="question-card" class="card hidden"></div>
        <div id="definition-summary" class="card hidden"></div>
        <div id="definition-outputs" class="card hidden"></div>
        <div id="definition-viewer" class="viewer">生成确认稿后，这里会显示 Markdown 预览。</div>
      </section>
    </section>
  </div>
  <script>
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
    const analysisSummaryNode = document.getElementById('analysis-summary');
    const processCardNode = document.getElementById('process-card');
    const questionCardNode = document.getElementById('question-card');
    const definitionSummaryNode = document.getElementById('definition-summary');
    const outputsNode = document.getElementById('definition-outputs');
    const viewerNode = document.getElementById('definition-viewer');
    const confirmationFormNode = document.getElementById('confirmation-form');

    let inferredTemplateKey = '';

    document.getElementById('analyze-btn').addEventListener('click', analyzeRequirement);
    document.getElementById('generate-btn').addEventListener('click', generateDefinitionDraft);

    async function analyzeRequirement() {
      statusNode.textContent = '正在分析需求并生成处理流程...';
      try {
        const response = await fetch('/api/incubator/definition', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'analyze',
            agent_name: agentNameNode.value.trim(),
            business_need: businessNeedNode.value.trim(),
            usage_scenario: usageScenarioNode.value.trim(),
          }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '分析失败');
        const guidance = payload.guidance || {};
        inferredTemplateKey = guidance.template_key || '';
        if (!agentNameNode.value.trim()) {
          agentNameNode.value = guidance.agent_name || '';
        }
        userRolesNode.value = (guidance.suggested_user_roles || []).join('\\n');
        inputDocumentsNode.value = (guidance.suggested_input_documents || []).join('\\n');
        expectedOutputsNode.value = (guidance.suggested_expected_outputs || []).join('\\n');
        successCriteriaNode.value = (guidance.suggested_success_criteria || []).join('\\n');
        nonGoalsNode.value = (guidance.suggested_non_goals || []).join('\\n');
        analysisSummaryNode.innerHTML = `
          <h3>${escapeHtml(guidance.agent_name || '需求分析结果')}</h3>
          <p><strong>建议路线：</strong>${escapeHtml(guidance.template_name || '')}</p>
          <p><strong>系统判断：</strong>${escapeHtml(guidance.product_direction || '')}</p>
        `;
        processCardNode.innerHTML = `
          <h3>建议处理流程</h3>
          <ol>${(guidance.handling_process || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ol>
        `;
        processCardNode.classList.remove('hidden');
        questionCardNode.innerHTML = `
          <h3>建议你补充确认的点</h3>
          <ul>${(guidance.clarification_questions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
        `;
        questionCardNode.classList.remove('hidden');
        confirmationFormNode.classList.remove('hidden');
        statusNode.textContent = '需求分析完成。请确认下面自动补出的默认项，再生成正式确认稿。';
      } catch (error) {
        statusNode.textContent = `需求分析失败：${error.message}`;
      }
    }

    async function generateDefinitionDraft() {
      statusNode.textContent = '正在生成需求定义确认稿...';
      try {
        const response = await fetch('/api/incubator/definition', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'generate',
            template_key: inferredTemplateKey,
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
        definitionSummaryNode.innerHTML = `
          <h3>${escapeHtml(draft.agent_name || '需求定义确认稿')}</h3>
          <p><strong>产品定义：</strong>${escapeHtml(draft.product_definition || '')}</p>
          <p><strong>第一版目标：</strong>${escapeHtml(draft.first_version_goal || '')}</p>
          <div><strong>能力边界：</strong><ul>${(draft.capability_boundary || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div>
        `;
        definitionSummaryNode.classList.remove('hidden');
        outputsNode.innerHTML = `
          <h3>产物路径</h3>
          <div><strong>JSON：</strong>${escapeHtml(payload.outputs?.json || '')}</div>
          <div><strong>Markdown：</strong>${escapeHtml(payload.outputs?.markdown || '')}</div>
        `;
        outputsNode.classList.remove('hidden');
        viewerNode.textContent = payload.preview_markdown || '';
        statusNode.textContent = '需求定义确认稿已生成。现在可以进入样例准备和蓝图设计。';
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
