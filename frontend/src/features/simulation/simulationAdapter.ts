import { CityNexusApiError } from "../../api/citynexus";

/**
 * ORD-0059 (b), adapter half -- the calls the Simulation entry makes, and the words it answers
 * with when one is refused.
 *
 * Two rules shape this file.  First: every action maps onto an endpoint the product already has
 * (`cityNexusApi` wraps most of them); nothing here grows a parallel state machine or edits an
 * array client-side, because a lifecycle the server did not agree to is a fake lifecycle.  The
 * one call that is not already wrapped is written here rather than by widening a shared module,
 * and it is written *without* `occurred_at`: the server has a deterministic default for it, and a
 * client-side `new Date()` in a Simulation entry is precisely the second clock ORD-0059 forbids.
 *
 * Second: a refusal is named, not smoothed over.  The status is checked before the body is
 * trusted (fetch does not reject on 5xx), the server's own code is kept, and the Chinese screen
 * gets Chinese words -- an English `detail` string pasted into a Chinese notice is the defect
 * ORD-0055 was written about.  Where there is no local wording for a code, the line says so and
 * shows the code instead of inventing an explanation.
 */

export type SimulatedEventType = "WEATHER" | "TRAFFIC_DELAY" | "CLOSURE" | "SCHEDULE_DELAY";

export type NamedFailure = {
  code: string;
  status: number;
  /** Traveller-facing copy, in the language the screen is using. */
  zh: string;
  en: string;
};

type ErrorBody = {
  detail?: unknown;
  error?: { code?: unknown; message?: unknown; message_key?: unknown; details?: unknown };
};

function bodyOf(error: unknown): ErrorBody | null {
  if (error instanceof CityNexusApiError) {
    const raw = (error as { body?: unknown }).body;
    if (raw && typeof raw === "object") return raw as ErrorBody;
  }
  return null;
}

/** The server's own name for the refusal: a code, a message key, or the HTTP status. */
export function failureCode(error: unknown): { code: string; status: number } {
  if (error instanceof CityNexusApiError) {
    const body = bodyOf(error);
    const nested = body?.error;
    const candidate =
      (typeof nested?.message_key === "string" && nested.message_key) ||
      (typeof nested?.code === "string" && nested.code) ||
      (typeof body?.detail === "string" && body.detail) ||
      "";
    return { code: candidate.trim() || `HTTP ${error.status}`, status: error.status };
  }
  if (error instanceof TypeError) return { code: "NETWORK", status: 0 };
  return { code: "UNKNOWN", status: 0 };
}

const TABLE: Record<
  string,
  { zh: (status: number, extra: string) => string; en: (status: number, extra: string) => string }
> = {
  DEMO_MODE_REQUIRED: {
    zh: () => "这台部署没有开模拟舞台（服务器要求 CITYNEXUS_DEMO_MODE=true）。它明确拒绝，并且说没有任何数据被删除。",
    en: () =>
      "This deployment is not a simulation stage (the server requires CITYNEXUS_DEMO_MODE=true). It refused and says nothing was deleted.",
  },
  /* ORD-0070's named 503, so the stage says "wait" instead of "nothing happened". */
  "generation.store_busy": {
    zh: (_s, extra) => `上一次的生成还占着存储${extra}。等它跑完再试，这一步没有失败，只是被挡住了。`,
    en: (_s, extra) =>
      `The previous generation still holds the store${extra}. Wait for it and try again -- this step was blocked, not refused.`,
  },
  GENERATION_STORE_BUSY: {
    zh: (_s, extra) => `上一次的生成还占着存储${extra}。等它跑完再试，这一步没有失败，只是被挡住了。`,
    en: (_s, extra) =>
      `The previous generation still holds the store${extra}. Wait for it and try again -- this step was blocked, not refused.`,
  },
  VALIDATION_ERROR: {
    zh: (_s, extra) => `服务器认为有字段不合法${extra}，所以这一步没有执行。`,
    en: (_s, extra) => `The server rejected one or more fields${extra}, so this step did not run.`,
  },
  NETWORK: {
    zh: () => "请求没有到达服务器（网络或进程断了）。场景状态没有变化，我们也无从得知它变了没有。",
    en: () =>
      "The request never reached the server (network or process down). Nothing about the scene is known from here.",
  },
};

