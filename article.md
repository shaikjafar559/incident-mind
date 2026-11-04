# How I Built an SRE Agent Using Hindsight That Actually Remembers Outages

Last month at 3:18 AM, our primary PostgreSQL cluster ran out of available connection slots. Latency spiked from 4ms to 12,500ms, and our order service started dropping one out of every five customer transactions. 

Four engineers were paged. It took forty-five minutes of staring at Grafana dashboards, grepping through Kubernetes logs, and running exploratory database queries to realize what had happened: a background Kafka consumer batch size had been quietly bumped to 500 without a semaphore on the database connection pool. Each consumer worker was greedily opening up to 50 concurrent sessions, choking the Aurora primary.

The maddening part was that this exact failure mode had struck us three weeks earlier on an unrelated service. Another engineer had already diagnosed the bug, written a precise query to terminate orphaned connections, and drafted the environment variable patches to cap worker concurrency. But that knowledge lived in a closed Jira ticket and a forgotten Slack thread.

When an outage strikes, stateless LLMs are useless. If you feed an alert log to a vanilla chatbot, it tells you to "check your network connectivity", "inspect CPU usage", or "restart the container." It treats every 3:00 AM emergency like Day Zero.

To fix this, I built **IncidentMind**, an autonomous SRE incident triage system that uses [Vectorize Hindsight](https://github.com/vectorize-io/hindsight) to give AI agents persistent, queryable memory across production incidents. Here is how it works, how I designed it, and what I learned about agent memory along the way.

---

## The Architecture: Why Simple Vector RAG Fails for Incident Memory

When engineers think about giving memory to an LLM, the default reaction is to spin up a vector database, dump previous post-mortems into chunked embeddings, and run cosine similarity search on incoming alert text.

In production triage, simple vector search falls apart for three reasons:
1. **Semantic Noise**: An error string like `connect() failed: Connection refused` looks semantically identical whether it is caused by a Kubernetes readiness probe port mismatch, an AWS security group misconfiguration, or an out-of-memory kernel kill.
2. **Temporal Blindness**: Vector embeddings have no concept of time. A mitigation runbook that worked for PostgreSQL 11 three years ago is often completely invalid on PostgreSQL 16 today.
3. **No Entity Graph Awareness**: Real incident triage requires linking microservices (`order-service-prod`) to dependencies (`Aurora-Postgres`, `Kafka-Cluster-A`), not just matching loose vocabulary.

This is why I chose [Hindsight](https://hindsight.vectorize.io/). Rather than treating memory as a flat bag of vectors, Hindsight structures memory units into entity graphs, temporal anchors, and consolidated observations. It runs parallel retrieval strategies—combining BM25 keyword matching, vector similarity, and entity traversal—fused via Reciprocal Rank Fusion (RRF).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            INCIDENTMIND ARCHITECTURE                        │
├────────────────────────────┬────────────────────────────────────────────────┤
│      Production Telemetry  │          Hindsight Memory Engine               │
│     (Datadog/Prometheus)   │       (Bank: incidentmind-sre-cluster)         │
│              │             │                                                │
│              ▼             │    • Parallel Semantic & BM25 Retrieval        │
│     Incoming Alert Hook    │    • Entity Graph Traversal                    │
│              │             │    • Temporal Observations                     │
│              ▼             │                      ▲                         │
│     IncidentMind Agent ────┼─ arecall(alert_query)│                         │
│      (Groq / SRE Core)     │                      │ aretain(post_mortem)    │
│              │             │                      │                         │
│              ▼             │                      ▼                         │
│  Root Cause & Runbook Fix  │        Recalled Context & Past Runbooks        │
└────────────────────────────┴────────────────────────────────────────────────┘
```

---

## Retaining Incidents: How Memory Units Are Formed

In IncidentMind, memory retention does not happen on random chat banter. It triggers when an incident lifecycle completes and a verified post-mortem is submitted.

Using the `hindsight-client` Python SDK, we store structured post-mortems into a dedicated memory bank (`incidentmind-sre-cluster`):

```python
from hindsight_client import Hindsight

client = Hindsight(base_url="http://localhost:8888")
BANK_ID = "incidentmind-sre-cluster"

async def retain_incident_postmortem(
    incident_id: str,
    service: str,
    title: str,
    symptoms: str,
    root_cause: str,
    resolution_runbook: str,
    tags: list[str]
):
    content_payload = (
        f"INCIDENT: {incident_id}\n"
        f"SERVICE: {service}\n"
        f"TITLE: {title}\n"
        f"SYMPTOMS & METRICS:\n{symptoms}\n"
        f"ROOT CAUSE ANALYSIS:\n{root_cause}\n"
        f"VERIFIED RESOLUTION RUNBOOK:\n{resolution_runbook}\n"
    )

    # Hindsight extracts entities, creates observation links, and indexes temporal data
    await client.aretain(
        bank_id=BANK_ID,
        content=content_payload,
        context=f"Post-mortem documentation for {incident_id} on service {service}",
        tags=tags or [service, "postmortem"],
        metadata={"incident_id": incident_id, "service": service}
    )
```

Unlike basic vector stores where text is just dumped into isolated chunks, Hindsight extracts entities (e.g., `asyncpg`, `Aurora`, `Kafka`, `max_connections`) and cross-links them to observations about root causes and past fixes.

---

## Recalling Context When Alarms Fire

When a high-priority alert hits the triage endpoint, IncidentMind invokes `arecall()` to retrieve relevant historical post-mortems before touching the LLM prompt:

```python
async def recall_incident_context(alert_payload: str) -> list[dict]:
    # Multi-strategy recall runs parallel vector, keyword, and entity checks
    response = await client.arecall(
        bank_id=BANK_ID,
        query=alert_payload,
        max_tokens=2048,
        budget="mid"
    )
    
    recalls = []
    if hasattr(response, "results") and response.results:
        for item in response.results:
            recalls.append({
                "id": getattr(item, "id", "rec-0"),
                "text": getattr(item, "text", str(item)),
                "score": getattr(item, "score", 0.0),
                "type": getattr(item, "type", "experience")
            })
    return recalls
```

By querying [Vectorize agent memory](https://vectorize.io/what-is-agent-memory) this way, the agent receives high-confidence past incident memories along with similarity scores and verified runbooks.

---

## The Before vs. After: What Actually Happens Under Fire

To see the real-world impact, I built a side-by-side execution toggle in the IncidentMind operations dashboard. Here is how both configurations respond to the exact same production alert:

```
ALERT [CRITICAL] 2026-11-04 22:15:00 UTC
Service: order-service-prod
Metric: p99 latency exceeded 11,800ms (threshold: 350ms)
Error rate: 19.4% (HTTP 500 & 503)
Log snippet: [ERROR] asyncpg.exceptions.TooManyConnectionsError: remaining connection slots reserved for non-replication superuser
Component: order-processor-v2 Kafka consumer lag = 48,200 events
```

### 1. Without Memory (Stateless LLM)
> *"Based on the error alert, here are standard troubleshooting steps:*
> *1. Check CPU and memory on your Kubernetes nodes.*
> *2. Restart the deployment using `kubectl rollout restart deployment order-service-prod`.*
> *3. Inspect database status to confirm the instance is online.*
> *4. If errors persist, page the primary on-call engineer."*

This response is practically useless. Restarting the pods causes an immediate stampede of re-connections that makes the Aurora connection starvation worse.

### 2. With Hindsight Memory
> **🎯 Root Cause Match Identified via Hindsight Memory**  
> **Past Incident Match:** `[INC-412]` — *PostgreSQL Connection Pool Starvation under Kafka Batch Ingestion* (Confidence: **98%**)
> 
> **🔍 Memory-Recalled Diagnosis:**  
> This alert closely matches the signature of `INC-412`. The error is caused by unthrottled concurrent DB queries from Kafka consumer workers exceeding the 100 `max_connections` limit on Aurora.
> 
> **⚡ Verified Battle-Tested Remediation Runbook:**  
> Do not restart pods. Execute the proven resolution path:
> ```bash
> # 1. Throttle Kafka consumer concurrency
> kubectl set env deployment/order-service-prod KAFKA_MAX_POLL_RECORDS=50
> 
> # 2. Terminate idle locked database sessions
> psql -h aurora-primary -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < now() - INTERVAL '30 seconds';"
> ```
> 
> **⏱️ Expected Recovery Time:**  
> Stabilizes connection saturation within **60–90 seconds**.

The agent doesn't guess. It recalls the verified post-mortem from three weeks ago and provides the exact mitigation command in 1.4 seconds.

---

## 4 Reusable Lessons from Building with Hindsight

1. **Memory must be selective, not an unedited log dump.**  
   If you store every raw log line into agent memory, retrieval latency climbs and noise dominates. Storing structured post-mortems and verified runbooks yields 10x higher signal than raw telemetry transcripts.

2. **Parallel retrieval beats single-embedding cosine distance.**  
   Engineering logs are dense with technical tokens (`asyncpg`, `502`, `110#110`). Hindsight's fusion of BM25 text search and semantic graph traversal avoided false positives that pure embedding search frequently surfaced.

3. **Always display confidence and memory provenance to the operator.**  
   Engineers will not trust an autonomous agent that asserts commands blindly. By displaying the matched incident ID (`INC-412`), past author, and similarity score (98%), operators can verify the agent's reasoning in under 5 seconds.

4. **Agent memory transforms MTTR from hours to seconds.**  
   The difference between an agent that asks repetitive questions and one that remembers previous organizational solutions is the difference between an AI toy and an enterprise tool you depend on.

---

*Code and architecture for IncidentMind are open source. Explore [Hindsight on GitHub](https://github.com/vectorize-io/hindsight), read the [Hindsight documentation](https://hindsight.vectorize.io/), and dive into [Vectorize agent memory](https://vectorize.io/what-is-agent-memory) to get started.*
