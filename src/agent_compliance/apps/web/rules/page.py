from __future__ import annotations


def rules_html() -> str:
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
      <p><a href="/">返回审查工作台</a> · <a href="/review-check">打开采购人审查页</a> · <a href="/review-next">打开增强审查页</a> · <a href="/incubator">打开孵化工厂控制台</a></p>
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
    let selectedCandidateId = null;
    let currentRuleFilter = 'pending';

    loadRules();

    async function loadRules() {
      try {
        const response = await fetch('/api/rules');
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '加载失败');
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
      const primaryCatalogs = (payload.candidate_rules || []).map((item) => item.primary_catalog_name).filter(Boolean);
      const primaryDomains = (payload.candidate_rules || []).map((item) => item.primary_domain_key).filter(Boolean);
      const primaryAuthorities = (payload.candidate_rules || []).map((item) => item.primary_authority).filter(Boolean);
      const sceneText = primaryCatalogs.length ? `；主品目 ${Array.from(new Set(primaryCatalogs)).slice(0, 3).join('、')}` : '';
      const domainText = primaryDomains.length ? `；领域 ${Array.from(new Set(primaryDomains)).slice(0, 3).join('、')}` : '';
      const authorityText = primaryAuthorities.length ? `；主依据 ${Array.from(new Set(primaryAuthorities)).slice(0, 2).join('、')}` : '';
      rulesSummaryNode.textContent = `正式规则 ${payload.formal_rules.length} 条；候选规则 ${payload.candidate_rules.length} 条；待确认 ${summary.pending || 0} 条；已确认 ${summary.confirmed || 0} 条${sceneText}${domainText}${authorityText}。`;

      const governance = payload.formal_rule_summary || {};
      const familyBits = Object.entries(governance.family_counts || {})
        .map(([key, value]) => `${key} ${value}`)
        .join('，');
      const statusBits = Object.entries(governance.status_counts || {})
        .map(([key, value]) => `${key} ${value}`)
        .join('，');

      rulesColHeadNode.innerHTML = `
        <h2>候选规则</h2>
        <div class="meta">当前沉淀了 ${payload.candidate_rules.length} 条候选规则。治理摘要：正式规则 ${governance.total || 0} 条；状态分层 ${statusBits || '暂无'}；家族分布 ${familyBits || '暂无'}。</div>
        <div class="rules-toolbar">
          ${[
            ['pending', '待确认'],
            ['confirmed', '已确认'],
            ['deferred', '暂缓'],
            ['ignored', '忽略'],
            ['all', '全部'],
          ].map(([value, label]) => `<button class="filter-chip ${currentRuleFilter === value ? 'active' : ''}" data-rule-filter="${value}">${label}</button>`).join('')}
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
        : '<div class="empty">当前筛选条件下没有候选规则。</div>';
      rulesListNode.querySelectorAll('.rule-card').forEach((node) => {
        node.addEventListener('click', () => {
          selectedCandidateId = node.dataset.ruleId;
          renderRules(latestRulePayload);
        });
      });

      const selected = candidates.find((item) => item.candidate_rule_id === selectedCandidateId) || candidates[0];
      if (selected) {
        selectedCandidateId = selected.candidate_rule_id;
        renderRuleDetail(selected);
      } else {
        ruleDetailNode.innerHTML = '<div class="empty">选择左侧候选规则后，在这里查看详情和记录决策。</div>';
      }
    }

    function renderRuleCard(item) {
      const active = item.candidate_rule_id === selectedCandidateId ? 'active' : '';
      const sceneParts = [
        item.primary_catalog_name ? `主品目：${item.primary_catalog_name}` : '',
        item.primary_domain_key ? `领域：${item.primary_domain_key}` : '',
        item.is_mixed_scope ? '混合采购' : '',
      ].filter(Boolean).join(' · ');
      return `
        <article class="rule-card ${active}" data-rule-id="${escapeHtml(item.candidate_rule_id)}">
          <div class="rule-card-title">${escapeHtml(item.title)}</div>
          <div class="rule-card-meta">问题类型：${escapeHtml(item.issue_type || '未标注')}</div>
          <div class="rule-card-meta">依据：${escapeHtml(item.primary_authority || '待补充')}</div>
          <div class="rule-card-meta">${escapeHtml(sceneParts || '未标注品目场景')}</div>
          <div class="rule-card-meta">当前决策：${escapeHtml(decisionLabelText(item.decision))}</div>
        </article>
      `;
    }

    function renderRuleDetail(item) {
      const suggestions = item.learning_suggestions || {};
      const sceneParts = [
        item.primary_catalog_name ? `主品目：${item.primary_catalog_name}` : '',
        item.primary_domain_key ? `领域：${item.primary_domain_key}` : '',
        item.is_mixed_scope ? '混合采购' : '',
      ].filter(Boolean).join(' · ');

      ruleDetailNode.innerHTML = `
        <div class="detail-pair">
          <div class="detail-label">标题</div>
          <div class="detail-value">${escapeHtml(item.title)}</div>
        </div>
        <div class="detail-pair">
          <div class="detail-label">问题类型 / 场景</div>
          <div class="detail-value">${escapeHtml(item.issue_type || '未标注')} ｜ ${escapeHtml(sceneParts || '未标注')}</div>
        </div>
        <div class="detail-pair">
          <div class="detail-label">主依据</div>
          <div class="detail-value">${escapeHtml(item.primary_authority || '待补充')}</div>
        </div>
        <div class="detail-pair">
          <div class="detail-label">适用逻辑</div>
          <div class="detail-value">${escapeHtml(item.applicability_logic || '待补充')}</div>
        </div>
        <div class="detail-pair">
          <div class="detail-label">建议规则</div>
          <div class="detail-value">${escapeHtml((suggestions.rules || []).join('\\n') || '暂无')}</div>
        </div>
        <div class="detail-pair">
          <div class="detail-label">建议 prompt</div>
          <div class="detail-value">${escapeHtml((suggestions.prompts || []).join('\\n') || '暂无')}</div>
        </div>
        <div class="detail-pair">
          <div class="detail-label">备注</div>
          <textarea id="rule-note" class="rule-note" placeholder="记录为什么确认入库、暂缓或忽略">${escapeHtml(item.note || '')}</textarea>
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
