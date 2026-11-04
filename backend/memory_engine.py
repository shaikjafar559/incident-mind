"""
IncidentMind Hindsight Memory Engine.
Manages persistent memory banks, semantic & graph recall, and knowledge retention
using Vectorize's Hindsight framework.
"""

import os
import time
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

try:
    from hindsight_client import Hindsight
    HINDSIGHT_CLIENT_AVAILABLE = True
except ImportError:
    HINDSIGHT_CLIENT_AVAILABLE = False

logger = logging.getLogger("incidentmind.memory")

BANK_ID = "incidentmind-sre-cluster"


class HindsightMemoryManager:
    """
    Unified Hindsight Memory Manager.
    Connects to Hindsight Cloud / Local Server when available,
    and provides a high-fidelity embedded Hindsight bank for immediate offline evaluation.
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv("HINDSIGHT_API_URL", "http://localhost:8888")
        self.api_key = api_key or os.getenv("HINDSIGHT_API_KEY", "")
        self.client: Optional[Any] = None
        self.is_live_connected = False
        self.memory_events: List[Dict[str, Any]] = []
        
        # Embedded Memory Bank (for zero-friction out-of-the-box local demo)
        self._local_bank: List[Dict[str, Any]] = []
        
        self._init_client()

    def _init_client(self):
        if HINDSIGHT_CLIENT_AVAILABLE and self.base_url:
            try:
                # Initialize Hindsight SDK
                self.client = Hindsight(
                    base_url=self.base_url,
                    api_key=self.api_key if self.api_key else None,
                    timeout=5.0
                )
                logger.info(f"Hindsight client initialized with base_url: {self.base_url}")
            except Exception as e:
                logger.warning(f"Could not initialize live Hindsight client: {e}. Falling back to embedded bank.")
                self.client = None

    async def verify_connection(self) -> bool:
        """Check if live Hindsight server is active."""
        if not self.client:
            return False
        try:
            # Check monitoring health or version
            resp = await self.client.monitoring.get_health()
            self.is_live_connected = True
            return True
        except Exception:
            self.is_live_connected = False
            return False

    async def retain_incident(
        self,
        incident_id: str,
        service: str,
        title: str,
        symptoms: str,
        root_cause: str,
        resolution_runbook: str,
        tags: Optional[List[str]] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retains a verified post-mortem / incident resolution into Hindsight memory.
        """
        content_payload = (
            f"INCIDENT: {incident_id}\n"
            f"SERVICE: {service}\n"
            f"TITLE: {title}\n"
            f"SYMPTOMS & METRICS:\n{symptoms}\n"
            f"ROOT CAUSE ANALYSIS:\n{root_cause}\n"
            f"VERIFIED RESOLUTION RUNBOOK:\n{resolution_runbook}\n"
        )
        
        event_record = {
            "type": "RETAIN",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "incident_id": incident_id,
            "service": service,
            "title": title,
            "tags": tags or [],
            "status": "retained"
        }

        retained_live = False
        if self.client:
            try:
                await self.client.aretain(
                    bank_id=BANK_ID,
                    content=content_payload,
                    context=context or f"Post-mortem documentation for {incident_id} on service {service}",
                    tags=tags or [service, "postmortem"],
                    metadata={"incident_id": incident_id, "service": service}
                )
                retained_live = True
                event_record["provider"] = "Hindsight Cloud/Server"
            except Exception as e:
                logger.warning(f"Live Hindsight retain failed: {e}. Saved to local bank.")

        # Always store in embedded bank to guarantee zero-downtime demo continuity
        local_entry = {
            "incident_id": incident_id,
            "service": service,
            "title": title,
            "symptoms": symptoms,
            "root_cause": root_cause,
            "resolution_runbook": resolution_runbook,
            "tags": tags or [],
            "retained_at": datetime.now(timezone.utc).isoformat(),
            "full_content": content_payload
        }
        # Update or append
        existing = [idx for idx, x in enumerate(self._local_bank) if x["incident_id"] == incident_id]
        if existing:
            self._local_bank[existing[0]] = local_entry
        else:
            self._local_bank.append(local_entry)

        if not retained_live:
            event_record["provider"] = "Hindsight Embedded Bank"

        self.memory_events.insert(0, event_record)
        return event_record

    async def recall_incidents(
        self,
        query: str,
        max_results: int = 3,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recalls historical incident memory units matching current telemetry or alert.
        """
        start_time = time.time()
        recalls: List[Dict[str, Any]] = []
        source_provider = "Embedded Bank"

        if self.client:
            try:
                response = await self.client.arecall(
                    bank_id=BANK_ID,
                    query=query,
                    max_tokens=2048,
                    tags=tags
                )
                # Parse Hindsight response items
                if hasattr(response, "results") and response.results:
                    for item in response.results:
                        recalls.append({
                            "id": getattr(item, "id", "rec-0"),
                            "text": getattr(item, "text", str(item)),
                            "score": getattr(item, "score", 0.91),
                            "type": getattr(item, "type", "experience")
                        })
                    source_provider = "Hindsight Cloud/Server"
            except Exception as e:
                logger.info(f"Live recall fallback: {e}")

        # If live response was empty or unavailable, execute embedded multi-strategy match
        if not recalls:
            recalls = self._local_hybrid_recall(query, max_results=max_results)
            source_provider = "Hindsight Embedded Bank"

        latency_ms = round((time.time() - start_time) * 1000, 2)
        event_record = {
            "type": "RECALL",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query[:120] + "..." if len(query) > 120 else query,
            "matches_found": len(recalls),
            "top_score": recalls[0]["score"] if recalls else 0.0,
            "latency_ms": latency_ms,
            "provider": source_provider
        }
        self.memory_events.insert(0, event_record)
        return recalls

    def _local_hybrid_recall(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Multi-signal keyword + semantic scoring on the embedded bank.
        """
        query_words = set(query.lower().replace(",", " ").replace(":", " ").replace("-", " ").split())
        scored: List[tuple[float, Dict[str, Any]]] = []

        for item in self._local_bank:
            item_text = (item["full_content"] + " " + " ".join(item["tags"])).lower()
            item_words = set(item_text.replace(",", " ").replace(":", " ").replace("-", " ").split())
            
            # Intersection of keywords
            intersection = query_words.intersection(item_words)
            # Bonus weight for exact service or error code matches
            bonus = 0.0
            if item["service"].lower() in query.lower():
                bonus += 0.45
            for tag in item["tags"]:
                if tag.lower() in query.lower():
                    bonus += 0.25
            if item["incident_id"].lower() in query.lower():
                bonus += 0.50

            base_score = len(intersection) / max(len(query_words), 1)
            final_score = min(0.98, round(0.40 * base_score + bonus, 3))

            if final_score > 0.15:
                scored.append((final_score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, item in scored[:max_results]:
            results.append({
                "id": item["incident_id"],
                "score": score,
                "service": item["service"],
                "title": item["title"],
                "symptoms": item["symptoms"],
                "root_cause": item["root_cause"],
                "resolution_runbook": item["resolution_runbook"],
                "tags": item["tags"],
                "text": item["full_content"]
            })
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Returns memory bank statistics."""
        return {
            "bank_id": BANK_ID,
            "total_incidents_retained": len(self._local_bank),
            "live_connected": self.is_live_connected,
            "base_url": self.base_url,
            "recent_events": self.memory_events[:15]
        }
