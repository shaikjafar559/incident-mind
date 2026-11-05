"""
Comprehensive Unit & Integration Test Suite for IncidentMind.
Verifies Hindsight memory retention, recall accuracy, and agent reasoning.
"""

import asyncio
from backend.memory_engine import HindsightMemoryManager
from backend.agent import SREAgent
from backend.seed_data import INITIAL_INCIDENTS, LIVE_TEST_SCENARIOS


def test_memory_retention_lifecycle():
    """Verify that incidents are successfully retained into the Hindsight bank."""
    async def _run():
        memory_mgr = HindsightMemoryManager()
        initial_count = len(memory_mgr._local_bank)
        
        event = await memory_mgr.retain_incident(
            incident_id="INC-TEST-001",
            service="payment-gateway",
            title="Payment webhook timeout under load",
            symptoms="504 Gateway Timeout on Stripe webhook ingress",
            root_cause="Synchronous database write blocked async event loop",
            resolution_runbook="Offload DB write to Celery queue with retry=3",
            tags=["stripe", "webhook", "timeout", "celery"]
        )
        
        assert event["status"] == "retained"
        assert event["incident_id"] == "INC-TEST-001"
        assert len(memory_mgr._local_bank) == initial_count + 1

    asyncio.run(_run())


def test_hindsight_recall_accuracy():
    """Verify that multi-signal recall matches incoming alert to the correct historical incident."""
    async def _run():
        memory_mgr = HindsightMemoryManager()
        for inc in INITIAL_INCIDENTS:
            await memory_mgr.retain_incident(
                incident_id=inc["incident_id"],
                service=inc["service"],
                title=inc["title"],
                symptoms=inc["symptoms"],
                root_cause=inc["root_cause"],
                resolution_runbook=inc["resolution_runbook"],
                tags=inc.get("tags", [])
            )
            
        query_alert = LIVE_TEST_SCENARIOS["kafka_db_starvation"]["raw_alert"]
        recalls = await memory_mgr.recall_incidents(query_alert, max_results=1)
        
        assert len(recalls) > 0
        top_hit = recalls[0]
        assert top_hit["id"] == "INC-412"
        assert top_hit["score"] >= 0.70
        assert "pg_terminate_backend" in top_hit["resolution_runbook"]

    asyncio.run(_run())


def test_stateless_vs_hindsight_behavior_divergence():
    """Verify clear behavior divergence between Stateless mode and Hindsight-augmented mode."""
    async def _run():
        memory_mgr = HindsightMemoryManager()
        for inc in INITIAL_INCIDENTS:
            await memory_mgr.retain_incident(
                incident_id=inc["incident_id"],
                service=inc["service"],
                title=inc["title"],
                symptoms=inc["symptoms"],
                root_cause=inc["root_cause"],
                resolution_runbook=inc["resolution_runbook"],
                tags=inc.get("tags", [])
            )
        agent = SREAgent(memory_mgr)
        alert = LIVE_TEST_SCENARIOS["kafka_db_starvation"]["raw_alert"]
        
        # 1. Stateless execution (Memory OFF)
        stateless_result = await agent.triage_incident(alert, use_memory=False)
        assert stateless_result["use_memory"] is False
        assert stateless_result["recalled_count"] == 0
        assert "INC-412" not in stateless_result["response"]
        
        # 2. Hindsight execution (Memory ON)
        memory_result = await agent.triage_incident(alert, use_memory=True)
        assert memory_result["use_memory"] is True
        assert memory_result["recalled_count"] > 0
        assert "INC-412" in memory_result["response"]
        assert "pg_terminate_backend" in memory_result["response"]

    asyncio.run(_run())