function fieldsOf(error: unknown): string {
  const body = bodyOf(error);
  const errors = (body?.error?.details as { errors?: unknown } | undefined)?.errors;
  if (!Array.isArray(errors)) return "";
  const names = errors
    .map((item) => {
      const record = item as { loc?: unknown; msg?: unknown };
      const loc = Array.isArray(record.loc)
        ? record.loc.filter((part) => typeof part === "string" || typeof part === "number").join(".")
        : "";
      return loc ? String(loc) : "";
    })
    .filter(Boolean);
  return names.length ? `：${[...new Set(names)].join("、")}` : "";
}

function retryHint(error: unknown): string {
  const details = (bodyOf(error)?.error?.details ?? {}) as { retry_after_ms?: unknown };
  const ms = typeof details.retry_after_ms === "number" ? details.retry_after_ms : null;
  if (ms === null) return "（服务器没说要等多久）";
  return ms <= 0 ? "（现在就可以再试）" : `（约 ${Math.round(ms)} 毫秒后再试）`;
}

export function describeFailure(error: unknown): NamedFailure {
  const { code, status } = failureCode(error);
  const fields = code === "VALIDATION_ERROR" ? fieldsOf(error) : "";
  const busy = code === "generation.store_busy" || code === "GENERATION_STORE_BUSY";
  const hit = TABLE[code];
  if (hit) {
    const extra = busy ? retryHint(error) : fields;
    return { code, status, zh: hit.zh(status, extra), en: hit.en(status, extra) };
  }
  if (code.startsWith("INVALID_ACTIVITY_TRANSITION")) {
    /* The server's own name carries the from->to it refused, so the sentence can quote the fact
       instead of guessing which step the stage is really on. */
    return {
      code,
      status,
      zh: `服务器说这一步的顺序不对（${code.replace("INVALID_ACTIVITY_TRANSITION:", "")}），活动状态没有被改动。上面那行会跟着服务器的状态换成它允许的那一步。`,
      en: `The server refused this step's order (${code.replace("INVALID_ACTIVITY_TRANSITION:", "")}); the activity is unchanged. The row above follows the server's state to the step it allows.`,
    };
  }
  /* No local wording for this one.  Say that, name it, and keep the number -- translating the
     server's English sentence into a Chinese guess would be this lane inventing a reason. */
  return {
    code,
    status,
    zh: `服务器拒绝了这个动作（HTTP ${status}，具名码 ${code}）。我们没有这条拒绝的本地文案，所以不替它编造原因。`,
    en: `The server refused this action (HTTP ${status}, code ${code}). There is no local wording for it, so no reason is invented here.`,
  };
}

/**
 * "重置到场景起点".  ORD-0074 made reset run the real pipeline (`plans/generate` -> `select` ->
 * `/start`) and report what happened in `simulation_advance` -- as a JSON string, and as a
 * **recorded refusal on a 200** when a step is denied.  So `status: 200` is not the success
 * signal here; the advance report is.  Reading only the 200 would let this screen claim a
 * lifecycle the server explicitly did not grant, which is the failure ORD-0059 forbids.
 */
export type AdvanceStep = {
  step?: string;
  ms?: number;
  ok?: boolean;
  refused?: string | number;
  detail?: string;
};

export type DemoReset = {
  status: string;
  traveler_id?: string;
  journey_id?: string;
  city_code?: string;
  advance: {
    steps: AdvanceStep[];
    totalMs: number | null;
    journeyStatus: string | null;
    selectedPlanVersionId: string | null;
  } | null;
};

