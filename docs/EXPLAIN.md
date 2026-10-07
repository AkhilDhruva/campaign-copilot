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
