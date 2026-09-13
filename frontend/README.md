# DHRUVA — Frontend

ISRO PS 26176 (ORCA). The interface layer from `IMPLEMENTATION.md` Phase 5 — a landing
page framing the problem/approach, the Boat surface, Shore Console, and Study routes —
now wired to a **real backend** (`../backend`, Phase 3/4 built alongside this) rather
than only the mock fixtures Phase 5 originally shipped against.

**Stack:** React 19 + Vite + TypeScript, MapLibre GL, Dexie (IndexedDB), Vitest.

## Running it

```bash
npm install
npm run dev       # http://localhost:5173
npm test          # vitest — 38 tests, including the codec corpus SHARED with
                   # the Python backend's test suite (eval/capsule_corpus.jsonl)
                   # and the "verdict renders before PFZ" safety-contract test
npm run build      # tsc -b && vite build — production PWA bundle
npm run lint
```

`.env.local` (gitignored) sets `VITE_API_BASE_URL=http://localhost:8000` so this talks
to the real backend (see `../backend/README.md` — `uvicorn dhruva.app:app --port 8000`,
no API keys or database needed). Delete that file, or unset the variable, to fall back
to the bundled mock fixtures (`src/shared/api/mock.ts`) — the whole app still works with
zero backend running, useful for pure UI iteration.

## The backend integration

Every component reads `AdvisoryResponse` / `Conditions` / `RiskVerdict` etc. from
`src/shared/types/domain.ts`, never from the mock file directly. `shared/api/client.ts`
is the seam: with `VITE_API_BASE_URL` set it calls the real `/query` endpoint and gets
back JSON shaped exactly like these types (camelCase, matching field-for-field — see
`domain.ts`'s header comment and `backend/dhruva/api/schemas.py`'s converters). The one
thing that stays mock regardless of backend availability is the Shore Console's fleet
list — there's no real vessel-tracking (AIS) data source anywhere in this system's
scope, and the UI says so.

## What's actually demoable right now

- **A landing page** (`src/landing/`) framing the ISRO brief, the multi-agent approach,
  and honest differentiation vs. SAMUDRA 2.0/Jal Anveshak — with all 8 official queries
  as direct deep links (`/boat?q=...`) that auto-submit on load.
- **All 8 official query types**, live against the real backend by default, each with a
  narrative, evidence, and (where applicable) a verdict, PFZ estimate, boundary
  distance, route, or capsule.
- **A visual multi-agent pipeline** (`AgentPipeline`) that animates each specialist
  agent lighting up in sequence — the actual point of "agentic" made visible, not just
  claimed in a paragraph of prose that would look identical from a single LLM call.
- **Real location and boat-class wiring**: a "Use my location" geolocation button and a
  boat-class selector (small/medium/large) actually get sent to the backend now — this
  was a real gap found while integrating (the UI existed to type a query, but neither
  the user's actual position nor their boat's safety thresholds ever reached the
  request). Boat class changes which wave/wind thresholds the verdict is computed
  against; persisted locally so it's a one-time setup, not asked every query.
- **A map embedded directly in the answer** (`shared/map/MiniMap`), not just in Shore
  Console — spatial queries (nearest PFZ, safest route, zones to avoid) show a real
  MapLibre view with the location, candidate zone, and route plotted.
- **Progressive disclosure for a real end user**: the verdict, map, numbers, PFZ,
  boundary and capsule are always visible in plain language; the agent pipeline and
  firewall-validation status sit behind a collapsed "How was this worked out?" toggle
  (`TechnicalDetails`) — a fisherman gets a clean answer, a judge can still inspect
  everything underneath it in one tap.
- **The 145-bit offline capsule**, end to end: ask "is it safe to venture out", get a
  verdict, the app encodes it into a 145-bit capsule and renders it as a QR (real
  `qrcode` library, real bits — `src/shared/capsule/`). Scan it with a phone camera
  (`jsqr`, live camera loop) or paste the base32 string, and it decodes **entirely
  client-side with zero network calls** into a spoken-style advisory sentence via the
  reason codebook. Verified with a capsule the **Python backend** actually generated
  from live data — not just this codebase's own fixtures.
- **The numeric firewall's UI contract**: `Observation`/`EvidenceBundleEntry` types make
  it structurally impossible for a component to render a number without a source,
  timestamp, and (for forecasts) an explicit forecast label. `EvidencePanel` shows
  firewall retry/fallback status per answer.
- **NO-GO-outranks-everything**, enforced and tested: `BoatApp.test.tsx` asserts the
  verdict card renders before the PFZ row in DOM order even for a favourable-zone query.
