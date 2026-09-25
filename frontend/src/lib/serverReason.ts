/**
 * ORD-0326 -- the one channel a server's own reason travels through to the screen.
 *
 * Before this, every catch site wrote its own `?? payload.detail` / `error instanceof Error ?
 * error.message : …`, and each of those sites was measured reaching the DOM with whatever the server or
 * a browser exception happened to put in the string (r3/r4 read them at AgentComposer.tsx:98,
 * CopilotDock.tsx:363/:617, HotelsPanel.tsx:93, V8Experience.tsx:1030 -- r4 names the render sinks at
 * :185, :450, :770, :229, :1385 and :1562). One channel means: a catch site hands this module the
 * evidence, and the screen is only ever shown what this module returns.
 *
 * The boundary is the one Q64=① states. Six machine fields may appear (`http_status`, `content_type`,
 * `body_bytes`, `response_received`, `elapsed_ms`, `request_id`) plus, per CMDR_DECISION Q67=①, the
 * server's own sentence -- and that sentence only ever goes into the 技术详情 slot with an attribution
 * label, never into the main copy. A raw body, a caught object, or a stack never leaves this module:
 * there is no return path that can carry one, because the only text it can emit is read from named
 * fields of a parsed JSON envelope.
 *
 * R14 (failureAttribution.ts) stays the owner of *why the request failed*. This module does not
 * reclassify anything: it answers the narrower question "what did the server actually say, and what may
 * a screen show". A failure that this module reports as `noServerSentence` is still whatever R14 called
 * it; the fallback wording below is deliberately about the answer's shape, not about its cause.
 */

/** The only machine facts Q64=① lets onto a screen. */
export type AllowedFields = {
  http_status: number | null;
  content_type: string | null;
  body_bytes: number | null;
  response_received: boolean;
  elapsed_ms: number | null;
  request_id: string | null;
};

export type ServerSentence = {
  kind: "server_sentence";
  /** Verbatim, as the server wrote it. Rendered only inside <ServerReasonDetail>. */
  text: string;
  /** Where the text came from, so a reviewer can check it without re-deriving it. */
  slot: "error.message" | "error.detail";
  origin_label_zh: string;
  origin_label_en: string;
} & AllowedFields;

export type NoServerSentence = {
  kind: "no_server_sentence";
  /** Which of the three honest absences this is -- they are different facts, not one blank. */
  absent_because: "empty_body" | "not_json" | "html_document" | "no_response" | "server_gave_no_text";
  /** Device-written, always non-empty, always names the status. This is what the main copy may show. */
  fallback_zh: string;
  fallback_en: string;
} & AllowedFields;

export type ServerReason = ServerSentence | NoServerSentence;

/** What a call site knows at the moment it catches. Nothing here is a raw body. */
export type FailureEvidence = {
  /** Parsed JSON error envelope, i.e. the `{"error": {...}}` main.py:492 answers with. */
  envelope?: unknown;
  /** The caught value, if this came from a catch. Only `.name`/`message`-shaped facts are read. */
  cause?: unknown;
  http_status?: number | null;
  content_type?: string | null;
  /** Bytes the body actually held -- `0` is a fact, not a missing measurement. */
  body_bytes?: number | null;
  /** False only when nothing arrived at all (transport failure / our own deadline). */
  response_received?: boolean;
  elapsed_ms?: number | null;
  request_id?: string | null;
};

const MAX_SENTENCE = 600;

function text(v: unknown): string | null {
  if (typeof v !== "string") return null;
  const t = v.trim();
  if (!t) return null;
  /* A stack is multi-line by construction; a server reason is one sentence. Truncating is not the
     guard -- the guard is that this only ever reads a named field of a parsed envelope -- but a
     multi-line value means somebody handed us something other than a reason, and saying
     "no sentence" is more honest than pasting it. */
  if (t.includes("\n")) return null;
  return t.slice(0, MAX_SENTENCE);
}

function envelopeError(envelope: unknown): Record<string, unknown> | null {
  if (!envelope || typeof envelope !== "object") return null;
  const outer = envelope as Record<string, unknown>;
  const inner = outer.error;
  if (inner && typeof inner === "object") return inner as Record<string, unknown>;
  return outer;
}

