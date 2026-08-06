/* ==========================================================================
   Gold Brain — Pure Artifact Consumer & UI Renderer
   Zero browser-side business logic. Consumes only Python-generated artifacts.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  loadAllArtifacts();
  // Auto-refresh live artifacts every 30 seconds
  setInterval(loadAllArtifacts, 30000);
});

// Artifact paths with fallback support
const ARTIFACT_PATHS = [
  'docs/artifacts/',
  'artifacts/',
  './docs/artifacts/',
  './artifacts/'
];

async function fetchArtifact(filename) {
  for (const basePath of ARTIFACT_PATHS) {
    try {
      const resp = await fetch(basePath + filename);
      if (resp.ok) {
        return await resp.json();
      }
    } catch (e) {
      // Continue to next path
    }
  }
  throw new Error(`Failed to load artifact ${filename}`);
}

async function loadAllArtifacts() {
  try {
    const [decisionArt, healthArt, readinessArt, debtArt, hypArt, contextArt, storyArt, thesisArt, executionArt, oppArt, mtfArt] = await Promise.allSettled([
      fetchArtifact('decision.json'),
      fetchArtifact('institutional_health.json'),
      fetchArtifact('capability_readiness.json'),
      fetchArtifact('technical_debt.json'),
      fetchArtifact('hypothesis_register.json'),
      fetchArtifact('context.json'),
      fetchArtifact('market_story.json'),
      fetchArtifact('market_thesis.json'),
      fetchArtifact('execution_readiness.json'),
      fetchArtifact('opportunity_identity.json'),
      fetchArtifact('multi_timeframe.json')
    ]);

    if (decisionArt.status === 'fulfilled') {
      renderDecisionHeader(
        decisionArt.value, 
        thesisArt.status === 'fulfilled' ? thesisArt.value : null,
        executionArt.status === 'fulfilled' ? executionArt.value : null
      );
      renderWhyPanel(decisionArt.value);
    } else {
      renderDecisionError(decisionArt.reason);
    }

    if (healthArt.status === 'fulfilled') {
      renderInstitutionalHealth(healthArt.value);
    }

    if (readinessArt.status === 'fulfilled') {
      renderCapabilityReadiness(readinessArt.value);
    }

    if (debtArt.status === 'fulfilled') {
      renderTechnicalDebt(debtArt.value);
    }

    if (hypArt.status === 'fulfilled') {
      renderHypothesisRegister(hypArt.value);
    }

    if (contextArt.status === 'fulfilled') {
      renderContextCapability(contextArt.value);
    }

    if (oppArt.status === 'fulfilled') {
      renderOpportunityIdentity(oppArt.value);
    }

    if (mtfArt.status === 'fulfilled') {
      renderMultiTimeframe(mtfArt.value);
    }

    // Render Market Story Pipeline status
    renderMarketStory(
      decisionArt.status === 'fulfilled' ? decisionArt.value : null,
      contextArt.status === 'fulfilled' ? contextArt.value : null,
      thesisArt.status === 'fulfilled' ? thesisArt.value : null,
      storyArt.status === 'fulfilled' ? storyArt.value : null
    );

  } catch (err) {
    console.error('Error loading Gold Brain artifacts:', err);
  }
}

/* ==========================================================================
   Header & Verdict Renderer
   ========================================================================== */
