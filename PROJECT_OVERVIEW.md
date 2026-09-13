# DHRUVA — What's built, why, how, and what's next

ISRO PS 26176 (ORCA), Smart India Hackathon 2026. This document is the single place
to understand the whole build without reading every commit — what exists, why it
exists, how it works, what's honestly missing, and what to do next.

---

## 1. The problem, in one paragraph

ISRO and global agencies produce huge volumes of satellite ocean data every day —
wave forecasts, sea surface temperature, chlorophyll, cyclone tracks. A fisherman
deciding whether to sail tomorrow morning can't query a NetCDF file. Existing tools
(INCOIS SAMUDRA 2.0, academic chatbots like Jal Anveshak) either push raw advisories
or answer one narrow question — none reason across sources, in the user's own
language, with evidence attached. The brief asks for an **agentic AI conversational
platform**: decompose the question, coordinate specialist agents across
heterogeneous data, reason spatially and temporally, and return an explainable,
evidence-backed answer.

## 2. What "DHRUVA" actually is

**D**eep-sea **H**azard, **R**outing & **U**nderstanding **v**ia **V**ernacular
**A**gents. The thesis, from day one: *"reasoning runs onshore, answers survive
offshore."* Two things follow from that thesis and shape almost every decision in
this codebase:

1. **A full advisory has to be small enough to survive a connection that barely
   exists** — hence the 145-bit offline capsule (§4).
2. **The system has to be honest about what it knows**, because a wrong "safe to
   sail" verdict has real safety consequences — hence the numeric firewall (§5) and
   the constant discipline of saying "we don't have this data" instead of guessing.

## 3. Architecture — how a question becomes an answer

```
User question
     │
     ▼
┌─────────────┐   classifies into one of the 8 official query types
│  Planner    │   (keyword-based today — see §7, "no LLM yet")
└─────┬───────┘
      │  resolves a location: explicit lat/lon > named place > default
      ▼
┌─────────────────────┐  real, live, parallel — Open-Meteo (no key needed)
│ Marine Data          │  wave height, wind, SST fetched per point;
│ Discovery            │  every value carries its dataset id + timestamp
└─────┬────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Specialist agents, dispatched by intent:                 │
│  • risk_assessment    → safe/caution/no-go verdict         │
│  • geospatial_reasoning → PFZ estimate, route, boundaries   │
│  • ocean_analytics     → SST trend, chlorophyll (partial)   │
└─────┬─────────────────────────────────────────────────────┘
      │  every number produced goes into an EvidenceBundle
      ▼
┌─────────────────────┐
│  Numeric firewall     │  the narrative text is checked: does every
│  (evidence/firewall)  │  number in it trace back to the evidence
└─────┬────────────────┘  bundle? If not, the answer is withheld and
      │                    replaced with a safe template — never shipped
      ▼                    unvalidated.
Answer to the user
(+ a 145-bit capsule if the answer includes a verdict)
```

**Why not LangGraph**, even though it's an installed dependency: LangGraph earns its
place when an LLM is making real routing decisions. With no LLM key configured yet,
every "agent" here is a deterministic Python function and routing is a dict lookup —
a LangGraph state machine over that would be more moving parts for no benefit today.
The node boundaries above are drawn exactly where a real LangGraph graph's nodes
would be, so wiring one in later is a mechanical wrap, not a redesign.

## 4. The 145-bit offline capsule — the actual differentiator

The whole "reasoning runs onshore, answers survive offshore" thesis, made real:

- A full advisory (risk verdict, wave/wind/current/SST, nearest PFZ, boundary
  distance, a reason code) compresses into **145 bits** — smaller than a single
  NavIC L5 message segment (220 bits).
- It's carried as a QR code, and the *same* 19-byte wire format would ride Bluetooth
  or SMS unchanged.