- **Full Hindi and Tamil UI localisation** (chrome strings + the offline reason
  codebook — see "Known scope reductions" below for exactly how much of each).
- **Shore Console**: live MapLibre map (vessel markers, SST/chlorophyll/wave synthetic
  layers, PFZ point, indicative IMBL line, all toggleable), breach watch, fleet list,
  and a broadcast composer that shows real payload cost (capsule bits vs SMS segments)
  before you'd send anything.
- **Study routes**: chlorophyll/SST anomaly explorer, a marine-heatwave diverging chart,
  and an agent-trace inspector per query type.
- Offline PWA shell (service worker + Dexie for capsules/conditions cache, 7-day vessel
  track purge implemented and tested).
- Accessibility: chip colours are unit-tested at ≥7:1 contrast (WCAG AAA) against this
  app's actual dark surface, not just eyeballed; every risk state pairs colour with a
  glyph and a text label; all interactive targets are ≥56px.

## Documented deviations from the locked plan (say so, don't hide it)

CLAUDE.md: *"if a decision here looks wrong, say so and stop, do not quietly change
it."* These are demo-time simplifications, not disagreements with the plan:

- **No deck.gl.** The Shore Console map uses MapLibre's own GL paint layers (circle/line)
  for SST, chlorophyll, wave height, PFZ, and boundaries instead of deck.gl. The visual
  result is the same layer set the plan calls for; deck.gl's actual value-add (GPU
  compositing for large animated fleets, arbitrary WebGL layers) isn't exercised by a
  four-vessel demo fleet. Swapping specific layers to deck.gl later is additive.
- **No Bhashini/Sarvam in the browser, ever — by design, not by omission.** Vite inlines
  `VITE_`-prefixed env vars into the shipped bundle, so the ULCA API key must never
  reach frontend code. `src/shared/voice/speech.ts` calls a backend proxy contract
  (`/voice/asr`, `/voice/tts`) that doesn't exist yet, and falls back to the browser's
  own Web Speech API today — real, working, zero-key, but limited to whatever
  languages/voices the OS and browser ship.
- **No live Langfuse.** `TraceInspector` reads the same `QueryTrace[]` shape a real
  Langfuse-backed inspector will read, off the mock advisories, so swapping in real
  traces is a data-source change, not a UI rewrite.
- **Reason codebook seeded, not complete.** 24 of the planned 256 entries, in English/
  Hindi/Tamil (3 of the planned 12 languages) — covers every combination the mock
  fixtures actually exercise. The schema (`src/shared/capsule/codebook.ts`) already
  supports the full 256×12; the remainder is content work, not architecture.
- **Demo/dev only: this frontend was built and run on Node 20**, one major version
  below the `>=22` some transitive deps (`@mapbox/jsonlint-lines-primitives`) declare
  in their `engines` field. It installs and runs fine (verified: full test suite,
  production build, and manual browser verification of every surface); flag it if CI
  or a teammate's machine pins Node engines strictly.

## Directory layout

```
src/
  shared/
    types/domain.ts       # the API contract — mirrors backend Pydantic models
    capsule/               # the 145-bit codec: fieldTable, bits, quantizers,
                           # codec, base32, qr, codebook — fully unit tested
    api/                   # client.ts (swap point) + mock.ts (fixtures)
    offline/db.ts          # Dexie: capsule cache, conditions cache, vessel tracks
    voice/speech.ts        # voice I/O contract + Web Speech API fallback
    i18n/strings.ts        # UI chrome strings (EN/HI/TA)
    theme/                 # design tokens, risk-chip visuals, contrast tests
    charts/                # dependency-free SVG line + diverging bar charts
  boat/                    # the boat surface — build/finish this one first
  shore/                   # shore console: fleet, breach watch, map, broadcast
  study/                   # anomaly explorer, heatwave view, trace inspector
```

## Demo script (suggested)

1. Land on `/` — problem, approach, differentiation vs. SAMUDRA 2.0/Jal Anveshak.
2. Tap any of the 8 official query cards — opens the Boat surface, auto-answers live.
3. Point out the verdict, the map, the real numbers — then open "How was this worked
   out?" to show the agent pipeline and firewall status underneath.
4. Scroll to the capsule panel, paste the shown payload into the decode box — a real
   answer, decoded with zero network calls.
5. Switch language to Hindi or Tamil — whole UI and the capsule's own narrative
   re-render in-language.
6. Shore Console — toggle map layers, point at the breach-watch vessel near the
   indicative IMBL line.
7. Study — trace inspector, pick a different query, show the agent-by-agent trace.