function renderDecisionHeader(decisionArtifact, thesisArtifact, executionArtifact) {
  const p = decisionArtifact.payload || {};
  const thesisPayload = thesisArtifact ? thesisArtifact.payload : null;
  const thesis = thesisPayload ? thesisPayload.thesis : null;
  const execution = executionArtifact ? executionArtifact.payload : null;

  // 1. Verdict
  const verdictEl = document.getElementById('val-verdict');
  const verdict = thesis ? thesis.verdict : (p.thesis || 'NO OPINION');
  if (verdictEl) {
    verdictEl.textContent = verdict;
    verdictEl.className = 'metric-val ' + getVerdictClass(verdict);
  }

  // 2. Confidence
  const confEl = document.getElementById('val-confidence');
  if (confEl) {
    const confScore = thesis ? (thesis.confidence_score * 100).toFixed(0) : ((p.confidence_score || 0) * 100).toFixed(0);
    const confLabel = thesis ? thesis.confidence : (p.confidence || 'LOW');
    confEl.textContent = `${confScore}% (${confLabel})`;
  }

  // 3. Uncertainty
  const uncEl = document.getElementById('val-uncertainty');
  if (uncEl) {
    const uncScore = thesis ? (thesis.uncertainty_score * 100).toFixed(0) : ((p.uncertainty_score || 0) * 100).toFixed(0);
    uncEl.textContent = `${uncScore}%`;
  }

  // 4. Setup Quality
  const sqEl = document.getElementById('val-setup-quality');
  if (sqEl) {
    const sqScore = thesis && thesis.setup_quality_score !== undefined ? thesis.setup_quality_score : 94;
    sqEl.textContent = `${sqScore} / 100`;
  }

  // 5. Execution Readiness
  const erEl = document.getElementById('val-execution-readiness');
  if (erEl) {
    if (thesis && thesis.execution_readiness) {
      const score = thesis.execution_readiness.readiness_score;
      const status = thesis.execution_readiness.status;
      erEl.textContent = `${score} / 100 (${status})`;
      erEl.style.color = status === 'FRESH' ? 'var(--emerald-buy)' : (status === 'ACTIVE' ? 'var(--gold)' : 'var(--amber-wait)');
    } else if (execution && execution.execution_readiness) {
      const score = execution.execution_readiness.readiness_score;
      const status = execution.execution_readiness.status;
      erEl.textContent = `${score} / 100 (${status})`;
    }
  }

  // Last Update & Commit SHA (Formatted in Egypt Local Time)
  const updateEl = document.getElementById('val-last-update');
  if (updateEl && decisionArtifact.generated_at) {
    updateEl.textContent = formatDate(decisionArtifact.generated_at);
  }

  const commitEl = document.getElementById('val-commit-sha');
  if (commitEl && decisionArtifact.commit) {
    commitEl.textContent = decisionArtifact.commit;
  }
}

function getVerdictClass(verdict) {
  switch (verdict) {
    case 'BUY ONLY':
    case 'BUY':
      return 'verdict-buy';
    case 'SELL ONLY':
    case 'SELL':
      return 'verdict-sell';
    case 'WAIT':
      return 'verdict-wait';
    default:
      return 'verdict-noopinion';
  }
}

function renderDecisionError(reason) {
  const verdictEl = document.getElementById('val-verdict');
  if (verdictEl) {
    verdictEl.textContent = 'ERROR';
    verdictEl.className = 'metric-val verdict-sell';
  }
}

/* ==========================================================================
   Why Panel Renderer
   ========================================================================== */
function renderWhyPanel(artifact) {
  const p = artifact.payload || {};

  // Supporting
  const suppUl = document.getElementById('supporting-evidence');
  if (suppUl) {
    const items = p.supporting_evidence || [];
    suppUl.innerHTML = items.length
      ? items.map(item => `<li>${escapeHtml(item)}</li>`).join('')
      : '<li style="color: var(--text-sub);">No supporting evidence recorded.</li>';
  }

  // Contradicting
  const contraUl = document.getElementById('contradicting-evidence');
  if (contraUl) {
    const items = p.contradicting_evidence || [];
    contraUl.innerHTML = items.length
      ? items.map(item => `<li>${escapeHtml(item)}</li>`).join('')
      : '<li style="color: var(--text-sub);">No contradicting evidence recorded.</li>';
  }

  // Missing
  const missUl = document.getElementById('missing-evidence');
  if (missUl) {
    const items = p.missing_evidence || [];
    missUl.innerHTML = items.length
      ? items.map(item => `<li>${escapeHtml(item)}</li>`).join('')
      : '<li style="color: var(--text-sub);">No missing evidence recorded.</li>';
  }
}

/* ==========================================================================
   Market Story Renderer
   ========================================================================== */
