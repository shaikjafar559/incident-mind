"""
Realistic Production Seed Incidents & Post-Mortems for IncidentMind.
These provide rich domain memory for the Hindsight memory engine.
"""

INITIAL_INCIDENTS = [
    {
        "incident_id": "INC-412",
        "service": "order-service-prod",
        "severity": "P1-CRITICAL",
        "timestamp": "2026-10-14T03:12:44Z",
        "title": "PostgreSQL Connection Pool Starvation under Kafka Batch Ingestion",
        "symptoms": (
            "HTTP 500 error rate spiked to 22%. PostgreSQL latency escalated from 4ms to 12,500ms. "
            "Pod logs indicate: 'asyncpg.exceptions.TooManyConnectionsError: remaining connection slots reserved for non-replication superuser'. "
            "Kafka consumer group 'order-processor-v2' lag jumped above 40,000 messages."
        ),
        "root_cause": (
            "Kafka batch size was increased to 500 in deployment v2.14.0 without a corresponding semaphore "
            "on the database connection pool. Each batch consumer worker spawned up to 50 concurrent DB queries, "
            "exhausting the max_connections limit (100) on the Aurora primary node."
        ),
        "resolution_runbook": (
            "1. Throttled Kafka consumer concurrency via environment config: KAFKA_MAX_POLL_RECORDS=50\n"
            "2. Tuned HikariCP/AsyncPG pool max_size=15 and pool_timeout=5000ms\n"
            "3. Executed emergency active connection kill on Aurora PostgreSQL:\n"
            "   SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < now() - INTERVAL '30 seconds';\n"
            "4. Service recovered within 90 seconds after rolling restart."
        ),
        "tags": ["postgres", "kafka", "connection-pool", "order-service", "concurrency"]
    },
    {
        "incident_id": "INC-489",
        "service": "auth-session-cache",
        "severity": "P2-HIGH",
        "timestamp": "2026-10-22T14:45:10Z",
        "title": "Redis OOM Eviction Cascade via Leaked JWT Revocation Keys",
        "symptoms": (
            "Redis cluster nodes reporting memory usage > 98.4%. Commands failing with 'OOM command not allowed when used memory > maxmemory'. "
            "User login requests failing with 504 Gateway Timeout across web and mobile clients."
        ),
        "root_cause": (
            "A recently deployed auth token revocation feature in auth-v3.2 was writing blacklisted tokens with "
            "a key prefix 'revoked:token:<hash>' without setting an explicit EXPIRE / TTL. Over 8 million stale "
            "keys accumulated in 72 hours, triggering memory fragmentation and all-keys-lru thrashing."
        ),
        "resolution_runbook": (
            "1. Adjusted Redis maxmemory-policy to volatile-ttl temporarily, then executed SCAN + UNLINK for stale keys:\n"
            "   redis-cli --scan --pattern 'revoked:token:*' | xargs -L 1000 redis-cli UNLINK\n"
            "2. Patched auth-service config to enforce strict TTL (TTL=86400s) on all token revocation entries.\n"
            "3. Memory consumption dropped from 15.8GB to 1.4GB; latency normalized to 1.2ms."
        ),
        "tags": ["redis", "auth", "oom", "memory-leak", "cache", "ttl"]
    },
    {
        "incident_id": "INC-531",
        "service": "billing-gateway",
        "severity": "P1-CRITICAL",
        "timestamp": "2026-10-31T09:18:02Z",
        "title": "Kubernetes Ingress 502 Bad Gateway during Canary Rollout",
        "symptoms": (
            "Ingress controller (nginx-ingress) returning 502 Bad Gateway on /v1/charges and /v1/invoices. "
            "52% of ingress traffic failing. Upstream pods in 'billing-gateway-canary' stuck in CrashLoopBackOff."
        ),
        "root_cause": (
            "The Helm chart for deployment v4.1.0 changed the container port from 8080 to 9090 for metrics segregation, "
            "but the Kubernetes readinessProbe was still pointed at http-get :8080/healthz. Kubernetes continuously "
            "failed readiness checks and dropped endpoints from the service slice."
        ),
        "resolution_runbook": (
            "1. Immediate rollback of canary release via helm:\n"
            "   helm rollback billing-gateway-prod 18\n"
            "2. Corrected values.yaml readinessProbe.httpGet.port to 9090.\n"
            "3. Re-ran progressive rollout with verified health probe."
        ),
        "tags": ["kubernetes", "ingress", "502-bad-gateway", "readiness-probe", "helm", "billing"]
    }
]

# Interactive live test scenario to demonstrate the before/after contrast
LIVE_TEST_SCENARIOS = {
    "kafka_db_starvation": {
        "alert_title": "CRITICAL: order-service-prod database timeout cascade",
        "raw_alert": (
            "ALERT [CRITICAL] 2026-11-04 22:15:00 UTC\n"
            "Service: order-service-prod\n"
            "Metric: p99 latency exceeded 11,800ms (threshold: 350ms)\n"
            "Error rate: 19.4% (HTTP 500 & 503)\n"
            "Log snippet: [ERROR] asyncpg.exceptions.TooManyConnectionsError: remaining connection slots reserved for non-replication superuser\n"
            "Component: order-processor-v2 Kafka consumer lag = 48,200 events"
        ),
        "expected_match_incident": "INC-412"
    },
    "redis_oom_spike": {
        "alert_title": "HIGH: auth-session-cache memory saturation alert",
        "raw_alert": (
            "ALERT [HIGH] 2026-11-04 22:20:15 UTC\n"
            "Service: auth-session-cache\n"
            "Metric: memory_used_percent = 99.1%\n"
            "Log snippet: (error) OOM command not allowed when used memory > 'maxmemory'\n"
            "Component: User token revocation pipeline failing with 504 timeouts"
        ),
        "expected_match_incident": "INC-489"
    },
    "k8s_canary_502": {
        "alert_title": "CRITICAL: billing-gateway ingress 502 gateway error",
        "raw_alert": (
            "ALERT [CRITICAL] 2026-11-04 22:25:30 UTC\n"
            "Service: billing-gateway\n"
            "Metric: 502 HTTP errors > 40% on /v1/charges\n"
            "Log snippet: [error] 110#110: *84501 connect() failed (111: Connection refused) while connecting to upstream\n"
            "Component: Kubernetes pods billing-gateway-canary in CrashLoopBackOff"
        ),
        "expected_match_incident": "INC-531"
    }
}
