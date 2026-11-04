# 3-Minute Demo Video Script: IncidentMind & Hindsight Memory

**Project:** IncidentMind — Autonomous SRE Agent with Hindsight Memory  
**Target Duration:** 2.5 – 3.0 minutes  
**Format:** Screen recording with voiceover (talking-head webcam in corner recommended)

---

## 5 High-Performing YouTube Titles
1. *I Built an SRE Agent That Remembers How We Fixed Past Outages*
2. *Why Your AI Agents Forget Everything (And How Hindsight Fixes It)*
3. *Stop Re-Diagnosing the Same Outage: Autonomous SRE with Memory*
4. *How Agent Memory Reduced Our Incident MTTR from 45 Mins to 90 Secs*
5. *Vector RAG Wasn't Enough: Building Stateful DevOps Agents with Hindsight*

---

## Scene-by-Scene Script with On-Screen Cues

### Scene 1: The Hook & Intro (0:00 – 0:30)
* **[Screen Cue]**: Camera on you or full-screen view of the **IncidentMind** dark-mode dashboard at `http://localhost:8000`. Show the header with the active Hindsight memory bank badge.
* **[Voiceover]**:
  > *"Hey everyone, my name is Ali. If you have ever been on-call at 3:00 AM when production crashes, you know the sinking feeling of staring at cryptic error logs while downtime minutes tick away.*
  >
  > *Most AI agents today suffer from severe amnesia. When an outage happens, they treat your stack like Day 1 and give you generic advice like 'restart your pods'.*
  >
  > *I built **IncidentMind**—an autonomous SRE triage agent powered by **Hindsight**, a long-term memory engine from Vectorize. Instead of forgetting, IncidentMind remembers every past incident post-mortem and verified runbook, turning repeated outages into instant 90-second fixes."*

---

### Scene 2: The Problem — The Stateless Agent Fails (0:30 – 1:00)
* **[Screen Cue]**: On the UI left pane, toggle **Hindsight Memory** to **OFF** (turns red: `STATLESS / OFF`). Click the preset **"Kafka DB Pool Starvation"**. Show the raw alert text. Click **"Run SRE Triage"**.
* **[Voiceover]**:
  > *"Let's see what happens without memory. We're receiving a critical P1 alert: `order-service-prod` database latency has spiked to 12,000ms, Kafka consumer lag is above 40,000 messages, and `asyncpg` is throwing 'TooManyConnectionsError'.*
  >
  > *Watch the agent's diagnosis. Because memory is OFF, it gives us generic textbook advice: 'check CPU usage', 'grep logs', and 'restart the Kubernetes deployment'.*
  >
  > *In production, restarting these pods would trigger a connection stampede and crash the entire database. The stateless agent doesn't know that, because it has no memory."*

---

### Scene 3: The Demo — Hindsight Recall & Precision Fix (1:00 – 2:15)
* **[Screen Cue]**: Toggle **Hindsight Memory** back to **ACTIVE** (turns emerald green). Click **"Side-by-Side Compare (Memory vs Stateless)"**. Highlight the live stream on the right pane updating with `[RECALL]` latency and match score.
* **[Voiceover]**:
  > *"Now, let's flip Hindsight Memory ON and run the side-by-side comparison.*
  >
  > *Look at the right pane: IncidentMind just called `arecall()` against our Hindsight memory bank `incidentmind-sre-cluster`. In 42 milliseconds, Hindsight's hybrid semantic and keyword search matched **Incident #412** with 98% confidence.*
  >
  > *Look at the diagnosis now on the right: it immediately recognizes the exact root cause: two weeks ago, a Kafka consumer batch size change caused worker connection pool exhaustion on Aurora.*
  >
  > *And instead of a dangerous pod restart, it prescribes the exact verified remediation: throttling `KAFKA_MAX_POLL_RECORDS` to 50 and executing this specific `pg_terminate_backend` query to clear idle locks. MTTR dropped from 45 minutes to 90 seconds."*

---

### Scene 4: Retaining New Memory in Real-Time (2:15 – 2:40)
* **[Screen Cue]**: Click **"+ Retain Post-Mortem"** button in the top navigation. Enter a quick new incident (e.g. `INC-604: Payment worker unbuffered stream OOM`). Click **"Retain into Bank"**. Point to the `[RETAIN]` event badge appearing at the top of the memory stream.
* **[Voiceover]**:
  > *"What happens when a new outage is resolved? We simply click 'Retain Post-Mortem'.*
  >
  > *IncidentMind calls Hindsight's `aretain()` API. Hindsight extracts key entities, updates observation links, and persists this knowledge into the bank. The next time anyone on the team faces this error, the agent will instantly recall it."*

---

### Scene 5: Wrap Up & Key Takeaway (2:40 – 3:00)
* **[Screen Cue]**: Back to camera / clean UI view. Show GitHub repo and links.
* **[Voiceover]**:
  > *"The big takeaway for me: raw vector RAG simply wasn't enough for DevOps logs. Hindsight's multi-signal recall combining temporal anchors and graph relations made the agent genuinely useful under pressure.*
  >
  > *The full code, FastAPI backend, and pre-seeded incident bank are open source in the repo below. Check out Hindsight and give your agents a real memory. Thanks for watching!"*
