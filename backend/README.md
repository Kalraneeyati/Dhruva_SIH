# DHRUVA backend

ISRO PS 26176 (ORCA). Phase 0-2 (toolchain, repo skeleton, data plane — source
registry, Open-Meteo/Copernicus adapters, Zarr cache, PostGIS boundary loader,
PFZ scraper) were already built and tested (71 tests) before this pass. This
document covers what was added on top: **Phase 3 (risk engine, numeric
firewall, orchestrator), Phase 4 (145-bit capsule codec)**, and a working
`/query` endpoint that actually answers all 8 official PS26176 queries from
live data — no LLM key, no Docker, no Postgres required to run it.

## Running it

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[data,geo,graph,dev]"
uvicorn dhruva.app:app --port 8000
```

Then, from `frontend/`: copy `.env.local` with `VITE_API_BASE_URL=http://localhost:8000`
and `npm run dev`. No API keys, no database, no external services needed —
every live number in a response comes from Open-Meteo (no key required).

```bash
pytest -q          # 137 tests, ~16s (some hit live Open-Meteo)
```

## What's real vs. what's honestly stubbed

| Capability | Status |
|---|---|
| Live wave/wind/SST from Open-Meteo | **Real.** `conditions_at()` (Phase 2, unchanged) fans out in parallel, every value carries its dataset id and timestamp. |
| Risk verdict (safe/caution/no-go) | **Real.** `risk/rules.py` against the IMPLEMENTATION.md 3.2 threshold table, tested at every boundary. |
| Numeric firewall | **Real**, and it isn't decorative — it caught three real bugs during development (nearest_pfz, safe_route, geofence_avoidance each initially stated a number with no matching evidence entry; the firewall silently replaced the narrative with a withdrawal message, `tests/test_orchestrator.py` now guards against a regression). |
| 145-bit capsule codec | **Real**, and proven cross-language: `eval/capsule_corpus.jsonl` is loaded by both `tests/test_codec_corpus.py` (Python) and `frontend/src/shared/capsule/sharedCorpus.test.ts` (TypeScript) — same fixtures, same assertions, both must pass. Verified live in-browser too: a capsule encoded by this backend from real data decodes correctly in the frontend's independent TS implementation. |
| Geofencing / boundary distance | **Real**, Postgres-free. `geo/local_boundaries.py` uses the real Marine Regions/VLIZ data (fetched once, bundled at `data/layers/india_boundaries.geojson`, 18 real lines including the actual India-Sri Lanka IMBL treaty line), geodesic distance via pyproj. This is an ADDITION alongside the locked `geo/boundaries.py` (PostGIS) path, not a replacement — see that file's own module docstring. |
| Nearest PFZ | **Honest partial.** INCOIS's PFZ bulletin has no confirmed public URL (a known Phase-2 finding); rather than fabricate an "official" entry, `graph/pfz_estimator.py` computes a *candidate* zone from a live SST gradient (Open-Meteo, no key) and labels every response as NOT an official INCOIS bulletin. |
| Chlorophyll-dependent answers (chlorophyll/SST zones, productivity decline) | **Honestly incomplete.** Needs Copernicus Marine credentials this deployment doesn't have. The response says so explicitly rather than guessing a chlorophyll number or a productivity trend. |
| Cyclone/lightning absolute override | **Not implemented**, by design — IMPLEMENTATION.md flags that no confirmed public IMD/RSMC API exists. `risk/rules.py` has an `OVERRIDE_TODO` marker for where it plugs in once one is confirmed. |
| Orchestration | Deterministic Python dispatch (`graph/orchestrator.py`), not LangGraph, despite LangGraph being an installed dependency — see that module's docstring for why (no LLM key configured yet means no real routing decisions to make; adding one is a mechanical wrap of the existing node boundaries, not a redesign). |
| Fleet / vessel tracking (Shore Console) | **Mock, deliberately, permanently for now** — there is no AIS/vessel-tracking data source anywhere in scope. The frontend labels this explicitly regardless of backend availability. |

## New modules

```
dhruva/
  risk/
    thresholds.py       # IMPLEMENTATION.md 3.2 table
    rules.py             # assess_risk() — wave/wind -> verdict
  evidence/
    schema.py            # EvidenceBundleEntry, RiskVerdict (camelCase wire format)
    firewall.py          # extract_numbers, validate_narration, render_template
  codec/
    field_table.py bits.py enums.py quantizers.py codec.py base32.py
                         # Python half of the 145-bit codec — see eval/capsule_corpus.jsonl
  geo/
    local_boundaries.py  # Postgres-free geofencing, real bundled data
  graph/
    gazetteer.py         # named Indian coastal locations -> lat/lon
    intent.py            # classifies the 8 official query types
    pfz_estimator.py      # live SST-gradient candidate PFZ
    orchestrator.py       # ties it all together, per-intent handlers
  api/
    schemas.py            # camelCase response models (does NOT touch Prateek's
                          # sources/base.py or sources/conditions.py — converts
                          # at the boundary instead, so his ongoing local work
                          # never has to reconcile a wire-format change here)
    query.py               # POST/GET /query
```

## Known gaps for whoever picks this up next

- LLM integration: `graph/orchestrator.py` narrates via Python string
  formatting today. Wiring an LLM (Gemini/Kimi/MiniMax per the team's
  zero-spend stack) means: the LLM writes the narrative, `evidence/firewall.py`
  validates it (already built, already tested against adversarial cases),
  one retry on failure, template fallback on a second failure (also already
  built — `render_template`). The plumbing is there; only the LLM call itself
  is missing.
- Real PostGIS path (`geo/boundaries.py`) needs Docker + Postgres to actually
  run — untested on this machine. The Postgres-free path
  (`geo/local_boundaries.py`) is what the API actually uses today.
- Cyclone/lightning bulletins: needs a confirmed IMD/RSMC feed URL.
- Chlorophyll: needs Copernicus Marine credentials
  (`COPERNICUSMARINE_SERVICE_USERNAME`/`PASSWORD` in `.env`).
