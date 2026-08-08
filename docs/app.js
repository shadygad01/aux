/* ==========================================================================
   Gold Brain — Pure Artifact Consumer & UI Renderer
   Zero browser-side business logic. Consumes only Python-generated artifacts.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initNotifications();
  loadAllArtifacts();
  // Auto-refresh live artifacts every 30 seconds
  setInterval(loadAllArtifacts, 30000);
});

/* ==========================================================================
   Buy-signal browser notifications
   Fires a Notification whenever the published verdict transitions to BUY.
   ========================================================================== */
const NOTIFY_PREF_KEY = 'goldBrainNotifyEnabled';
const NOTIFY_LAST_VERDICT_KEY = 'goldBrainLastVerdict';

function initNotifications() {
  const btn = document.getElementById('notify-toggle');
  if (!btn) return;

  if (!('Notification' in window)) {
    btn.textContent = '🔕 Notifications unsupported';
    btn.disabled = true;
    return;
  }

  updateNotifyButton(btn);

  btn.addEventListener('click', async () => {
    if (Notification.permission === 'denied') return;

    if (Notification.permission === 'default') {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        updateNotifyButton(btn);
        return;
      }
      localStorage.setItem(NOTIFY_PREF_KEY, 'true');
    } else {
      const currentlyOn = isNotifyEnabled();
      localStorage.setItem(NOTIFY_PREF_KEY, currentlyOn ? 'false' : 'true');
    }

    if (isNotifyEnabled()) {
      // Re-arm so turning alerts on re-checks the latest verdict immediately,
      // notifying right away if it is already BUY.
      localStorage.removeItem(NOTIFY_LAST_VERDICT_KEY);
      loadAllArtifacts();
    }

    updateNotifyButton(btn);
  });
}

function isNotifyEnabled() {
  return 'Notification' in window &&
    Notification.permission === 'granted' &&
    localStorage.getItem(NOTIFY_PREF_KEY) !== 'false';
}

function updateNotifyButton(btn) {
  if (Notification.permission === 'denied') {
    btn.textContent = '🔕 Notifications blocked';
    btn.classList.remove('notify-on');
    btn.disabled = true;
    return;
  }
  btn.disabled = false;
  if (isNotifyEnabled()) {
    btn.textContent = '🔔 Buy Alerts On';
    btn.classList.add('notify-on');
  } else {
    btn.textContent = '🔔 Enable Buy Alerts';
    btn.classList.remove('notify-on');
  }
}

function checkBuySignalNotification(decision) {
  if (!('Notification' in window)) return;

  const verdict = (decision.verdict || 'WAIT').toUpperCase();
  const lastVerdict = localStorage.getItem(NOTIFY_LAST_VERDICT_KEY);

  if (verdict === 'BUY' && lastVerdict !== 'BUY' && isNotifyEnabled()) {
    const scorePct = Math.round((decision.score || 0) * 100);
    const n = new Notification('Gold Brain — BUY signal', {
      body: `Confidence: ${decision.confidence} (${scorePct}%)\n${decision.meaning || ''}`,
      tag: 'gold-brain-buy-signal'
    });
    n.onclick = () => {
      window.focus();
      n.close();
    };
  }

  localStorage.setItem(NOTIFY_LAST_VERDICT_KEY, verdict);
}

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
      renderResearchStatus(hypArt.value);
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
      storyArt.status === 'fulfilled' ? storyArt.value : null
    );

  } catch (err) {
    console.error('Artifact loading error:', err);
  }
}

