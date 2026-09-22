/**
 * R14 / ORD-0169 -- one classification, four consumers.
 *
 * The defect this exists to prevent was measured on the production bundle at 390x844:
 * `localStorage["citynexus.v8.journey_id"]` held `ca0f1ed1-…`, a journey the server does not have,
 * so `GET /journeys/ca0f1ed1-…/experience` answered **404** -- and the screen said
 * 「网络不可用 · 正在显示只读的已保存行程」.  The banner, the read-only fallback and the missing map
 * were all downstream of one misread: an HTTP response was treated as a transport failure.
 *
 * R14's rule is that the classification happens **once**, at the boundary where the discriminating
 * evidence is available, and is then propagated.  So this module owns the only mapping from evidence
 * to reason, and the screen copy, the `aria-live` announcement, the telemetry record and the
 * recovery action all read the same object.  Nothing downstream may invent a cause.
 *
 * Evidence precedence (R14 §3), strongest first:
 *   1. the server's own structured code on a response  (HTTP status + body);
 *   2. the HTTP status of that request;
 *   3. a transport exception/timeout for that request;
 *   4. browser heuristics -- and only when nothing above exists.
 * `navigator.onLine` is deliberately **not** consulted here: it is true on a captive portal and true
 * while a backend is dead, so it cannot distinguish anything this module is asked to distinguish.
 */

export type AttributionReason =
  | "JOURNEY_NOT_FOUND"
  | "NETWORK_UNAVAILABLE"
  | "SERVER_ERROR"
  | "UNAUTHORIZED"
  /* ORD-0126 补项: 403 is not 401.  A 403 means the server knows who is asking and still refuses
     *this step* -- telling that traveller to sign in again promises a fix that cannot arrive, which
     is the same "rewrite a named HTTP answer into a different cause" defect this module exists to
     stop. */
  | "FORBIDDEN"
  | "UNKNOWN_FAILURE";

export type EvidenceKind = "HTTP_RESPONSE" | "TRANSPORT" | "HEALTH_PROBE";

export type SourceLayer = "RESOURCE_STATE" | "TRANSPORT" | "RUNTIME";

/** What the traveller can actually do about it.  One action per cause -- R14 §5. */
export type RecoveryAction =
  | "choose-journey"
  | "retry"
  | "read-only-cached"
  | "sign-in";

export type Attribution = {
  reason: AttributionReason;
  /** Which evidence produced `reason`.  Telemetry must record this, not just the conclusion. */
  evidence_kind: EvidenceKind;
  http_status: number | null;
  source_layer: SourceLayer;
  retryable: boolean;
  recovery_action: RecoveryAction;
  /** Stable key for the copy table, so a message is looked up rather than written at a catch site. */
  message_key: string;
  /** The server's own code, when it gave one.  A refusal must be quotable, not paraphrased. */
  server_code?: string | null;
  /** Short, greppable line for production logs.  Shape follows R14 §8. */
  telemetry: string;
};

/** The server's structured error body, as `v8Request` reads it. */
export type ServerErrorShape = {
  status?: number;
  code?: string | null;
  message?: string | null;
};

const NOT_FOUND_CODES = ["NOT_FOUND", "RESOURCE_NOT_FOUND", "JOURNEY_NOT_FOUND"];

function make(
  reason: AttributionReason,
  evidence_kind: EvidenceKind,
  http_status: number | null,
  source_layer: SourceLayer,
  retryable: boolean,
  recovery_action: RecoveryAction,
  message_key: string,
  server_code?: string | null,
): Attribution {
  return {
    reason,
    evidence_kind,
    http_status,
    source_layer,
    retryable,
    recovery_action,
    message_key,
    ...(server_code ? { server_code } : {}),
    telemetry: [
      `attribution_reason=${reason}`,
      `evidence_kind=${evidence_kind}`,
      `http_status=${http_status ?? "none"}`,
      `source_layer=${source_layer}`,
      `retryable=${retryable ? "true" : "false"}`,
      `recovery_action=${recovery_action}`,
      ...(server_code ? [`server_code=${server_code}`] : []),
    ].join(" "),
  };
}

/**
 * Classify a failed journey read.  The order of the branches *is* the evidence precedence: a
 * response that arrived outranks any transport guess, because a response is proof the request
 * reached the server.
 */
