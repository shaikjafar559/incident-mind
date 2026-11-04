"""
IncidentMind Main Application Server.
Exposes REST and SSE endpoints for incident triage, memory inspection, and seed management.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from backend.memory_engine import HindsightMemoryManager
from backend.agent import SREAgent
from backend.seed_data import INITIAL_INCIDENTS, LIVE_TEST_SCENARIOS

memory_manager = HindsightMemoryManager()
agent = SREAgent(memory_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-populate memory bank with initial production incidents
    for inc in INITIAL_INCIDENTS:
        await memory_manager.retain_incident(
            incident_id=inc["incident_id"],
            service=inc["service"],
            title=inc["title"],
            symptoms=inc["symptoms"],
            root_cause=inc["root_cause"],
            resolution_runbook=inc["resolution_runbook"],
            tags=inc.get("tags", []),
            context=f"Initial seeded post-mortem {inc['incident_id']}"
        )
    yield


app = FastAPI(
    title="IncidentMind — AI SRE Agent with Hindsight Memory",
    description="Autonomous SRE triage powered by Vectorize's Hindsight memory system.",
    version="1.0.0",
    lifespan=lifespan
)

# Static files for UI
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


class TriageRequest(BaseModel):
    alert_text: str
    use_memory: bool = True
    model_name: Optional[str] = "openai/gpt-oss-120b"


class RetainRequest(BaseModel):
    incident_id: str
    service: str
    title: str
    symptoms: str
    root_cause: str
    resolution_runbook: str
    tags: Optional[List[str]] = None


@app.get("/")
async def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "IncidentMind API Running. Access static dashboard at /static/index.html"}


@app.get("/api/scenarios")
async def get_scenarios():
    return JSONResponse(LIVE_TEST_SCENARIOS)


@app.post("/api/triage")
async def triage(req: TriageRequest):
    if not req.alert_text.strip():
        raise HTTPException(status_code=400, detail="Alert payload cannot be empty")
    result = await agent.triage_incident(
        alert_payload=req.alert_text,
        use_memory=req.use_memory,
        model_name=req.model_name
    )
    return JSONResponse(result)


@app.post("/api/retain")
async def retain_incident(req: RetainRequest):
    result = await memory_manager.retain_incident(
        incident_id=req.incident_id,
        service=req.service,
        title=req.title,
        symptoms=req.symptoms,
        root_cause=req.root_cause,
        resolution_runbook=req.resolution_runbook,
        tags=req.tags
    )
    return JSONResponse(result)


@app.get("/api/stats")
async def get_stats():
    stats = memory_manager.get_stats()
    return JSONResponse(stats)


@app.post("/api/reset_seed")
async def reset_seed():
    for inc in INITIAL_INCIDENTS:
        await memory_manager.retain_incident(
            incident_id=inc["incident_id"],
            service=inc["service"],
            title=inc["title"],
            symptoms=inc["symptoms"],
            root_cause=inc["root_cause"],
            resolution_runbook=inc["resolution_runbook"],
            tags=inc.get("tags", [])
        )
    return JSONResponse({"status": "re-seeded successfully", "count": len(INITIAL_INCIDENTS)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
