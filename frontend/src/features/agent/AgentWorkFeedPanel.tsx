/* Issue #31 C：「AI 工作动态」——一块只讲服务器事实的面板。
 *
 * 它存在的理由：Today 与行程页原先都没有一个能看见"AI 这一趟到底做了什么"的地方。
 * `CopilotDock` 里那条原生时间线要你先问一句话才出现（run id 是回答里带回来的），
 * 所以不问就什么都看不见；而 `agent-feed` 这条门（`GET /api/v1/journeys/{id}/agent-feed`，
 * 服务器自己把审计表投出来）早就存在，却没有入口。这一格就是那个入口。
 *
 * GPT 复核 P1-TRUTH 把一件事点出来了，这一版照做：`agent-feed` 是**审计事件流**，
 * 里面既有 AI 与工具的事件，也有"人建了行程"这种行程系统自己的事件。把 `Journey.created`
 * 摆在「这一趟上 AI 做过什么」下面，等于把人的动作暗示成 AI 的工作。所以这里分成两段：
 * 上面只放经服务器确证的 Agent／工具事件，没有就明写「暂无真实运行」；
 * 行程系统自己的事件另起一段，标题不冒充 AI。
 *
 * 同一份复核还点了落地门的 `CODES_ON_SCREEN` 那一类：人读的位置不铺大写内部字段。
 * 每台机器码都收在 `data-*` 与那块可展开的「技术详情」里，屏幕正文一律中文说法。
 *
 * 三条不许越过的线：
 *  1. 每一行都必须来自 `agent-feed` 的事件或 `agent/runtime-status` 的字段；服务器回 0 条，
 *     屏上就是"还没有记录"，不写"正在分析"、不排假步骤；
 *  2. 行上的标记只按那一行自己的 `event_type` 词根判（见 `markOf`），判不出就不给状态；
 *  3. 读不到走全应用同一套归属（ORD-0101/R14），并留一颗真的再查一次。
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
import { agentEventGloss, agentWorkCopy, aiStateGloss } from "../../i18n/agentWorkFeedCopy";
import "./agentWorkFeed.css";

type FeedState = "loading" | "ready" | "refused";

/** 哪些事件是"AI／工具真的动过手"——词根取自服务器自己写的事件类型。 */
const AGENT_WORDS = /(agent|tool|run|approval|replan|guardian|gateway|hermes|proposal)/i;

/** 现在挂着几块 AI 工作动态面板：0 表示这一屏没有东西要那颗药丸让位。 */
let SURFACES = 0;

/**
 * 行标记的唯一判据：那一行自己写的事件类型。
 *
 * `requested` / `started` 只可能是"进行到这一步"，`failed` / `refused` / `rejected` 才是失败，
 * 其余（completed、validated、corroborated、created、resolved…）是过去的事实。
 */
export function markOf(eventType: string): AgentRailStep["status"] {
  const word = eventType.toLowerCase();
  if (/(failed|refused|rejected|denied|blocked)/.test(word)) return "failed";
  if (/(approval|required)/.test(word)) return "approval";
  if (/(requested|started|begin|pending)/.test(word)) return "active";
  return "done";
}

/**
 * 审计行没带摘要时，服务器的投影把事件类型本身当摘要发回来（`journey.created` → "Journey.created"）。
 * 这一格下面那份行程动态走词表，只有这条轨道优先信 `summary`，于是同一件事在一块面板里两种说法，
 * 中文屏上还混进一串英文散文。
 *
 * 判的是形状：按服务器那条派生规则逐字比对，认出来就当我们没有这句，交给词表；真写过人话的行原样保留。
 */
function humanSummary(eventType: string, summary: string | null | undefined): string | null {
  const text = (summary ?? "").trim();
  if (!text) return null;
  const derived = [eventType.replace(/_/g, " "), eventType];
  if (derived.some((shape) => shape.toLowerCase() === text.toLowerCase())) return null;
  return text;
}