- **Written independently in Python (backend) and TypeScript (frontend)** — not one
  ported from the other. A shared test corpus is loaded by both languages' test
  suites and both must produce byte-identical results. This caught a real bug:
  Python's `round()` and JavaScript's `Math.round()` disagree on exactly `.5`
  boundaries (banker's rounding vs. round-half-up) — left alone, this would have
  silently corrupted capsules depending on which side encoded them.
- **Verified live, not just in tests**: a capsule the backend generated from real
  Open-Meteo data was pasted into the frontend's decode box and produced the correct
  advisory sentence with zero network calls.

## 5. The numeric firewall — the trust story

"The model may not introduce a number" (this is written as a rule specifically
because an LLM is the eventual narrator — see §7). Today, with no LLM wired in yet,
narration is built from string formatting, which can't hallucinate by construction —
but the firewall runs over it anyway, for two reasons: it's the exact mechanism that
will matter once an LLM is added, and it caught **real bugs** during development:

- Three query handlers (nearest PFZ, safe route, geofence avoidance) each stated a
  number in their narrative with no matching evidence entry. The firewall correctly
  rejected all three and replaced them with a withdrawal message. Fixed by attaching
  proper evidence to each stated number.
- The number-extraction regex discarded minus signs entirely — a cooling trend
  narrated as "-1.5°C" would extract the unsigned `1.5`, which could never match a
  `-1.5` evidence value, and the firewall would wrongly withhold a *correct* answer.
  Fixed with a sign-aware regex that still doesn't mistake an ordinary hyphenated
  word ("sea-state") for a minus sign.

It also reads Devanagari and Tamil numerals, not just ASCII digits, and permits
declared unit conversions (m→ft, kt→km/h) without requiring the exact source value
to appear verbatim.

## 6. What's real vs. what's honestly incomplete

| Capability | Status |
|---|---|
| Live wave/wind/SST | **Real** — Open-Meteo, no key, parallel fetch with full provenance |
| Risk verdict (safe/caution/no-go) | **Real** — tested at every boat-class threshold boundary |
| Numeric firewall | **Real**, caught real bugs (§5) |
| 145-bit capsule | **Real**, cross-language proven (§4) |
| Geofencing (boundary distance) | **Real** — actual India-Sri Lanka IMBL treaty line + 17 other real lines, Postgres-free |
| Safe route | **Real** — Dijkstra over a live wave-height grid, actively routes around hazard cells |
| SST trend (productivity query) | **Real** — 40+ real days of historical data, a genuine trend number |
| Nearest PFZ | **Partial, honestly labelled** — a live SST-gradient estimate, explicitly NOT claimed as an official INCOIS bulletin (INCOIS has no confirmed public API) |
| Chlorophyll-dependent answers | **Missing, disclosed** — needs Copernicus Marine credentials nobody has requested yet |
| Cyclone/lightning alerts | **Missing, disclosed** — no confirmed public IMD/RSMC feed exists yet |
| LLM narration | **Not yet** — templated strings today; firewall is ready for when one is added |
| Bhashini voice/translation | **Not yet** — browser's native Web Speech API today (works, but isn't the real government infrastructure); the UI chrome and offline capsule are separately translated to Hindi/Tamil already |
| Shore Console fleet tracking | **Permanently mock** — no AIS/vessel-tracking source is in scope for this project at all |

Every one of these says so in the UI or the API response. Nothing pretends to be
live when it isn't — that's a deliberate, repeated decision, not an oversight.

## 7. Future roadmap, in priority order

1. **Wire a real LLM** behind the numeric firewall — highest leverage single
   change, and the firewall/retry/template-fallback plumbing is already built and
   tested for exactly this.
2. **Real Bhashini integration** for ASR/TTS and narrative translation (today only
   the UI chrome and the offline capsule are translated; live narration is
   English-only from the backend).
3. **Copernicus Marine credentials** to unlock real chlorophyll — upgrades the PFZ
   estimate to the real front-detection method INCOIS itself uses, and turns the
   productivity-decline answer from "SST alone" into a real chlorophyll+SST
   correlation.
4. **A confirmed IMD/RSMC cyclone/lightning feed** to implement the absolute
   safety overrides the risk engine already has a marked slot for.
5. Bring up the real PostGIS boundary path once Docker is available to test it
   (a Postgres-free equivalent is what's running today).
6. Scale the route planner's grid; let a user pick among several candidate zones
   or specify their own destination port.

## 8. How to run it

```bash
./start.sh     # starts both servers, opens the app in your browser
./stop.sh      # stops both
```

First run installs dependencies automatically (~1 min); after that it's instant.
See `backend/README.md` and `frontend/README.md` for what each script does under
the hood, and for running the test suites (`pytest -q` / `npm test`).

## 9. Test coverage

```
Backend:  151 tests   (pytest -q, ~20s, some hit live Open-Meteo)
Frontend:  38 tests   (npm test, ~1.5s, includes the Python↔TypeScript
                        shared capsule corpus check)
```

Every real bug mentioned in §4 and §5 above was caught by either these tests or by
manually testing the running app end-to-end — not by code review alone.
