# Campaign Copilot

A bank marketer types a goal such as "Grow checking deposits 10% at our Dallas branches this quarter".
A team of agents plans the campaign, pulls numbers from the bank's data through an MCP server,
drafts the copy, checks it against a compliance rulebook, scores it, and waits for a human to approve
before anything ships. Every step is written to a tamper-evident audit log.

Built for a fictional bank, **Northwind Community Bank**. All data is synthetic. This is independent
portfolio work and is not affiliated with any real company.

> Work in progress. This README is filled in module by module; see `docs/EXPLAIN.md` for the
> plain-English explanation of each part and `docs/DECISIONS.md` for the choices made along the way.

## Run it in two commands

```bash
python manage.py test     # builds the synthetic data, runs the offline test suite
python manage.py api      # starts the backend on http://localhost:8000
```

No API key is needed. `MOCK_LLM=1` (the default in `.env.example`) uses deterministic stand-in
model outputs so the demo, tests and evals work offline and cost nothing. Set `MOCK_LLM=0` and an
`ANTHROPIC_API_KEY` in `.env` to use a real model.

`make <target>` works too if GNU make is installed; `manage.py` has the same targets.

## Status

| Module | State |
|---|---|
| Synthetic data (5,000 customers, 12 branches, 48 past campaigns) | done |
| MCP server (`query_segments`, `branch_performance`, `past_campaign_results`) | in progress |
| LangGraph workflow (planner, audience, copy, compliance, evaluator, human approval) | planned |
| Hash-chained audit log | planned |
| FastAPI backend and React front end | planned |
| Golden evals and CI | planned |
