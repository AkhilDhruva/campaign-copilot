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

## Module 2: Model layer (`campaign_copilot/llm/`, `agents/schemas.py`)

1. Every agent asks the model for exactly one pydantic shape (`Plan`, `AudienceBrief`, `CopyDraft`, `ComplianceFixes`, `Evaluation`), so the rest of the code never parses free text.
2. `LLM.structured(agent, system, user, schema, context)` is the only entry point. It records every call (agent, backend, schema, prompt size, duration) for the audit log.
3. `MockLLM` is the default. It ignores the prompt text and builds the schema object from `context`, the same structured data the prompt was rendered from. No randomness, so runs are reproducible.
4. `AnthropicLLM` calls Claude through the official SDK with `messages.parse(..., output_format=Schema)`, which guarantees the JSON validates. It checks for a `refusal` stop reason and raises a clear error instead of returning junk.
5. The mock's first copy draft deliberately says "Guaranteed approval" and "FREE ... for life" and fixes both on revision 1, so the compliance loop is visible offline.

**Quiz:** (1) Why does the mock take `context` instead of the prompt? (2) What does `messages.parse` guarantee that `messages.create` does not? (3) Where would you look to see how many model calls a run made?

## Module 3: Compliance (`campaign_copilot/compliance/`, `policies/`)

1. The rulebook is five plain-text policy files with numbered paragraphs (1.1, 1.2, ...). `load_passages` splits them into paragraphs; `PolicyIndex` ranks paragraphs with BM25, a standard keyword-scoring formula.
2. `rules.check` runs thirteen deterministic rules over each piece (letter, email, ad 1, ad 2): "guaranteed", "free" without a condition, APY without the three disclosures, protected-class words, missing "Member FDIC", missing "Equal Housing Lender", missing unsubscribe, jargon, length limits.
3. When a rule fires, the checker runs a retrieval query and attaches the top paragraph, so every flag carries a citation like "Policy 2.2 (02_apy_disclosure.txt)" plus the paragraph text.
4. "block" issues fail the draft; "warn" issues are reported but do not block. The model is asked for a fix suggestion per issue, but the model never decides whether something is flagged.
5. The copy agent gets the issues and fixes back as feedback on the next revision, which is how the loop converges.

**Quiz:** (1) Why not just ask the model "is this compliant?" (2) What makes "free" acceptable under policy 1.2? (3) What are the three APY disclosures?

## Module 4: Audit log (`campaign_copilot/audit/log.py`)

1. One JSON object per line in `logs/audit.jsonl`: sequence number, timestamp, run id, step, inputs, outputs, tool calls, timing.
2. Each record stores `prev_hash` (the previous record's hash) and `hash` = SHA-256 of `prev_hash` plus the record's canonical JSON (sorted keys, no whitespace).
3. `verify()` replays the chain from the genesis hash (64 zeros). A changed value, a deleted line or a reordered line changes some hash and the function reports the first bad sequence number.
4. Appending resumes from the last line on disk, so restarting the server keeps one continuous chain.
5. It is append-only by construction: there is no update or delete function, and the file is opened in append mode.

**Quiz:** (1) Why hash the previous hash and not just the record? (2) If someone edits line 2 and recomputes line 2's hash, why does verification still fail? (3) What is not protected by this design (hint: who can rewrite the whole file)?

## Module 5: Workflow (`campaign_copilot/graph.py`, `agents/nodes.py`, `runner.py`, `tools.py`)

1. `CampaignState` is a typed dictionary. Each node returns only the keys it changed; LangGraph merges them. `timeline` uses `operator.add` so events append instead of overwrite.
2. Edges: planner, audience, copy, compliance, evaluator, then a conditional edge back to copy ("revise", at most twice) or on to publish. `recursion_limit=25` is the hard stop on total steps.
3. `interrupt_before=["publish"]` plus a checkpointer means `astream` returns before publish runs. `decide()` writes `decision` into the saved state with `aupdate_state` and resumes with `astream(None, config)`.
4. `DataTools` is the agents' only door to the data: an MCP client, either in-process or launching the server as a stdio subprocess. Every call is recorded with arguments, a summary and timing.
5. The audience node makes four tool calls in a fixed order, and the business-impact estimate multiplies reach by the historical response and conversion rates of the chosen channel.

**Quiz:** (1) What happens if the evaluator still says "revise" after two revisions? (2) Why does `decide()` check `snapshot.next` before resuming? (3) What does the `thread_id` in the config do?

## Module 6: API, UI, evals, CI (`api/main.py`, `frontend/`, `evals/`, `.github/`)

1. `POST /api/runs` starts the workflow as a background task and returns at once; `GET /api/runs/{id}/events` is a Server-Sent Events stream that replays past events and then streams new ones until a terminal event.
2. The React app subscribes with `EventSource`, renders the timeline live, then fetches the full state. Approve and Reject call `POST /api/runs/{id}/decision`, which resumes the paused graph.
3. The draft view shows one tab per revision; flagged snippets are wrapped in `<mark>` from the compliance report for that draft, with the policy citation and the proposed fix.
4. `evals/run.py` runs 20 golden goals and checks 12 to 13 properties each; the score must stay above `evals/baseline.json` or CI fails. Writing the evals found four bugs (product detection order, branch names, mortgage disclosures on every piece, segment words in copy).
5. CI runs ruff, pytest, the evals and the front-end build on every push, all in `MOCK_LLM=1` mode, so it is free and deterministic.

**Quiz:** (1) Why SSE instead of WebSockets here? (2) Why do the evals run in mock mode? (3) What would you change first to run this in production (hint: MemorySaver, single process)?
