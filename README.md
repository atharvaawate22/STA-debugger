# STA Debugger

A full-stack tool that parses OpenSTA static timing analysis reports and works out *why* paths fail: it diagnoses each violation with a rule engine, groups violations that share a root cause, and compares reports before and after a fix.

**Stack:** FastAPI + SQLAlchemy + SQLite backend, React (Vite) frontend, JWT auth with an admin role, pytest.

## Why

Reading raw STA reports is tedious: a `report_checks` dump for a real design is thousands of lines of path tables, and figuring out *why* a path fails (one slow cell? a ripple-carry chain? a hold fix that will break setup?) means tracing each one by hand. This tool automates that first pass. Nothing in the diagnosis depends on an LLM — the rules are deterministic, tested, and each suggestion says which rule produced it.

## How the analysis works

### 1. Parsing (`backend/app/sta_parser.py`)

An OpenSTA report is a sequence of path blocks. The parser walks each block line by line, tracking whether it is in the data *arrival* or *required* section, and extracts:

- start/endpoint, path group, path type (`max` = setup, `min` = hold; inferred from the "library setup/hold time" line when the header is missing)
- the logic chain — instance pin, cell, delay, cumulative time, edge — from the arrival section only
- **fanout, capacitance and slew** when the report was generated with `-fields {fanout cap slew}`; the column header decides which numbers map to which field
- launch/capture clock latency, capture clock edge, input/output external delay, slack and verdict

Blocks that can't be parsed (truncated, wrong format) are skipped and counted, and the UI tells you how many.

### 2. Rule engine (`backend/app/rules.py`)

Rules are small registered functions (`@setup_rule("slow-cell")`); each returns a suggestion tagged with its rule id, and suggestions are ordered by priority.

| Rule id | Fires when | What it says |
|---|---|---|
| `slow-cell` | one stage has ≥ 35% of the path's logic delay | Upsize to the *next drive strength* (`NAND2_X2` → `NAND2_X4`), with the violation expressed as a share of that stage's delay. If the cell is already at drive ≥ 8, it recommends splitting the load instead of upsizing |
| `serial-chain` | ≥ 4 consecutive stages from the same cell family (drive ignored) | A run of `maj3`/adder cells is a ripple-carry chain → carry-lookahead; other repeated gates → rebalance into a tree. Reports the run's share of the delay |
| `high-fanout` | a stage drives ≥ 8 loads (needs fanout data) | Buffer or duplicate the driver |
| `logic-depth` | ≥ 8 levels / 5–7 levels | Pipeline / restructure the cone |
| `negative-skew` | capture clock earlier than launch | Balance the clock tree |
| `io-constraint` | endpoint is an output port | Compares the external delay to the violation: if relaxing the budget alone would close the path, says so |
| `distributed-delay` | nothing else fired | States how much of the logic delay must be recovered |
| `hold-buffers` | hold violation | Delay buffers, with a rough count based on the path's typical stage delay |
| `positive-skew`, `recheck-post-cts` | hold | Skew and post-CTS notes |
| `hold-setup-headroom` | hold violation whose setup path is in the same report | Looks up the *setup slack on the same startpoint/endpoint*. If it can absorb the padding: safe. If not: "buffer padding alone cannot fix this" |

Severity is |slack| relative to the clock period (absolute fallback).

### 3. Root-cause grouping

After per-path diagnosis, violations (setup and hold separately) are grouped by what they share: the same instance on several failing paths, endpoints on the same bus (`sumreg[*]`), a common startpoint, or the same slow cell. Each group reports its worst slack and share of TNS, so "fix `m1`, help 3 paths and 87% of TNS" is one line. Clicking a group filters the path list.

### 4. Before/after comparison (`backend/app/compare.py`)

Pick two saved analyses; paths are matched by startpoint, endpoint, check type and group, and classified as fixed, improved, regressed, unchanged, newly violating, or no longer reported, along with WNS/TNS deltas. Slack changes under 5 ps are treated as noise.

### 5. Optional AI explanations (`backend/app/llm.py`)

Each violated path has an "Explain with AI" button that turns the rule engine's diagnosis into prose using Groq. The model is told to explain only the listed suggestions. It is optional: the app is fully functional without a key. Keys are an admin-managed pool; users pick one by label and never see or paste a raw key. The server operator can alternatively set `GROQ_API_KEY`.

## Screens

- **Login/Register** — JWT auth, bcrypt-hashed passwords; admins are routed to the admin console
- **New Analysis** — drag-and-drop a `.txt`/`.rpt`/`.log` report
- **Results** — WNS/TNS summary, slack chart, root-cause groups, and an expandable card per path with stage delays (and fanout), suggestions tagged by rule id
- **History** — past analyses per user, reopenable and deletable
- **Compare** — before/after report diff
- **Admin** — users, all analyses, usage stats, API-key pool

## Running it

Backend (Python 3.10+):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend (Node 18+), in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` to the backend on port 8000. Register an account, then try [`sample_reports/`](sample_reports):

- `sky130_with_violation.txt` — a setup violation through a 5-stage `maj3` chain
- `adder_before.txt` / `adder_after.txt` — a report with fanout/cap/slew columns, a bus of violations sharing one ripple-carry chain, and a hold violation that conflicts with its setup path. Upload both, then use **Compare**.

The `adder_*` reports are synthetic (generated to exercise the rules); the others come from OpenSTA runs on nangate45 and sky130.

Interactive API docs are at http://localhost:8000/docs.

## Tests

```bash
cd backend
python -m pytest
```

72 tests cover the parser (including the fanout-column format, clock lines with extra columns, truncated blocks), each rule, hold/setup interplay, grouping, report comparison, and the API (auth, per-user isolation, compare access checks, and loading analyses saved before groups/rule ids existed).

## Project layout

```
backend/
  app/
    sta_parser.py      # OpenSTA report parser
    rules.py           # rule registry, path diagnosis, grouping
    compare.py         # before/after report comparison
    schemas.py         # Pydantic models (parser output + API)
    auth.py            # bcrypt + JWT
    db_models.py       # SQLAlchemy: users, analyses, API keys
    llm.py             # optional Groq explanations
    routers/           # /api/auth, /api/analyses, /api/admin, /api/api-keys
  tests/               # pytest: parser, rules, compare, API
frontend/
  src/
    pages/             # Login, Upload, Analysis, History, Compare, Admin
    components/        # SummaryCards, SlackChart, GroupsPanel, PathCard, Navbar
sample_reports/        # OpenSTA outputs (nangate45, sky130) + synthetic adder pair
```

## Known limitations

- The parser targets OpenSTA's `report_checks` format; PrimeTime reports differ enough to need their own parsing path. Times are assumed to be in one consistent unit (no ns/ps conversion).
- The rules are heuristics over one report. Drive-strength suggestions assume the usual 1/2/4/8/16 sizes and can't check that a variant exists in your library; delay-cell counts are estimates. Nothing here re-runs timing to confirm a fix works.
- Severity uses the capture clock edge as a proxy for the clock period, which is pessimistic for multicycle paths.
- Hold/setup headroom only looks at the same startpoint/endpoint pair inside the uploaded report; if the setup path isn't in the report, no headroom check is made.
- SQLite and a single process are plenty for a personal tool; a team deployment would want Postgres and proper secret management.
