/**
 * The one file that changes when Phase 3/4's real /query endpoint ships.
 *
 * Every component imports `queryAdvisory`/`fetchFleet` from here, never from
 * mock.ts directly and never a raw `fetch`. Today, with no
 * VITE_API_BASE_URL configured, both resolve from the mock fixtures. Once the
 * backend exists: set VITE_API_BASE_URL in `.env`, and the real branch below
 * takes over with zero component changes — the AdvisoryResponse/FleetVessel
 * shapes were written to match the backend's own Pydantic models exactly
 * (see shared/types/domain.ts header comment).
 */
import type { AdvisoryResponse, FleetVessel, QueryIntent } from "../types/domain";
import { MOCK_ADVISORIES, MOCK_FLEET, mockAnswerForText } from "./mock";

const API_BASE = import.meta.env.VITE_API_BASE_URL as string | undefined;
const MOCK_LATENCY_MS = 550; // makes the trace/loading UI honestly demoable

function delay<T>(value: T, ms = MOCK_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export interface QueryOptions {
  language?: string;
  location?: { lat: number; lon: number };
  boatClass?: string;
}

export async function queryAdvisory(text: string, opts: QueryOptions = {}): Promise<AdvisoryResponse> {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, ...opts }),
    });
    if (!res.ok) throw new Error(`query failed: ${res.status}`);
    return (await res.json()) as AdvisoryResponse;
  }
  return delay(mockAnswerForText(text));
}

export async function queryAdvisoryByIntent(intent: QueryIntent): Promise<AdvisoryResponse> {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/query?intent=${intent}`);
    if (!res.ok) throw new Error(`query failed: ${res.status}`);
    return (await res.json()) as AdvisoryResponse;
  }
  return delay(MOCK_ADVISORIES[intent]);
}

export async function fetchFleet(): Promise<FleetVessel[]> {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/fleet`);
    if (!res.ok) throw new Error(`fleet fetch failed: ${res.status}`);
    return (await res.json()) as FleetVessel[];
  }
  return delay(MOCK_FLEET, 300);
}

export function isUsingMockData(): boolean {
  return !API_BASE;
}
