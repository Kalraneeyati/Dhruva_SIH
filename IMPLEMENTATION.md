# DHRUVA — Implementation Guide

Build instructions for ISRO PS 26176 (ORCA). This file is the working contract: it assumes the
decisions in the plan are settled and does not re-open them. Work top to bottom. Every phase ends
in a gate — do not start the next phase until the gate passes.

**What we are building:** reasoning runs onshore, answers survive offshore. The full advisory
compresses to 145 bits (one NavIC segment is 220), and the phone reconstructs a spoken
regional-language explanation with no network.

---

## Phase 0 — Toolchain (do this first, ~45 min)

### 0.1 Claude Code plugins

Run each inside a Claude Code session. The official marketplace is built in.

```
/plugin install pyright-lsp@claude-plugins-official
/plugin install typescript-lsp@claude-plugins-official
/plugin install context7@claude-plugins-official
/plugin install mcp-server-dev@claude-plugins-official
/plugin install security-guidance@claude-plugins-official
/plugin install code-review@claude-plugins-official
/plugin install github@claude-plugins-official
```

| Plugin | Why it is here |
|---|---|
| `pyright-lsp` | Real type errors across the agent graph and the codec. Catches bit-width mistakes early. |
| `typescript-lsp` | Same for the React/deck.gl frontend. |
| `context7` | Current docs for LangGraph, xarray, deck.gl, copernicusmarine. These libraries move fast and stale API guesses cost hours. |
| `mcp-server-dev` | We write our own MCP wrappers for ERDDAP and Copernicus; none exist. |
| `security-guidance` | We handle live vessel positions and six API keys. |
| `code-review` | Multi-agent review before merges once more than one person is committing. |
| `github` | Issues and PRs from inside the session. |

Language servers need binaries on the machine:

```bash
npm i -g pyright typescript typescript-language-server
```

Add later, only when the phase needs them: `frontend-design` (D14), `duckdb-skills` (data
exploration), `document-skills@anthropic-agent-skills` for the pptx deck (D18).

Do **not** install ECC, awesome-claude-code-toolkit, or any other mega-bundle. They add hundreds of
generic skill descriptions to every session's context and none of them know anything about ocean
data.

### 0.2 MCP servers for development

These help us *write* the system. They are not part of the product.

```
claude mcp add open-meteo -- npx -y open-meteo-mcp
```

Optional, if the geospatial work gets heavy: `gis-mcp` (PyPI, `pip install gis-mcp`) for shapely
and pyproj operations through natural language.

### 0.3 Project subagents

Create these in `.claude/agents/` in the repo root. They exist because the same three mistakes
recur in this domain.

**`.claude/agents/erddap-explorer.md`**

```markdown
---
name: erddap-explorer
description: Queries INCOIS ERDDAP and Copernicus, inspects NetCDF structure, and writes fetch code. Use for any task involving dataset discovery, griddap URLs, or xarray loading.
tools: Bash, Read, Write, Edit, WebFetch
model: sonnet
---

You work with oceanographic data servers.

ERDDAP griddap URL form:
  {base}/erddap/griddap/{datasetID}.{ext}?{var}[({t_start}):{stride}:({t_end})][({lat_min}):({lat_max})][({lon_min}):({lon_max})]
Extensions: .json for small probes, .nc for real subsets, .csv for eyeballing.

Rules:
- Always call the dataset's /info page before writing a query. Never assume variable names,
  dimension order, or time units.
- INCOIS ERDDAP has a TLS chain that fails verification on some hosts. Pin the CA bundle.
  Never pass verify=False.
- Time dimensions are frequently cf-time, not datetime64. Decode with cftime, check calendar.
- Longitudes may be 0-360 or -180-180. Check before subsetting the Indian Ocean.
- Report the actual numbers you got back, with units, not just that the call succeeded.
```

**`.claude/agents/geo-reviewer.md`**

```markdown
---
name: geo-reviewer
description: Reviews geospatial code for CRS errors, coordinate order bugs, and boundary logic mistakes. Use before merging anything touching lat/lon, PostGIS, distances, or the EEZ/IMBL layers.
tools: Read, Grep, Glob, Bash
model: sonnet
---

You review geospatial code for the specific errors that survive testing.

Check every time:
- Coordinate order. shapely is (x=lon, y=lat). Most marine data is (lat, lon). Most bugs live here.
- CRS. Distances in EPSG:4326 degrees are wrong. Project to EPSG:32643/32644 (UTM 43N/44N for
  the Indian coast) or use geodesic distance. Never trust a degree-based buffer.
- Antimeridian and pole handling can be ignored for the Indian EEZ. Say so rather than adding
  dead code.
- Boundary semantics. "Distance to IMBL" is distance to a line, not to a polygon centroid.
  Drift projection must use surface current plus heading, and must state its assumed time step.
- Any rendered boundary must be labelled indicative. We are not publishing legal lines.

Report file:line and the concrete failing case. Do not restate what the code does.
```