export function classifyReadFailure(error: unknown, server?: ServerErrorShape | null): Attribution {
  const status = server?.status ?? (error instanceof Error && "status" in error ? Number((error as { status?: number }).status) : null);
  const code = (server?.code ?? (error instanceof Error && "code" in error ? (error as { code?: string | null }).code : null)) ?? null;

  /* 1 + 2: the server answered, so this is a resource/state fact, never a transport one. */
  if (typeof status === "number" && status > 0) {
    if (status === 404 || status === 410 || (code !== null && NOT_FOUND_CODES.includes(code))) {
      return make(
        "JOURNEY_NOT_FOUND",
        "HTTP_RESPONSE",
        status,
        "RESOURCE_STATE",
        false,
        "choose-journey",
        "failure.journeyNotFound",
      );
    }
    if (status === 401) {
      return make("UNAUTHORIZED", "HTTP_RESPONSE", status, "RESOURCE_STATE", false, "sign-in", "failure.unauthorized", code);
    }
    if (status === 403) {
      return make("FORBIDDEN", "HTTP_RESPONSE", status, "RESOURCE_STATE", false, "choose-journey", "failure.forbidden", code);
    }
    if (status >= 500) {
      return make("SERVER_ERROR", "HTTP_RESPONSE", status, "RUNTIME", true, "retry", "failure.serverError");
    }
    return make("UNKNOWN_FAILURE", "HTTP_RESPONSE", status, "RESOURCE_STATE", false, "retry", "failure.unknown");
  }

  /* 3: no response at all -- the request itself failed to travel.  This is the *only* branch that
     may say the network is unavailable, which is what keeps the reverse direction honest. */
  if (error instanceof TypeError) {
    return make("NETWORK_UNAVAILABLE", "TRANSPORT", null, "TRANSPORT", true, "read-only-cached", "failure.networkUnavailable");
  }

  /* 4: nothing discriminating.  Say so instead of borrowing a cause. */
  return make("UNKNOWN_FAILURE", "TRANSPORT", null, "TRANSPORT", true, "retry", "failure.unknown");
}

/**
 * The health probe's verdict folded into the same vocabulary, for the case where the journey read
 * failed and the question is whether the origin answers at all.  A 2xx probe means the network is
 * fine and the failure was something else -- the reading that proves a 网络不可用 banner is over-broad.
 */
export function classifyHealthProbe(healthy: boolean): Attribution {
  return healthy
    ? make("UNKNOWN_FAILURE", "HEALTH_PROBE", null, "TRANSPORT", true, "retry", "failure.unknown")
    : make("NETWORK_UNAVAILABLE", "HEALTH_PROBE", null, "TRANSPORT", true, "read-only-cached", "failure.networkUnavailable");
}

/**
 * Telemetry sink.  R14 §8: the record must say what the classifier decided and on what evidence, so
 * a false cause is discoverable in production rather than only in a screenshot.  There is no
 * analytics backend in this build, so the record is kept where a test (and a future reporter) can
 * read it -- emitting `network_unavailable` for an HTTP 404 is exactly the line this prevents.
 */
export type AttributionRecord = Attribution & { at: string; context: string };

const TELEMETRY_LIMIT = 50;
const telemetry: AttributionRecord[] = [];

declare global {
  interface Window {
    citynexusAttribution?: AttributionRecord[];
  }
}

export function recordAttribution(attribution: Attribution, context: string): AttributionRecord {
  const record: AttributionRecord = { ...attribution, at: new Date().toISOString(), context };
  telemetry.push(record);
  if (telemetry.length > TELEMETRY_LIMIT) telemetry.shift();
  if (typeof window !== "undefined") {
    window.citynexusAttribution = [...telemetry];
    window.dispatchEvent(new CustomEvent("citynexus:attribution", { detail: record }));
  }
  return record;
}

export function readAttribution(): AttributionRecord[] {
  return [...telemetry];
}

/**
 * The stored references that point at "the journey this device is on".  R14-S requires the invalid
 * one to be cleared or quarantined once a stale-journey classification has been made, and this is
 * the one place that knows which keys those are -- a `removeItem` per catch site is how one of them
 * gets forgotten and the refresh walks into the same 404 again.
 */
export const JOURNEY_REFERENCE_KEYS = [
  "citynexus.v8.journey_id",
  "citynexus.demo.journey_id",
  "citynexus.demo.agent_run_id",
] as const;