/* 1. HOME PAGE — Immediate Answers Header */
function renderDecisionHeader(artifact, thesisArtifact, executionArtifact) {
  const d = artifact.payload.decision;
  const rawVerdict = (d.verdict || 'WAIT').toUpperCase();

  checkBuySignalNotification(d);

  const priceEl = document.getElementById('val-gold-price');
  if (priceEl) {
    const price = artifact.payload.current_price;
    priceEl.textContent = typeof price === 'number' ? `$${price.toFixed(2)} / oz` : 'Unavailable';
  }

  // Format verdict: BUY ONLY, SELL ONLY, WAIT, NO OPINION
  let displayVerdict = 'WAIT';
  let badgeClass = 'thesis-WAIT';

  if (rawVerdict === 'BUY') {
    displayVerdict = 'BUY ONLY';
    badgeClass = 'thesis-BUY-ONLY';
  } else if (rawVerdict === 'SELL') {
    displayVerdict = 'SELL ONLY';
    badgeClass = 'thesis-SELL-ONLY';
  } else if (rawVerdict === 'WAIT') {
    displayVerdict = 'WAIT';
    badgeClass = 'thesis-WAIT';
  } else {
    displayVerdict = 'NO OPINION';
    badgeClass = 'thesis-NO-OPINION';
  }

  // Update Thesis Display
  const thesisBox = document.getElementById('thesis-badge');
  if (thesisBox) {
    thesisBox.className = `thesis-badge-large ${badgeClass}`;
    thesisBox.textContent = displayVerdict;
  }

  // Update Details
  const meaningEl = document.getElementById('thesis-meaning');
  if (meaningEl) meaningEl.textContent = d.meaning || 'Evaluated decision output';

  const confEl = document.getElementById('val-confidence');
  if (confEl) confEl.textContent = `${d.confidence} (${(d.score * 100).toFixed(0)}%)`;

  // Calculate Uncertainty = (1 - score)
  const uncertaintyVal = (1.0 - (d.score || 0)).toFixed(2);
  const uncEl = document.getElementById('val-uncertainty');
  if (uncEl) uncEl.textContent = `${uncertaintyVal} (${((1.0 - (d.score || 0)) * 100).toFixed(0)}%)`;

  // Setup Quality rendering
  const sqEl = document.getElementById('val-setup-quality');
  if (sqEl) {
    if (executionArtifact && executionArtifact.payload) {
      sqEl.textContent = `${executionArtifact.payload.setup_quality_score} / 100`;
    } else {
      sqEl.textContent = 'Unavailable';
    }
  }

  // Execution Readiness rendering
  const erEl = document.getElementById('val-execution-readiness');
  if (erEl) {
    if (executionArtifact && executionArtifact.payload && executionArtifact.payload.execution_readiness) {
      const er = executionArtifact.payload.execution_readiness;
      erEl.textContent = `${er.readiness_score} / 100 (${er.status})`;
    } else {
      erEl.textContent = 'Unavailable';
    }
  }

  // Timestamps & Meta
  const updateEl = document.getElementById('val-last-update');
  if (updateEl) updateEl.textContent = formatDate(d.evaluated_at || artifact.generated_at);

  const versionEl = document.getElementById('val-build-version');
  if (versionEl) versionEl.textContent = `v${d.contract_version || '1.0.0'}`;

  const commitEl = document.getElementById('val-commit-sha');
  if (commitEl) {
    const sha = artifact.commit || 'local';
    commitEl.textContent = sha === 'local' ? 'local' : sha.substring(0, 8);
  }
}

function renderDecisionError(err) {
  const thesisBox = document.getElementById('thesis-badge');
  if (thesisBox) {
    thesisBox.className = 'thesis-badge-large thesis-NO-OPINION';
    thesisBox.textContent = 'NO OPINION';
  }
  const meaningEl = document.getElementById('thesis-meaning');
  if (meaningEl) meaningEl.textContent = `Failed to load decision artifact: ${err}`;
}

/* 2. WHY PANEL */
function renderWhyPanel(artifact) {
  const d = artifact.payload.decision;

  // Supporting Evidence
  const suppEl = document.getElementById('supporting-evidence');
  if (suppEl) {
    if (d.reasons && d.reasons.length > 0) {
      suppEl.innerHTML = d.reasons.map(r => `<li>${r}</li>`).join('');
    } else {
      suppEl.innerHTML = `<span class="empty-evidence">None / No supporting evidence reported.</span>`;
    }
  }

  // Contradicting Evidence
  const confEl = document.getElementById('contradicting-evidence');
  if (confEl) {
    if (d.conflicts && d.conflicts.length > 0) {
      confEl.innerHTML = d.conflicts.map(c => `<li>${c}</li>`).join('');
    } else {
      confEl.innerHTML = `<span class="empty-evidence">None / No contradicting evidence found.</span>`;
    }
  }

  // Missing Evidence
  const missEl = document.getElementById('missing-evidence');
  if (missEl) {
    if (d.missing_evidence && d.missing_evidence.length > 0) {
      missEl.innerHTML = d.missing_evidence.map(m => `<li>${m}</li>`).join('');
    } else {
      missEl.innerHTML = `<span class="empty-evidence">None / All required evidence items present.</span>`;
    }
  }
}

