/**
 * Client for the SimulationRun contract that Codex owns (Issue #47):
 * `docs/revolution/SIMULATION_RUN_API_20261025.md` on the codex branch.
 *
 * Nothing here is called until its endpoint exists. A 404/405 from the current
 * backend means "not deployed", and callers must render nothing rather than an
 * error, so the classroom screen is unchanged until the backend lands.
 */
import { travelerAuthHeaders } from "../../lib/travelerSession";

export type SimulationCity = {
  city_code: string;
  status: string;
  missing: string[];
  poi: Array<{ place_id: string; name: string; provider: string }>;
  routes: Array<{ origin_place_id: string; destination_place_id: string; minutes: number }>;
};

export type SimulationCities = {
  available: true;
  seed: number;
  status: string;
  required: number;
  eligible_count: number;
  cities: SimulationCity[];
};

export type SimulationRun = {
  run_id: string;
  journey_id: string;
  city_code: string;
  seed: number;
  timezone: string;
  virtual_now: string;
  sequence: number;
  status: string;
  state: Record<string, unknown>;
  history: Array<Record<string, unknown>>;
  execution_truth: Record<string, unknown>;
  updated_at: string;
};

export type SimulationCurrent =
  | { available: true; run: SimulationRun | null; status: string }
  | { available: false };

const unavailable = { available: false as const };

export class SimulationError extends Error {
  constructor(public code: string, public detail: string, public status: number) {
    super(`${detail || code || "SIMULATION_ERROR"} http_status=${status}`);
  }
}

function base(journeyId: string): string {
  return `/api/v1/journeys/${journeyId}/simulation`;
}

async function call<T>(path: string, init?: RequestInit): Promise<T | null> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: "application/json", ...travelerAuthHeaders(), ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (response.status === 404 || response.status === 405) return null;
  if (!response.ok) {
    let code = "";
    let detail = "";
    try {
      const body = (await response.json()) as { error?: { code?: string; message?: string } };
      code = body.error?.code ?? "";
      detail = body.error?.message ?? "";
    } catch {
      code = "";
    }
    throw new SimulationError(code, detail, response.status);
  }
  return (await response.json()) as T;
}

function key(): string {
  return `presenter-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function writeInit(body: Record<string, unknown>): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": key() },
    body: JSON.stringify(body),
  };
}

export const simulationApi = {
  async cities(journeyId: string, seed: number): Promise<SimulationCities | typeof unavailable> {
    const body = await call<{
      seed: number;
      status: string;
      required_city_count: number;
      eligible_city_count: number;
      cities: SimulationCity[];
    }>(`${base(journeyId)}/cities?seed=${encodeURIComponent(String(seed))}`);
    if (body === null) return unavailable;
    return {
      available: true,
      seed: body.seed,
      status: body.status,
      required: body.required_city_count,
      eligible_count: body.eligible_city_count,
      cities: body.cities ?? [],
    };
  },

  async current(journeyId: string): Promise<SimulationCurrent> {
    const body = await call<SimulationRun | { run_id: null; journey_id: string; status: string }>(
      `${base(journeyId)}/runs/current`,
    );
    if (body === null) return unavailable;
    if ((body as { run_id: string | null }).run_id === null) {
      return { available: true, run: null, status: (body as { status: string }).status };
    }
    return { available: true, run: body as SimulationRun, status: (body as SimulationRun).status };
  },

  async start(journeyId: string, seed: number): Promise<SimulationRun | null> {
    return call<SimulationRun>(`${base(journeyId)}/runs`, writeInit({ seed }));
  },

  async advance(journeyId: string, runId: string, sequence: number, minutes?: number): Promise<SimulationRun | null> {
    const body: Record<string, unknown> = { expected_sequence: sequence };
    if (minutes !== undefined) body.minutes = minutes;
    return call<SimulationRun>(`${base(journeyId)}/runs/${runId}/advance`, writeInit(body));
  },

  async scene(
    journeyId: string,
    runId: string,
    sequence: number,
    scene: { scene_id: string; event_type: string; activity_id?: string; delay_minutes?: number },
  ): Promise<SimulationRun | null> {
    return call<SimulationRun>(`${base(journeyId)}/runs/${runId}/scenes`, writeInit({ expected_sequence: sequence, ...scene }));
  },

  async guardian(journeyId: string, runId: string, sequence: number): Promise<SimulationRun | null> {
    return call<SimulationRun>(
      `${base(journeyId)}/runs/${runId}/guardian`,
      writeInit({ expected_sequence: sequence, model_consent: true }),
    );
  },

  async resume(journeyId: string, runId: string, sequence: number): Promise<SimulationRun | null> {
    return call<SimulationRun>(`${base(journeyId)}/runs/${runId}/resume`, writeInit({ expected_sequence: sequence }));
  },
};