function fieldsOf(e: FailureEvidence): AllowedFields {
  const env = envelopeError(e.envelope);
  return {
    http_status: typeof e.http_status === "number" ? e.http_status : null,
    content_type: text(e.content_type),
    body_bytes: typeof e.body_bytes === "number" ? e.body_bytes : null,
    response_received: e.response_received !== false,
    elapsed_ms: typeof e.elapsed_ms === "number" ? e.elapsed_ms : null,
    /* The server's own id, from the envelope main.py:487 writes, or a header the caller already read. */
    request_id: text(e.request_id) ?? text(env?.trace_id) ?? text(env?.request_id),
  };
}

function absent(
  e: FailureEvidence,
  because: NoServerSentence["absent_because"],
): NoServerSentence {
  const f = fieldsOf(e);
  const status = f.http_status === null ? "没有状态码" : `HTTP ${f.http_status}`;
  const statusEn = f.http_status === null ? "no status code" : `HTTP ${f.http_status}`;
  const zh: Record<NoServerSentence["absent_because"], string> = {
    empty_body: `服务器这次回话里没有任何文字（${status}，正文 ${f.body_bytes ?? 0} 字节）。这台设备没有替它编一句原因。`,
    not_json: `服务器回了 ${status}，但正文不是这台设备能读的格式（${f.content_type ?? "未声明 content-type"}），所以没有可读的原因。`,
    html_document: `服务器回了 ${status}，正文是一份 HTML 文档而不是接口回答，所以这里没有可读的原因。`,
    no_response: `这一发请求没有收到任何回答（${status}），所以没有服务器给的原因可显示。`,
    server_gave_no_text: `服务器回了 ${status}，但它没有写原因，只给了编号。这台设备不替它补。`,
  };
  const en: Record<NoServerSentence["absent_because"], string> = {
    empty_body: `The server answered ${statusEn} with no text at all (${f.body_bytes ?? 0} bytes). This device did not invent a reason for it.`,
    not_json: `The server answered ${statusEn} with something this device cannot read (${f.content_type ?? "no content-type"}), so there is no reason to show.`,
    html_document: `The server answered ${statusEn} with an HTML document rather than an API answer, so there is no reason to show.`,
    no_response: `Nothing answered this request (${statusEn}), so there is no server-given reason to show.`,
    server_gave_no_text: `The server answered ${statusEn} without writing a reason, only a code. This device will not supply one.`,
  };
  return { kind: "no_server_sentence", absent_because: because, fallback_zh: zh[because], fallback_en: en[because], ...f };
}

/**
 * The single entry point. A call site passes what it knows; it never passes a string it then shows.
 *
 * Order is deliberate: the envelope is the only place a server sentence can come from, so a caught
 * object is never read for prose -- that is what keeps `cause.message` off the screen while still
 * letting a caller that already parsed the body report what the server said.
 */
export function describeServerReason(e: FailureEvidence): ServerReason {
  const f = fieldsOf(e);
  if (!f.response_received) return absent(e, "no_response");
  const env = envelopeError(e.envelope);
  if (!env) {
    if (typeof e.body_bytes === "number" && e.body_bytes === 0) return absent(e, "empty_body");
    if ((f.content_type ?? "").includes("html")) return absent(e, "html_document");
    if (e.envelope === undefined && f.http_status !== null) return absent(e, "server_gave_no_text");
    return absent(e, "not_json");
  }
  const message = (typeof env === "string" ? (env as string) : null) ?? text(env.message);
  if (message) return { kind: "server_sentence", text: message, slot: "error.message",
    origin_label_zh: "服务器自己写的原因", origin_label_en: "The server's own words", ...f };
  const detail = text(env.detail);
  if (detail) return { kind: "server_sentence", text: detail, slot: "error.detail",
    origin_label_zh: "服务器自己写的原因", origin_label_en: "The server's own words", ...f };
  return absent(e, "server_gave_no_text");
}