**`.claude/agents/capsule-auditor.md`**

```markdown
---
name: capsule-auditor
description: Verifies the 145-bit capsule codec — field widths, offsets, round-trip fidelity, and the bit budget. Use after any change to codec code, the field table, or the reason codebook.
tools: Read, Bash, Grep
model: sonnet
---

You audit the capsule codec against docs/CAPSULE_SPEC.md.

Verify on every change:
- Total width is exactly 145 bits and no field overlaps another. Recompute offsets from widths
  rather than trusting the constants.
- Every quantiser clamps. An out-of-range wave height must saturate, never wrap. Wrapping turns
  a 9 m sea into a calm one.
- Round-trip: encode(decode(x)) == x for the full corpus in eval/capsule_corpus.jsonl.
- Decoder is pure. No network, no filesystem, no clock. It must run offline forever.
- The reason codebook has exactly 256 entries and every entry renders in all 12 languages.

Fail loudly on drift between the spec table and the code.
```

### 0.4 CLAUDE.md

Write `CLAUDE.md` at the repo root containing: the stack table from the plan, the data source
table with its traps, the numeric-firewall rule, and the line "PFZ has no API — it is scraped and
attributed." Without this every session re-derives the architecture and occasionally re-litigates
it.

### 0.5 Accounts (start now, approval is not instant)

- Copernicus Marine — account, then `pip install copernicusmarine` and `copernicusmarine login`
- Bhashini — ULCA registration, note the two-step config-then-compute handshake
- Sarvam — API key from the dashboard
- NASA Earthdata — only if PACE enrichment is in scope
- Open-Meteo, INCOIS ERDDAP — no key needed

Nobody buys hardware. Transport for the offline demo is QR, Bluetooth and SMS. One person files a
request with the MAIT communications lab for an RTL-SDR or USRP, because free hardware is worth
asking for and paid hardware is not.

**Gate 0:** `/plugin list` shows the seven plugins, the three subagents load, and `CLAUDE.md`
exists. One ERDDAP query returns a real SST number for a real lat/lon.

---

## Phase 1 — Repo and skeleton (D1–D2)

```
dhruva/
├── CLAUDE.md
├── docker-compose.yml
├── .env.example
├── .claude/agents/            # the three subagents above
├── backend/
│   ├── pyproject.toml
│   ├── dhruva/
│   │   ├── api/               # FastAPI routers
│   │   ├── graph/             # LangGraph nodes, state, edges
│   │   ├── sources/           # erddap.py, copernicus.py, openmeteo.py, pfz_scraper.py
│   │   ├── analytics/         # fronts.py, anomaly.py, heatwave.py
│   │   ├── geo/               # boundaries.py, drift.py, routing.py
│   │   ├── risk/              # thresholds.py, rules.py
│   │   ├── evidence/          # schema.py, firewall.py
│   │   ├── codec/             # encode.py, decode.py, codebook.py
│   │   └── lang/              # bhashini.py, sarvam.py
│   └── tests/
├── frontend/                  # Vite + React + TS
│   └── src/{boat,shore,study,shared}/
├── data/
│   ├── registry.yaml          # dataset catalogue
│   ├── codebook/              # 256 reason templates × 12 languages
│   └── layers/                # EEZ, IMBL, MPA shapefiles
├── eval/
│   ├── queries.jsonl          # 60-query benchmark
│   └── capsule_corpus.jsonl
└── docs/
    ├── CAPSULE_SPEC.md
    └── THRESHOLDS.md
```

Python toolchain: `uv` if available, else pip + venv. Lint with `ruff`, format with `ruff format`,
test with `pytest`. Type-check with `pyright` in CI.

Services in `docker-compose.yml`: `api`, `postgres` (PostGIS + pgvector + TimescaleDB),
`redis`, `langfuse`, `caddy`.

**Gate 1:** `docker compose up` brings the stack online, `/health` returns 200, `pytest` runs
green on an empty suite.

---

## Phase 2 — Data plane (D3–D6)

1. **Source registry** (`data/registry.yaml`). Each entry: variable, source, dataset ID, spatial
   and temporal extent, resolution, units, latency, auth. The discovery node reads this; adding a
   dataset must never require code.
2. **Fetch layer** (`sources/`). One function per source returning an `xarray.Dataset` subset.
   All of them normalise to: lat ascending, lon in -180..180, time in UTC, SI units.
