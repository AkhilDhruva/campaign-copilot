# Decisions log

Short records of choices made when the brief was silent or ambiguous. Newest at the bottom.

## 2026-10-06

- **Work folder.** Using `W:\Akhil Reddy Gaddam\Portfolio-2026`, the example path from the brief. Akhil did not object when asked.
- **Overseer title.** Akhil chose the brief's title: "Overseer: Tamper-Evident Memory for AI Agents Using Bitemporal Knowledge Graphs". The Zenodo record (DOI 10.5281/zenodo.23023088) carries a different title. The portfolio will use Akhil's title and still link the DOI.
- **Git identity.** Set the global identity to "Akhil Reddy Gaddam" with the GitHub noreply address `37544296+AkhilDhruva@users.noreply.github.com`, which Akhil approved. Older commits by `dugyalavishal1999` were left as they are; rewriting history is forbidden by the brief.
- **Overseer push.** Not done. Akhil has not yet approved pushing the paper bundle to `overseer-agentic-memory`. Will ask again at Phase 2.
- **Repo layout.** One git repo at the folder root for Campaign Copilot (`backend/`, `frontend/`, `mcp_server/`, `evals/`, `docs/`). The portfolio site refresh (Phase 2) will be a separate clone of `akhil-portfolio`.
- **Phase 0 report kept out of git.** `PHASE0_GITHUB_AUDIT.md` names private repos and local paths, so it lives in the git-ignored `private/` folder. The very first local commit was amended before any push to drop it from history; nothing shared was rewritten.
- **`make` not installed on this PC.** Kept the Makefile for CI and Linux/macOS users and added `manage.py` with the same targets for Windows. Install GNU make with `winget install ezwinports.make` if you prefer `make`.

## 2026-10-07

- **Official Anthropic SDK instead of `langchain-anthropic`.** The model call is one function using structured outputs (`messages.parse`), which is easier to read and explain than a framework wrapper. LangGraph is still the orchestrator. `langchain-anthropic` was removed from the dependencies and `anthropic` added.
- **Server-side refusal fallbacks not enabled.** The Anthropic reference recommends the `fallbacks` parameter by default on current models. It is left out to keep the structured-output path simple; the client raises a clear error on a refusal. Revisit if real-model runs hit refusals.
- **Default model `claude-opus-5-5`** when `MOCK_LLM=0`, overridable with `LLM_MODEL`.
- **MCP transport defaults to in-process.** The agents still speak MCP (JSON-RPC over an in-memory channel). `MCP_TRANSPORT=stdio` launches the server as a subprocess and was verified working. In-process is the default because it is robust on Windows and in CI.
- **In-memory checkpointer.** `MemorySaver` keeps paused runs in the API process. Fine for a demo; a database checkpointer is the production swap.
- **BM25 over policy paragraphs rather than embeddings.** Five short files, exact wording matters, no vector database to run. Retrieval still decides which paragraph is cited.
- **Compliance is rules first, model second.** Flags are deterministic; the model only proposes fixes. This keeps compliance auditable and testable offline.
- **The mock's first draft is intentionally non-compliant.** It makes the revision loop visible and testable offline.
- **Projections keep decimals.** The dataset has customers only, so single-branch "product gap" audiences can be under 100 people. Rounding small projections to zero looked broken; showing 0.4 accounts is honest. Noted in the README.
- **Evals found bugs; the fixes went into the code, not the expectations**, except Preston Hollow, where the expectation itself was wrong (it is one branch, not four).
- **Demo GIF assembled from browser screenshots** taken during verification. Replace with a screen recording if a smoother one is wanted.

## 2026-10-07, Phase 2 (portfolio site)

- **Site cloned into `site/` inside this folder** and git-ignored by the Campaign Copilot repo, so both repos live under one workspace. Work is on branch `portfolio-2026-refresh`; nothing pushed.
- **Campaign Copilot "Try it" is a static replay embedded in the site** (`site/campaign-copilot/`, built from `frontend/` with `base: "./"`). It needs no backend, so the portfolio can stay on Vercel's static hosting. The page says so and points to the repo for the live agents.
- **Overseer demo is a standalone page** (`site/overseer-demo.html`) using the browser's Web Crypto API for SHA-256. It mirrors the Python audit log's hashing rule (previous hash + canonical JSON) so the two demos tell one story.
- **Third flagship is AeroMind FlightLab** (drone sim) rather than the data-center site, because it is a self-contained build with a live link and a repo, and it reads as engineering rather than courseware.
- **Instructional-design case studies were moved, not deleted.** The whole section now sits below Credentials as "06 - Other work" with a shorter header; the 15-section case studies still open.
- **Code links point at `AkhilDhruva/campaign-copilot` and `AkhilDhruva/overseer-agentic-memory`.** The first does not exist yet and the second is empty; both need Akhil's OK to push.
- **Pushed on Akhil's OK (2026-10-07):** `AkhilDhruva/campaign-copilot` created and pushed; `overseer-agentic-memory` received the staged bundle; portfolio PR #6 merged into main for Vercel to redeploy. MIT license on both code repos, per Akhil.
