// IncidentMind Interactive Dashboard Controller

let scenarios = {};
let currentScenarioKey = 'kafka_db_starvation';

document.addEventListener('DOMContentLoaded', async () => {
  initElements();
  await loadScenarios();
  await refreshStats();
  setupEventListeners();
});

let elements = {};

function initElements() {
  elements = {
    alertInput: document.getElementById('alertInput'),
    runTriageBtn: document.getElementById('runTriageBtn'),
    compareModeBtn: document.getElementById('compareModeBtn'),
    memoryToggle: document.getElementById('memoryToggle'),
    toggleStatus: document.getElementById('toggleStatus'),
    outputBody: document.getElementById('outputBody'),
    metaMode: document.getElementById('metaMode'),
    metaModel: document.getElementById('metaModel'),
    streamLog: document.getElementById('streamLog'),
    knowledgeCards: document.getElementById('knowledgeCards'),
    retainedCountBadge: document.getElementById('retainedCountBadge'),
    bankIdBadge: document.getElementById('bankIdBadge'),
    comparisonContainer: document.getElementById('comparisonContainer'),
    closeCompareBtn: document.getElementById('closeCompareBtn'),
    statelessContent: document.getElementById('statelessContent'),
    hindsightContent: document.getElementById('hindsightContent'),
    openRetainModalBtn: document.getElementById('openRetainModalBtn'),
    retainModal: document.getElementById('retainModal'),
    closeModalBtn: document.getElementById('closeModalBtn'),
    cancelModalBtn: document.getElementById('cancelModalBtn'),
    retainForm: document.getElementById('retainForm'),
    refreshStatsBtn: document.getElementById('refreshStatsBtn'),
  };
}

async function loadScenarios() {
  try {
    const res = await fetch('/api/scenarios');
    scenarios = await res.json();
    selectScenario(currentScenarioKey);
  } catch (err) {
    console.error('Failed to load scenarios', err);
  }
}

function selectScenario(key) {
  currentScenarioKey = key;
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.scenario === key);
  });
  if (scenarios[key]) {
    elements.alertInput.value = scenarios[key].raw_alert;
  }
}

async function refreshStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    
    elements.retainedCountBadge.textContent = data.total_incidents_retained;
    elements.bankIdBadge.textContent = data.bank_id;

    // Render Stream Log
    renderStreamLog(data.recent_events || []);
    
    // Render Knowledge Cards
    renderKnowledgeCards();
  } catch (err) {
    console.error('Failed to refresh stats', err);
  }
}

function renderStreamLog(events) {
  if (!events.length) {
    elements.streamLog.innerHTML = '<div class="stream-item"><span class="stream-desc">No memory events recorded yet.</span></div>';
    return;
  }

  elements.streamLog.innerHTML = events.map(ev => {
    const isRecall = ev.type === 'RECALL';
    const badgeClass = isRecall ? 'recall' : 'retain';
    const timeStr = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '';
    
    let detailText = '';
    if (isRecall) {
      detailText = `Query: "${ev.query}" &bull; Top Score: <span class="stream-score">${(ev.top_score * 100).toFixed(0)}%</span> (${ev.latency_ms}ms)`;
    } else {
      detailText = `Retained post-mortem: <strong>${ev.incident_id}</strong> (${ev.service})`;
    }

    return `
      <div class="stream-item">
        <div class="stream-item-header">
          <span class="stream-badge ${badgeClass}">${ev.type}</span>
          <span class="stream-time">${timeStr}</span>
        </div>
        <div class="stream-desc">${detailText}</div>
      </div>
    `;
  }).join('');
}