3. **Zarr cache.** Key on (dataset, bbox, time window, variables). The demo bounding box is
   pre-warmed. Cold queries must still work, just slower.
4. **PostGIS layers.** Load EEZ, IMBL and MPA polygons from Marine Regions. Index with GiST.
   Store an `indicative` flag on every boundary row and carry it to the UI.
5. **PFZ scraper.** Pull the INCOIS bulletin, parse lat/lon/depth/bearing, store with
   `source_url` and `fetched_at`. Cache aggressively; their site is not fast and we are guests.

**Gate 2:** one function `conditions_at(lat, lon, when)` returns wave, wind, current, SST and
chlorophyll from four sources with units and timestamps, in under 3 s warm.

---

## Phase 3 — Graph and risk engine (D7–D10)

### 3.1 Nodes

Implement as LangGraph nodes over a typed state object: `planner(0)`, `discovery(2)`,
`ocean(3)`, `weather(4)`, `geo(5)`, `risk(6)`, `route(7)`, `evidence(8)`, `codec(9)`.
Language (1) wraps the graph — everything inside runs in English.

Nodes 2–5 run in parallel. The planner emits a tool plan; it does not call tools itself.

### 3.2 Risk thresholds

`docs/THRESHOLDS.md` holds the table. Starting values, **clearly marked provisional**:

| Boat class | Caution H_s | No-go H_s | Caution wind | No-go wind |
|---|---|---|---|---|
| FRP / country craft < 12 m | 2.0 m | 3.0 m | 20 kt | 28 kt |
| Mechanised 12–20 m | 2.5 m | 3.5 m | 25 kt | 33 kt |
| Deep-sea > 20 m | 3.5 m | 4.5 m | 30 kt | 40 kt |

Absolute overrides regardless of class: active cyclone warning within 300 km, lightning within
50 km, or any tsunami alert → NO-GO.

> These numbers are engineering placeholders. Before any public claim, replace them with the
> published INCOIS Ocean State Forecast criteria and cite the source in the file. Never present
> invented safety thresholds as official.

### 3.3 Numeric firewall

The rule: the model may not introduce a number.

```
1. Tools produce an EvidenceBundle: list of {key, value, unit, dataset_id, cell, valid_time,
   threshold?, rule_id?}.
2. The LLM receives the bundle and writes narration.
3. The validator extracts every numeric token from the narration — ASCII and Indic digits,
   plus spelled-out numerals in the target language.
4. Each extracted value must match a bundle value, within rounding tolerance, or appear in the
   explicitly allowed derived set (unit conversions declared per field, e.g. m→ft, kt→km/h).
5. On failure: one retry with a stricter prompt. On second failure: render the pure template
   and log the incident. Never ship the unvalidated string.
```

Test it with adversarial cases in `tests/test_firewall.py`: an injected fabricated wave height,
a hallucinated distance, a converted unit that was not declared, a Tamil numeral.

**Gate 3:** CI fails when a fabricated number is injected into narration. Eight PS query types
route to the right node set.

---

## Phase 4 — Capsule codec (D11–D13)

Full field table lives in `docs/CAPSULE_SPEC.md`. Bit layout, MSB-first, total **145 bits**:

| Offset | Width | Field | Encoding |
|---:|---:|---|---|
| 0 | 4 | msg_type | 0=advisory, 1=alert, 2=all-clear, 3=test |
| 4 | 3 | schema_ver | integer |
| 7 | 10 | issue_slot | 15-min slots, 7-day wrap (0–671) |
| 17 | 4 | valid_hours | 0–15 |
| 21 | 20 | zone_id | `lat_idx * 560 + lon_idx`, bbox 6–24 °N / 66–94 °E, step 0.05° |
| 41 | 8 | lat_offset | position in cell, 0.05/256 ≈ 22 m |
| 49 | 8 | lon_offset | same |
| 57 | 2 | risk_class | 0=safe, 1=caution, 2=no-go, 3=unknown |
| 59 | 8 | hazard_flags | bitmap: wave, wind, squall, lightning, cyclone, current, fog, tsunami |
| 67 | 5 | wave_hs | `round(H_s / 0.25)`, 0–7.75 m, saturating |
| 72 | 6 | wind_kt | 0–63 kt, saturating |
| 78 | 4 | wind_dir | 16-point compass index |
| 82 | 5 | curr_kt | `round(kt / 0.1)`, 0–3.1 kt |
| 87 | 4 | curr_dir | 16-point |
| 91 | 5 | sst | `round((°C − 18) / 0.5)`, 18–33.5 °C |
| 96 | 2 | chl_class | 0=low, 1=moderate, 2=high, 3=very high |
| 98 | 4 | pfz_bearing | 16-point |
| 102 | 6 | pfz_dist_nm | 0–63 nm |
| 108 | 2 | pfz_conf | 0–3 |
| 110 | 5 | bnd_dist_nm | 0–31 nm |
| 115 | 2 | bnd_type | 0=none, 1=IMBL, 2=MPA, 3=closed |
| 117 | 8 | bnd_eta_min | 0–255 min, drift-projected |
| 125 | 8 | reason_code | codebook index |
| 133 | 12 | evidence_hash | truncated SHA-256 of the bundle, for audit |

