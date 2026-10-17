/* Issue #31 C：「AI 工作动态」——一块只讲服务器事实的面板。
 *
 * 它存在的理由：Today 与行程页原先都没有一个能看见"AI 这一趟到底做了什么"的地方。
 * `CopilotDock` 里那条原生时间线要你先问一句话才出现（run id 是回答里带回来的），
 * 所以不问就什么都看不见；而 `agent-feed` 这条门（`GET /api/v1/journeys/{id}/agent-feed`，
 * 服务器自己把审计表投出来）早就存在，却没有入口。这一格就是那个入口。
 *
 * 三条不许越过的线：
 *  1. 每一行都必须来自 `agent-feed` 的事件或 `agent/runtime-status` 的字段。服务器回 0 条，
 *     屏上就是"这一趟还没有 AI 工作记录"，不写"正在分析"、不排假步骤；
 *  2. 行上的标记（done/active/failed）只按那一行自己的 `event_type` 词根判（见 `markOf`），
 *     判不出就是 `done` 以外都不给——宁可少一个色，不要编一个状态；
 *  3. 读不到就按 ORD-0101/R14 那套归属把"是谁拒的、拒在哪一层"说出来，并留一颗真的再查一次。
 */
import { useCallback, useEffect, useState } from "react";
import {
  cityNexusApi,
  type AgentFeedEntry,
  type AgentRuntimeStatus,
} from "../../api/citynexus";
import { AgentRunRail, type AgentRailStep } from "./AgentRunRail";
import { classifyReadFailure, copyFor, type Attribution } from "../../lib/failureAttribution";
import { useLocale } from "../../i18n/LocaleContext";
import { agentWorkCopy, aiStateGloss } from "../../i18n/agentWorkFeedCopy";
import "./agentWorkFeed.css";

type FeedState = "loading" | "ready" | "refused";

/**
 * 行标记的唯一判据：那一行自己写的事件类型。
 *
 * `requested` / `started` 只可能是"进行到这一步"，`failed` / `refused` / `rejected` 才是失败，
 * 其余（completed、validated、corroborated、created、resolved…）是过去的事实。
 * 词根表在这里，是为了让 e2e 能用真事件去钉它，而不是钉一个组件里的私有形状。
 */
export function markOf(eventType: string): AgentRailStep["status"] {
  const word = eventType.toLowerCase();
  if (/(failed|refused|rejected|denied|blocked)/.test(word)) return "failed";
  if (/(approval|required)/.test(word)) return "approval";
  if (/(requested|started|started_at|begin|pending)/.test(word)) return "active";
  return "done";
}

/**
 * 入口自己带面板：`hub-secondary-actions` 与行程页那两块的分发器都是别的车道在改的文件，
 * 从壳里往下穿一条 `onOpenAgentWork` 回调要动两处签名与一份注册表状态，而这一格要的只是
 * "看得见、点得开、点开之后是服务器的事"。所以按钮与它展开的面板是一体的，宿主页只需要摆一个 `<AgentWorkEntry/>`。
 */
export function AgentWorkEntry({
  journeyId,
  surface,
}: {
  journeyId: string;
  surface: "today" | "trip";
}) {
  const { locale } = useLocale();
  const [open, setOpen] = useState(false);
  return (
    <div className="cn-agent-work-entry" data-testid={`agent-work-entry-${surface}`}>
      <button
        type="button"
        className="v8-quiet-button"
        data-testid={surface === "today" ? "hub-ai-work" : "trip-ai-work"}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {agentWorkCopy(locale, surface === "today" ? "entryToday" : "entryTrip")}
      </button>
      {open ? (
        <AgentWorkFeedPanel journeyId={journeyId} compact={surface === "trip"} />
      ) : null}
    </div>
  );
}

/** 服务器给的时间是 ISO；屏上不铺原始串（ORD-0423 那条同一件事）。 */
function moment(raw: string, zh: boolean): string {
  const parsed = Date.parse(raw);
  if (Number.isNaN(parsed)) return raw;
  return new Intl.DateTimeFormat(zh ? "zh-CN" : "en-GB", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(parsed));
}

