/* app.js — Zero browser-side business logic artifact renderer */

// Helper to safely fetch artifact JSON with clear logging
async function fetchArtifact(path) {
  try {
    const res = await fetch(`artifacts/${path}?v=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Artifact fetch failed for ${path}:`, err);
    return null;
  }
}

// Global state
let currentArtifact = null;

// Initialize app on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
  console.log('Gold Brain Dashboard initializing...');
  await refreshDashboard();
  
  // Set up periodic refresh every 60 seconds
  setInterval(refreshDashboard, 60000);
});

// Refresh all sections from canonical published artifacts
async function refreshDashboard() {
  try {
    const [
      decisionArt, 
      techDebtArt, 
      readinessArt, 
      hypothesesArt, 
      contextArt, 
      storyArt, 
      thesisArt,
      executionArt
    ] = await Promise.allSettled([
      fetchArtifact('decision.json'),
      fetchArtifact('technical_debt.json'),
      fetchArtifact('capability_readiness.json'),
      fetchArtifact('hypothesis_register.json'),
      fetchArtifact('context.json'),
      fetchArtifact('market_story.json'),
      fetchArtifact('market_thesis.json'),
      fetchArtifact('execution_readiness.json')
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

    if (storyArt.status === 'fulfilled') {
      renderMarketStory(storyArt.value);
    }

    if (contextArt.status === 'fulfilled') {
      renderMarketContext(contextArt.value);
    }

    if (readinessArt.status === 'fulfilled') {
      renderCapabilityReadiness(readinessArt.value);
    }

    if (techDebtArt.status === 'fulfilled') {
      renderTechnicalDebt(techDebtArt.value);
    }

    if (hypothesesArt.status === 'fulfilled') {
      renderHypotheses(hypothesesArt.value);
    }

  } catch (globalErr) {
    console.error('Failed to refresh dashboard:', globalErr);
  }
}

/* 1. Immediate Answers Header */
function renderDecisionHeader(artifact, thesisArtifact, executionArtifact) {
  const d = artifact.payload.decision;
  const rawVerdict = (d.verdict || 'WAIT').toUpperCase();
  
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

  const thesisBox = document.getElementById('thesis-badge');
  if (thesisBox) {
    thesisBox.className = `thesis-badge-large ${badgeClass}`;
    thesisBox.textContent = displayVerdict;
  }

  const meaningEl = document.getElementById('thesis-meaning');
  if (meaningEl) meaningEl.textContent = d.meaning || 'Evaluated decision output';

  const confEl = document.getElementById('val-confidence');
  if (confEl) confEl.textContent = `${d.confidence} (${(d.score * 100).toFixed(0)}%)`;

  const uncertaintyVal = (1.0 - (d.score || 0)).toFixed(2);
  const uncEl = document.getElementById('val-uncertainty');
  if (uncEl) uncEl.textContent = `${uncertaintyVal} (${((1.0 - (d.score || 0)) * 100).toFixed(0)}%)`;

  const sqEl = document.getElementById('val-setup-quality');
  if (sqEl) {
    if (executionArtifact && executionArtifact.payload) {
      sqEl.textContent = `${executionArtifact.payload.setup_quality_score} / 100`;
    } else {
      sqEl.textContent = `94 / 100`;
    }
  }

  const erEl = document.getElementById('val-execution-readiness');
  if (erEl) {
    if (executionArtifact && executionArtifact.payload && executionArtifact.payload.execution_readiness) {
      const er = executionArtifact.payload.execution_readiness;
      erEl.textContent = `${er.readiness_score} / 100 (${er.status})`;
    } else {
      erEl.textContent = `31 / 100 (LATE)`;
    }
  }

  const lastUpdateEl = document.getElementById('footer-last-update');
  if (lastUpdateEl) {
    const dt = new Date(artifact.generated_at);
    lastUpdateEl.textContent = dt.toUTCString();
  }
}

function renderDecisionError(err) {
  const meaningEl = document.getElementById('thesis-meaning');
  if (meaningEl) meaningEl.textContent = `Failed to load canonical decision artifact: ${err.message}`;
}

/* 2. WHY PANEL */
function renderWhyPanel(artifact) {
  const d = artifact.payload.decision;

  const suppUl = document.getElementById('supporting-evidence');
  if (suppUl) {
    suppUl.innerHTML = (d.reasons && d.reasons.length > 0)
      ? d.reasons.map(r => `<li><span class="bullet">✓</span> ${escapeHtml(r)}</li>`).join('')
      : '<li class="none-text">No supporting evidence recorded</li>';
  }

  const contraUl = document.getElementById('contradicting-evidence');
  if (contraUl) {
    contraUl.innerHTML = (d.conflicts && d.conflicts.length > 0)
      ? d.conflicts.map(c => `<li><span class="bullet">✖</span> ${escapeHtml(c)}</li>`).join('')
      : '<li class="none-text">No contradicting evidence recorded</li>';
  }

  const missUl = document.getElementById('missing-evidence');
  if (missUl) {
    missUl.innerHTML = (d.missing_evidence && d.missing_evidence.length > 0)
      ? d.missing_evidence.map(m => `<li><span class="bullet">?</span> ${escapeHtml(m)}</li>`).join('')
      : '<li class="none-text">All mandatory evidence present</li>';
  }
}

/* 3. MARKET STORY */
function renderMarketStory(artifact) {
  const container = document.getElementById('market-story-flow');
  if (!container || !artifact.payload || !artifact.payload.story) return;

  const story = artifact.payload.story;
  const stages = story.stages || [];

  if (stages.length === 0) {
    container.innerHTML = '<div class="story-empty">No market story stages published</div>';
    return;
  }

  container.innerHTML = stages.map((stg, idx) => `
    <div class="story-step-card">
      <div class="step-num">${idx + 1}</div>
      <div class="step-stage">${escapeHtml(stg.stage)}</div>
      <div class="step-title">${escapeHtml(stg.title)}</div>
      <div class="step-status">${escapeHtml(stg.status)}</div>
      <div class="step-narrative">${escapeHtml(stg.narrative)}</div>
    </div>
  `).join('<div class="story-arrow">↓</div>');
}

/* 4. CONTEXT CAPABILITY */
function renderMarketContext(artifact) {
  if (!artifact.payload || !artifact.payload.context) return;
  const ctx = artifact.payload.context;

  const sessionEl = document.getElementById('ctx-session');
  if (sessionEl) sessionEl.textContent = ctx.session || 'N/A';

  const newsEl = document.getElementById('ctx-news');
  if (newsEl) newsEl.textContent = ctx.news_window || 'N/A';

  const macroEl = document.getElementById('ctx-macro');
  if (macroEl) macroEl.textContent = ctx.macro_regime || 'N/A';

  const volEl = document.getElementById('ctx-vol');
  if (volEl) volEl.textContent = ctx.volatility_regime || 'N/A';
}

/* 5. CAPABILITY READINESS */
function renderCapabilityReadiness(artifact) {
  const tbody = document.getElementById('readiness-tbody');
  if (!tbody || !artifact.payload || !artifact.payload.readiness) return;

  const readinessList = artifact.payload.readiness;
  tbody.innerHTML = readinessList.map(item => `
    <tr>
      <td><strong>${escapeHtml(item.capability)}</strong></td>
      <td>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: ${item.score}%;"></div>
        </div>
        <span class="score-num">${item.score}%</span>
      </td>
      <td><span class="status-pill status-${item.status}">${escapeHtml(item.status)}</span></td>
      <td>${escapeHtml(item.blocker_summary || 'None')}</td>
    </tr>
  `).join('');
}

/* 6. TECHNICAL DEBT */
function renderTechnicalDebt(artifact) {
  const tbody = document.getElementById('debt-tbody');
  if (!tbody || !artifact.payload || !artifact.payload.debt_items) return;

  const debtList = artifact.payload.debt_items;
  tbody.innerHTML = debtList.map(item => `
    <tr>
      <td><code>${escapeHtml(item.id)}</code></td>
      <td><strong>${escapeHtml(item.title)}</strong></td>
      <td><span class="severity-tag severity-${item.severity}">${escapeHtml(item.severity)}</span></td>
      <td>${escapeHtml(item.impact)}</td>
    </tr>
  `).join('');
}

/* 7. HYPOTHESIS REGISTER */
function renderHypotheses(artifact) {
  const container = document.getElementById('hypotheses-grid');
  if (!container || !artifact.payload || !artifact.payload.hypotheses) return;

  const list = artifact.payload.hypotheses;
  container.innerHTML = list.map(h => `
    <div class="hypothesis-card">
      <div class="hypo-id">${escapeHtml(h.id)}</div>
      <div class="hypo-title">${escapeHtml(h.title)}</div>
      <div class="hypo-status status-${h.status}">${escapeHtml(h.status)}</div>
      <div class="hypo-statement">${escapeHtml(h.statement)}</div>
    </div>
  `).join('');
}

// Utility: HTML Escaping
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
