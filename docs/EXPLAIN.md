# EXPLAIN.md

Five plain-English lines per module, written so Akhil can explain every part of this project
without notes. Each entry ends with the quiz questions that were asked before moving on.

## Module 1a: Synthetic data (`campaign_copilot/data/generate.py`, `schema.sql`)

1. The bank's data is three SQLite tables: `branches` (12 rows), `customers` (5,000 rows) and `campaigns` (48 past campaigns with what was sent, who responded, how many accounts opened, and what it cost).
2. Everything is generated from the fixed seed 42 with Python's `random.Random`, so the file is byte-for-byte identical every time it is built; a test proves this.
3. Each customer gets a segment (young professional, family, retiree, small business, student) and that segment drives everything else: which products they hold, typical balances, how often they log in, and whether they opted in to mail or email.
4. Past campaigns carry per-channel economics (direct mail costs most per piece but converts best; email is cheapest; digital ads are in between), so "cost per acquired account" is a real calculation, not a made-up number.
5. There are no names, addresses, or protected attributes such as race, sex or age in the data. Targeting can only use branch, segment, product holdings, balances and engagement.

## Module 1b: Query layer (`campaign_copilot/data/queries.py`)

1. Four read-only functions wrap SQL: `resolve_branches` (turns "Dallas" or "DFW" into branch ids), `query_segments`, `branch_performance` and `past_campaign_results`.
2. They open the database in read-only mode (`mode=ro`), so no agent can ever write to the bank's data, by construction.
3. `query_segments` composes filters: branch list, segment, a "product gap" (customers who do *not* hold a product yet), minimum digital engagement, and channel opt-in. Every number it returns traces back to one SQL statement.
4. `past_campaign_results` returns both the matching campaign rows and a per-channel roll-up with response rate, conversion rate and cost per account, which is what the business-impact panel shows.
5. The same functions are called in-process by tests and wrapped as MCP tools for the agents, so the tools are tested without starting a server.

## Module 1c: MCP server (`campaign_copilot/mcp_server/server.py`)

1. MCP (Model Context Protocol) is a standard way for a model to discover and call tools; the server publishes each tool's name, description and input schema, and the client calls them over JSON-RPC.
2. This server is built with `MCPServer` from the MCP Python SDK 2.x (the class was called `FastMCP` in 1.x). Each `@mcp.tool()` function's type hints become the JSON schema automatically, and its docstring becomes the description the model reads.
3. The four tools are thin wrappers over the query layer: `resolve_branches`, `query_segments`, `branch_performance`, `past_campaign_results`. No business logic lives in the server, so the same code is tested in-process and served over stdio.
4. Running `python -m campaign_copilot.mcp_server.server` serves it on stdio, which is how the LangGraph workflow will launch it as a subprocess; `mcp dev` opens it in the MCP Inspector for manual poking.
5. The tests connect with the SDK's own `Client(mcp)` in-process, so they exercise the real protocol (list tools, call tools, error handling) without a subprocess or a port.

**Quiz asked before moving on:** (1) Why is the database opened read-only, and where is that enforced? (2) What happens if an agent passes `product_gap="crypto"`? (3) How does the MCP server know the JSON schema of each tool's inputs? (4) Why do the tests use `Client(mcp)` instead of starting the server on a port?