function renderKnowledgeCards() {
  // Static representation of core memory units
  const cards = [
    {
      id: "INC-412",
      service: "order-service-prod",
      title: "PostgreSQL Pool Starvation under Kafka Batch Ingestion",
      cause: "Kafka batch size 500 spawned unthrottled concurrent DB queries, exhausting max_connections.",
      tags: ["postgres", "kafka", "pool-exhaustion"]
    },
    {
      id: "INC-489",
      service: "auth-session-cache",
      title: "Redis OOM Eviction via Leaked JWT Revocation Keys",
      cause: "Revoked tokens written without explicit TTL, accumulating 8M keys and triggering OOM.",
      tags: ["redis", "auth", "oom-leak"]
    },
    {
      id: "INC-531",
      service: "billing-gateway",
      title: "Kubernetes Ingress 502 Bad Gateway during Canary Rollout",
      cause: "Canary container port changed to 9090 while readinessProbe remained on 8080.",
      tags: ["kubernetes", "ingress-502", "helm-canary"]
    }
  ];

  elements.knowledgeCards.innerHTML = cards.map(c => `
    <div class="k-card" onclick="loadRelatedScenario('${c.id}')">
      <div class="k-card-header">
        <span class="k-card-id">${c.id}</span>
        <span class="k-card-service">${c.service}</span>
      </div>
      <div class="k-card-title">${c.title}</div>
      <div class="k-card-cause">${c.cause}</div>
      <div class="k-card-tags">
        ${c.tags.map(t => `<span class="k-tag">#${t}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

window.loadRelatedScenario = function(incId) {
  if (incId === 'INC-412') selectScenario('kafka_db_starvation');
  if (incId === 'INC-489') selectScenario('redis_oom_spike');
  if (incId === 'INC-531') selectScenario('k8s_canary_502');
};

function setupEventListeners() {
  // Preset buttons
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selectScenario(btn.dataset.scenario);
    });
  });

  // Memory toggle
  elements.memoryToggle.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    elements.toggleStatus.textContent = isChecked ? 'ACTIVE' : 'OFF';
    elements.toggleStatus.className = `status-indicator ${isChecked ? 'on' : 'off'}`;
    elements.metaMode.textContent = `Mode: ${isChecked ? 'Hindsight ON' : 'Stateless (Memory OFF)'}`;
  });

  // Run Triage
  elements.runTriageBtn.addEventListener('click', runTriage);

  // Compare Mode
  elements.compareModeBtn.addEventListener('click', runComparison);
  elements.closeCompareBtn.addEventListener('click', () => {
    elements.comparisonContainer.classList.add('hidden');
  });

  // Refresh
  elements.refreshStatsBtn.addEventListener('click', refreshStats);

  // Retain Modal
  elements.openRetainModalBtn.addEventListener('click', () => {
    elements.retainModal.classList.remove('hidden');
  });
  elements.closeModalBtn.addEventListener('click', () => {
    elements.retainModal.classList.add('hidden');
  });
  elements.cancelModalBtn.addEventListener('click', () => {
    elements.retainModal.classList.add('hidden');
  });

  // Retain Form Submit
  elements.retainForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      incident_id: document.getElementById('incId').value,
      service: document.getElementById('incService').value,
      title: document.getElementById('incTitle').value,
      symptoms: document.getElementById('incSymptoms').value,
      root_cause: document.getElementById('incRootCause').value,
      resolution_runbook: document.getElementById('incRunbook').value,
      tags: document.getElementById('incTags').value.split(',').map(s => s.trim()).filter(Boolean)
    };

    try {
      const res = await fetch('/api/retain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        elements.retainModal.classList.add('hidden');
        elements.retainForm.reset();
        await refreshStats();
      }
    } catch (err) {
      alert('Error retaining incident: ' + err.message);
    }
  });
}

async function runTriage() {
  const alertText = elements.alertInput.value.trim();
  if (!alertText) {
    alert('Please enter or select an incident alert');
    return;
  }

  const useMemory = elements.memoryToggle.checked;
  elements.runTriageBtn.disabled = true;
  elements.runTriageBtn.innerHTML = '<span>⏳ Diagnosing...</span>';
  elements.outputBody.innerHTML = '<div class="placeholder-state"><p>Querying agent reasoner & Hindsight memory bank...</p></div>';

  try {
    const res = await fetch('/api/triage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        alert_text: alertText,
        use_memory: useMemory
      })
    });
    const data = await res.json();
    elements.metaMode.textContent = `Mode: ${data.mode}`;
    elements.metaModel.textContent = `Provider: ${data.provider}`;
    elements.outputBody.innerHTML = renderMarkdown(data.response);

    await refreshStats();
  } catch (err) {
    elements.outputBody.innerHTML = `<div style="color:#f43f5e">Triage error: ${err.message}</div>`;
  } finally {
    elements.runTriageBtn.disabled = false;
    elements.runTriageBtn.innerHTML = '<span class="btn-icon">⚡</span> Run SRE Triage';
  }
}

async function runComparison() {
  const alertText = elements.alertInput.value.trim();
  if (!alertText) {
    alert('Please enter or select an incident alert first');
    return;
  }

  elements.comparisonContainer.classList.remove('hidden');
  elements.statelessContent.innerHTML = '<em>Running stateless analysis...</em>';
  elements.hindsightContent.innerHTML = '<em>Querying Hindsight memory & synthesizing runbook...</em>';
  elements.comparisonContainer.scrollIntoView({ behavior: 'smooth' });

  try {
    const [statelessRes, hindsightRes] = await Promise.all([
      fetch('/api/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_text: alertText, use_memory: false })
      }).then(r => r.json()),
      fetch('/api/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_text: alertText, use_memory: true })
      }).then(r => r.json())
    ]);

    elements.statelessContent.innerHTML = renderMarkdown(statelessRes.response);
    elements.hindsightContent.innerHTML = renderMarkdown(hindsightRes.response);

    await refreshStats();
  } catch (err) {
    elements.statelessContent.innerHTML = `Error: ${err.message}`;
    elements.hindsightContent.innerHTML = `Error: ${err.message}`;
  }
}

// Lightweight Markdown Renderer for clean technical presentation
function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/`([^`]+)`/gim, '<code style="background:#0b101c;padding:2px 5px;border-radius:4px;color:#38bdf8;">$1</code>')
    .replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>')
    .replace(/```bash([\s\S]*?)```/gim, '<pre><code class="language-bash">$1</code></pre>')
    .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
    .replace(/\n\n/gim, '<br><br>');
  return html;
}