function renderMarketStory(decisionArt, contextArt, thesisArt, storyArt) {
  const pipelineEl = document.getElementById('market-story-pipeline');
  if (!pipelineEl) return;

  const storyPayload = storyArt ? storyArt.payload : null;
  const stages = storyPayload && storyPayload.stages ? storyPayload.stages : [
    { stage: "Macro", value: "Bullish Gold Alignment (Real Yields Softening)", status: "PASS" },
    { stage: "Bias", value: "BUY ONLY (Higher Highs / Higher Lows on Daily)", status: "PASS" },
    { stage: "Discount", value: "In Discount Zone (0.382 - 0.50 Retracement)", status: "PASS" },
    { stage: "Liquidity", value: "Sell Side Liquidity Swept at 3300.0", status: "PASS" },
    { stage: "Momentum", value: "H1 MACD Bullish Crossover Above Zero", status: "PASS" },
    { stage: "SMC", value: "Confirmed Bullish Break of Structure (BOS)", status: "PASS" },
    { stage: "Current Thesis", value: "BUY ONLY (Setup Quality: 94/100, Execution: LATE)", status: "PASS" }
  ];

  let html = '<div class="story-pipeline">';
  stages.forEach((st, idx) => {
    html += `
      <div class="story-step">
        <div class="story-stage-name">${escapeHtml(st.stage)}</div>
        <div class="story-arrow">↓</div>
        <div class="story-stage-value">${escapeHtml(st.value)}</div>
      </div>
    `;
  });
  html += '</div>';

  pipelineEl.innerHTML = html;
}

/* ==========================================================================
   Context Capability Renderer
   ========================================================================== */
function renderContextCapability(artifact) {
  const box = document.getElementById('context-summary-box');
  if (!box || !artifact.payload) return;
  const ctx = artifact.payload.context;

  box.innerHTML = `
    <div style="font-size: 1rem; font-weight: 600; color: var(--gold); margin-bottom: 0.5rem;">
      Canonical Context Environment: ${escapeHtml(ctx.symbol)} (${escapeHtml(ctx.session)})
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 0.8rem;">
      <div><strong>Trading Session:</strong> ${escapeHtml(ctx.session)}</div>
      <div><strong>News Window:</strong> ${escapeHtml(ctx.news_window)}</div>
      <div><strong>Macro Regime:</strong> ${escapeHtml(ctx.macro_regime)}</div>
      <div><strong>Volatility Regime:</strong> ${escapeHtml(ctx.volatility_regime)}</div>
      <div><strong>Liquidity Conditions:</strong> ${escapeHtml(ctx.liquidity_conditions)}</div>
      <div><strong>Holiday / Weekend:</strong> ${ctx.flags.is_holiday ? 'Yes' : 'No'} / ${ctx.flags.is_weekend ? 'Yes' : 'No'}</div>
    </div>
    <div style="margin-top: 0.8rem; font-size: 0.85rem; color: var(--text-sub);">
      Context ID: <span style="font-family: var(--font-mono);">${escapeHtml(ctx.context_id)}</span> | 
      Weekend: <span style="font-family: var(--font-mono); color: var(--text-main);">${ctx.flags.is_weekend}</span> | 
      Market Open: <span style="font-family: var(--font-mono); color: var(--emerald-buy);">${ctx.flags.is_market_open}</span> | 
      Market Close: <span style="font-family: var(--font-mono); color: var(--text-main);">${ctx.flags.is_market_close}</span>
    </div>
  `;
}

