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

/** The phases this component itself drives, in the order it can enter them. */
type PhaseKey = "baseline" | "request" | "verify" | "fallback";

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

const EXAMPLES = [
  {
    zh: "我和朋友两个人去厦门，想轻松一点，想去鼓浪屿、环岛路，想吃沙茶面和海鲜，不想太赶，也想找性价比高的酒店。",
    en: "Two of us in Xiamen, relaxed pace, Gulangyu and the Ring Road, local seafood, and a good-value hotel.",
  },
  {
    zh: "带爸妈去厦门三天，不要走太多路，下午要有休息时间，酒店要靠近地铁。",
    en: "Three days in Xiamen with my parents, not much walking, an afternoon rest, hotel near the metro.",
  },
];

/** Map internal mission status -> traveller language. */
function statusCopy(
  status: string,
  zh: boolean,
  planCount = 0,
): { title: string; body: string; tone: "ok" | "warn" | "busy" | "neutral" } {
  const s = (status || "").toUpperCase();
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
        ? "你的需求已理解，但这次没能排出可行方案。你的行程没有被改动，可以调整预算或换个说法再试。"
        : "Your request was understood, but no feasible plan came out. Your trip is unchanged — adjust the budget or rephrase and try again.",
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
}: {
  journeyId: string;
  cityCode?: string;
  onClose: () => void;
  onPlanned?: () => void;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<PhaseKey | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [aiState, setAiState] = useState<"checking" | "ready" | "unconfigured" | "unknown">(
    "checking",
  );
  const [result, setResult] = useState<null | {
    status: string;
    failureReason: string | null;
    summary: string | null;
    planCount?: number;
    newPlanIds?: string[];
  }>(null);
  const abortRef = useRef<AbortController | null>(null);
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
    if (command.length < 8) return;
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
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ command }),
        signal,
      });
      const body = await response.json().catch(() => null);
      const mission = body?.mission ?? null;
      if (!response.ok) {
        /* A refused or failed request is reported as what it is.  Letting the
           fallback re-plan run here would let a synthetic plan answer for a request
           the backend explicitly rejected. */
        setResult({
          status: `HTTP_${response.status}`,
          failureReason:
            (typeof body?.detail === "string" ? body.detail : null) ??
            (typeof body?.error?.message === "string" ? body.error.message : null) ??
            `HTTP ${response.status}`,
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
      if (baseline !== null && planCount === 0) {
        enter("fallback");
        try {
          const placesResponse = await fetch(
            `/api/v1/places?city_code=${encodeURIComponent(cityCode)}`,
            { headers: { Accept: "application/json" }, signal },
          );
          const places = placesResponse.ok ? await placesResponse.json() : [];
          const ids = Array.isArray(places)
            ? places.map((item: { id?: string }) => item?.id).filter(Boolean).slice(0, 8)
            : [];
          if (ids.length >= 2) {
            const generate = await fetch(
              `/api/v1/journeys/${journeyId}/plans/generate`,
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ place_ids: ids, candidate_count: 3 }),
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
            }
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
      } else if (missionStatus.includes("EXTERNAL") || missionStatus.includes("SKIPPED")) {
        status = "SKIPPED_EXTERNAL_DEPENDENCY";
      } else {
        // Compiled, but produced nothing the traveller can use.
        status = "NO_PLANS_PRODUCED";
      }
      setResult({
        status,
        newPlanIds,
        failureReason: mission?.failure_reason ?? null,
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
        setResult({ status: "NETWORK", failureReason: null, summary: null });
      }
    } finally {
      abortRef.current = null;
      setBusy(false);
      setPhase(null);
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
  };

  const copy = result ? statusCopy(result.status, zh, result.planCount ?? 0) : null;
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

        <label className="plan-ai-field">
          <span className="v8-sr-only">{zh ? "旅行需求" : "Trip request"}</span>
          <textarea
            data-testid="plan-ai-input"
            rows={5}
            value={text}
            disabled={busy}
            onChange={(event) => setText(event.target.value)}
            placeholder={zh ? EXAMPLES[0].zh : EXAMPLES[0].en}
          />
        </label>

        <div className="plan-ai-examples">
          {EXAMPLES.map((item) => (
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
            data-plan-count={result?.planCount ?? 0}
            data-new-plan-ids={(result?.newPlanIds ?? []).join(",")}
            role="status"
          >
            <b>{copy.title}</b>
            <p>{copy.body}</p>
            {result?.failureReason && (
              <details className="plan-ai-detail">
                <summary data-testid="plan-ai-detail-toggle">
                  {zh ? "技术详情" : "Technical detail"}
                </summary>
                <code data-testid="plan-ai-reason">{result.failureReason}</code>
              </details>
            )}
            {result?.summary && !result.failureReason && <p className="plan-ai-summary">{result.summary}</p>}
          </div>
        )}

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
            disabled={busy || text.trim().length < 8}
            onClick={() => void submit()}
          >
            {busy ? (zh ? "规划中…" : "Planning…") : zh ? "开始规划" : "Plan my trip"}
          </button>
        </div>
      </section>
    </div>
  );
}
