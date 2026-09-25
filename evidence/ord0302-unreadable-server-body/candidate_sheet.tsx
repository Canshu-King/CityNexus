/**
 * "AI 帮我规划" — natural-language trip planning entry.
 *
 * Design rules honoured here:
 *  - the traveller types plain language; no internal vocabulary is shown;
 *  - progress shows only what this component can prove.  `POST /agent/commands`
 *    is synchronous and the backend reports no intermediate phase, so the wait is
 *    shown as elapsed seconds and an honest "no stage signal", never as a step that
 *    ticked by on a timer (ORD-0038 §2: a fake progress bar is worse than none,
 *    because it makes people believe the system is working);
 *  - the steps that ARE listed are the ones this file actually awaits -- baseline
 *    read, request, verification re-count, and the fallback re-plan when it really
 *    runs;
 *  - internal action enums (REQUEST_REPLAN, ACCEPT_REPLAN, …) and mission
 *    internals are never rendered;
 *  - a provider failure is shown honestly with a retry, never faked as success
 *    (master mission Phase 10), and a cancellation is neither.
 */

import { useEffect, useRef, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { markPendingContinuation } from "../../api/journeyContinuation";

/** The phases this component itself drives, in the order it can enter them. */
type PhaseKey = "baseline" | "request" | "verify" | "fallback";

/* ORD-0250: this floor used to be a bare `8` inside submit() while the button next to it refused
   silently -- so an empty box looked like a button that did nothing.  Named once, read by the
   refusal, the control's aria-disabled and the reason we now paint on screen. */
const REQUEST_MIN_LENGTH = 8;

const PHASES: { key: PhaseKey; zh: string; en: string }[] = [
  { key: "baseline", zh: "读取已有方案作为基线", en: "Reading existing plans as a baseline" },
  { key: "request", zh: "发出请求，等待模型返回", en: "Request sent, waiting for the model" },
  { key: "verify", zh: "核对本次是否真的产出了新方案", en: "Checking whether this run produced plans" },
  {
    key: "fallback",
    zh: "改用已发现的城市地点重新排一版",
    en: "Re-planning from the places already discovered",
  },
];

/*
 * ORD-0104 ①: an example has to be about *this* trip, or there is no example.
 *
 * What used to sit here were two hardcoded Xiamen itineraries ("我和朋友两个人去厦门…鼓浪屿、环岛路、
 * 沙茶面"), shown as the placeholder and as two chips -- so a traveller on a Tianjin or Beijing trip
 * was handed another city's concrete facts as their own suggestion.  That is the same class of defect
 * as a fabricated progress bar: the screen states something it did not learn.
 *
 * Now the sentences are built from place names the server actually returned for this journey's city,
 * and when it returns fewer than two there is nothing to show -- an absent example is honest, an
 * invented one is not.
 */
const NEUTRAL_PLACEHOLDER = {
  zh: "用你自己的话说：这趟想怎么玩、想吃什么、哪儿一定要去。",
  en: "In your own words: how you want this trip to go, what to eat, what you must not miss.",
};

/* ORD-0250: what the screen says when a press is refused for want of a request.  It names the grey
   example as an example, because that is exactly what makes an empty box look answerable.  No number
   here: the length floor lives in one place in code, and prose that repeats it goes stale. */
const REQUEST_TOO_SHORT = {
  zh: "还差你自己的一句话：上面灰色的例子只是提示，不算你说的需求，所以我们没有东西可以拿去排。",
  en: "We still need it in your own words. The grey example above is a hint, not a request we can plan from.",
};

function examplesFor(
  placeNames: string[],
  zh: boolean,
): Array<{ zh: string; en: string }> {
  /* Ordered by name rather than by the order the read happened to return, so this cannot become a
     second `slice(0, 8)` in disguise (R7): which two places appear in an *example sentence* must not
     be decided by a provider's row order, because that order is not a claim about the trip. */
  const picked = placeNames
    .filter((name) => name.trim().length > 0)
    .sort((a, b) => a.localeCompare(b, zh ? "zh-CN" : "en"))
    .slice(0, 2);
  if (picked.length < 2) return [];
  const [first, second] = picked;
  return [
    {
      zh: `我想去${first}和${second}，节奏轻松一点，再找点当地吃的。`,
      en: `I would like to fit in ${first} and ${second} at an easy pace, with somewhere local to eat.`,
    },
    {
      zh: `${first}排在下午，${second}放在傍晚，别排太满。`,
      en: `Put ${first} in the afternoon and ${second} in the early evening, and leave the rest open.`,
    },
  ];
}

/**
 * The server's own names for "why there is nothing to plan with", and the one next step each of them
 * earns.  Keyed by `error.code` / `error.reason_code` and **never by an English sentence** -- a
 * substring match on provider wording is how a screen ends up telling a traveller to "adjust the
 * budget" when the real cause was an empty catalogue (ORD-0107).  The codes are the ones the backend
 * lanes are putting names on (ORD-0101/0108: `services.py:843/:902/:932`, `CATALOG_EMPTY` at the
 * compose exit); anything the table does not know is shown as unknown, with the server's own sentence
 * under 技术详情, because inventing a paraphrase of a code we have not read is a lie waiting to happen.
 */
const BLOCKED_BY_CODE: Record<
  string,
  { zh: string; en: string; action: "another-city" | "retry" | "none" }
> = {
  CATALOG_EMPTY: {
    zh: "这座城我们还没有任何地点数据，所以不是你描述得不对——是没有东西可排。",
    en: "We hold no place data for this city yet, so nothing about your wording failed — there was nothing to assemble a trip from.",
    action: "another-city",
  },
  CATALOG_INSUFFICIENT: {
    zh: "这座城我们手上的地点太少，配不平一天的行程。",
    en: "We have too few places for this city to balance a day's itinerary.",
    action: "another-city",
  },
  PLACES_NOT_IN_CATALOG: {
    zh: "要排的地点不在我们的目录里，所以排不出行程。",
    en: "The places this was asked to plan are not in our catalogue, so no itinerary could be built.",
    action: "another-city",
  },
  PLACE_COST_UNVERIFIED: {
    zh: "地点有了，但费用我们没能核实，所以没有给出带价格的方案。",
    en: "The places were found but their costs could not be verified, so no priced plan was offered.",
    action: "retry",
  },
  PLACE_OUTSIDE_JOURNEY_WINDOW: {
    zh: "这些地点的开放时间和你这趟的日期对不上。",
    en: "These places' opening hours do not fit the dates of this trip.",
    action: "another-city",
  },
  MOBILITY_DATA_UNAVAILABLE: {
    zh: "这趟的出行数据缺了一段（站与站之间的时间没读到），所以没排出来。",
    en: "Part of this trip's mobility data is missing, so nothing could be scheduled.",
    action: "retry",
  },
};

/** The server's name for a refusal, from its envelope.  Empty when it gave none -- and then this
    screen says it does not know, rather than guessing a cause. */
function serverReasonCode(body: unknown): string {
  const error = (body as { error?: Record<string, unknown> } | null)?.error;
  if (!error || typeof error !== "object") return "";
  for (const key of ["reason_code", "code", "message_key"]) {
    const value = error[key];
    if (typeof value === "string" && value.trim()) return value.trim().toUpperCase();
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  return typeof detail === "string" ? detail.slice(0, 60).toUpperCase() : "";
}

/** The server's own sentence, kept verbatim for 技术详情. */
function serverReasonSentence(body: unknown): string | null {
  const error = (body as { error?: Record<string, unknown> } | null)?.error;
  if (error && typeof error.message === "string" && error.message.trim()) return error.message;
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return null;
}

/**
 * ORD-0280: which mouth a failure sentence came from, carried with the sentence.
 *
 * `server` means this very answer carried the words; `device` means this screen composed them.  The
 * distinction used to be lost at render time, so a client-invented `HTTP 500` sat under the label
 * 「服务器给出的原因」 and a traveller read our guess as the backend's own statement -- the same trust hole
 * ORD-0262 closed for the copilot's copy, in a different sheet.
 *
 * The shape is `simulationAdapter.ts`'s existing `said ? <quote it> : <say we have no wording>`, moved
 * here as one decision point so all three refusal legs share it.  Nothing is deleted: a device-composed
 * line stays visible as what it is, because the status code really was observed and is worth reading.
 */
type FailureNote = { text: string; from: "server" | "device" };

function failureNote(serverText: string | null, deviceText: string): FailureNote {
  return serverText ? { text: serverText, from: "server" } : { text: deviceText, from: "device" };
}


/** Map internal mission status -> traveller language. */
function statusCopy(
  status: string,
  zh: boolean,
  planCount = 0,
): {
  title: string;
  body: string;
  tone: "ok" | "warn" | "busy" | "neutral";
  action?: "another-city" | "retry";
} {
  const s = (status || "").toUpperCase();
  /* A named block from the server's own envelope.  The code decides the words; nothing here is
     inferred from how a provider phrased its sentence. */
  if (s.startsWith("BLOCKED:")) {
    const code = s.slice("BLOCKED:".length);
    const known = BLOCKED_BY_CODE[code];
    return {
      title: zh ? "这次排不出方案：数据不够，不是你说的不对" : "No plan this time: the data is short, not your wording",
      body: known
        ? zh
          ? `${known.zh}（服务器给的原因编号：${code}）`
          : `${known.en} (server reason code: ${code})`
        : zh
          ? `服务器回的原因编号是 ${code || "（没给编号）"}，这条我们还没有本地文案，所以不替你解释它——原话在"技术详情"里。`
          : `The server's reason code is ${code || "(none given)"} and we have no wording for it, so we quote rather than explain — the sentence is under "Technical detail".`,
      tone: "warn",
      action: known ? known.action === "another-city" ? "another-city" : "retry" : "retry",
    };
  }
  if (s === "COMPLETED" || s === "SUCCEEDED") {
    return {
      title: zh ? `已生成 ${planCount} 个可选方案` : `${planCount} candidate plans are ready`,
      body: zh
        ? "去“今天”对比这几个方案，选一个再继续。"
        : "Compare them on Today, then choose one to continue.",
      tone: "ok",
    };
  }
  if (s === "CANCELLED") {
    return {
      title: zh ? "已取消" : "Cancelled",
      body: zh
        ? "请求已中止，你的行程没有被改动。可以改个说法再来一次。"
        : "The request was aborted. Your trip is untouched — rephrase and try again.",
      tone: "neutral",
    };
  }
  if (s === "CANCELLED_AFTER_SEND") {
    return {
      title: zh ? "已中止后续核对" : "Stopped before verification",
      body: zh
        ? "请求本身已经发出去了，可能已经生成方案。请先刷新确认，不要重复提交。"
        : "The request had already been sent, so it may have produced plans. Refresh and check before submitting again.",
      tone: "warn",
    };
  }
  if (s === "NETWORK") {
    return {
      title: zh ? "连不上服务端" : "The server could not be reached",
      body: zh
        ? "网络或后端没有响应，这与你的需求内容无关。你的行程没有被改动，检查网络后可以重试。"
        : "Neither the network nor the backend answered — this is not about what you typed. Your trip is unchanged; retry once you are connected.",
      tone: "warn",
    };
  }
  if (s === "HTTP_422") {
    return {
      title: zh ? "这个要求被明确拒绝" : "The request was refused",
      body: zh
        ? "服务端说明了原因（见“技术详情”）。你的行程没有被改动，按原因调整条件或换个说法再试。"
        : "The backend gave a reason (see “Technical detail”). Your trip is unchanged — adjust to that reason and retry.",
      tone: "warn",
    };
  }
  if (s.startsWith("HTTP_5")) {
    return {
      title: zh ? "服务端处理失败" : "The server failed to finish",
      body: zh
        ? "这次是服务端出错，不是你的需求有问题。行程未被改动，可稍后重试；反复出现请保留“技术详情”。"
        : "The server errored out — not your request. Your trip is unchanged; retry later and keep the technical detail if it repeats.",
      tone: "warn",
    };
  }
  if (s === "PLANS_WITHOUT_AI") {
    return {
      title: zh
        ? `AI 没有参与这次规划（生成了 ${planCount} 个备选）`
        : `AI did not take part — ${planCount} options were still assembled`,
      body: zh
        ? "这些方案是按已经找到的城市地点重新排的，不代表系统理解了你刚才那段话。想按你的要求排，请重试；原因在“技术详情”里。"
        : "These were assembled from places already found for this city; they do not show that your request was understood. Retry to plan from what you typed — the reason is under “Technical detail”.",
      tone: "warn",
    };
  }
  if (s === "BASELINE_UNAVAILABLE") {
    return {
      title: zh ? "无法确认这次的结果" : "We could not confirm this run",
      body: zh
        ? "无法确认本次是否生成了新方案，请重试或刷新页面。"
        : "We could not confirm whether this run produced new plans. Please retry or refresh.",
      tone: "warn",
    };
  }
  if (s === "NO_PLANS_PRODUCED") {
    return {
      title: zh ? "没有生成可行方案" : "No usable plans were produced",
      body: zh
        ? "服务器说这次没排出可行方案，但没有给出具体原因编号，所以我们不替你猜是预算、措辞还是数据的问题。你的行程没有被改动；原因原文在“技术详情”里，可以再试一次或换一座城市。"
        : "The server said no feasible plan came out but gave no reason code, so we will not guess whether that was your budget, your wording or our data. Your trip is unchanged; its sentence is under “Technical detail”. You can retry or try another city.",
      tone: "warn",
    };
  }
  if (s.includes("SKIPPED_EXTERNAL_DEPENDENCY") || s.includes("EXTERNAL")) {
    return {
      title: zh ? "AI 暂时不可用" : "AI is unavailable right now",
      body: zh
        ? "规划助手这次没能连上。你的行程没有被改动，可以稍后重试。"
        : "The planning assistant could not be reached. Your trip is unchanged; you can retry.",
      tone: "warn",
    };
  }
  if (s === "RUNNING" || s === "PENDING" || s === "QUEUED") {
    return {
      title: zh ? "正在规划…" : "Planning…",
      body: zh ? "正在处理你的需求。" : "Working on your request.",
      tone: "busy",
    };
  }
  return {
    title: zh ? "暂时无法完成规划" : "Could not finish planning",
    body: zh
      ? "这次没能生成方案。你的行程没有被改动，可以重试或换个说法。"
      : "We could not produce plans this time. Your trip is unchanged; retry or rephrase.",
    tone: "warn",
  };
}

/**
 * fetch() rejects a cancelled request with a DOMException named AbortError.  Without
 * this, "I pressed cancel" and "the network died" collapse into the same message.
 */
function isAbort(cause: unknown): boolean {
  return cause instanceof Error && cause.name === "AbortError";
}

export function PlanWithAiSheet({
  journeyId,
  cityCode,
  onClose,
  onPlanned,
  onChooseAnotherCity,
}: {
  journeyId: string;
  cityCode?: string;
  onClose: () => void;
  /** Where the "换一座城市" next step goes.  Optional because the sheet is also mounted from paths
      that have no city picker to open; without it the refusal still reads in full, it just has no
      button to offer. */
  onChooseAnotherCity?: () => void;
  onPlanned?: () => void;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const [text, setText] = useState("");
  /* The destination's own words, from the same read the fallback uses.  Read once when the sheet
     opens; a failure leaves `[]`, which means "no examples", not "use the old ones". */
  const [placeNames, setPlaceNames] = useState<string[]>([]);
  /* Whether the read that decides the suggestions has answered at all.  Without it the area under the
     input means "this city has nothing to suggest" and "we are still looking" at once, and a traveller
     watching suggestions appear a second later has no way to tell which happened. */
  const [namesRead, setNamesRead] = useState(false);
  const [busy, setBusy] = useState(false);
  /* Set when a press was refused because there is nothing to plan from; the reason is painted, not
     announced only to a screen reader.  Cleared by the same gate once the words are long enough. */
  const [requestTooShort, setRequestTooShort] = useState(false);
  const [phase, setPhase] = useState<PhaseKey | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [aiState, setAiState] = useState<"checking" | "ready" | "unconfigured" | "unknown">(
    "checking",
  );
  const [result, setResult] = useState<null | {
    status: string;
    failureReason: FailureNote | null;
    summary: string | null;
    planCount?: number;
    newPlanIds?: string[];
  }>(null);
  const abortRef = useRef<AbortController | null>(null);
  /* ORD-0246: `disabled={busy}` is a *rendered* fact, and two clicks inside one tick both arrive
     before React re-renders, so the render cannot be the re-entry guard. This ref can. */
  const runningRef = useRef(false);
  const startedAt = useRef(0);

  /* The only number this sheet is allowed to animate is one it can prove: seconds
     that really passed since the request was made. */
  useEffect(() => {
    if (!busy) return;
    const tick = () => setElapsed(Math.floor((Date.now() - startedAt.current) / 1000));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [busy]);

  /* Closing the sheet must not leave a request running that nobody can see or stop. */
  useEffect(() => () => abortRef.current?.abort(), []);

  /* ORD-0104 ①: the examples are read from this journey's own city.  A non-2xx or a short list leaves
     the list empty, and empty means "show no examples" -- the fallback is silence, not the old Xiamen
     sentences. */
  useEffect(() => {
    let stale = false;
    const controller = new AbortController();
    void fetch(`/api/v1/places?city_code=${encodeURIComponent(cityCode ?? "")}`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => {
        if (stale) return;
        setNamesRead(true);
        if (!Array.isArray(body)) return;
        setPlaceNames(
          body
            .map((item: { name?: string }) => (typeof item?.name === "string" ? item.name : ""))
            .filter((name: string) => name.trim().length > 0),
        );
      })
      .catch(() => {
        /* aborted or unreachable: nothing to suggest, which is the honest state -- and it is settled,
           not pending. */
        if (!stale) setNamesRead(true);
      });
    return () => {
      stale = true;
      controller.abort();
    };
  }, [cityCode]);

  useEffect(() => {
    let stale = false;
    void fetch("/api/v1/agent/runtime-status", { headers: { Accept: "application/json" } })
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => {
        if (stale) return;
        setAiState(
          body && typeof body.deepseek_configured === "boolean"
            ? body.deepseek_configured
              ? "ready"
              : "unconfigured"
            : "unknown",
        );
      })
      .catch(() => {
        /* A failed pre-flight is reported as unknown, never as "ready". */
        if (!stale) setAiState("unknown");
      });
    return () => {
      stale = true;
    };
  }, []);

  /**
   * Ids of every candidate plan that already existed, or `null` when the
   * baseline could not be fetched.
   *
   * Fail-CLOSED: an empty set means "there really were no plans before this
   * run".  A failed / non-OK / unparsable lookup must NOT masquerade as an
   * empty baseline — otherwise an old plan appears later and is mis-attributed
   * to THIS run.  `null` = the baseline is indeterminate.
   */
  const existingPlanIds = async (signal: AbortSignal): Promise<Set<string> | null> => {
    try {
      const response = await fetch(`/api/v1/journeys/${journeyId}/plans`, {
        headers: { Accept: "application/json" },
        signal,
      });
      if (!response.ok) return null;
      const plans = await response.json();
      // A non-array body is not a trustworthy "no plans" answer either.
      if (!Array.isArray(plans)) return null;
      return new Set(
        plans.map((item: { id?: string }) => item?.id).filter(Boolean) as string[],
      );
    } catch (cause) {
      // A cancellation is a decision, not an indeterminate baseline.
      if (isAbort(cause)) throw cause;
      return null;
    }
  };

  const submit = async () => {
    const command = text.trim();
    if (command.length < REQUEST_MIN_LENGTH) {
      /* ORD-0250: this `return` used to be silent -- no request, no word, nothing to read.  The press
         is still refused (there is genuinely nothing to plan from) but it now leaves a reason on the
         screen, and the placeholder example is not treated as if the traveller had said it. */
      setRequestTooShort(true);
      return;
    }
    setRequestTooShort(false);
    /* Synchronous, ahead of every await and every setState below: the second click of a same-tick
       double tap reaches this function while the button is still rendered as enabled, so refusing
       it here is the only place it can be refused.  Silence is deliberate -- the first request is
       running and the screen already says so. */
    if (runningRef.current) return;
    runningRef.current = true;
    /* ORD-0253: one identity per submission INTENT.  Minted here -- after the synchronous guard that
       refuses the second click of a same-tick double tap, and before the first await -- so a refused
       burst never gets one, both legs of the accepted press carry the same one, and the next deliberate
       press mints a new one.  Not held in state, storage or a cooldown: none of those is the intent,
       and a cooldown dressed up as correctness would let two different asks reuse a key.
       The leg that matters is `plans/generate` -- the server reads the transport key there
       (`main.py`, ORD-0272), and its validator wants 8..128 characters, which a v4 UUID satisfies. */
    const idempotencyKey = crypto.randomUUID();
    const controller = new AbortController();
    abortRef.current = controller;
    const signal = controller.signal;
    setBusy(true);
    setResult(null);
    setElapsed(0);
    startedAt.current = Date.now();
    /* How far we actually got, kept in a local because state is stale inside this
       closure.  A cancel before the request leaves is a clean cancellation; one after
       it is not, because the backend may already have produced plans. */
    let reached: PhaseKey = "baseline";
    const enter = (next: PhaseKey) => {
      reached = next;
      setPhase(next);
    };
    enter("baseline");
    let baseline: Set<string> | null = null;
    try {
      // This run must be judged on what IT produced.  Counting all plans let an
      // old ACTIVE/SELECTED plan satisfy a failed new run.  `null` means we could
      // not read the baseline at all, so nothing can be attributed to this run —
      // fail CLOSED instead of assuming an empty baseline.
      baseline = await existingPlanIds(signal);
      enter("request");
      const response = await fetch(`/api/v1/journeys/${journeyId}/agent/commands`, {
        method: "POST",
        /* The transport key travels with the whole intent.  This route declares no such parameter
           today, so it is inert HERE -- the leg that reads it is plans/generate below.  The body
           gains nothing: AgentCommandRequest is extra="forbid", so a new key would be a 422. */
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify({ command }),
        signal,
      });
      const body = await response.json().catch(() => null);
      const mission = body?.mission ?? null;
      /* ORD-0269 clause 1: the pending marker is written the moment leg 1 returns a mission id --
         after the response is in hand and before leg 2 could ever be sent.  It is NOT cleared when
         a request goes out (clause 5); only a visible outcome supersedes it. */
      if (mission?.id) {
        markPendingContinuation(journeyId, String(mission.id));
      }
      if (!response.ok) {
        /* A refused or failed request is reported as what it is.  Letting the
           fallback re-plan run here would let a synthetic plan answer for a request
           the backend explicitly rejected. */
        setResult({
          status: `HTTP_${response.status}`,
          /* ORD-0280 site 1 of 3.  The server fields are read through the same helper the other legs
             use, so one envelope cannot be "from the server" here and "unknown" there; the status line
             is kept as what it is, and the LABEL is what says who spoke.  Side effect worth stating:
             when an answer carries BOTH `error.message` and `detail`, `error.message` wins now, where
             the old inline chain answered `detail` first -- the other two legs already treat
             `error.message` as the server's sentence, so the sheet now agrees with itself. */
          failureReason: failureNote(
            serverReasonSentence(body),
            `agent/commands -> HTTP ${response.status}`,
          ),
          summary: null,
          planCount: -1,
          newPlanIds: [],
        });
        return;
      }
      // A plan id only counts as "new" when we KNOW it was absent from the
      // pre-run baseline.  With an indeterminate baseline there is no such id.
      const isNewPlanId = (id: string | undefined): id is string =>
        typeof id === "string" && id.length > 0 && baseline !== null && !baseline.has(id);
      // A COMPLETED mission only means the request compiled.  It does NOT mean
      // candidate plans exist, so the real plan count decides what we report.
      // Reporting "plans are ready" without checking was a false success.
      // Returns `null` when the answer is unknowable (bad baseline OR bad
      // re-count) — NOT the same as "[] = no new plans".
      const countNewPlans = async (): Promise<string[] | null> => {
        if (baseline === null) return null;
        try {
          const plansResponse = await fetch(`/api/v1/journeys/${journeyId}/plans`, {
            headers: { Accept: "application/json" },
            signal,
          });
          if (!plansResponse.ok) return null;
          const plans = await plansResponse.json();
          if (!Array.isArray(plans)) return null;
          return plans.map((item: { id?: string }) => item?.id).filter(isNewPlanId);
        } catch (cause) {
          if (isAbort(cause)) throw cause;
          return null;
        }
      };
      enter("verify");
      const counted = await countNewPlans();
      let newPlanIds: string[] = counted ?? [];
      let planCount = counted === null ? -1 : newPlanIds.length;
      // The mission compiler can succeed while the agent runtime (an external
      // dependency) produces nothing.  Before reporting failure, try the real
      // product path: compose candidates from the city places that discovery
      // has already materialised for this journey.  Only attempted when the
      // baseline is KNOWN — otherwise we cannot attribute what it created.
      let blockedCode = "";
      let blockedSentence: FailureNote | null = null;
      if (baseline !== null && planCount === 0) {
        enter("fallback");
        try {
          const placesResponse = await fetch(
            `/api/v1/places?city_code=${encodeURIComponent(cityCode)}`,
            { headers: { Accept: "application/json" }, signal },
          );
          /* ORD-0107 ②: this read used to answer `[]` on any non-2xx, which made "we could not look"
             indistinguishable from "this city has nothing" and, three lines later, from "your request
             produced nothing".  A failed read is now its own named state. */
          if (!placesResponse.ok) {
            const unreadable = await placesResponse.json().catch(() => null);
            setResult({
              status: `BLOCKED:${serverReasonCode(unreadable) || `PLACES_HTTP_${placesResponse.status}`}`,
              /* ORD-0280 site 2 of 3. */
              failureReason: failureNote(
                serverReasonSentence(unreadable),
                `GET /places -> HTTP ${placesResponse.status}`,
              ),
              summary: null,
              planCount: -1,
              newPlanIds: [],
            });
            return;
          }
          const catalogue = await placesResponse.json();
          const knownIds = new Set(
            (Array.isArray(catalogue) ? catalogue : [])
              .map((item: { id?: string }) => item?.id)
              .filter((id: unknown): id is string => typeof id === "string" && id.length > 0),
          );
          if (knownIds.size < 2) {
            /* The old code simply did not send the request and the traveller saw nothing.  Two places is
               the server's own floor (`schemas.py:423 min_length=2`), so this is a fact about our data,
               said as one. */
            setResult({
              status: knownIds.size === 0 ? "BLOCKED:CATALOG_EMPTY" : "BLOCKED:CATALOG_INSUFFICIENT",
              /* A count this screen measured out of a 200 it was allowed to read.  It is a fact about
                 our data, said as one, and it is NOT the server's reason -- ORD-0280 puts the label
                 where the words came from. */
              failureReason: {
                text: `GET /places?city_code=${cityCode} -> ${knownIds.size} places`,
                from: "device",
              },
              summary: null,
              planCount: -1,
              newPlanIds: [],
            });
            return;
          }
          /* ORD-0107 ①: the positional slice is gone.  Taking the first eight ids in whatever order the
             read returned was this screen inventing a shortlist -- the model proposes no places at all
             (`app/agent/mission.py:21-35` carries objectives and bounds, `:490-498` adds policy bounds;
             neither has a place id), so there was no proposal to intersect and no basis for the order.
             Sending no `place_ids` hands the choice back to the server's catalogue path
             (`services.py` `_catalogue_templates`), the same one the demo stage plans through. */
          const generate = await fetch(
            `/api/v1/journeys/${journeyId}/plans/generate`,
            {
              method: "POST",
              /* ORD-0253's whole point: this is the leg the server reads the transport key on.
                 Without it the request reaches the route with no identity at all, and the durable
                 receipt machinery never sees this submission -- "the phone's press leaves no trace"
                 is literally this header being absent. */
              headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
                "Idempotency-Key": idempotencyKey,
              },
              body: JSON.stringify({ candidate_count: 3 }),
              signal,
            },
          );
          if (generate.ok) {
            const created = await generate.json();
            // Only artifacts this run created count as success.
            newPlanIds = (Array.isArray(created) ? created : [])
              .map((item: { id?: string }) => item?.id)
              .filter(isNewPlanId);
            if (newPlanIds.length === 0) {
              const recounted = await countNewPlans();
              if (recounted !== null) newPlanIds = recounted;
            }
            planCount = newPlanIds.length;
          } else {
            const refused = await generate.json().catch(() => null);
            blockedCode = serverReasonCode(refused);
            /* ORD-0280 site 3 of 3. */
            blockedSentence = failureNote(
              serverReasonSentence(refused),
              `POST /plans/generate -> HTTP ${generate.status}`,
            );
          }
        } catch (cause) {
          if (isAbort(cause)) throw cause;
          /* keep planCount at 0 and report honestly */
        }
      }

      const missionStatus = String(mission?.status ?? "").toUpperCase();
      /* A mission that did not complete is not a success, however many rows exist
         afterwards.  Measured on the production build with no model configured: the
         mission came back with `DeepSeek API key is not configured`, the fallback re-plan
         produced 2 plans, and the sheet reported "已生成 2 个可选方案" as plain success.
         Those rows are real, but nothing about them answers what the traveller typed. */
      const missionCompleted = missionStatus === "COMPLETED" || missionStatus === "SUCCEEDED";
      let status: string;
      if (baseline === null) {
        // Indeterminate baseline: whatever we see afterwards cannot be
        // attributed to this run, so success is never claimed.  The harness
        // reads planCount === -1 as "not a success".
        status = "BASELINE_UNAVAILABLE";
        planCount = -1;
        newPlanIds = [];
      } else if (planCount > 0 && missionCompleted) {
        status = "COMPLETED";
      } else if (planCount > 0) {
        status = "PLANS_WITHOUT_AI";
      } else if (blockedCode) {
        /* Ahead of the "AI unavailable" branch on purpose: when the compose step named a data cause,
           that is both more specific and more actionable than "retry later", and the mission's own
           reason still sits under 技术详情. */
        status = `BLOCKED:${blockedCode}`;
      } else if (missionStatus.includes("EXTERNAL") || missionStatus.includes("SKIPPED")) {
        status = "SKIPPED_EXTERNAL_DEPENDENCY";
      } else {
        // Compiled, but produced nothing the traveller can use.
        status = "NO_PLANS_PRODUCED";
      }
      setResult({
        status,
        newPlanIds,
        /* `failure_reason` is the mission's own stored field, i.e. words that came off this server, so
           it is labelled as such; the refused-request note carries its own origin from where it was set.
           ORD-0302 X-5: this branch's own card text tells the traveller the reason sits under 技术详情,
           so it may not render a screen where that block does not exist.  Q53=① chose "render it" over
           "soften the sentence", so when the mission stored no reason we show what THIS screen measured
           -- a count it derived from the two reads it was allowed to make -- labelled as a device reading. */
        failureReason: mission?.failure_reason
          ? { text: mission.failure_reason, from: "server" as const }
          : blockedSentence ?? (status === "NO_PLANS_PRODUCED"
              ? failureNote(null, `plans compiled; ${planCount} usable result(s) reached this screen`)
              : null),
        summary: mission?.reasoning_summary ?? null,
        planCount,
      });
      if (status === "COMPLETED") onPlanned?.();
    } catch (cause) {
      if (isAbort(cause)) {
        /* `reached` is "request" or later once the POST has been issued, which is
           the point after which cancelling no longer guarantees nothing happened. */
        setResult({
          status: reached === "baseline" ? "CANCELLED" : "CANCELLED_AFTER_SEND",
          failureReason: null,
          summary: null,
        });
      } else {
        /* ORD-0302 ②: this used to write `failureReason: null`, and because 技术详情 is gated on
           `failureReason || summary`, the whole block left the DOM -- a traveller looking at 「连不上服务端」
           had nothing to open, and no way to tell "the origin never answered" from "we could not read what
           it answered".  A note THIS device composed, labelled as such, is the honest minimum: it says we got
           no wording, without inventing the server's. */
        setResult({
          status: "NETWORK",
          failureReason: failureNote(null, "no readable answer reached this device (network or origin)"),
          summary: null,
        });
      }
    } finally {
      abortRef.current = null;
      runningRef.current = false;
      setBusy(false);
      setPhase(null);
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
  };

  const copy = result ? statusCopy(result.status, zh, result.planCount ?? 0) : null;
  const examples = examplesFor(placeNames, zh);
  const here = phase ? PHASES.findIndex((item) => item.key === phase) : -1;
  const currentPhase = here >= 0 ? PHASES[here] : null;
  const phaseLabel = currentPhase
    ? zh
      ? currentPhase.zh
      : currentPhase.en
    : zh
      ? "正在处理"
      : "Working";

  return (
    <div className="v8-sheet-backdrop" role="dialog" aria-modal="true" data-testid="plan-ai-sheet">
      <section className="plan-ai-sheet">
        <header className="plan-ai-head">
          <div>
            <b>{zh ? "AI 帮我规划" : "Plan my trip with AI"}</b>
            <small>
              {zh
                ? "用你自己的话描述这趟旅行，越具体越好。"
                : "Describe the trip in your own words — the more specific the better."}
            </small>
          </div>
          <button type="button" className="plan-ai-close" aria-label={zh ? "关闭" : "Close"} onClick={onClose}>
            ×
          </button>
        </header>

        {/* Everything that may grow lives in one scroll region between two pinned ends. */}
        <div className="plan-ai-scroll" data-testid="plan-ai-scroll">
        <label className="plan-ai-field">
          <span className="v8-sr-only">{zh ? "旅行需求" : "Trip request"}</span>
          <textarea
            data-testid="plan-ai-input"
            rows={5}
            value={text}
            disabled={busy}
            aria-describedby={
              requestTooShort && text.trim().length < REQUEST_MIN_LENGTH ? "plan-ai-request-hint" : undefined
            }
            onChange={(event) => setText(event.target.value)}
            placeholder={
              examples.length
                ? zh
                  ? examples[0].zh
                  : examples[0].en
                : zh
                  ? NEUTRAL_PLACEHOLDER.zh
                  : NEUTRAL_PLACEHOLDER.en
            }
          />
        </label>

        {/* ORD-0250: the example sentence sits in the box as a placeholder, so a traveller who presses
            开始规划 with nothing typed sees a filled-looking field and an inert button.  The refusal
            stays (there is nothing to plan from) but it now says what is missing, in painted text --
            and it says the box is still empty, which is the part the placeholder hides. */}
        {requestTooShort && text.trim().length < REQUEST_MIN_LENGTH && (
          <p
            className="plan-ai-field-hint"
            id="plan-ai-request-hint"
            data-testid="plan-ai-empty-request"
            data-request-length={text.trim().length}
            role="status"
          >
            {zh ? REQUEST_TOO_SHORT.zh : REQUEST_TOO_SHORT.en}
          </p>
        )}

        {/* No chips at all when this city has fewer than two catalogued places -- an absent
            suggestion is honest, an invented one is a claim about a trip we know nothing about. */}
        <div
          className="plan-ai-examples"
          data-testid="plan-ai-examples"
          data-example-count={examples.length}
          data-examples-state={!namesRead ? "reading" : examples.length ? "suggested" : "none"}
        >
          {examples.map((item) => (
            <button
              key={item.en}
              type="button"
              disabled={busy}
              onClick={() => setText(zh ? item.zh : item.en)}
            >
              {zh ? item.zh.slice(0, 18) + "…" : item.en.slice(0, 26) + "…"}
            </button>
          ))}
        </div>

        {aiState !== "checking" && (
          <p
            className={`plan-ai-preflight ${aiState}`}
            data-testid="plan-ai-preflight"
            data-ai-state={aiState}
          >
            {aiState === "ready" &&
              (zh ? "这台服务已接入 AI 模型。" : "A model is configured on this server.")}
            {aiState === "unconfigured" &&
              (zh
                ? "这台服务没有接入 AI 模型：现在提交不会真的由 AI 规划，结果会走其它路径。"
                : "No model is configured here, so submitting will not be planned by AI.")}
            {aiState === "unknown" &&
              (zh
                ? "读不到 AI 状态（状态接口没有应答）。这只说明我们不知道，不代表它可用或不可用。"
                : "The AI status endpoint did not answer. That means we do not know — not that it works or that it is broken.")}
          </p>
        )}

        {busy && (
          <div
            className="plan-ai-live"
            data-testid="plan-ai-live"
            data-elapsed-seconds={elapsed}
            data-phase={phase ?? ""}
          >
            <p className="plan-ai-live-line" data-testid="plan-ai-elapsed">
              <span className="plan-ai-pulse" aria-hidden="true" />
              <span>
                {phaseLabel} · {zh ? `已等待 ${elapsed} 秒` : `waiting ${elapsed}s`}
              </span>
            </p>
            <p className="plan-ai-live-note">
              {zh
                ? "后端不会中途汇报进度，所以这里只有真实等待时间，没有百分比，也没有猜。"
                : "The backend reports nothing until it finishes, so this is measured waiting time — no percentage, no guessing."}
            </p>
            <ol className="plan-ai-steps" data-testid="plan-ai-steps">
              {PHASES.map((item, index) => {
                if (item.key === "fallback" && phase !== "fallback") return null;
                const state = index < here ? "done" : index === here ? "active" : "";
                return (
                  <li
                    key={item.key}
                    className={state}
                    data-phase={item.key}
                    data-phase-state={state || "pending"}
                  >
                    <span className="plan-ai-dot" aria-hidden="true">
                      {state === "done" ? "✓" : state === "active" ? "●" : "○"}
                    </span>
                    <span>{zh ? item.zh : item.en}</span>
                  </li>
                );
              })}
            </ol>
            <button
              type="button"
              className="plan-ai-cancel v8-outline-button"
              data-testid="plan-ai-cancel"
              onClick={cancel}
            >
              {zh ? "取消" : "Cancel"}
            </button>
          </div>
        )}

        {copy && (
          <div
            className={`plan-ai-result ${copy.tone}`}
            data-testid="plan-ai-result"
            data-result-status={result?.status ?? ""}
            data-result-tone={copy.tone}
            /* ORD-0251: `-1` is how this component knows "we could not tell" (indeterminate baseline or
               an unread re-count).  That is a real state; it is not a number of plans, and publishing it
               on an attribute a gate reads made "unknowable" indistinguishable from a count. */
            data-plan-count={
              result?.planCount !== undefined && result.planCount >= 0 ? result.planCount : "unknown"
            }
            data-new-plan-ids={(result?.newPlanIds ?? []).join(",")}
            role="status"
          >
            <b>{copy.title}</b>
            <p>{copy.body}</p>
            {(result?.failureReason || result?.summary) && (
              <details className="plan-ai-detail">
                <summary data-testid="plan-ai-detail-toggle">
                  {zh ? "技术详情" : "Technical detail"}
                </summary>
                {result?.failureReason && (
                  <>
                    {/* ORD-0280: the label is chosen by who spoke, not by whichever branch ran.  A
                        server-sent sentence keeps 「服务器给出的原因」; anything this screen composed says
                        so, because an HTTP number we invented is not the backend's statement -- the
                        screen used to print our guess under the attribution label on all three refusal
                        legs.  `data-reason-origin` is here so a gate can read the same fact the
                        traveller reads instead of parsing prose. */}
                    <span
                      className="plan-ai-detail-label"
                      data-testid="plan-ai-detail-kind"
                      data-reason-origin={result.failureReason.from}
                    >
                      {result.failureReason.from === "server"
                        ? zh
                          ? "服务器给出的原因"
                          : "Reason the server gave"
                        : zh
                          ? "这台设备自己的读数（服务器没给句子）"
                          : "This device's own reading (the server sent no sentence)"}
                    </span>
                    <code data-testid="plan-ai-reason">{result.failureReason.text}</code>
                  </>
                )}
                {result?.summary && (
                  <>
                    {/* ORD-0240: this is the model's own sentence, not this screen's wording.  It is
                        neither translated nor added to a dictionary -- dynamic prose put through a
                        static table would be claimed as "already translated", which is the hole this
                        order closes.  Unlabelled in the main flow, a Chinese traveller read it as our
                        promise. */}
                    <span className="plan-ai-detail-label" data-testid="plan-ai-model-label">
                      {zh ? "模型原始输出（未翻译，不代表本界面的结论）" : "Model's own words (not translated, not this screen's conclusion)"}
                    </span>
                    <code data-testid="plan-ai-model-output">{result.summary}</code>
                  </>
                )}
              </details>
            )}
            {/* A refusal the traveller cannot act on is a dead end, so the reason carries exactly one
                next step -- and it is the step the server's own code earns, not a generic "try again". */}
            {copy?.action === "another-city" && onChooseAnotherCity && (
              <button
                type="button"
                className="v8-primary-button plan-ai-next-step"
                data-testid="plan-ai-next-step"
                data-next-step="another-city"
                onClick={() => {
                  onClose();
                  onChooseAnotherCity();
                }}
              >
                {zh ? "换一座有数据的城市" : "Try a city we have data for"}
              </button>
            )}
            {copy?.action === "retry" && (
              <button
                type="button"
                className="v8-primary-button plan-ai-next-step"
                data-testid="plan-ai-next-step"
                data-next-step="retry"
                onClick={() => void submit()}
              >
                {zh ? "照原话再试一次" : "Try again with the same words"}
              </button>
            )}
          </div>
        )}

        </div>

        <div className="plan-ai-actions">
          <button
            type="button"
            className="v8-outline-button"
            data-testid="plan-ai-dismiss"
            onClick={() => {
              abortRef.current?.abort();
              onClose();
            }}
          >
            {busy ? (zh ? "取消并关闭" : "Cancel & close") : zh ? "稍后" : "Later"}
          </button>
          <button
            type="button"
            className="v8-primary-button"
            data-testid="plan-ai-submit"
            /* Busy is a real `disabled` (the control means something else while a run is going).  A
               missing request is `aria-disabled` instead -- the ORD-0066 (甲) shape -- so the press
               reaches submit() and the traveller reads why it did not advance, instead of tapping a
               dead surface.  The existing `[aria-disabled="true"]` rule keeps it looking unwalkable. */
            disabled={busy}
            aria-disabled={text.trim().length < REQUEST_MIN_LENGTH || undefined}
            onClick={() => void submit()}
          >
            {busy ? (zh ? "规划中…" : "Planning…") : zh ? "开始规划" : "Plan my trip"}
          </button>
        </div>
      </section>
    </div>
  );
}