/* 3. MARKET STORY PANEL */
const STORY_STAGE_COLOR = {
  // Positive / actionable statuses
  BULLISH_FOR_GOLD: 'var(--emerald-buy)', BULLISH: 'var(--emerald-buy)',
  DISCOUNT: 'var(--emerald-buy)', VALIDATED: 'var(--emerald-buy)',
  BUY: 'var(--emerald-buy)', SELL_SIDE_SWEPT: 'var(--emerald-buy)', BUY_SIDE_SWEPT: 'var(--emerald-buy)',
  // Negative statuses
  BEARISH_FOR_GOLD: 'var(--rose-sell)', BEARISH: 'var(--rose-sell)',
  PREMIUM: 'var(--rose-sell)', SELL: 'var(--rose-sell)',
  // Neutral / incomplete / unknown
  NEUTRAL: 'var(--amber-wait)', EQUILIBRIUM: 'var(--amber-wait)', WAIT: 'var(--amber-wait)',
  NOT_VALIDATED: 'var(--amber-wait)', NOT_SWEPT: 'var(--amber-wait)', UNKNOWN: 'var(--slate-no-opinion)',
};

function storyStageColor(status) {
  return STORY_STAGE_COLOR[status] || 'var(--slate-no-opinion)';
}

function renderMarketStory(decisionArtifact, storyArtifact) {
  const container = document.getElementById('market-story-pipeline');
  if (!container) return;

  const hasStory = storyArtifact && storyArtifact.payload && storyArtifact.payload.story;
  if (!hasStory) {
    const hasDecision = decisionArtifact && decisionArtifact.payload && decisionArtifact.payload.decision;
    const d = hasDecision ? decisionArtifact.payload.decision : null;
    container.innerHTML = `
      <div style="font-size: 0.85rem; color: var(--text-muted); padding: 0.75rem; background: var(--bg-card-alt); border-radius: 6px;">
        <strong>Market Story unavailable.</strong> Current verdict: <span style="color: var(--gold-primary); font-weight: 700;">${d ? escapeHtml(d.verdict) : 'WAIT'}</span>
      </div>
    `;
    return;
  }

  const story = storyArtifact.payload.story;
  const nodes = story.stages.map((stage, i) => {
    const arrow = i > 0 ? '<div class="arrow-down">→</div>' : '';
    const color = storyStageColor(stage.status);
    return `
      ${arrow}
      <div class="story-node" title="${escapeHtml(stage.narrative)}">
        <div class="node-label">${escapeHtml(stage.title)}</div>
        <div class="node-status" style="color: ${color};">${escapeHtml(stage.status)}</div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="story-pipeline">${nodes}</div>
    <div style="margin-top: 1.25rem; font-size: 0.85rem; color: var(--text-muted); padding: 0.75rem; background: var(--bg-card-alt); border-radius: 6px;">
      ${escapeHtml(story.evolution_summary)}
    </div>
  `;
}

/* 4. SYSTEM STATUS — Capability Readiness */
function renderCapabilityReadiness(artifact) {
  const p = artifact.payload;
  const tableBody = document.getElementById('readiness-table-body');
  if (!tableBody) return;

  tableBody.innerHTML = p.capabilities.map(c => `
    <tr>
      <td style="font-weight: 700; color: var(--text-main);">${c.capability}</td>
      <td>
        <span class="score-pill score-${c.score}">${c.score}% — ${c.milestone}</span>
      </td>
      <td>${c.reason}</td>
    </tr>
  `).join('');
}

/* 4. SYSTEM STATUS — Institutional Health */
function renderInstitutionalHealth(artifact) {
  const p = artifact.payload;
  const healthBox = document.getElementById('health-summary-box');
  if (!healthBox) return;

  healthBox.innerHTML = `
    <div style="display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1rem;">
      <div class="metric-card">
        <div class="metric-label">Project Score</div>
        <div class="metric-val" style="color: var(--gold-primary); font-size: 1.8rem;">${p.project_score} / 100</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Readiness Band</div>
        <div class="metric-val" style="color: var(--amber-wait);">${p.readiness_band}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Avg Capability Score</div>
        <div class="metric-val">${p.average_capability_score}%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">P0 Critical Blockers</div>
        <div class="metric-val" style="color: var(--rose-sell);">${p.p0_debt_count}</div>
      </div>
    </div>

    <div style="font-size: 0.85rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--rose-sell);">P0 CRITICAL BLOCKERS:</div>
    <ul class="evidence-ul missing">
      ${p.critical_blockers.map(b => `<li>${b}</li>`).join('')}
    </ul>
  `;
}

/* 4. SYSTEM STATUS — Technical Debt */
function renderTechnicalDebt(artifact) {
  const p = artifact.payload;
  const debtBody = document.getElementById('debt-table-body');
  if (!debtBody) return;

  debtBody.innerHTML = p.items.map(i => `
    <tr>
      <td style="font-family: var(--font-mono); color: var(--gold-primary);">${i.id}</td>
      <td><span class="score-pill score-0">${i.priority}</span></td>
      <td>${i.reason}</td>
      <td>${i.impact}</td>
      <td>${i.owner}</td>
      <td style="font-family: var(--font-mono);">${i.estimated_cost}</td>
    </tr>
  `).join('');
}

/* 4. SYSTEM STATUS — Research Status */
function renderResearchStatus(artifact) {
  const p = artifact.payload;
  const hypBody = document.getElementById('hyp-table-body');
  if (!hypBody) return;

  hypBody.innerHTML = p.hypotheses.map(h => `
    <tr>
      <td style="font-family: var(--font-mono); color: var(--gold-primary);">${h.id}</td>
      <td style="color: var(--text-main);">${h.hypothesis}</td>
      <td><span class="not-implemented-pill">${h.status}</span></td>
      <td>${h.initial_implementation}</td>
    </tr>
  `).join('');
}

/* Tab Switching Logic */
function initTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      btn.classList.add('active');
      const target = btn.getAttribute('data-tab');
      const targetEl = document.getElementById(`tab-${target}`);
      if (targetEl) targetEl.classList.add('active');
    });
  });
}

