"""High-level API used by the FastAPI backend, the evals and the tests.

runner = CampaignRunner()
await runner.start(run_id, goal, on_event=...)   # runs until the human-approval pause
await runner.decide(run_id, "approve")           # resumes through publish
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from campaign_copilot.agents.nodes import Runtime
from campaign_copilot.audit import AuditLog
from campaign_copilot.compliance.retrieval import PolicyIndex
from campaign_copilot.graph import build_graph, run_config
from campaign_copilot.llm import LLM, get_llm
from campaign_copilot.tools import DataTools

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


class CampaignRunner:
    def __init__(
        self,
        llm: LLM | None = None,
        audit: AuditLog | None = None,
        policy_index: PolicyIndex | None = None,
        transport: str | None = None,
    ) -> None:
        self.llm = llm or get_llm()
        self.audit = audit or AuditLog()
        self.policy_index = policy_index or PolicyIndex.from_dir()
        self.transport = transport
        self.checkpointer = MemorySaver()
        self._tools = DataTools(transport)
        self.rt = Runtime(self.llm, self._tools, self.audit, self.policy_index)
        self.graph = build_graph(self.rt, self.checkpointer)

    async def __aenter__(self) -> CampaignRunner:
        await self._tools.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._tools.__aexit__(*exc)

    @staticmethod
    def new_run_id() -> str:
        return uuid.uuid4().hex[:12]

    async def _drain(self, inputs: Any, run_id: str, on_event: EventCallback | None) -> None:
        async for update in self.graph.astream(inputs, run_config(run_id), stream_mode="updates"):
            if on_event is None:
                continue
            for node, delta in update.items():
                if node == "__interrupt__":
                    continue
                for ev in (delta or {}).get("timeline", []):
                    await on_event({"node": node, **ev})

    async def start(self, run_id: str, goal: str, on_event: EventCallback | None = None) -> dict:
        self.audit.append(run_id, "start", inputs={"goal": goal}, backend=self.llm.name)
        if on_event:
            await on_event({"node": "start", "step": "start", "status": "started", "summary": goal})
        await self._drain(
            {"run_id": run_id, "goal": goal, "revision": 0, "timeline": []}, run_id, on_event
        )
        state = await self.state(run_id)
        if on_event and state.get("status") == "awaiting_approval":
            await on_event(
                {
                    "node": "approval",
                    "step": "approval",
                    "status": "waiting",
                    "summary": "waiting for a human to approve or reject",
                }
            )
        return state

    async def decide(
        self, run_id: str, decision: str, on_event: EventCallback | None = None
    ) -> dict:
        if decision not in ("approve", "reject"):
            raise ValueError("decision must be 'approve' or 'reject'")
        cfg = run_config(run_id)
        snapshot = await self.graph.aget_state(cfg)
        if "publish" not in snapshot.next:
            raise RuntimeError(f"run {run_id} is not waiting for approval (next={snapshot.next})")
        self.audit.append(run_id, "human_decision", outputs={"decision": decision})
        await self.graph.aupdate_state(cfg, {"decision": decision})
        await self._drain(None, run_id, on_event)
        return await self.state(run_id)

    async def state(self, run_id: str) -> dict[str, Any]:
        snapshot = await self.graph.aget_state(run_config(run_id))
        values = dict(snapshot.values)
        values["next"] = list(snapshot.next)
        # Tool calls are per run: each audience event carries the calls it made.
        values["tool_calls"] = [
            c for ev in values.get("timeline", []) for c in ev.get("tool_calls", [])
        ]
        return values