/** 服务器写的事件类型 → 人读的一句话。词表外的一律回 null，屏上就不假装看懂了。 */
function eventGloss(locale: string, eventType: string): string | null {
  const key = agentEventGloss(locale, eventType);
  return key ? agentWorkCopy(locale, key) : null;
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

/**
 * 入口自己带面板：`hub-secondary-actions` 与行程页那两块的分发器都是别的车道在改的文件，
 * 从壳里往下穿一条回调要动两处签名与一份注册表状态，而这一格要的只是"看得见、点得开、
 * 点开之后是服务器的事"。所以按钮与它展开的面板是一体的，宿主页只需要摆一个 `<AgentWorkEntry/>`。
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
  const [runtimeReadable, setRuntimeReadable] = useState(true);
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
    // 运行状态读不到不算这格的失败：事件已经拿到了，就把拿到的说清楚，那一行单独标"没读回来"。
    setRuntime(status.status === "fulfilled" ? status.value : null);
    setRuntimeReadable(status.status === "fulfilled");
    setState("ready");
  }, [journeyId, limit, locale]);

  useEffect(() => {
    void read();
  }, [read, attempt]);

  /* 这一格是全宽、而且比一屏高：那颗药丸缩成边条也仍然压在面板的行上（390x844 现读——面板
   * 17,473 起 356x398，让位后的边条 215,706 的 165x54，两个盒子在视口里真的相交）。既然
   * 390 宽的屏上没有"面板之外"的位置可停，打开的这一块就把药丸整枚请出这一屏，关掉再回来。
   * 记数而不是记布尔：Today 与行程页可能同时挂着两块面板。 */
  useEffect(() => {
    SURFACES += 1;
    const root = document.documentElement;
    root.dataset.agentWorkSurface = String(SURFACES);
    return () => {
      SURFACES = Math.max(0, SURFACES - 1);
      if (SURFACES === 0) delete root.dataset.agentWorkSurface;
      else root.dataset.agentWorkSurface = String(SURFACES);
    };
  }, []);

  const agentEvents = events.filter((item) => AGENT_WORDS.test(item.event_type));
  const tripEvents = events.filter((item) => !AGENT_WORDS.test(item.event_type));

  const rail = (rows: AgentFeedEntry[]): AgentRailStep[] =>
    rows.slice(-12).map((item) => ({
      id: item.id,
      // 服务器写了人话就用服务器的人话；没写就用它的类型查词表；词表也没有就不铺裸码。
      label:
        humanSummary(item.event_type, item.summary) ||
        eventGloss(locale, item.event_type) ||
        agentWorkCopy(locale, "unlistedEvent"),
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
      data-feed-agent-events={String(agentEvents.length)}
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
        <p className="v8-message error" data-testid="agent-work-refused">
          {problem}
        </p>
      ) : null}

      {state === "ready" ? (
        <>
          <h3 className="cn-agent-work-section" data-testid="agent-work-agent-heading">
            {copy("sectionAgent")}
          </h3>
          {agentEvents.length ? (
            <AgentRunRail steps={rail(agentEvents)} />
          ) : (
            <p className="cn-agent-work-empty" data-testid="agent-work-no-run">
              <b>{copy("noRun")}</b>
              <small>{copy("noRunHint")}</small>
            </p>
          )}

          {tripEvents.length ? (
            <>
              <h3 className="cn-agent-work-section" data-testid="agent-work-trip-heading">
                {copy("sectionTrip")}
              </h3>
              <ul className="cn-agent-work-trip" data-testid="agent-work-trip-events">
                {tripEvents.slice(-12).map((item) => (
                  <li key={item.id} data-event-type={item.event_type}>
                    <b>{eventGloss(locale, item.event_type) ?? copy("unlistedEvent")}</b>
                    <span>{moment(item.timestamp, zh)}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}

          <details className="cn-agent-work-tech" data-testid="agent-work-tech">
            <summary>{copy("techDetails")}</summary>
            <dl className="cn-agent-work-facts" data-testid="agent-work-facts">
              <div>
                <dt>{copy("aiStateLabel")}</dt>
                <dd data-ai-state={runtime?.ai_state ?? "NOT_READ"}>
                  {runtime ? (gloss ? copy(gloss) : copy("unlistedEvent")) : copy("unread")}
                </dd>
              </div>
              <div>
                <dt>{copy("runtimeLabel")}</dt>
                <dd data-runtime-identity={runtime?.runtime_identity ?? "unread"}>
                  {runtimeReadable ? copy("runtimeNamed") : copy("unread")}
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
                    : copy("unread")}
                </dd>
              </div>
              <div>
                <dt>{copy("lastEventLabel")}</dt>
                <dd data-testid="agent-work-last-moment">
                  {last ? moment(last.timestamp, zh) : copy("noLastEvent")}
                </dd>
              </div>
              <div>
                <dt>{copy("sourceLabel")}</dt>
                <dd data-feed-source-raw={source ?? "unknown"}>{copy("sourceAudit")}</dd>
              </div>
            </dl>
          </details>
        </>
      ) : null}
    </section>
  );
}
