# DHRUVA — Phase 5 Frontend

ISRO PS 26176 (ORCA). This is the interface layer from `IMPLEMENTATION.md` Phase 5: the
Boat surface, Shore Console, and Study routes, built against the Phase 3/4 API contract
so it can be merged with the real backend (`../backend`, currently through Phase 2) by
swapping one file.

**Stack:** React 19 + Vite + TypeScript, MapLibre GL, Dexie (IndexedDB), Vitest.

## Running it

```bash
npm install
npm run dev       # http://localhost:5173
npm test          # vitest — 29 tests, includes the capsule codec corpus and
                   # the "verdict renders before PFZ" safety-contract test
npm run build      # tsc -b && vite build — production PWA bundle
npm run lint
```

No backend, no API key, no `.env` needed to run it — it works fully standalone against
mock fixtures (`src/shared/api/mock.ts`) covering all 8 official PS query types.

## Merging with the real backend

Every component reads `AdvisoryResponse` / `Conditions` / `FleetVessel` etc. from
`src/shared/types/domain.ts`, never from the mock file directly. Those types mirror the
backend's own Pydantic models field-for-field (see the header comment in `domain.ts`)
and transcribe the Phase 3/4 shapes (`RiskVerdict`, `Capsule`, evidence bundle) straight
out of `IMPLEMENTATION.md`/`CLAUDE.md` for the modules that don't exist yet.

To wire in the real backend once it exposes `/query` and `/fleet`:

1. Copy `.env.example` to `.env.local`, set `VITE_API_BASE_URL`.
2. Delete `src/shared/api/mock.ts` and the mock branches in `src/shared/api/client.ts`.

That's the entire integration — no component changes.

## What's actually demoable right now

- **All 8 official query types** (`src/shared/api/mock.ts`), each with a narrative,
  evidence, and (where applicable) a verdict, PFZ row, boundary row, or route.
- **The 145-bit offline capsule**, end to end: ask "is it safe to venture out", get a
  verdict, the app encodes it into a 145-bit capsule and renders it as a QR (real
  `qrcode` library, real bits — `src/shared/capsule/`). Scan it with a phone camera
  (`jsqr`, live camera loop) or paste the base32 string, and it decodes **entirely
  client-side with zero network calls** into a spoken-style advisory sentence via the
  reason codebook. This is the actual "reasoning runs onshore, answers survive
  offshore" thesis, working in a browser.
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

1. Boat surface, tap "Is it safe to venture into the sea tomorrow morning?" — verdict
   card, evidence, capsule QR all appear.
2. Scroll to the capsule panel, paste the shown payload into the decode box — point out
   it just decoded a full advisory with zero network calls.
3. Switch language to Hindi or Tamil — whole UI and the capsule's own narrative
   re-render in-language.
4. Shore Console — toggle map layers, point at the breach-watch vessel near the
   indicative IMBL line.
5. Study — trace inspector, pick a different query, show the agent-by-agent trace.
