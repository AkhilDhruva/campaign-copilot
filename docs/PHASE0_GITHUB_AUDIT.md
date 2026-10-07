# Phase 0: GitHub audit

Date: 2026-10-06. Read-only audit. Nothing was pushed, deleted, fetched into local refs, or rewritten.

## 1. Things I need from you before Phase 1

1. **GitHub CLI.** Done. It was not installed at the start of the audit; you installed `gh` 2.102.0 via winget and logged in as `AkhilDhruva` during this session (scopes: repo, workflow, read:org, gist). Note for future sessions: it lives at `C:\Program Files\GitHub CLI\gh.exe` and is not on PATH in shells opened before the install.

2. **Your global git identity is set to another person's account.** `git config --global user.name` is `dugyalavishal1999` with email `159156982+dugyalavishal1999@users.noreply.github.com`. Thirteen commits in your repos are attributed to that account (aqua-sim: 2, DATA-CENTER-TRAINING-latest: 3, Terrain-Memory-for-RL: 6, tm-isaac: 2). Repos that set a local identity (ProtoGraph, RepoPilot, Research) are fine. Suggested fix (I will run it only on your OK):

   ```powershell
   git config --global user.name "Akhil Reddy Gaddam"
   git config --global user.email "37544296+AkhilDhruva@users.noreply.github.com"
   ```

   Past commits cannot be re-attributed without rewriting history, which the brief forbids. I recommend leaving them.

3. **Overseer decision.** See section 3. The GitHub repo exists but is empty; the code is local and not under git.

4. **Target folder.** The brief suggests `W:\Akhil Reddy Gaddam\Portfolio-2026`. It does not exist yet. On your OK I will create it, move this session there, and start Phase 1.

5. **Paper title mismatch.** The Zenodo DOI in the brief resolves to a different title than the brief gives (section 3). Tell me which title the portfolio should use.

## 2. GitHub account