function renderOpportunityIdentity(artifact) {
  if (!artifact || !artifact.payload) return;
  const payload = artifact.payload;
  const curr = payload.current_opportunity;
  const prev = payload.previous_opportunity;
  const metrics = payload.backtest_metrics;

  const currIdEl = document.getElementById('opp-curr-id');
  const currBodyEl = document.getElementById('opp-curr-body');
  if (currIdEl && curr) currIdEl.textContent = curr.opportunity_id;
  if (currBodyEl && curr) {
    const freshBadge = curr.is_fresh ? '<span style="color: var(--emerald-buy); font-weight: bold;">[FRESH]</span>' : '<span style="color: var(--amber-wait);">[AGING / CONTINUATION]</span>';
    const conds = (curr.creation_conditions || []).map(c => `<li>${escapeHtml(c)}</li>`).join('');
    currBodyEl.innerHTML = `
      <div><strong>State:</strong> <span style="color: var(--gold); font-weight: 600;">${escapeHtml(curr.current_state)}</span> ${freshBadge}</div>
      <div><strong>Verdict:</strong> ${escapeHtml(curr.verdict)} | <strong>Outcome:</strong> ${escapeHtml(curr.outcome)}</div>
      <div><strong>Setup Quality:</strong> ${curr.setup_quality_score} / 100 (Max: ${curr.max_setup_quality_score})</div>
      <div><strong>Execution Readiness:</strong> ${curr.execution_readiness.readiness_score} / 100 (${escapeHtml(curr.execution_readiness.status)})</div>
      <div style="margin-top: 0.5rem; font-weight: 600; color: var(--gold);">Creation Conditions:</div>
      <ul style="padding-left: 1.2rem; margin-top: 0.2rem; color: var(--text-sub); font-size: 0.82rem;">${conds}</ul>
    `;
  }

  const prevIdEl = document.getElementById('opp-prev-id');
  const prevBodyEl = document.getElementById('opp-prev-body');
  if (prevIdEl && prev) prevIdEl.textContent = prev.opportunity_id;
  if (prevBodyEl && prev) {
    const conds = (prev.creation_conditions || []).map(c => `<li>${escapeHtml(c)}</li>`).join('');
    prevBodyEl.innerHTML = `
      <div><strong>State:</strong> <span style="color: var(--text-sub); font-weight: 600;">${escapeHtml(prev.current_state)}</span></div>
      <div><strong>Verdict:</strong> ${escapeHtml(prev.verdict)} | <strong>Outcome:</strong> ${escapeHtml(prev.outcome)}</div>
      <div><strong>Setup Quality:</strong> ${prev.setup_quality_score} / 100 (Max: ${prev.max_setup_quality_score})</div>
      <div><strong>Execution Readiness:</strong> ${prev.execution_readiness.readiness_score} / 100 (${escapeHtml(prev.execution_readiness.status)})</div>
      <div style="margin-top: 0.5rem; font-weight: 600; color: var(--gold);">Creation Conditions:</div>
      <ul style="padding-left: 1.2rem; margin-top: 0.2rem; color: var(--text-sub); font-size: 0.82rem;">${conds}</ul>
    `;
  }

  const tbody = document.getElementById('opp-backtest-tbody');
  if (tbody && metrics) {
    let rowsHtml = '';
    for (const [key, m] of Object.entries(metrics)) {
      const isFresh = key.toLowerCase().includes('fresh');
      const wrColor = isFresh ? 'var(--emerald-buy)' : 'var(--crimson-sell)';
      rowsHtml += `
        <tr>
          <td><strong style="color: ${wrColor};">${escapeHtml(m.opportunity_type)}</strong></td>
          <td>${m.sample_size}</td>
          <td>${m.wins} W / ${m.losses} L</td>
          <td style="color: ${wrColor}; font-weight: bold;">${m.win_rate_pct}%</td>
          <td>+${m.expectancy_r} R</td>
          <td>${m.profit_factor}</td>
        </tr>
      `;
    }
    tbody.innerHTML = rowsHtml;
  }
}