/**
 * The bridge for a catch site. Recognised by *name*, the same way `isOriginResponseUnusable` is, so a
 * bundling or minify pass cannot silently change what a screen shows.
 *
 * Two thrown shapes exist on this channel and neither may be read for prose:
 *   - `CityNexusApiError` (api/citynexus.ts:635) carries `.status` and `.body`, where `.body` is the
 *     parsed envelope -- that is the only thing here that can produce a server sentence;
 *   - `OriginResponseUnusableError` (lib/failureAttribution.ts:89) carries `.status`, `.content_type`
 *     and `.body_kind`, which is precisely the "answered, but not with readable content" case.
 * Anything else -- a TypeError from fetch, an abort, a hand-made Error -- yields no envelope, so the
 * channel answers with a named fallback rather than echoing `cause.message` the way every one of the
 * sinks measured by r3/r4 currently does.
 */
export function reasonFromThrown(cause: unknown): FailureEvidence {
  if (cause && typeof cause === "object") {
    const c = cause as Record<string, unknown>;
    const name = typeof c.name === "string" ? c.name : "";
    if (name === "OriginResponseUnusableError") {
      const status = typeof c.status === "number" ? c.status : null;
      const kind = typeof c.body_kind === "string" ? c.body_kind : "not_json";
      return {
        envelope: null,
        http_status: status,
        content_type: typeof c.content_type === "string" ? c.content_type : null,
        body_bytes: kind === "empty" ? 0 : null,
        response_received: true,
      };
    }
    const body = c.body;
    if (body !== undefined) {
      return {
        envelope: body,
        http_status: typeof c.status === "number" ? c.status : null,
        content_type: null,
        /* `.body` is whatever requestJsonInner parked there: a parsed object, or the undecoded text
           when the parse failed (citynexus.ts:674). Length is the honest byte count either way. */
        body_bytes: typeof body === "string" ? body.length : body === null ? 0 : null,
        response_received: typeof c.status === "number",
      };
    }
  }
  return { response_received: false };
}

/**
 * The exact strings a screen is allowed to show for this reason, computed once, outside JSX.
 *
 * `ServerReasonDetail` renders these and adds nothing of its own, so an assertion on this function is an
 * assertion on what lands in the DOM -- which matters here because Playwright's own transform rewrites
 * JSX into a node shape `react-dom/server` refuses to render, so a component-level render is not
 * available to a spec in this harness. The text, not the markup, is where the ruling bites.
 */
export type ServerReasonScreenTexts = {
  /** The attribution label the Q67=① slot must carry. */
  label: string;
  /** Server sentence verbatim, or the device fallback -- the only free text this channel emits. */
  sentence: string;
  /** The allowed machine fields, one line. */
  machine: string;
  /** What the *main* copy may say. Never carries the server's sentence. */
  headline: string;
  attribution: "server" | "device";
};

/** Every character a screen shows for this reason, computed outside JSX so a spec can assert on it. */
export function serverReasonScreenTexts(reason: ServerReason, zh: boolean): ServerReasonScreenTexts {
  const machine = [
    `http_status=${reason.http_status ?? "absent"}`,
    `content_type=${reason.content_type ?? "absent"}`,
    `body_bytes=${reason.body_bytes ?? "absent"}`,
    `response_received=${reason.response_received ? "yes" : "no"}`,
    `elapsed_ms=${reason.elapsed_ms ?? "absent"}`,
    `request_id=${reason.request_id ?? "absent"}`,
  ].join(" · ");
  if (reason.kind === "server_sentence") {
    return {
      label: zh ? reason.origin_label_zh : reason.origin_label_en,
      sentence: reason.text,
      machine,
      attribution: "server",
      headline: zh
        ? "服务器给了原因，已放在下面的技术详情里。"
        : "The server gave a reason; it is in the technical detail below.",
    };
  }
  return {
    label: zh ? "这台设备自己的说明（服务器没给句子）" : "This device's own note (the server sent no sentence)",
    sentence: zh ? reason.fallback_zh : reason.fallback_en,
    machine,
    attribution: "device",
    headline: zh ? reason.fallback_zh : reason.fallback_en,
  };
}