/* 4. SYSTEM STATUS — Context Capability */
function renderContextCapability(artifact) {
  const p = artifact.payload;
  const ctx = p.context;
  const ctxBox = document.getElementById('context-summary-box');
  if (!ctxBox) return;

  ctxBox.innerHTML = `
    <div style="font-size: 0.85rem; color: var(--gold-primary); font-weight: 700; margin-bottom: 0.75rem;">
      Canonical Context Statement: ${p.statement}
    </div>

    <div class="metrics-row">
      <div class="metric-card">
        <div class="metric-label">Session</div>
        <div class="metric-val" style="color: var(--emerald-buy);">${ctx.session}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">News Window</div>
        <div class="metric-val" style="color: var(--emerald-buy);">${ctx.news_window}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Macro Regime</div>
        <div class="metric-val">${ctx.macro_regime}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Volatility Regime</div>
        <div class="metric-val">${ctx.volatility_regime}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Liquidity Conditions</div>
        <div class="metric-val">${ctx.liquidity_conditions}</div>
      </div>
    </div>

    <div style="margin-top: 1rem; font-size: 0.85rem; color: var(--text-sub);">
      <strong>Calendar Flags:</strong> 
      Holiday: <span style="font-family: var(--font-mono); color: var(--text-main);">${ctx.flags.is_holiday}</span> | 
      Weekend: <span style="font-family: var(--font-mono); color: var(--text-main);">${ctx.flags.is_weekend}</span> | 
      Market Open: <span style="font-family: var(--font-mono); color: var(--emerald-buy);">${ctx.flags.is_market_open}</span> | 
      Market Close: <span style="font-family: var(--font-mono); color: var(--text-main);">${ctx.flags.is_market_close}</span>
    </div>
  `;
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

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderOpportunityIdentity(artifact) {
  if (!artifact || !artifact.payload) return;
  const payload = artifact.payload;
  const curr = payload.current_opportunity;
  const prev = payload.previous_opportunity;

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

}

function renderRiskGuidance(risk) {
  if (!risk || risk.risk_status !== 'OK') {
    const reason = risk ? risk.risk_status : 'UNAVAILABLE';
    return `Unavailable (${escapeHtml(reason)})`;
  }
  return `SL ${risk.stop_loss_price} | TP ${risk.target_price} | R:R 1:${risk.risk_reward} ` +
    `(${escapeHtml(risk.invalidation_source)} invalidation, ${escapeHtml(risk.target_source)} target)`;
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
      <div><strong>Risk Guidance:</strong> ${renderRiskGuidance(mtf.risk_guidance)}</div>
      <div><strong>Higher Timeframe Bias (${escapeHtml(mtf.higher_timeframe)}):</strong> ${escapeHtml(mtf.htf_bias)} (Setup Quality: ${mtf.setup_quality_score}/100)</div>
      <div style="margin-top: 0.5rem; font-weight: 600; color: var(--gold);">Cascade Validation Notes:</div>
      <ul style="padding-left: 1.2rem; margin-top: 0.2rem; color: var(--text-sub); font-size: 0.82rem;">${reasons}</ul>
    `;
  }
}

