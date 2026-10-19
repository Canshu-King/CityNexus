/* Issue #31 C：「AI 工作动态」这块屏自己的词表。
 *
 * 为什么单开一份（而不是往 `LocaleContext.tsx` 里塞）：那张字典正被别的车道同时改，
 * 号令者的收块规则是按文件摘取（见 `src/i18n/mapPanelCopy.ts` 开头的同一条理由）。
 * 这里每一句都必须要么是当前屏幕上真实的服务器事实，要么是"服务器没说"的那种说法——
 * 面板里绝不允许出现编出来的进度。
 */

export type AgentWorkCopyKey =
  | "entryToday"
  | "entryTrip"
  | "sheetTitle"
  | "sheetLede"
  | "close"
  | "loading"
  | "noRecord"
  | "noRecordHint"
  | "aiStateLabel"
  | "runtimeLabel"
  | "gatewayLabel"
  | "gatewayOn"
  | "gatewayOff"
  | "lastEventLabel"
  | "noLastEvent"
  | "unread"
  | "retry"
  | "sectionAgent"
  | "sectionTrip"
  | "noRun"
  | "noRunHint"
  | "techDetails"
  | "unlistedEvent"
  | "runtimeNamed"
  | "sourceLabel"
  | "sourceAudit"
  | "railAria"
  | "derivedRule"
  | "stateConfiguredUnverified"
  | "stateNotConfigured"
  | "stateDisabledByOps"
  | "stateProviderRefused";

const TABLE: Record<"en" | "zh", Record<AgentWorkCopyKey, string>> = {
  en: {
    entryToday: "AI work activity",
    entryTrip: "What the AI did on this trip",
    sheetTitle: "What the AI has done on this trip",
    sheetLede: "Everything below is read from this server, for this trip.",
    close: "Close",
    loading: "Reading the server's record for this trip…",
    noRecord: "No AI work recorded on this trip yet",
    noRecordHint: "The server returned zero events for this journey. Ask the assistant something, and the first line will appear here.",
    aiStateLabel: "AI availability",
    runtimeLabel: "Runtime named by the server",
    gatewayLabel: "Native gateway",
    gatewayOn: "reachable",
    gatewayOff: "not reachable",
    lastEventLabel: "Last recorded moment",
    noLastEvent: "none",
    unread: "this read did not come back",
    retry: "Read again",
    sectionAgent: "What the AI and its tools actually did",
    sectionTrip: "Trip system activity",
    noRun: "No real AI run yet",
    noRunHint: "The server has not confirmed a run for this trip.",
    techDetails: "Technical details",
    unlistedEvent: "an event with no wording for it yet",
    runtimeNamed: "named by the server itself",
    sourceLabel: "Where these rows come from",
    sourceAudit: "the server's own audit feed",
    railAria: "AI work events for this trip",
    derivedRule: "Rows come from the audit feed; the mark on each row is read off that row's own event type.",
    stateConfiguredUnverified: "configured, not yet verified by this server",
    stateNotConfigured: "not configured on this deployment",
    stateDisabledByOps: "disabled by operations",
    stateProviderRefused: "the model provider refused",
  },
  zh: {
    entryToday: "AI 工作动态",
    entryTrip: "AI 工作动态",
    sheetTitle: "这一趟上 AI 做过什么",
    sheetLede: "下面每一行都来自这台服务器关于这一趟的记录。",
    close: "关闭",
    loading: "正在读这台服务器上关于这一趟的记录…",
    noRecord: "这一趟还没有 AI 工作记录",
    noRecordHint: "服务器对这一趟回了零条事件。去问一句，第一条就会落在这里。",
    aiStateLabel: "AI 可用性",
    runtimeLabel: "服务器自报的运行身份",
    gatewayLabel: "原生网关",
    gatewayOn: "可达",
    gatewayOff: "不可达",
    lastEventLabel: "最近一条的时刻",
    noLastEvent: "无",
    unread: "这一路没读回来",
    retry: "再查一次",
    sectionAgent: "AI 与工具真的做过的事",
    sectionTrip: "行程系统自己的动态",
    noRun: "暂无真实运行",
    noRunHint: "服务器还没有确证过一次运行。",
    techDetails: "技术详情",
    unlistedEvent: "这一行还没有对应说法",
    runtimeNamed: "由服务器自己报出（见上一格）",
    sourceLabel: "这些行是从哪来的",
    sourceAudit: "服务器自己的审计事件流",
    railAria: "这一趟的 AI 工作事件",
    derivedRule: "行来自审计事件流；每行那个标记，读的是那一行自己的事件类型。",
    stateConfiguredUnverified: "已配置，本机服务器尚未验证",
    stateNotConfigured: "这个部署未配置",
    stateDisabledByOps: "被运维停用",
    stateProviderRefused: "模型侧拒绝",
  },
};

/** `zh` 由调用方从 locale 判出来，和 `mapCopy` 一样：一个函数，一张表，不写死在产品码里。 */
export function agentWorkCopy(locale: string, key: AgentWorkCopyKey): string {
  return TABLE[locale.startsWith("zh") ? "zh" : "en"][key];
}

/**
 * 服务器给的 `ai_state` 词 → 屏幕上的说法。词表外的一律回 `null`：
 * 这时面板显示服务器原词本身（在 `data-ai-state` 上），而不是猜一个中文说法。
 */
export function aiStateGloss(
  locale: string,
  word: string | null | undefined,
): AgentWorkCopyKey | null {
  switch (word) {
    case "CONFIGURED_UNVERIFIED":
      return "stateConfiguredUnverified";
    case "NOT_CONFIGURED":
      return "stateNotConfigured";
    case "DISABLED_BY_OPS":
      return "stateDisabledByOps";
    case "PROVIDER_REFUSED":
      return "stateProviderRefused";
    default:
      return null;
  }
}
