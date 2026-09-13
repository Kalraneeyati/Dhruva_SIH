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
pytest -q          # 151 tests, ~20s (some hit live Open-Meteo)
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
| Safe route | **Real, hazard-avoiding.** `graph/route_planner.py` fetches live wave height across a 5x5 grid (one batched Open-Meteo request — confirmed the API supports comma-separated multi-point queries) and runs Dijkstra with a hard penalty at/above the boat class's no-go threshold, so the path actively steers around a hazard cell rather than merely preferring lower waves. This replaces an earlier straight-line stub that said outright it didn't do this yet. |
| Productivity decline (chlorophyll trend) | **Honestly upgraded, still partial.** Still no chlorophyll (needs Copernicus credentials this deployment doesn't have). But `graph/sst_history.py` discovered Open-Meteo's marine endpoint serves real historical daily SST — previously unused in this codebase — so the answer now cites a real 40+ day SST trend (e.g. "+1.1°C over 43 days") instead of refusing to say anything, while still declining to state a productivity conclusion chlorophyll data alone would be needed to support. |
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
    route_planner.py      # Dijkstra over a live batched wave-height grid
    sst_history.py         # real 40+ day historical SST trend (Open-Meteo)
    orchestrator.py       # ties it all together, per-intent handlers
  api/
    schemas.py            # camelCase response models (does NOT touch Prateek's
                          # sources/base.py or sources/conditions.py — converts
                          # at the boundary instead, so his ongoing local work
                          # never has to reconcile a wire-format change here)
    query.py               # POST/GET /query
```

## Real bugs the tests and live testing actually caught

Worth stating plainly rather than just "137 tests pass" — these were found by
building this out and testing it end-to-end, not hypothetical:

1. **The firewall itself correctly rejected three of my own early narratives**
   (nearest_pfz, safe_route, geofence_avoidance) because each stated a number
   with no `EvidenceBundleEntry` behind it. Found via manual curl testing,
   then locked in as a regression test (`tests/test_orchestrator.py`).
2. **A Python-vs-JS rounding divergence** in the capsule codec: Python's
   `round()` is banker's-rounding (`round(4.5) == 4`), JS's `Math.round` is
   round-half-up (`Math.round(4.5) == 5`). Unreconciled, this would have
   silently produced different capsule bytes for the same input depending on
   which language encoded it. Fixed in `codec/bits.py`, caught by a corpus
   fixture deliberately placed on a `.5` boundary.
3. **The firewall's number extractor discarded sign entirely** — a cooling
   trend narrated as "-1.5°C" extracted the unsigned `1.5`, which could never
   match a `-1.5` evidence value, and would have wrongly withheld a correct
   answer the first time a real trend happened to be negative. Fixed in
   `evidence/firewall.py`'s number-matching regex (a negative lookbehind so
   an ordinary hyphenated word like "sea-state" is never mistaken for a minus
   sign).
4. **The frontend never actually sent the user's location or boat class to
   `/query`** — every query silently used the gazetteer/default location and
   the smallest boat's safety thresholds regardless of who was asking or
   where. Fixed by wiring `BoatClassSelector` and `LocationControl`
   (geolocation) into `BoatApp.tsx`'s actual request.

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

## Future roadmap (realistic next steps, roughly in priority order)

1. **Wire a real LLM** behind the numeric firewall (already built) for richer,
   more natural narration than the current template strings — the highest
   leverage single change, and the plumbing is ready for it.
2. **Bhashini integration** for real ASR/TTS and translation of the narrative
   itself (today only the UI chrome and the offline capsule's codebook are
   translated; the live narrative is English-only from the backend).
3. **Copernicus Marine credentials** to unlock real chlorophyll data — turns
   the PFZ estimate from an SST-only proxy into the real front-detection
   method INCOIS itself uses, and turns the productivity-decline answer from
   "SST alone" into a real chlorophyll+SST correlation.
4. **A confirmed IMD/RSMC cyclone and lightning feed** to implement the
   absolute-override rules (`risk/rules.py`'s `OVERRIDE_TODO`) for real,
   rather than the current honest "no live feed" disclosure.
5. **Merge Prateek's local Phase 3 work** (LangGraph-based graph, if it
   diverges from this deterministic dispatch) and the PostGIS boundary path
   once Docker is available to test it — see `geo/boundaries.py`'s docstring
   for where this file's Postgres-free equivalent should hand off.
6. **Scale the route planner's grid** and add real multi-destination
   route options (currently one candidate zone; a real deployment would let
   a crew pick among several, or specify their own destination port).