export async function resetStage(): Promise<DemoReset> {
  const response = await fetch("/api/v1/demo/reset", {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  const text = await response.text();
  let body: Record<string, unknown> = {};
  if (text) {
    try {
      body = JSON.parse(text) as Record<string, unknown>;
    } catch {
      body = {};
    }
  }
  if (!response.ok) throw new CityNexusApiError(response.status, body, `demo/reset ${response.status}`);
  const rawAdvance = body.simulation_advance;
  let advance: DemoReset["advance"] = null;
  if (typeof rawAdvance === "string" && rawAdvance) {
    try {
      const parsed = JSON.parse(rawAdvance) as Record<string, unknown>;
      advance = {
        steps: Array.isArray(parsed.steps) ? (parsed.steps as AdvanceStep[]) : [],
        totalMs: typeof parsed.total_ms === "number" ? parsed.total_ms : null,
        journeyStatus: typeof parsed.journey_status === "string" ? parsed.journey_status : null,
        selectedPlanVersionId:
          typeof parsed.selected_plan_version_id === "string" ? parsed.selected_plan_version_id : null,
      };
    } catch {
      /* An unreadable report is reported as unreadable below, never read as a success. */
      advance = { steps: [], totalMs: null, journeyStatus: null, selectedPlanVersionId: null };
    }
  }
  return {
    status: typeof body.status === "string" ? body.status : "unknown",
    traveler_id: typeof body.traveler_id === "string" ? body.traveler_id : undefined,
    journey_id: typeof body.journey_id === "string" ? body.journey_id : undefined,
    city_code: typeof body.city_code === "string" ? body.city_code : undefined,
    advance,
  };
}
/**
 * "推进一个活动".  The server owns the activity state graph -- `NOT_STARTED|ACTIVE -> EN_ROUTE ->
 * ARRIVED -> IN_PROGRESS -> COMPLETED` -- and answers a named 409 (`INVALID_ACTIVITY_TRANSITION:
 * <from>-><to>; expected=<from…>`) for a step that is out of order, which is exactly what a panel
 * that hard-codes "complete" gets on a frozen V12/V13 plan.  So the row offers the one transition
 * the server currently allows, and the label changes because the server's state changed.
 */
export type StageStep = "depart" | "arrive" | "begin" | "complete";

export const NEXT_STEP: Record<string, { step: StageStep; zh: string; en: string } | undefined> = {
  NOT_STARTED: { step: "depart", zh: "出发", en: "depart" },
  ACTIVE: { step: "depart", zh: "出发", en: "depart" },
  EN_ROUTE: { step: "arrive", zh: "到达", en: "arrive" },
  ARRIVED: { step: "begin", zh: "开始这项活动", en: "begin" },
  IN_PROGRESS: { step: "complete", zh: "完成这项活动", en: "complete" },
};

export type TransitionTwin = {
  current_activity_id: string | null;
  projection_status: string;
  active_plan_version_id?: string | null;
};

export async function transitionStage(
  journeyId: string,
  activityId: string,
  step: StageStep,
): Promise<TransitionTwin> {
  const response = await fetch(`/api/v1/journeys/${journeyId}/activities/${activityId}/${step}`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  /* The envelope survives as a CityNexusApiError on purpose: the plain Error the shared helper
     builds drops the status, and a refusal whose name is dropped is the ORD-0070 defect again. */
  if (!response.ok) {
    throw new CityNexusApiError(response.status, body, `activities/${activityId}/${step} ${response.status}`);
  }
  return body as TransitionTwin;
}

/**
 * "触发一次中断".  `provenance` is omitted: the handler assigns SIMULATED for stage input and
 * rejects a client that claims trusted provenance, so claiming it here would be the fake-trust
 * shape the backend already refuses.  `occurred_at` is omitted for the same reason -- the server
 * derives it from the cursor, and a client clock must not enter this path.
 */
export async function postSimulatedEvent(
  journeyId: string,
  event: { eventType: SimulatedEventType; severity: "MINOR" | "MAJOR" | "CRITICAL"; activityId: string | null },
): Promise<{ id: string; occurred_at: string; status: string }> {
  const response = await fetch(`/api/v1/journeys/${journeyId}/events`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({
      event_type: event.eventType,
      severity: event.severity,
      affected_activity_id: event.activityId,
      payload: { source: "simulation-panel" },
    }),
  });
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }
  if (!response.ok) throw new CityNexusApiError(response.status, body, `events ${response.status}`);
  return body as { id: string; occurred_at: string; status: string };
}