145 used, **75 free** inside a 220-bit segment. Reserved use for the free bits: a 4-waypoint
return route at reduced precision when `risk_class == 2`.

Implementation notes:

- Use `bitstruct` or hand-rolled shifts. Write the field table once as data and generate both
  encoder and decoder from it, so they cannot drift apart.
- Every quantiser **clamps**. Wrapping a 9 m sea into a calm reading is the worst bug this
  project can ship.
- The decoder must be pure — no network, no filesystem, no clock — and must be ported to
  TypeScript for the PWA. Both implementations run the same corpus in CI.
- Reason codebook: 256 entries, each a template with slots filled from capsule fields, translated
  into 12 languages. The server chooses the index; the phone renders the sentence.
- Transports: QR (19 bytes, base32 for scanner reliability), Bluetooth, SMS. The wire format is
  identical across all three.

**Gate 4:** a phone in airplane mode scans a QR and speaks a full Tamil advisory. Round-trip
tests pass in both Python and TypeScript.

---

## Phase 5 — Interfaces (D14–D17)

Build in this order; the boat surface is the one that must be finished.

**Boat (PWA).** Verdict card → readout → PFZ row → boundary countdown → buttons. Constraints are
binding, not aspirational: 7:1 contrast, 56 px touch targets, colour never carrying the verdict
alone, data age visible on every screen, NO-GO rendering above any favourable fishing zone.
Offline via service worker + Dexie: codebook, last capsules, cached fields, map tiles for the
coastal window only.

**Shore console.** Fleet list with status, breach watch, MapLibre + deck.gl layers (SST,
chlorophyll, H_s, PFZ zones, boundaries), broadcast composer showing payload cost before send.

**Study routes.** Anomaly explorer, time series, marine heatwave view, Langfuse trace inspector.

**Voice.** Bhashini ASR → graph → Bhashini TTS, with Sarvam Saarika/Bulbul as the fallback and
the better demo voice. IVR through Asterisk for the feature-phone path.

**Gate 5:** spoken Tamil question returns a spoken Tamil answer with a map and a tappable
evidence card, end to end.

---

## Phase 6 — Evaluation (D18–D21)

`eval/queries.jsonl` — 60 queries covering all eight PS question types, each with expected
intent, expected tool set, and a ground-truth answer sourced from INCOIS or IMD bulletins for
that date. Record the source for every ground truth; unsourced expectations are worthless.

| Metric | Target | Method |
|---|---|---|
| Numeric provenance | 100% | Firewall pass rate over the whole eval set. Hard gate. |
| Intent routing | ≥ 92% | Predicted vs expected node set |
| p95 latency | ≤ 6 s online, ≤ 400 ms capsule decode | Langfuse traces |
| Boundary lead time | ≥ 20 min median | Replayed vessel tracks against known crossings |
| Language round-trip | chrF ≥ 55 | Back-translation on the query set |

Failure drills before the demo: Bhashini down, Copernicus timing out, no network at all, and a
deliberately poisoned scraped bulletin. Each must degrade visibly rather than silently.

---

## Conventions

- Commits: `area: imperative summary` (`codec: clamp wave quantiser at 7.75 m`).
- One PR per phase gate. `code-review` plugin runs before merge.
- Every number rendered anywhere carries its evidence. No exceptions, including in the console.
- Vessel positions quantise to the 0.05° grid at rest; tracks purge after 7 days; no third-party
  analytics anywhere in the frontend.
- Every advisory response carries: advisory only, follow official INCOIS and IMD warnings.

## Working with Claude Code on this repo

One phase per session. Start each with "read CLAUDE.md and IMPLEMENTATION.md, we are on Phase N."
Use `erddap-explorer` for anything touching datasets, `geo-reviewer` before merging geospatial
code, and `capsule-auditor` after every codec change. Let the gates decide when to move on — the
temptation near a deadline is to skip Phase 3's firewall tests, and that is the one thing that
makes the whole pitch collapse under a judge's question.
