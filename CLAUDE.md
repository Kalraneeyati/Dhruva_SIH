# DHRUVA — project context

Deep-sea Hazard, Routing & Understanding via Vernacular Agents. ISRO PS 26176 (ORCA).

**The thesis:** reasoning runs onshore, answers survive offshore. A full advisory compresses to
**145 bits** — one NavIC L5 segment is 220 — and the phone reconstructs a spoken
regional-language explanation from a shipped codebook with no network.

Plan: `dhruva-plan.html`. Build contract and phase gates: `IMPLEMENTATION.md`. Neither is
re-opened mid-build; if a decision here looks wrong, say so and stop, do not quietly change it.

---

## Settled decisions that keep getting re-litigated

- **No hardware is purchased.** The NavIC uplink is ISRO's — no team gets to transmit. Our claim
  is *segment conformance*, which is arithmetic and checkable against the field table. The
  identical 145-bit wire format rides QR (19 bytes, base32), Bluetooth and SMS. An SDR is used
  only if the MAIT communications lab loans one; hard abandon at D13.
- **The LLM never emits a number.** See the numeric firewall below. This is the whole trust story.
- **PFZ has no API — it is scraped and attributed.** Never imply a feed exists. Say it in the
  architecture diagram, carry `source_url` and `fetched_at` on every row.
- **Boundaries are indicative, never legal.** Every rendered EEZ/IMBL/MPA line carries the flag.
- **Python is pinned to 3.12** via uv. The system interpreter is 3.14 and the scientific stack
  does not have wheels for it.

## Stack — locked

| Layer | Choice |
|---|---|
| Orchestration | LangGraph 0.2 + Pydantic v2 — explicit state, checkpointing, cyclic re-planning |
| Model (planning) | Gemini 2.5 Flash via OpenRouter — tool selection and decomposition |
| Model (Indic) | Sarvam-30B API / Sarvam-105B open weights; Qwen3-8B on Ollama is the offline path |
| Backend | Python 3.12 · FastAPI · arq |
| Array compute | xarray · dask · Zarr cache |
| Database | PostgreSQL 16 · PostGIS · pgvector · TimescaleDB — one engine, no separate vector DB |
| Tiles | TiTiler (raster) · pg_tileserv (vector) |
| Frontend | React 19 · Vite · TypeScript · MapLibre GL · deck.gl — MapLibre, not Mapbox: no token, no quota |
| Offline | PWA · service worker · Dexie (IndexedDB) |
| Language | Bhashini ULCA primary; Sarvam Saarika ASR + Bulbul v3 TTS as fallback and demo voice |
| Voice channel | Asterisk IVR + WhatsApp Cloud API — reaches a feature phone |
| Observability | Langfuse, self-hosted — traces double as the explainability record |
| Infra | Docker Compose · Oracle A1 (2 OCPU / 12 GB, Mumbai) · Caddy |

## Data sources — and the trap in each

| Source | Gives | Access | Trap |
|---|---|---|---|
| INCOIS ERDDAP | Oceansat-2 OCM ocean colour, Indian Ocean grids | griddap REST, no key | Server omits the `GlobalSign RSA OV SSL CA 2018` intermediate — use `data/ca/incois-bundle.pem` via `INCOIS_CA_BUNDLE`, **never `verify=False`**. Only 15 griddap datasets. `NOAA_AVHRR_AMSR_datasets` has dims `[time][zlev][lat][lon]` (the summary omits `zlev`) and ends **2011-10-04** — archive, not a feed. `/search` 302-redirects; follow redirects or use `/griddap/index.json`. |
| Copernicus Marine | SST, chlorophyll, currents, waves | `copernicusmarine` toolbox, free account | Registration approval is not instant — day 1, not day 12 |
| Open-Meteo Marine | Wave height, swell, wind, ERA5 archive | REST, no key | Coarse near shore — label it forecast, never observation |
| MOSDAC (ISRO) | INSAT-3D/3DR imagery, cyclone products | registered download | Bulk ordering is slow — cache a fixed demo window |
| INCOIS PFZ advisory | Official daily PFZ lines, 586 landing centres | HTML/text bulletins, **no API** | Must be scraped and attributed |
| NASA PACE OCI | Hyperspectral ocean colour, phytoplankton community | OB.DAAC · `earthaccess` | Enrichment only — the core path never depends on it |
| Marine Regions (VLIZ) | EEZ, IMBL, MPA polygons | shapefile → PostGIS | Indicative boundaries — never render as a legal line |
| GEBCO | Bathymetry, depth and shelf context | grid download | Large — subset to the Indian EEZ once, store as COG |
| Bhashini | ASR, translation, TTS, 22 languages | two-step config-then-compute | Auth is a config call returning the real endpoint and key — build that handshake first |

## The numeric firewall — non-negotiable

The model may not introduce a number.

1. Tools produce an `EvidenceBundle`: `{key, value, unit, dataset_id, cell, valid_time, threshold?, rule_id?}`.
2. The LLM receives the bundle and writes narration.
3. The validator extracts **every** numeric token from the narration — ASCII and Indic digits,
   plus spelled-out numerals in the target language.
4. Each value must match a bundle value within rounding tolerance, or appear in the explicitly
   allowed derived set (unit conversions declared per field: m→ft, kt→km/h).
5. On failure: one retry with a stricter prompt. On second failure: render the pure template and
   log the incident. **Never ship the unvalidated string.**

A number with no evidence cannot be rendered anywhere — the UI component requires the bundle.
This includes the shore console.

## Capsule

Field table is `docs/CAPSULE_SPEC.md` and it is the single source of truth: generate encoder and
decoder from it so they cannot drift. Total **145 bits**, 75 free inside a 220-bit segment.

- Every quantiser **clamps**. Wrapping a 9 m sea into a calm reading is the worst bug we can ship.
- Capsule figures are quantised, not rounded for display: wave 0.25 m, SST 0.5 °C, current
  0.1 kt, all bearings to the 16-point compass. Demo values must sit on the grid or the online
  and offline cards disagree on screen.
- The decoder is pure: no network, no filesystem, no clock. Python and TypeScript run the same
  corpus in CI.

## Risk thresholds

`docs/THRESHOLDS.md`. Current values are **engineering placeholders**. Before any public claim,
replace with published INCOIS Ocean State Forecast criteria and cite the source in the file.
Never present invented safety thresholds as official. Absolute overrides regardless of boat
class: cyclone warning within 300 km, lightning within 50 km, any tsunami alert → NO-GO.

## Conventions

- Commits: `area: imperative summary` (`codec: clamp wave quantiser at 7.75 m`).
- One PR per phase gate. Gates are in `IMPLEMENTATION.md`; do not start a phase before the
  previous gate passes.
- Vessel positions quantise to the 0.05° grid at rest, tracks purge after 7 days, no third-party
  analytics anywhere in the frontend.
- Every advisory response carries: *advisory only, follow official INCOIS and IMD warnings.*
- NO-GO outranks everything. A favourable fishing zone never renders above an active hazard.

## Subagents

`erddap-explorer` for anything touching datasets · `geo-reviewer` before merging geospatial code
· `capsule-auditor` after every codec change.
