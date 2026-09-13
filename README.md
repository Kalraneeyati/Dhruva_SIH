# DHRUVA

**D**eep-sea **H**azard, **R**outing & **U**nderstanding **v**ia **V**ernacular **A**gents.
ISRO PS 26176 (ORCA), Smart India Hackathon 2026.

> "Reasoning runs onshore. Answers survive offshore."

Full project context and decisions: [`CLAUDE.md`](CLAUDE.md). Build plan and
phase gates: [`IMPLEMENTATION.md`](IMPLEMENTATION.md). Backend specifics:
[`backend/README.md`](backend/README.md). Frontend specifics:
[`frontend/README.md`](frontend/README.md).

## Run the whole thing (two terminals, no Docker, no API keys)

**Terminal 1 — backend:**
```bash
cd backend
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[data,geo,graph,dev]"
uvicorn dhruva.app:app --port 8000
```

**Terminal 2 — frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — the landing page explains the problem and
approach; **Launch the live demo** goes to the Boat surface, which is now
talking to the real backend (`frontend/.env.local` points it at
`http://localhost:8000`; delete that file to fall back to bundled mock data
with zero backend needed).

## What's real right now

- Live wave/wind/SST data (Open-Meteo, no key) flowing through a real risk
  engine into a real safe/caution/no-go verdict.
- A numeric firewall that has already caught real bugs during development —
  see `backend/README.md`.
- A 145-bit offline advisory capsule, encoded by the **Python** backend and
  decoded by an **independently-written TypeScript** implementation in the
  browser — proven identical against a shared test corpus
  (`eval/capsule_corpus.jsonl`) AND verified live: paste a backend-generated
  capsule's payload into the Boat surface's decode box and it renders the
  correct advisory with zero network calls.
- Real geofencing distance to the actual India-Sri Lanka IMBL treaty line
  (and 17 other real maritime boundary lines), computed geodesically,
  entirely offline (bundled data, no Postgres needed).
- All 8 official PS26176 example queries answered end-to-end.

## What's honestly not there yet

See the tables in `backend/README.md` and `frontend/README.md` — chlorophyll
needs Copernicus credentials this deployment doesn't have, PFZ is a live
SST-gradient estimate (not an official INCOIS bulletin, and says so), cyclone/
lightning bulletins need a confirmed IMD feed, and the Shore Console's fleet
is illustrative (no AIS source in scope). Every one of these says so in the
UI or the API response rather than quietly guessing.

## Tests

```bash
cd backend && source .venv/bin/activate && pytest -q     # 137 tests
cd frontend && npm test                                   # 38 tests
```
