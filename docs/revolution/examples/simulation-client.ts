// Copy into the Presenter integration. No framework dependency or shared server key.
// The server-side presenter issues a one-use ticket; the browser only redeems it.
export type SimulationRun = {
  run_id: string;
  journey_id: string;
  sequence: number;
  status: string;
  virtual_now: string;
  state: { pending_event_id?: string };
};

export type RunProgress = {
  run_id: string;
  sequence: number;
  status: string;
  virtual_now: string;
  current_active_plan_version_id: string | null;
  readiness: { missing: string[]; model_credentials_configured: boolean; network_checked: false };
  guardian_runs: { id: string; event_id: string; status: string; action_status: string; proposal_id: string | null }[];
  agent_runs: { id: string; status: string }[];
  steps: { id: string; agent_run_id: string; sequence: number; tool_name: string; status: string; error_code: string | null }[];
  proposals: { id: string; status: string; proposed_plan_version_id: string; acceptance_audit_ids: string[] }[];
};

export class ApiFailure extends Error {
  constructor(public status: number) { super(`HTTP ${status}`); }
  get action(): "PAIR_AGAIN" | "CHECK_ROLE" | "RELOAD_STATE" | "SHOW_UNAVAILABLE" | "SHOW_ERROR" {
    return this.status === 401 ? "PAIR_AGAIN" : this.status === 403 ? "CHECK_ROLE"
      : this.status === 409 ? "RELOAD_STATE" : this.status === 503 ? "SHOW_UNAVAILABLE" : "SHOW_ERROR";
  }
}

export class SimulationClient {
  private constructor(private origin: string, public journeyId: string, private bearer: string) {}

  static async pair(origin: string, ticket: string): Promise<SimulationClient> {
    const response = await fetch(`${origin}/api/v1/demo/pairing/redeem`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticket }), cache: "no-store",
    });
    if (!response.ok) throw new ApiFailure(response.status);
    const result: { journey_id: string; access_token: string } = await response.json();
    return new SimulationClient(origin, result.journey_id, result.access_token);
  }

  private async request<T>(path: string, body?: object, key?: string): Promise<T> {
    const response = await fetch(`${this.origin}/api/v1${path}`, {
      method: body === undefined ? "GET" : "POST", cache: "no-store",
      headers: {
        Authorization: `Bearer ${this.bearer}`,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...(key ? { "Idempotency-Key": key } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) throw new ApiFailure(response.status);
    return await response.json() as T;
  }

  private get base(): string { return `/journeys/${this.journeyId}/simulation/runs`; }
  current(): Promise<SimulationRun | { run_id: null; status: "NOT_STARTED" }> {
    return this.request(this.base + "/current");
  }
  start(seed: number, key: string): Promise<SimulationRun> {
    return this.request(this.base, { seed }, key);
  }
  read(runId: string): Promise<SimulationRun> { return this.request(`${this.base}/${runId}`); }
  progress(runId: string): Promise<RunProgress> { return this.request(`${this.base}/${runId}/progress`); }
  advance(run: SimulationRun, key: string, minutes?: number): Promise<SimulationRun> {
    return this.request(`${this.base}/${run.run_id}/advance`, {
      expected_sequence: run.sequence, ...(minutes === undefined ? {} : { minutes }),
    }, key);
  }
  scene(run: SimulationRun, key: string, activityId: string, sceneId: string,
    eventType: "CLOSURE" | "WEATHER" | "SCHEDULE_DELAY"): Promise<SimulationRun> {
    return this.request(`${this.base}/${run.run_id}/scenes`, {
      expected_sequence: run.sequence, scene_id: sceneId, event_type: eventType, activity_id: activityId,
    }, key);
  }
  // Call only after the user chooses to run AI. Poll progress separately while this awaits.
  guardian(run: SimulationRun, key: string): Promise<SimulationRun> {
    return this.request(`${this.base}/${run.run_id}/guardian`, {
      expected_sequence: run.sequence, model_consent: true,
    }, key);
  }
  // Existing native accept endpoint retains feasibility and collective-authority checks.
  accept(proposalId: string, key: string): Promise<unknown> {
    return this.request(`/replans/${proposalId}/accept`, {}, key);
  }
  resume(run: SimulationRun, key: string): Promise<SimulationRun> {
    return this.request(`${this.base}/${run.run_id}/resume`, { expected_sequence: run.sequence }, key);
  }
}

// Usage (from separate user actions; do not auto-run this sequence on page load):
// const client = await SimulationClient.pair(location.origin, ticketFromPresenter);
// const run = await client.current(); // restore after refresh; never start a second run
// const commandKey = crypto.randomUUID(); // retain with this exact request until reconciled
// const pending = client.guardian(run as SimulationRun, commandKey);
// await client.progress((run as SimulationRun).run_id); // actual DB steps, not a timer animation
// await pending;
// If the connection drops, GET read/progress first. Replay only the identical body/key.
// 409: refresh sequence/state and ask whether to issue a new operation. Do not auto-loop.
// 503: keep the current run visible; retry only on another explicit user action.
// 401: redeem a new one-use ticket. Never store the shared presenter key in browser code.
// Acceptance and resume are distinct user actions with separate idempotency keys.