export function AgentWorkFeedPanel({
  journeyId,
  limit = 30,
  compact = false,
}: {
  journeyId: string;
  limit?: number;
  compact?: boolean;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const copy = (key: Parameters<typeof agentWorkCopy>[1]) => agentWorkCopy(locale, key);
  const [state, setState] = useState<FeedState>("loading");
  const [events, setEvents] = useState<AgentFeedEntry[]>([]);
  const [source, setSource] = useState<string | null>(null);
  const [runtime, setRuntime] = useState<AgentRuntimeStatus | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [facts, setFacts] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  /* 依赖里不能有 `copy`：那种每渲染新建的闭包会把 `read` 变成新函数，`useEffect` 就一圈一圈
   * 自己追自己。词表函数本身是模块级的，依赖只写真正会变的事实：哪一趟、哪种语言。 */
  const read = useCallback(async () => {
    setState("loading");
    setProblem(null);
    const [feed, status] = await Promise.allSettled([
      cityNexusApi.getAgentFeed(journeyId, limit),
      cityNexusApi.getAgentRuntimeStatus(),
    ]);
    if (feed.status === "rejected") {
      const attribution: Attribution = classifyReadFailure(feed.reason);
      setFacts(attribution.telemetry);
      setProblem(
        copyFor(attribution, locale.startsWith("zh")).body ?? agentWorkCopy(locale, "retry"),
      );
      setState("refused");
      return;
    }
    setEvents(Array.isArray(feed.value.events) ? feed.value.events : []);
    setSource(typeof feed.value.source === "string" ? feed.value.source : null);
    // 运行状态读不到不算这格的失败：事件已经拿到了，就把拿到的说清楚，那一行单独标"读不到"。
    setRuntime(status.status === "fulfilled" ? status.value : null);
    setState("ready");
  }, [journeyId, limit, locale]);

  useEffect(() => {
    void read();
  }, [read, attempt]);

  const steps: AgentRailStep[] = events.slice(-12).map((item) => ({
    id: item.id,
    // `summary` 是服务器写的句子；没有就退回它写的事件类型，绝不拼一句"完成了什么"。
    label: item.summary && item.summary.trim() ? item.summary : item.event_type,
    status: markOf(item.event_type),
    runMeta: `${moment(item.timestamp, zh)}${item.tool ? ` · ${item.tool}` : ""}`,
  }));

  const gloss = aiStateGloss(locale, runtime?.ai_state);
  const last = events.length ? events[events.length - 1] : null;

  return (
    <section
      className={`cn-agent-work${compact ? " compact" : ""}`}
      data-testid="agent-work-feed"
      data-feed-state={state}
      data-feed-events={String(events.length)}
      data-feed-source={source ?? "unknown"}
      data-attempt={String(attempt)}
      {...(facts ? { "data-attribution": facts } : {})}
    >
      <header className="cn-agent-work-head">
        <div>
          <b>{copy("sheetTitle")}</b>
          <small>{copy("derivedRule")}</small>
        </div>
        <button
          type="button"
          className="v8-quiet-button"
          data-testid="agent-work-retry"
          onClick={() => setAttempt((n) => n + 1)}
        >
          {copy("retry")}
        </button>
      </header>

      {state === "loading" ? (
        <p className="cn-agent-work-state" data-testid="agent-work-loading">
          {copy("loading")}
        </p>
      ) : null}

      {state === "refused" ? (
        <p className="v8-message error" data-testid="agent-work-refused" {...(facts ? { "data-attribution": facts } : {})}>
          {problem}
        </p>
      ) : null}

      {state === "ready" ? (
        <>
          <dl className="cn-agent-work-facts" data-testid="agent-work-facts">
            <div>
              <dt>{copy("aiStateLabel")}</dt>
              <dd data-ai-state={runtime?.ai_state ?? "NOT_READ"}>
                {runtime
                  ? gloss
                    ? copy(gloss)
                    : String(runtime.ai_state ?? "—")
                  : copy("unread")}
              </dd>
            </div>
            <div>
              <dt>{copy("runtimeLabel")}</dt>
              <dd data-runtime-identity={runtime?.runtime_identity ?? "unread"}>
                {runtime?.runtime_identity ?? "—"}
              </dd>
            </div>
            <div>
              <dt>{copy("gatewayLabel")}</dt>
              <dd
                data-gateway-runs={String(Boolean(runtime?.hermes_native_gateway?.runs))}
                data-gateway-events={String(Boolean(runtime?.hermes_native_gateway?.events))}
              >
                {runtime?.hermes_native_gateway
                  ? runtime.hermes_native_gateway.reachable
                    ? copy("gatewayOn")
                    : copy("gatewayOff")
                  : "—"}
              </dd>
            </div>
            <div>
              <dt>{copy("lastEventLabel")}</dt>
              <dd data-testid="agent-work-last-moment">
                {last ? moment(last.timestamp, zh) : copy("noLastEvent")}
              </dd>
            </div>
          </dl>

          {steps.length ? (
            <AgentRunRail steps={steps} />
          ) : (
            <p className="cn-agent-work-empty" data-testid="agent-work-empty">
              <b>{copy("noRecord")}</b>
              <small>{copy("noRecordHint")}</small>
            </p>
          )}
        </>
      ) : null}
    </section>
  );
}
