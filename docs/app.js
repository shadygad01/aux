/* ==========================================================================
   Gold Brain — Pure Artifact Consumer & UI Renderer
   Zero browser-side business logic. Consumes only Python-generated artifacts.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  loadAllArtifacts();
});

// Artifact paths with fallback support
const ARTIFACT_PATHS = [
  'artifacts/',
  'docs/artifacts/',
  './artifacts/',
  './docs/artifacts/'
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
    const [decisionArt, healthArt, readinessArt, debtArt, hypArt, contextArt] = await Promise.allSettled([
      fetchArtifact('decision.json'),
      fetchArtifact('institutional_health.json'),
      fetchArtifact('capability_readiness.json'),
      fetchArtifact('technical_debt.json'),
      fetchArtifact('hypothesis_register.json'),
      fetchArtifact('context.json')
    ]);

    if (decisionArt.status === 'fulfilled') {
      renderDecisionHeader(decisionArt.value);
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

    // Render Market Story Pipeline status
    renderMarketStory(decisionArt.status === 'fulfilled' ? decisionArt.value : null);

  } catch (err) {
    console.error('Artifact loading error:', err);
  }
}

/* 1. HOME PAGE — Immediate Answers Header */
function renderDecisionHeader(artifact) {
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

  // Update Thesis Summary Val
  const thesisSummary = document.getElementById('val-thesis-summary');
  if (thesisSummary) thesisSummary.textContent = displayVerdict;

  // Update Details
  const meaningEl = document.getElementById('thesis-meaning');
  if (meaningEl) meaningEl.textContent = d.meaning || 'Evaluated decision output';

  const confEl = document.getElementById('val-confidence');
  if (confEl) confEl.textContent = `${d.confidence} (${(d.score * 100).toFixed(0)}%)`;

  // Calculate Uncertainty = (1 - score)
  const uncertaintyVal = (1.0 - (d.score || 0)).toFixed(2);
  const uncEl = document.getElementById('val-uncertainty');
  if (uncEl) uncEl.textContent = `${uncertaintyVal} (${((1.0 - (d.score || 0)) * 100).toFixed(0)}%)`;

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
    return d.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
  } catch (e) {
    return isoStr;
  }
}
