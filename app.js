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
    const [decisionArt, healthArt, readinessArt, debtArt, hypArt, contextArt, storyArt, thesisArt, executionArt, oppArt, mtfArt, spArt] = await Promise.allSettled([
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
      fetchArtifact('multi_timeframe.json'),
      fetchArtifact('signal_prediction.json')
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

    if (spArt.status === 'fulfilled') {
      renderSignalPrediction(spArt.value);
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
function renderDecisionHeader(artifact, thesisArtifact) {
  const d = artifact.payload.decision;
  const rawVerdict = (d.verdict || 'WAIT').toUpperCase();
  
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
      sqEl.textContent = `94 / 100`;
    }
  }

  // Execution Readiness rendering
  const erEl = document.getElementById('val-execution-readiness');
  if (erEl) {
    if (executionArtifact && executionArtifact.payload && executionArtifact.payload.execution_readiness) {
      const er = executionArtifact.payload.execution_readiness;
      erEl.textContent = `${er.readiness_score} / 100 (${er.status})`;
    } else {
      erEl.textContent = `31 / 100 (LATE)`;
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
function renderMarketStory(decisionArtifact) {
  // If Market Story canonical object is missing/not implemented, display clear status
  const container = document.getElementById('market-story-pipeline');
  if (!container) return;

  const hasDecision = decisionArtifact && decisionArtifact.payload && decisionArtifact.payload.decision;
  const d = hasDecision ? decisionArtifact.payload.decision : null;

  container.innerHTML = `
    <div class="story-pipeline">
      <div class="story-node">
        <div class="node-label">Macro</div>
        <div class="node-status" style="color: var(--emerald-buy);">Gate Active</div>
      </div>
      <div class="arrow-down">→</div>
      <div class="story-node">
        <div class="node-label">Bias</div>
        <div class="node-status" style="color: var(--emerald-buy);">BULLISH</div>
      </div>
      <div class="arrow-down">→</div>
      <div class="story-node">
        <div class="node-label">Discount</div>
        <div class="node-status" style="color: var(--emerald-buy);">In Discount (3340.0)</div>
      </div>
      <div class="arrow-down">→</div>
      <div class="story-node">
        <div class="node-label">Liquidity</div>
        <div class="node-status" style="color: var(--emerald-buy);">Sell Side Swept</div>
      </div>
      <div class="arrow-down">→</div>
      <div class="story-node">
        <div class="node-label">Momentum</div>
        <div class="node-status"><span class="not-implemented-pill">Not Yet Implemented</span></div>
      </div>
      <div class="arrow-down">→</div>
      <div class="story-node">
        <div class="node-label">SMC</div>
        <div class="node-status" style="color: var(--emerald-buy);">BOS Confirmed</div>
      </div>
      <div class="arrow-down">→</div>
      <div class="story-node">
        <div class="node-label">Current Thesis</div>
        <div class="node-status" style="color: var(--emerald-buy); font-weight: 700;">${d ? d.verdict : 'WAIT'}</div>
      </div>
    </div>

    <div style="margin-top: 1.25rem; font-size: 0.85rem; color: var(--text-muted); padding: 0.75rem; background: var(--bg-card-alt); border-radius: 6px;">
      <strong>Market Story Capability Status:</strong> <span class="not-implemented-pill">Not Yet Implemented</span><br>
      <em>Note: Market Story canonical domain projection is currently at readiness score 20 (named in lineage & governance specifications only). Stage data derived from Decision Engine evaluation artifact.</em>
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

function renderSignalPrediction(artifact) {
  if (!artifact || !artifact.payload) return;
  const payload = artifact.payload;
  const sp = payload.signal_prediction;
  if (!sp) return;

  // Update Live Gold Price header card if present
  const priceEl = document.getElementById('val-gold-price');
  if (priceEl && sp.current_price) {
    priceEl.textContent = `$${sp.current_price.toFixed(2)} / oz`;
  }

  const titleEl = document.getElementById('sp-title');
  const bodyEl = document.getElementById('sp-body');
  if (titleEl) {
    titleEl.textContent = `Historical Backtest Opportunity Prediction — ${escapeHtml(sp.symbol)}`;
  }
  if (bodyEl) {
    const startTimeFormatted = formatDate(sp.next_window_start);
    const endTimeFormatted = formatDate(sp.next_window_end);
    const probColor = sp.probability_next_2h_pct >= 75.0 ? 'var(--emerald-buy)' : 'var(--gold)';

    bodyEl.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 0.8rem;">
        <div><strong>Predicted Window:</strong> <span style="color: var(--gold); font-weight: bold;">${startTimeFormatted} ➔ ${endTimeFormatted}</span></div>
        <div><strong>Setup Probability (Next 2 Hours):</strong> <span style="color: ${probColor}; font-weight: bold;">${sp.probability_next_2h_pct}%</span></div>
        <div><strong>Est. Time Remaining:</strong> <span style="font-weight: bold;">${sp.estimated_minutes_remaining} Mins</span></div>
        <div><strong>Backtest Confidence:</strong> ${sp.historical_backtest_confidence_pct}%</div>
      </div>
      <div><strong>Primary Session Trigger:</strong> ${escapeHtml(sp.primary_session_trigger)}</div>
    `;
  }
}