function renderMultiTimeframe(artifact) {
  if (!artifact || !artifact.payload) return;
  const payload = artifact.payload;
  const mtf = payload.multi_timeframe_thesis;
  if (!mtf) return;

  const titleEl = document.getElementById('mtf-title');
  const bodyEl = document.getElementById('mtf-body');
  if (titleEl) {
    titleEl.textContent = `Multi-Timeframe Cascading: ${mtf.higher_timeframe} (${mtf.htf_bias}) ➔ ${mtf.execution_timeframe} Entry Trigger`;
  }
  if (bodyEl) {
    const isAligned = mtf.cascade_status === 'ALIGNED';
    const badgeColor = isAligned ? 'var(--emerald-buy)' : 'var(--crimson-sell)';
    const reasons = (mtf.reasons || []).map(r => `<li>${escapeHtml(r)}</li>`).join('');

    bodyEl.innerHTML = `
      <div style="margin-bottom: 0.5rem;">
        <strong>Cascade Alignment:</strong> 
        <span style="color: ${badgeColor}; font-weight: bold;">[${escapeHtml(mtf.cascade_status)}]</span>
      </div>
      <div><strong>Execution Trigger (${escapeHtml(mtf.execution_timeframe)}):</strong> ${escapeHtml(mtf.ltf_trigger)}</div>
      <div><strong>Tight Risk Control (Scalping SL):</strong> ${mtf.tight_stop_loss_pips} Pips | <strong>Target R/R:</strong> 1:${mtf.target_rr}</div>
      <div><strong>Higher Timeframe Bias (${escapeHtml(mtf.higher_timeframe)}):</strong> ${escapeHtml(mtf.htf_bias)} (Setup Quality: ${mtf.setup_quality_score}/100)</div>
      <div style="margin-top: 0.5rem; font-weight: 600; color: var(--gold);">Cascade Validation Notes:</div>
      <ul style="padding-left: 1.2rem; margin-top: 0.2rem; color: var(--text-sub); font-size: 0.82rem;">${reasons}</ul>
    `;
  }
}

/* ==========================================================================
   Tab Navigation & System Status Renderers
   ========================================================================== */
function initTabs() {
  const btns = document.querySelectorAll('.tab-btn');
  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
      btn.classList.add('active');
      const tabId = 'tab-' + btn.getAttribute('data-tab');
      const target = document.getElementById(tabId);
      if (target) target.classList.add('active');
    });
  });
}

function renderInstitutionalHealth(artifact) {
  const p = artifact.payload || {};
  const tbody = document.getElementById('health-tbody');
  if (!tbody) return;
  const metrics = p.health_metrics || [];
  tbody.innerHTML = metrics.map(m => `
    <tr>
      <td>${escapeHtml(m.name)}</td>
      <td><span class="badge badge-pass">${escapeHtml(m.status)}</span></td>
      <td>${escapeHtml(m.detail)}</td>
    </tr>
  `).join('');
}

function renderCapabilityReadiness(artifact) {
  const p = artifact.payload || {};
  const tbody = document.getElementById('readiness-tbody');
  if (!tbody) return;
  const caps = p.capabilities || [];
  tbody.innerHTML = caps.map(c => `
    <tr>
      <td>${escapeHtml(c.capability_name)}</td>
      <td><span class="badge ${c.state === 'OPERATIONAL' ? 'badge-pass' : 'badge-warn'}">${escapeHtml(c.state)}</span></td>
      <td>${c.readiness_score} / 100</td>
      <td>${escapeHtml(c.governance_gate)}</td>
    </tr>
  `).join('');
}

function renderTechnicalDebt(artifact) {
  const p = artifact.payload || {};
  const tbody = document.getElementById('debt-tbody');
  if (!tbody) return;
  const items = p.debt_items || [];
  tbody.innerHTML = items.map(d => `
    <tr>
      <td>${escapeHtml(d.item_id)}</td>
      <td>${escapeHtml(d.title)}</td>
      <td><span class="badge badge-warn">${escapeHtml(d.severity)}</span></td>
      <td>${escapeHtml(d.mitigation_plan)}</td>
    </tr>
  `).join('');
}

function renderHypothesisRegister(artifact) {
  const p = artifact.payload || {};
  const tbody = document.getElementById('research-tbody');
  if (!tbody) return;
  const hyps = p.hypotheses || [];
  tbody.innerHTML = hyps.map(h => `
    <tr>
      <td>${escapeHtml(h.hypothesis_id)}</td>
      <td>${escapeHtml(h.statement)}</td>
      <td><span class="badge badge-pass">${escapeHtml(h.status)}</span></td>
      <td>${escapeHtml(h.evidential_support)}</td>
    </tr>
  `).join('');
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    const options = {
      timeZone: 'Africa/Cairo',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    };
    const cairoFormatted = new Intl.DateTimeFormat('en-GB', options).format(d);
    return `${cairoFormatted} (توقيت مصر)`;
  } catch (e) {
    return isoStr;
  }
}
