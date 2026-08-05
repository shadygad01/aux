/* ==========================================================================
   Gold Brain — Client Interactive App & Evaluator Engine
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initScenarios();
  initEvaluator();
  initReadinessMatrix();
});

// Pre-defined JSON scenarios mirroring Gold Brain decision logic
const SCENARIOS = {
  bullish: {
    contract_version: "1.0.0",
    symbol: "XAUUSD",
    timeframe: "H1",
    observed_at: "2026-08-05T11:30:00Z",
    source: "reviewed-manual-observation",
    structure: {
      bias: "BULLISH",
      break_of_structure: true,
      change_of_character: true
    },
    dealing_range: {
      low: 3300.0,
      high: 3400.0,
      current_price: 3340.0
    },
    liquidity: [
      {
        side: "SELL_SIDE",
        swept: true,
        displacement_confirmed: true
      }
    ]
  },
  bearish: {
    contract_version: "1.0.0",
    symbol: "XAUUSD",
    timeframe: "H1",
    observed_at: "2026-08-05T11:30:00Z",
    source: "reviewed-manual-observation",
    structure: {
      bias: "BEARISH",
      break_of_structure: true,
      change_of_character: true
    },
    dealing_range: {
      low: 3300.0,
      high: 3400.0,
      current_price: 3380.0
    },
    liquidity: [
      {
        side: "BUY_SIDE",
        swept: true,
        displacement_confirmed: true
      }
    ]
  },
  missing_liquidity: {
    contract_version: "1.0.0",
    symbol: "XAUUSD",
    timeframe: "H1",
    observed_at: "2026-08-05T11:30:00Z",
    source: "reviewed-manual-observation",
    structure: {
      bias: "BULLISH",
      break_of_structure: true,
      change_of_character: false
    },
    dealing_range: {
      low: 3300.0,
      high: 3400.0,
      current_price: 3350.0
    },
    liquidity: []
  },
  news_risk: {
    contract_version: "1.0.0",
    symbol: "XAUUSD",
    timeframe: "H1",
    observed_at: "2026-08-05T11:30:00Z",
    source: "reviewed-manual-observation",
    structure: {
      bias: "BULLISH",
      break_of_structure: true,
      change_of_character: true
    },
    dealing_range: {
      low: 3300.0,
      high: 3400.0,
      current_price: 3330.0
    },
    news_event: {
      title: "US NFP Payrolls",
      impact: "HIGH",
      active_window: true
    },
    liquidity: [
      {
        side: "SELL_SIDE",
        swept: true,
        displacement_confirmed: true
      }
    ]
  }
};

// 10 Core Capabilities & Readiness Scores from capability-readiness-matrix.md
const CAPABILITIES = [
  { name: "Collection", mission: "Acquire source facts without interpretation", score: 40, readiness: "Architecture Ready", risk: "Missing or stale facts", blocker: "Critical: no production collector." },
  { name: "Normalization", mission: "Convert facts into canonical units", score: 40, readiness: "Architecture Ready", risk: "Semantic corruption", blocker: "Major: unpublished contract." },
  { name: "Evidence", mission: "Create expiring weighted evidence", score: 60, readiness: "Implementation Ready", risk: "Provenance fragmentation", blocker: "Critical: lineage incomplete." },
  { name: "Knowledge", mission: "Preserve and query evidence memory", score: 60, readiness: "Implementation Ready", risk: "Search loss after restart", blocker: "Critical: restart safety." },
  { name: "Reasoning", mission: "Produce comprehensible reasoning story", score: 40, readiness: "Architecture Ready", risk: "Opaque/divergent reasoning", blocker: "Critical: Market Story missing." },
  { name: "Decision", mission: "Produce the sole Market Thesis", score: 40, readiness: "Architecture Ready", risk: "Conflicting decisions/scores", blocker: "Critical: canonical thesis absent." },
  { name: "Learning", mission: "Recommend governed improvements", score: 60, readiness: "Implementation Ready", risk: "Suggestions mistaken for authority", blocker: "Critical: durable memory absent." },
  { name: "Research", mission: "Test hypotheses & produce findings", score: 40, readiness: "Architecture Ready", risk: "Unsupported production claims", blocker: "Critical: finding/validation absent." },
  { name: "Publishing", mission: "Transform Market Thesis into Presentation", score: 20, readiness: "Prototype", risk: "Non-compliant public output", blocker: "Critical: no canonical presentation." },
  { name: "Monitoring", mission: "Measure health, readiness & governance", score: 20, readiness: "Prototype", risk: "False readiness & lost audit", blocker: "Critical: governance not executable." }
];

function initScenarios() {
  const scenarioBtns = document.querySelectorAll('.btn-scenario');
  const codeEditor = document.getElementById('json-editor');
  
  if (!codeEditor) return;
  
  // Set default scenario
  codeEditor.value = JSON.stringify(SCENARIOS.bullish, null, 2);
  
  scenarioBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      scenarioBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const key = btn.getAttribute('data-scenario');
      if (SCENARIOS[key]) {
        codeEditor.value = JSON.stringify(SCENARIOS[key], null, 2);
        evaluateObservation();
      }
    });
  });
}

function initEvaluator() {
  const evalBtn = document.getElementById('btn-evaluate');
  if (evalBtn) {
    evalBtn.addEventListener('click', evaluateObservation);
  }
}

function evaluateObservation() {
  const codeEditor = document.getElementById('json-editor');
  const verdictCard = document.getElementById('verdict-card');
  const verdictBadge = document.getElementById('verdict-badge');
  const verdictMeaning = document.getElementById('verdict-meaning');
  const verdictConfidence = document.getElementById('verdict-confidence');
  const reasonsContainer = document.getElementById('reasons-container');
  const jsonOutput = document.getElementById('json-output');

  try {
    const input = JSON.parse(codeEditor.value);
    
    // Client-side execution of Gold Brain decision rules
    let verdict = "WAIT";
    let meaning = "Fail-closed: conditions not fully met or missing evidence.";
    let confidence = "LOW";
    let score = 0.0;
    let reasons = [];
    let conflicts = [];
    let missing = [];

    // Check news gate
    if (input.news_event && input.news_event.active_window && input.news_event.impact === "HIGH") {
      verdict = "WAIT";
      meaning = "Execution paused due to active high-impact news event.";
      conflicts.push(`Active news event window: ${input.news_event.title}`);
    } 
    // Check mandatory liquidity evidence
    else if (!input.liquidity || input.liquidity.length === 0) {
      verdict = "WAIT";
      meaning = "Mandatory liquidity evidence is missing.";
      missing.push("Liquidity sweep evidence is required for a valid setup.");
    }
    // Check Bullish setup
    else if (input.structure && input.structure.bias === "BULLISH" && input.structure.break_of_structure) {
      const range = input.dealing_range;
      const discountThreshold = range.low + (range.high - range.low) * 0.5;
      
      if (range.current_price < discountThreshold) {
        const sweep = input.liquidity.find(l => l.side === "SELL_SIDE" && l.swept);
        if (sweep) {
          verdict = "BUY";
          meaning = "Search for a high-quality BUY setup";
          confidence = "HIGH";
          score = 1.0;
          reasons.push("Bullish structure has a confirmed break of structure.");
          reasons.push("Price is in discount, aligned with the BUY thesis.");
          reasons.push("Sell Side liquidity was swept with displacement confirmation.");
        } else {
          verdict = "WAIT";
          meaning = "Sell side liquidity sweep was not confirmed.";
          missing.push("Sell side liquidity sweep confirmation missing.");
        }
      } else {
        verdict = "WAIT";
        meaning = "Price is not in discount zone.";
        conflicts.push("Current price is above equilibrium; BUY requires discount.");
      }
    }
    // Check Bearish setup
    else if (input.structure && input.structure.bias === "BEARISH" && input.structure.break_of_structure) {
      const range = input.dealing_range;
      const premiumThreshold = range.low + (range.high - range.low) * 0.5;
      
      if (range.current_price > premiumThreshold) {
        const sweep = input.liquidity.find(l => l.side === "BUY_SIDE" && l.swept);
        if (sweep) {
          verdict = "SELL";
          meaning = "Search for a high-quality SELL setup";
          confidence = "HIGH";
          score = 1.0;
          reasons.push("Bearish structure has a confirmed break of structure.");
          reasons.push("Price is in premium, aligned with the SELL thesis.");
          reasons.push("Buy Side liquidity was swept with displacement confirmation.");
        } else {
          verdict = "WAIT";
          meaning = "Buy side liquidity sweep was not confirmed.";
          missing.push("Buy side liquidity sweep confirmation missing.");
        }
      } else {
        verdict = "WAIT";
        meaning = "Price is not in premium zone.";
        conflicts.push("Current price is below equilibrium; SELL requires premium.");
      }
    }

    // Construct response object
    const resultObj = {
      contract_version: "1.0.0",
      verdict: verdict,
      meaning: meaning,
      confidence: confidence,
      score: score,
      evaluated_at: new Date().toISOString(),
      observation_time: input.observed_at || new Date().toISOString(),
      reasons: reasons,
      conflicts: conflicts,
      missing_evidence: missing,
      policy_version: "v1-hypothesis-1",
      disclaimer: "Decision support only. The trader owns entry, stop, target, risk, and execution."
    };

    // Update UI
    verdictCard.className = `verdict-card verdict-${verdict}`;
    verdictBadge.textContent = verdict;
    verdictMeaning.textContent = meaning;
    verdictConfidence.textContent = `Confidence: ${confidence} (${(score * 100).toFixed(0)}%)`;

    let html = '';
    if (reasons.length > 0) {
      html += `<ul class="reasons-list">${reasons.map(r => `<li>${r}</li>`).join('')}</ul>`;
    }
    if (conflicts.length > 0) {
      html += `<ul class="reasons-list conflicts-list">${conflicts.map(c => `<li>${c}</li>`).join('')}</ul>`;
    }
    if (missing.length > 0) {
      html += `<ul class="reasons-list conflicts-list">${missing.map(m => `<li>${m}</li>`).join('')}</ul>`;
    }
    reasonsContainer.innerHTML = html;

    jsonOutput.textContent = JSON.stringify(resultObj, null, 2);

  } catch (err) {
    verdictCard.className = 'verdict-card verdict-WAIT';
    verdictBadge.textContent = 'ERROR';
    verdictMeaning.textContent = 'Invalid JSON input syntax';
    jsonOutput.textContent = err.toString();
  }
}

function initReadinessMatrix() {
  const tbody = document.getElementById('matrix-body');
  if (!tbody) return;

  tbody.innerHTML = CAPABILITIES.map(c => `
    <tr>
      <td>
        <div class="capability-name">
          <span>${c.name}</span>
        </div>
      </td>
      <td style="color: var(--text-secondary);">${c.mission}</td>
      <td>
        <span class="score-pill score-${c.score}">${c.score}% — ${c.readiness}</span>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: ${c.score}%; background-color: ${getScoreColor(c.score)};"></div>
        </div>
      </td>
      <td style="color: var(--text-secondary); font-size: 0.85rem;">${c.risk}</td>
      <td style="color: var(--amber-primary); font-size: 0.85rem; font-weight: 500;">${c.blocker}</td>
    </tr>
  `).join('');
}

function getScoreColor(score) {
  if (score >= 60) return 'var(--emerald-success)';
  if (score >= 40) return 'var(--sky-info)';
  if (score >= 20) return 'var(--amber-primary)';
  return 'var(--rose-danger)';
}
