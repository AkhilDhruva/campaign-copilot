"""HTTP API for Campaign Copilot.

    POST /api/runs                 {goal}      -> {run_id}; the workflow starts in the background
    GET  /api/runs/{id}                        -> full state (plan, audience, copy, compliance, ...)
    GET  /api/runs/{id}/events                 -> Server-Sent Events: the live timeline
    POST /api/runs/{id}/decision   {decision}  -> approve | reject, resumes the paused graph
    GET  /api/audit/verify                     -> hash-chain verification
    GET  /api/audit/{run_id}                   -> audit records for one run
    GET  /api/policies                         -> the compliance rulebook paragraphs
    GET  /api/health

One `CampaignRunner` lives for the life of the process. Runs are kept in memory, which is fine
for a demo; swap `MemorySaver` for a database checkpointer to survive restarts.
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from campaign_copilot import __version__
from campaign_copilot.audit import verify
from campaign_copilot.compliance.retrieval import load_passages
from campaign_copilot.llm.client import mock_mode
from campaign_copilot.runner import CampaignRunner

load_dotenv()

TERMINAL = {"waiting", "published", "rejected", "error"}


class RunRequest(BaseModel):
    goal: str = Field(min_length=8, max_length=400)


class DecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


class RunRecord:
    def __init__(self, run_id: str, goal: str) -> None:
        self.run_id = run_id
        self.goal = goal
        self.events: list[dict[str, Any]] = []
        self.subscribers: list[asyncio.Queue] = []
        self.error: str | None = None

    async def push(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        for q in list(self.subscribers):
            await q.put(event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    runner = CampaignRunner()
    await runner.__aenter__()
    app.state.runner = runner
    app.state.runs: dict[str, RunRecord] = {}
    try:
        yield
    finally:
        await runner.__aexit__(None, None, None)


app = FastAPI(title="Campaign Copilot", version=__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _runner() -> CampaignRunner:
    return app.state.runner


def _record(run_id: str) -> RunRecord:
    rec = app.state.runs.get(run_id)
    if rec is None:
        raise HTTPException(404, f"run {run_id} not found")
    return rec


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "version": __version__,
        "mock_llm": mock_mode(),
        "llm_backend": _runner().llm.name,
        "mcp_transport": _runner().rt.tools.transport,
        "bank": "Northwind Community Bank (fictional, synthetic data)",
    }


@app.post("/api/runs", status_code=202)
async def create_run(body: RunRequest) -> dict[str, str]:
    runner = _runner()
    run_id = runner.new_run_id()
    rec = RunRecord(run_id, body.goal)
    app.state.runs[run_id] = rec

    async def go() -> None:
        try:
            await runner.start(run_id, body.goal, rec.push)
        except Exception as exc:  # surface failures to the UI instead of a silent hang
            rec.error = str(exc)
            await rec.push(
                {"node": "error", "step": "error", "status": "error", "summary": str(exc)}
            )

    asyncio.create_task(go())
    return {"run_id": run_id}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    rec = _record(run_id)
    state = await _runner().state(run_id)
    return {"run_id": run_id, "goal": rec.goal, "error": rec.error, "events": rec.events, **state}


@app.get("/api/runs/{run_id}/events")
async def stream_events(run_id: str) -> StreamingResponse:
    rec = _record(run_id)

    async def gen():
        q: asyncio.Queue = asyncio.Queue()
        rec.subscribers.append(q)
        try:
            for ev in list(rec.events):  # replay what already happened
                yield f"data: {json.dumps(ev, default=str)}\n\n"
                if ev.get("status") in TERMINAL:
                    return
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps(ev, default=str)}\n\n"
                if ev.get("status") in TERMINAL:
                    return
        finally:
            rec.subscribers.remove(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/runs/{run_id}/decision")
async def decide(run_id: str, body: DecisionRequest) -> dict[str, Any]:
    rec = _record(run_id)
    try:
        state = await _runner().decide(run_id, body.decision, rec.push)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"run_id": run_id, "status": state.get("status"), "events": rec.events}


@app.get("/api/audit/verify")
async def audit_verify() -> dict[str, Any]:
    return verify(_runner().audit.path)


@app.get("/api/audit/{run_id}")
async def audit_records(run_id: str) -> list[dict[str, Any]]:
    return _runner().audit.records(run_id)


@app.get("/api/policies")
async def policies() -> list[dict[str, str]]:
    return [
        {"id": p.policy_id, "source": p.source, "title": p.title, "text": p.text}
        for p in load_passages()
    ]


# Serve the built front end, if present, so one process runs the whole demo.
_dist = Path(os.environ.get("FRONTEND_DIST", "frontend/dist"))
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
