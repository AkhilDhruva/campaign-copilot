"""The agents' only door to the bank's data: an MCP client.

`DataTools` opens an MCP session to the Northwind server and records every call (tool name,
arguments, a summary of the result, timing) so the audit log and the UI timeline can show
exactly which data each agent used.

Transport is chosen by MCP_TRANSPORT:
  * "inprocess" (default): the server object runs inside this process, still speaking MCP.
    Robust on every OS and what tests use.
  * "stdio": launches `python -m campaign_copilot.mcp_server.server` as a subprocess and talks
    JSON-RPC over its stdin/stdout, exactly as Claude Desktop or any other MCP host would.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from mcp import Client, StdioServerParameters


class DataTools:
    def __init__(self, transport: str | None = None) -> None:
        self.transport = transport or os.environ.get("MCP_TRANSPORT", "inprocess")
        self.calls: list[dict[str, Any]] = []
        self._client: Client | None = None

    async def __aenter__(self) -> DataTools:
        if self.transport == "stdio":
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "campaign_copilot.mcp_server.server"],
                env={**os.environ},
            )
            self._client = Client(params)
        else:
            from campaign_copilot.mcp_server.server import mcp

            self._client = Client(mcp)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.__aexit__(*exc)
            self._client = None

    async def call(self, tool: str, **args: Any) -> Any:
        if self._client is None:
            raise RuntimeError("DataTools must be used as `async with DataTools() as tools:`")
        started = time.perf_counter()
        result = await self._client.call_tool(tool, args)
        duration = round((time.perf_counter() - started) * 1000, 1)
        if result.is_error:
            text = " ".join(getattr(b, "text", "") for b in result.content)
            self.calls.append({"tool": tool, "args": args, "error": text, "duration_ms": duration})
            raise RuntimeError(f"{tool} failed: {text}")
        data = result.structured_content
        if isinstance(data, dict) and set(data) == {"result"}:
            data = data["result"]  # list-returning tools are wrapped by the SDK
        self.calls.append(
            {"tool": tool, "args": args, "summary": _summarise(data), "duration_ms": duration}
        )
        return data


def _summarise(data: Any) -> str:
    if isinstance(data, list):
        return f"{len(data)} rows"
    if isinstance(data, dict):
        keys = [k for k in ("customers", "campaign_count") if k in data]
        return ", ".join(f"{k}={data[k]}" for k in keys) or f"{len(data)} fields"
    return str(data)[:80]
