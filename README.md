# STA Debugger

A full-stack tool that parses OpenSTA static timing analysis reports and diagnoses every timing violation with a rule-based analysis engine — bottleneck cells, logic depth, clock skew, severity, and prioritized fix suggestions per path.

**Stack:** FastAPI + SQLAlchemy + SQLite backend, React (Vite) frontend, JWT auth, pytest.

## Why

Reading raw STA reports is tedious: a `report_checks` dump for a real design is thousands of lines of path tables, and figuring out *why* a path fails (one slow cell? too many logic levels? clock skew?) means tracing each one by hand. This tool automates that first pass. Upload a report, and every path comes back parsed, classified, and diagnosed, with the analysis history saved per user.

## How the analysis works

### 1. Parsing (`backend/app/sta_parser.py`)

An OpenSTA report is a sequence of path blocks. The parser walks each block line by line, tracking which timing section it is in (data *arrival* vs. data *required*), and extracts:

- start/endpoint, path group, path type (`max` = setup check, `min` = hold check)
- the full logic chain — instance pin, cell, incremental delay, cumulative time, rise/fall edge — from the arrival section only, so capture-side clock pins never leak into the chain
- launch and capture clock network latencies, the capture clock edge (≈ clock period), arrival/required times, and the slack line with its MET/VIOLATED verdict

### 2. Rule engine (`backend/app/rules.py`)

Each path is diagnosed from structural features, no external services involved:

| Feature | How it's computed | Rule that fires |
|---|---|---|
| Bottleneck cell | Stage with the largest share of total combinational delay | ≥ 35% share → suggest upsizing / higher drive strength for that specific cell |
| Logic depth | Combinational stages, excluding clock pins, ports, and the launch/capture flops | ≥ 8 levels → pipeline; 5–7 → restructure the logic cone |
| Clock skew | Capture latency − launch latency | Negative skew on a setup path → balance the clock tree; positive skew on a hold path → same, opposite reason |
| Endpoint type | Last chain stage is an I/O port | Setup violation on an output port → re-check the external delay budget in the constraints |
| Severity | \|slack\| relative to the clock period (absolute fallback) | critical / high / medium / low |
| Hold violations | Path type `min` + VIOLATED | Delay buffers on the data path (the standard fix), plus a post-CTS re-check note |

Report-level metrics (WNS, TNS, setup/hold violation counts) are aggregated over all paths.

### 3. Optional AI explanations (`backend/app/llm.py`)

Each violated path has an "Explain with AI" button that turns the rule engine's diagnosis into a short prose explanation using Groq's free-tier API. It is deliberately a thin layer on top of the rule engine — the app is fully functional without any API key. Users paste their own key in the UI (kept in browser localStorage, never stored server-side), or the server operator can set `GROQ_API_KEY`.

## Screens

- **Login/Register** — JWT-based, bcrypt-hashed passwords
- **New Analysis** — drag-and-drop a `.txt`/`.rpt`/`.log` report
- **Results** — summary metrics (WNS/TNS/violation counts), a worst-paths slack chart, and an expandable card per path with stage-by-stage delay bars and the suggested fixes
- **History** — every past analysis stored per user in SQLite, reopenable and deletable

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

Open http://localhost:5173 — the Vite dev server proxies `/api` to the backend on port 8000. Register an account, then upload one of the reports in [`sample_reports/`](sample_reports) (`sky130_with_violation.txt` shows a setup violation diagnosed end to end).

Interactive API docs are at http://localhost:8000/docs.

## Tests

```bash
cd backend
python -m pytest
```

25 tests cover the parser (using the real OpenSTA sample reports as fixtures), the rule engine's individual rules, and the API surface (auth flow, upload/list/get/delete, per-user isolation).

## Project layout

```
backend/
  app/
    sta_parser.py      # OpenSTA report parser
    rules.py           # rule-based diagnosis engine
    schemas.py         # Pydantic models (parser output + API)
    auth.py            # bcrypt + JWT
    db_models.py       # SQLAlchemy: users, analyses
    llm.py             # optional Groq explanations
    routers/           # /api/auth, /api/analyses
  tests/               # pytest: parser, rules, API
frontend/
  src/
    pages/             # Login, Upload, Analysis, History
    components/        # SummaryCards, SlackChart, PathCard, Navbar
sample_reports/        # real OpenSTA outputs (nangate45, sky130)
```

## Known limitations

- The parser targets OpenSTA's `report_checks` format; PrimeTime reports differ enough that they'd need their own parsing path.
- Severity uses the capture clock edge as a proxy for the clock period, which is right for single-cycle paths but pessimistic for multicycle ones.
- SQLite and a single process are plenty for a personal tool; a team deployment would want Postgres and a proper secret-management story.