/** Returns the keys it actually removed, so a gate can assert on the clearing rather than assume it. */
export function clearJourneyReferences(): string[] {
  const cleared: string[] = [];
  for (const key of JOURNEY_REFERENCE_KEYS) {
    try {
      if (localStorage.getItem(key) !== null) {
        localStorage.removeItem(key);
        cleared.push(key);
      }
    } catch {
      /* Blocked storage: the reference is not persisted anyway, so there is nothing to clear. */
    }
  }
  return cleared;
}

/**
 * The four consumers, derived from the one classification.  Keeping them in this file is the point:
 * screen copy, announcement, recovery action and telemetry cannot drift apart if they are functions
 * of the same object.
 */
export function copyFor(
  attribution: Attribution,
  zh: boolean,
  detail: { journeyId?: string; hasCachedCopy?: boolean } = {},
): {
  kicker: string;
  title: string;
  body: string;
} {
  const id = detail.journeyId ? `${detail.journeyId.slice(0, 8)}…` : "";
  switch (attribution.message_key) {
    case "failure.journeyNotFound":
      return {
        kicker: zh ? "连接正常" : "Connection is fine",
        title: zh ? "这台服务器上没有这一趟行程了" : "This trip is not on this server",
        body: zh
          ? `这台设备还记得行程 ${id}，但服务器明确回答它不存在（HTTP ${attribution.http_status}）。这不是网络问题：服务器刚才答得出来。你的其它行程没有受影响。`
          : `This device remembered trip ${id}, and the server answered plainly that it does not exist (HTTP ${attribution.http_status}). This is not a network problem: the server just answered. Your other trips are untouched.`,
      };
    case "failure.networkUnavailable":
      return {
        kicker: zh ? "连接" : "Connection",
        title: zh ? "网络不可用" : "Network unavailable",
        body: detail.hasCachedCopy
          ? zh
            ? "这一发请求没能出去，也没有收到任何回答，所以这是网络问题。你的行程数据没有丢失，已保存的只读副本还能看。请检查网络后重试。"
            : "This request could not travel and nothing came back, so this is a network problem. Your trip data has not been lost and the saved read-only copy is still available. Check your connection and try again."
          : zh
            ? "这一发请求没能出去，也没有收到任何回答，所以这是网络问题。这台设备上还没有可看的离线副本，所以现在没有可显示的内容。请检查网络后重试。"
            : "This request could not travel and nothing came back, so this is a network problem. This device holds no offline copy to show you, so there is nothing to display right now. Check your connection and try again.",
      };
    case "failure.serverError":
      return {
        kicker: zh ? "服务器" : "Server",
        title: zh ? "服务器这次没能把行程读出来" : "The server could not read your trip",
        body: zh
          ? `服务器自己报错了（HTTP ${attribution.http_status}）。这是它那边的问题，不是你填错了什么。可以重试；如果一直这样，稍后再来。`
          : `The server reported an error of its own (HTTP ${attribution.http_status}). That is on its side, not something you typed. Retry; if it persists, come back later.`,
      };
    case "failure.unauthorized":
      return {
        kicker: zh ? "身份" : "Identity",
        title: zh ? "这一趟需要重新登录才能读" : "This trip needs a fresh sign-in",
        body: zh
          ? `服务器拒绝了这次读取（HTTP ${attribution.http_status}）。登录之后这一趟还在。`
          : `The server refused this read (HTTP ${attribution.http_status}). Your trip is still there once you sign in.`,
      };
    case "failure.forbidden":
      return {
        kicker: zh ? "权限" : "Permission",
        title: zh ? "这一步这台服务器不允许" : "This server will not allow this step",
        body: zh
          ? `服务器认得你是谁，但明确拒绝了这一步（HTTP ${attribution.http_status}${attribution.server_code ? `：${attribution.server_code}` : ""}）。这不是网络问题，也不是登录问题——重新登录不会改变它的回答。你可以换一趟行程，或回到选择页。`
          : `The server knows who you are and still refused this step (HTTP ${attribution.http_status}${attribution.server_code ? `: ${attribution.server_code}` : ""}). This is not a network problem and not a sign-in problem -- signing in again will not change its answer. Choose another trip, or go back to the picker.`,
      };
    default:
      return {
        kicker: zh ? "读取" : "Read",
        title: zh ? "这一次没读到" : "This read failed",
        body: zh
          ? "服务器接上了，但这次读取没有成功，原因还没有分类。可以重试。"
          : "The server answered, but this read did not succeed and the cause is not yet classified. Retrying is safe.",
      };
  }
}
