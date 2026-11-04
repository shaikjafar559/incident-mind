# IncidentMind: Autonomous SRE Agent with Hindsight Memory

> **Persistent incident triage & root-cause memory for DevOps & Site Reliability Engineering teams using [Vectorize Hindsight](https://github.com/vectorize-io/hindsight).**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Memory Layer](https://img.shields.io/badge/Memory-Vectorize%20Hindsight-06b6d4.svg)](https://hindsight.vectorize.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 The Problem

When a critical production outage triggers at 3:00 AM, on-call SREs face an overwhelming flood of cryptic error logs, connection pool timeouts, and latency spikes. 

In traditional setups:
1. **Stateless LLMs** fail: They spit out boilerplate advice ("Check CPU", "Restart pod", "Check if DB is up").
2. **Knowledge fragmentation**: A senior engineer spent 4 hours resolving this exact Kafka batch pool starvation two weeks ago, but the runbook is buried in a Slack thread or Jira ticket.
3. **Repeated downtime**: Mean Time to Resolution (MTTR) remains 45+ minutes because the system cannot remember past incident post-mortems.

---

## 🧠 The Solution: IncidentMind with Hindsight

**IncidentMind** equips the SRE agent with persistent memory using [Vectorize's Hindsight memory framework](https://hindsight.vectorize.io/). 

Instead of treating every incident as day zero:
- **`retain()`**: When an incident is resolved, its symptoms, root cause analysis, and verified remediation commands are retained into the Hindsight memory bank (`incidentmind-sre-cluster`).
- **`recall()`**: When a new alarm triggers, the agent runs multi-signal semantic, graph, and temporal search across past post-mortems.
- **`reflect()`**: The agent maps current telemetry against historical incident patterns, pinpoints the root cause with confidence scoring, and outputs the proven runbook fix in seconds.

---

## ⚡ Architecture

```
                                      ┌─────────────────────────────────────┐
                                      │       Hindsight Memory Bank         │
                                      │   (Bank: incidentmind-sre-cluster)  │
                                      │   • Parallel Semantic & Graph Index │
                                      │   • Temporal Decay & Observations   │
                                      └──────────────────┬──────────────────┘
                                                         │
                                        arecall()        │    aretain()
                                     (Query & Scores)    │  (Post-Mortems)
                                                         ▼
┌───────────────────────────┐         ┌─────────────────────────────────────┐
│  Production Alert Stream  ├────────►│        IncidentMind Agent           │
│  (Datadog / Prometheus /  │         │   • Triage Reasoner (Groq / Core)   │
│   Kafka / K8s Ingress)    │         │   • Side-by-Side Memory Compare     │
└───────────────────────────┘         └──────────────────┬──────────────────┘
                                                         │
                                                         ▼
                                      ┌─────────────────────────────────────┐
                                      │        Dual-Pane Operations UI      │
                                      │   • Live Incident Triage Console    │
                                      │   • Real-Time Hindsight Stream Log  │
                                      │   • Knowledge Graph Inspector       │
                                      └─────────────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/your-username/incident-mind.git
cd incident-mind
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Set your keys if you want to connect to Hindsight Cloud or Groq:
```env
# Hindsight Cloud (Use promo code MEMHACK99 for $50 free credits at https://ui.hindsight.vectorize.io)
HINDSIGHT_API_URL=http://localhost:8888
HINDSIGHT_API_KEY=your_key_here

# Groq LLM (High-speed inference)
GROQ_API_KEY=gsk_your_groq_key
```

> **Note:** IncidentMind includes a built-in embedded fallback bank and internal deterministic reasoner. You can run and evaluate the entire application out-of-the-box immediately without any external API keys!

### 3. Start the Server

```bash
python -m backend.main
```

Open your browser at **`http://localhost:8000`**.

---

## 🎮 Interactive Demo Walkthrough (60 Seconds)

1. **Test Stateless Failure (Memory OFF)**:
   - Toggle **Hindsight Memory** to **OFF**.
   - Click the preset `Kafka DB Pool Starvation`.
   - Click **Run SRE Triage**.
   - *Result*: The agent returns generic troubleshooting steps ("Check host CPU", "Restart pod", "Check DB").

2. **Test Hindsight Precision (Memory ON)**:
   - Toggle **Hindsight Memory** to **ACTIVE**.
   - Click **Run SRE Triage**.
   - *Result*: The agent calls Hindsight `recall()`, identifies **INC-412** with 98% confidence, cites the Kafka batch size unthrottled worker concurrency, and provides the exact `pg_terminate_backend` kill command and `KAFKA_MAX_POLL_RECORDS` patch.

3. **1-Click Side-by-Side Comparison**:
   - Click **Side-by-Side Compare (Memory vs Stateless)** to see both outputs side-by-side.

4. **Live Memory Retention**:
   - Click **+ Retain Post-Mortem** in the top header.
   - Enter a new post-mortem (e.g. `INC-604` on `payment-worker-prod`).
   - Click **Retain into Bank**.
   - Watch the real-time Hindsight memory stream record the `[RETAIN]` event instantly.

---

## 📂 Project Structure

```
incident-mind/
├── backend/
│   ├── main.py            # FastAPI server & routes
│   ├── memory_engine.py   # Vectorize Hindsight client wrapper & bank manager
│   ├── agent.py           # SRE reasoning engine & memory-augmented prompt builder
│   └── seed_data.py       # High-fidelity incident post-mortems & alert scenarios
├── static/
│   ├── index.html         # Dual-pane SRE operations dashboard
│   ├── style.css          # Production dark-mode SRE UI styles
│   └── app.js             # Real-time event controller & live memory inspector
├── article.md             # In-depth technical article for dev publications
├── social_post.txt        # Andrej Karpathy-style LinkedIn post
├── video_script.md        # 3-minute demo video script with screen cues
├── thumbnail_prompt.txt   # Google Nano Banana thumbnail generator prompt
├── requirements.txt       # Project Python dependencies
└── README.md              # Project documentation
```

---

## 🔗 Official References

- **Hindsight GitHub**: [https://github.com/vectorize-io/hindsight](https://github.com/vectorize-io/hindsight)
- **Hindsight Documentation**: [https://hindsight.vectorize.io/](https://hindsight.vectorize.io/)
- **Vectorize Agent Memory Guide**: [https://vectorize.io/what-is-agent-memory](https://vectorize.io/what-is-agent-memory)
