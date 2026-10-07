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