- Account: `AkhilDhruva` (https://github.com/AkhilDhruva), created 2018, name "Akhil Reddy Gaddam". 20 repos: 12 public, 8 private, none archived, none forks, one empty.
- Profile bio already mentions Overseer. Profile link points at https://akhil-portfolio-pi-five.vercel.app.
- Stored git credential on this machine (Git Credential Manager) is for `AkhilDhruva`.
- `AkhilDhruva/RepoPulse` returns 404. The local repo points at it but the remote does not exist.

### Private repos (from `gh repo list`)

| Repo | Last push | Size KB | Description | Local clone |
|---|---|---|---|---|
| Terrain-Memory-for-RL- | 2026-10-01 | 2,462 | (none) | yes, `W:\...\RL Robotics\Terrain-Memory-for-RL` |
| ProtoGraph | 2026-09-29 | 7,004 | (none) | yes, `W:\...\Claude\ProtoGraph` |
| applystrike-os | 2026-07-28 | 81 | (none) | no (only a built dashboard under `W:\Portfolio\...\context-engine\builds\`) |
| Data-Center-HMI-Training- | 2026-06-25 | 25 | (none) | no |
| HMI-cockpit-simulator- | 2026-01-20 | 50 | "car" | no |
| Receipt-saver | 2026-01-07 | 13 | "rs" | no |
| spot-therm | 2026-01-07 | 22 | "hj" | no |
| Rocket-lunch-telemetry- | 2025-12-23 | 63 | "LCS for Firefly" | no |

Three private repos have placeholder descriptions ("car", "rs", "hj") and `applystrike-os` has its default branch set to `claude/update-z4ywvc` instead of `main`.

### Public repos (from the API)

| Repo | Last push | Size KB | Description |
|---|---|---|---|
| DATA-CENTER-TRAINING | 2026-09-30 | 129,048 | (none) |
| overseer-agentic-memory | 2026-09-25 | 0 | **empty repo, no commits** |
| tracepermit-ai-agent-overseer | 2026-09-17 | 34 | Demo and adversarial evaluation of content-addressed admission... |
| RepoPilot | 2026-09-14 | 844 | (none) |
| Aqua-SIM-Ohio-Report- | 2026-09-09 | 4,199 | (none) |
| aqua-sim | 2026-07-24 | 7,666 | Flood Zone Risk Simulator |
| akhil-portfolio | 2026-07-22 | 1,096 | portfolio site, deployed on Vercel |
| Gas-Turbine-3D-Interactive-Tutorial | 2026-06-28 | 13 | (none) |
| AeroMind-FlightLab | 2026-06-12 | 139 | 3D drone avionics training simulator |
| ohio-drivesmart-academy | 2026-06-04 | 40 | (none) |
| Ghost-X-HUD-Helmet-Simulator | 2026-02-02 | 15 | HUD helmet simulator |
| Ohio-Driving-Class-D-E-learning | 2026-01-21 | 40 | (none) |

Six of twelve public repos have no description. Phase 2 should fix that.

## 3. Overseer (brief item 5)

**Paper.** DOI 10.5281/zenodo.23023088 resolves to *"Overseer: Governed Graph Engineering for Source-Traceable Bitemporal Knowledge Graphs"*, Akhil Reddy Gaddam, published 2026-09-28, v1, file `Gaddam_2026_Overseer.pdf`. The brief calls it *"Overseer: Tamper-Evident Memory for AI Agents Using Bitemporal Knowledge Graphs"*. That title appears nowhere in the Zenodo record or in the local PDFs. The local `overseer_v2.pdf` (dated 2026-08-30) carries the Zenodo title, so "overseer_v2" is this paper.

**GitHub.** `AkhilDhruva/overseer-agentic-memory` was created 2026-09-25 and has zero commits. There is no public code for the paper.

**Local copies (all on W:).**

| What | Path | Git state |
|---|---|---|
| Engine, tests, verification campaign, paper bundle | `W:\Akhil Reddy Gaddam\Claude\TKG_MATRIX DECOMPOSITION\White paper on TKG\` | **not a git repo** |
| Frozen paper bundle with sha256 manifest | `...\White paper on TKG\arxiv_provenance_spine_v3\` | inside the folder above |
| Research notes, audits, Zenodo metadata, arXiv tex | `...\TKG_MATRIX DECOMPOSITION\Agent Memory Gatewaty\Research\` | local git, 214 commits (2026-06-30 to 2026-10-06), **no remote**, 16 MB |
| Paper PDF v1 and v2 | `W:\Akhil Reddy Gaddam\STEM_OPT\O1A research papers\overseer.pdf`, `overseer_v2.pdf` | plain files |

Engine files: `tkg_spine_v2.py` (v2.1, hash-pinned in the bundle README), `tkg_spine_v3.py` (2026-10-01), `tests/`, `verification/` (probes, ablations, Z3, adversarial battery, scaling), `CANONICAL_SERIALIZATION_SPEC.md`.

**Caution before any push.** The TKG folder holds about 100 MB of datasets (`gdelt_full.tsv` 69 MB, `icews14_full.tsv`, `synth_large.tsv`, YAGO and Wikidata interval files). The bundle README says ICEWS14 and GDELT are **CC BY-NC-SA 4.0 (non-commercial)** via BorealisAI/de-simple. They should not go into a public portfolio repo. Ship a fetch script instead. The Research repo also contains `.ots` OpenTimestamps proofs and `.docx` drafts that may not belong in a public code repo.

**Older, different "Overseer".** The July 2026 work in `W:\...\Claude\White Paper -3 and its algorithm\` (TracePermit, admission control for agent documents) is a separate project. Its site is on GitHub as `tracepermit-ai-agent-overseer`. Its research package is a local-only git repo in the `- Copy` folder (15 commits, no remote).

**Recommendation.** Build a clean public repo from `arxiv_provenance_spine_v3` (code, tests, verification scripts, paper PDF, dataset fetch script, no raw datasets) and push it to `overseer-agentic-memory`. I have not done this. Waiting for your OK and your answer on the title.

## 4. Three-column reconciliation

Third-party clones are excluded (IsaacLab, tech-writing-tools, CGProject2, CPS-563-VR-HW2-Sea-Dragon, cs4732-roller-coaster). Tool caches (`.uv-cache`, `.codex` internals) are excluded.

### A. On GitHub only (no current local clone)

| Repo | Last push | Local situation |
|---|---|---|
| overseer-agentic-memory | 2026-09-25 | empty on GitHub; code is local only (section 3) |
| Aqua-SIM-Ohio-Report- | 2026-09-09 | no local clone found |
| akhil-portfolio | 2026-07-22 | only a stale clone in `~\Downloads\files (3)\akhil-portfolio` from 2026-06-12; remote main is ahead and has 5 unmerged `claude/*` branches |
| Ghost-X-HUD-Helmet-Simulator | 2026-02-02 | no local clone found |
| Ohio-Driving-Class-D-E-learning | 2026-01-21 | no local clone found |
| applystrike-os (private) | 2026-07-28 | no local clone found |
| Data-Center-HMI-Training- (private) | 2026-06-25 | no local clone found |
| HMI-cockpit-simulator- (private) | 2026-01-20 | no local clone found |
| Receipt-saver (private) | 2026-01-07 | no local clone found |
| spot-therm (private) | 2026-01-07 | no local clone found |
| Rocket-lunch-telemetry- (private) | 2025-12-23 | no local clone found |

### B. Local only (never pushed anywhere)

| Local path | State | Note |
|---|---|---|
| `W:\...\TKG_MATRIX DECOMPOSITION\Agent Memory Gatewaty\Research` | 214 commits, no remote | Overseer research; your most active repo |
| `W:\...\TKG_MATRIX DECOMPOSITION\White paper on TKG` | not under git | Overseer engine and verification code |
| `W:\...\Claude\White Paper -3 and its algorithm - Copy` | 15 commits, no remote | TracePermit research package |
| `W:\...\Claude\White Paper -3 and its algorithm` | not under git | original of the above |
| `W:\...\Claude\RL Robotics\tm-isaac` | 16 commits; remote is a local `.bundle` file; 10 commits newer than the bundle | Isaac/Newton backend work |
| `W:\...\AKHIL RESUME\AI Egineer\Projects AI ML\repopulse` | 2 commits; remote `AkhilDhruva/RepoPulse` returns 404 | repo was never created or was deleted |
| `W:\...\Projects AI ML\fhir-evidenceguard` | `git init`, 138 files staged, 0 commits | |
| `W:\...\Projects AI ML\northline-agents` | `git init`, 20 untracked files, 0 commits | |
| `W:\...\Claude\Model_Neutral_Overseer_Cognitive_Substrate_White_Paper_Draft` | `git init`, 0 commits | |
| `~\OneDrive\Documents\Data center Server Training\sites-data-center-ui-mock` | 1 commit by "OpenAI Codex Sites", no remote | |
| `~\OneDrive\Documents\...` (ID infographics builder, Data center Server Training, GIT HUB -Repo..., Portfolio Website review..., RESUME Builder..., TEST, test 2) | 7 empty `git init` folders, 0 commits | OneDrive breaks git; see HANDOFF.md in the portfolio clone |
| `~\Documents\Codex\...` (Codex, RepoPulse, RepoPulse-Testbed) | 3 empty `git init` folders | Codex session leftovers |

### C. Both, but out of sync

| Repo | Local path | Problem |
|---|---|---|
| DATA-CENTER-TRAINING | `W:\...\Claude\DATA-CENTER-TRAINING` | local main is 6 commits behind; 4 untracked files |
| DATA-CENTER-TRAINING | `W:\...\Claude\DATA-CENTER-TRAINING-latest` | on branch `fix/drawer-straight-pullout`; remote has 3 refs this clone lacks |
| aqua-sim | `W:\...\Claude\aqua-sim` | remote has 2 refs this clone lacks; local commits carry the wrong author |
| ProtoGraph (private) | `W:\...\Claude\ProtoGraph` | remote has 4 refs this clone lacks |
| Terrain-Memory-for-RL- (private) | `W:\...\Claude\RL Robotics\Terrain-Memory-for-RL` | 1 modified file; remote has 1 new ref; checked out on a `claude/*` branch |
| tracepermit-ai-agent-overseer | `W:\...\White Paper -3 and its algorithm\overseer-site` (and the `- Copy` twin) | local 2026-07-21, remote pushed 2026-09-17; local is behind |
| akhil-portfolio | `~\Downloads\files (3)\akhil-portfolio` | stale since 2026-06-12 (see A) |

### D. Both and in sync

RepoPilot, Gas-Turbine-3D-Interactive-Tutorial, ohio-drivesmart-academy (clone in Downloads), AeroMind-FlightLab (clone in Downloads).

"Behind" and "new refs" come from `git fetch --dry-run`, so no local refs were changed.

### E. Unmerged branches and open pull requests on GitHub

Work that is on GitHub but not on the default branch. None of this is lost, but it is invisible to anyone reading the repo.

| Repo | Extra branches | Open PRs |
|---|---|---|
| akhil-portfolio | 5: `claude/ai-pivot`, `claude/data-center-upskilling`, `claude/job-application-analytics-cstd1v`, `claude/test-coverage-analysis-qr923q`, `claude/vercel-analytics` | 0 |
| DATA-CENTER-TRAINING | 4: `claude/data-hall-ride`, `claude/live-link-work-review-lk3qm7`, `claude/rack-screenshots-y0ye7j`, `fix/drawer-straight-pullout` | 0 |
| ProtoGraph (private) | 4 `claude/*` branches | 0 |
| Terrain-Memory-for-RL- (private) | 3: `claude/isaac-newton-backend`, `claude/portfolio-repos-standard-4fvorc`, `claude/terrain-memory-prototype-rui7un` | 1: "Add terrain-memory: provenance-gated replay reconciliation system", opened 2026-09-30 |
| applystrike-os (private) | 2: `cloudflare/workers-autoconfig`, `main` (default is `claude/update-z4ywvc`) | 1: "Add Cloudflare Workers configuration", opened 2026-07-24 |
| tracepermit-ai-agent-overseer | 1: `claude/portfolio-repos-standard-4fvorc` | 0 |
| aqua-sim | 1: `claude/flood-simulator-planning-myqfs0` | 0 |

The other 13 repos have a single branch and no open PRs.

## 5. Portfolio site (for Phase 2)

- Live at https://akhil-portfolio-pi-five.vercel.app. Static HTML on Vercel: `index.html` (about 93 KB), `assets/`, `ai-workflow-quest.html`, `SiteReady-ScissorLift-PreUseCard.html`, a `.github` workflow for SLSA provenance.
- Source of truth is GitHub `main` (last push 2026-07-22, "Hard pivot: AI-systems-first positioning"). No current local clone. Phase 2 should start from a fresh clone, not from the Downloads copy or the OneDrive folder.

## 6. Proposed clean-up (not done, needs your OK)

1. Fix the global git identity (section 1).
2. Push the Overseer bundle to `overseer-agentic-memory` once the title and dataset handling are settled.
3. Add descriptions to the six public repos that have none, and replace the three placeholder descriptions on private repos.
4. Decide whether `repopulse`, `fhir-evidenceguard` and `northline-agents` should get GitHub repos or stay local.
5. Review the two open PRs (Terrain-Memory, applystrike-os) and the 20 unmerged `claude/*` branches; merge or delete each one deliberately. Reset `applystrike-os` default branch to `main`.
6. Delete nothing. The OneDrive and Codex empty `git init` folders are harmless; leave them unless you want them gone.
