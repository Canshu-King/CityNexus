import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { Activity, AlertCircle, Check, CircleDashed, Send, Wrench, X } from "lucide-react";
import { CityNexusApiError, cityNexusApi, type NativeRuntimeEvent } from "../../api/citynexus";
import { readTravelerBearer, subscribeTravelerBearer } from "../../lib/travelerSession";
import { mergeNativeEvents, statusForNativeEvent, useNativeHermesTimeline, type NativeHermesRun as NativeHermesRunData } from "../../features/agent/nativeHermesTimeline";
import "./MobileHermesRun.css";

const TOOL_LABELS: Record<string, string> = {
  inspect_journey: "检查当前行程",
  inspect_twin: "核对行程事实",
  list_replans: "查看调整方案与受保护安排",
  search_city_services: "搜索地点与服务",
  request_replan: "请求生成调整建议",
  accept_replan: "接受调整方案",
  replace_activity: "替换一项活动",
  reschedule_activity: "调整活动时间",
  create_booking: "创建预订",
  cancel_refundable_booking: "取消可退款预订",
  request_commitment_change: "申请修改受保护安排",
};

const EVENT_LABELS: Record<string, string> = {
  "semantic.interpreted": "已理解你的需求",
  "mission.planned": "已形成执行计划",
  "run.started": "Hermes 已开始处理",
  "gateway.checked": "已通过行程规则检查",
  "guardian.checked": "已核对受保护安排",
  "proposal.created": "已生成方案建议",
  "approval.required": "需要你确认下一步",
  "run.completed": "Hermes 已完成本次运行",
  "run.failed": "Hermes 本次运行失败",
  "run.stopped": "Hermes 本次运行已停止",
};

const SAFE_TOOL_ERROR_MESSAGES: Record<string, string> = {
  MALFORMED_TOOL_ARGUMENTS: "参数格式不正确",
  SEARCH_BATCH_LIMIT: "搜索数量已达到本次上限",
  SEARCH_SATURATION: "搜索结果已足够",
  NO_ACTIONABLE_EVENT: "没有可执行的地点更新",
};

const RUN_MILESTONE_EVENTS = new Set(["run.started", "run.completed", "run.failed", "run.stopped"]);

type RequestState = "idle" | "sending" | "ready" | "unauthorized" | "error";
type RestoreState = "idle" | "checking" | "empty" | "available" | "failed";

function terminalRun(status: string) {
  return /^(completed|succeeded|failed|error|stopped|cancelled|canceled)$/i.test(status);
}

function approvalStateForEvent(event: NativeRuntimeEvent): "pending" | "approved" | "closed" | "unknown" {
  const status = String(event.approval_status ?? "").trim().toUpperCase();
  if (status === "PENDING" || status === "APPROVAL_REQUIRED") return "pending";
  if (status === "APPROVED" || status === "CONSUMED") return "approved";
  if (["REJECTED", "EXPIRED", "CANCELLED", "CANCELED", "REVOKED"].includes(status)) return "closed";
  return "unknown";
}

function pendingApprovalEvent(events: NativeRuntimeEvent[]) {
  const seen = new Set<string>();
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.event_type !== "approval.required" || !event.approval_id || seen.has(event.approval_id)) continue;
    seen.add(event.approval_id);
    if (approvalStateForEvent(event) === "pending") return event;
  }
  return null;
}

function statusForMobileEvent(event: NativeRuntimeEvent) {
  if (event.event_type !== "approval.required") return statusForNativeEvent(event);
  const approvalState = approvalStateForEvent(event);
  if (approvalState === "pending") return "approval";
  if (approvalState === "approved") return "done";
  if (approvalState === "closed") return "failed";
  return "active";
}

function safeEventLabel(event: NativeRuntimeEvent) {
  if (event.event_type === "approval.required") {
    const approvalState = approvalStateForEvent(event);
    if (approvalState === "pending") return "等待你确认";
    if (approvalState === "approved") return "操作已获批准";
    if (approvalState === "closed") return "审批已结束";
    return "审批状态待确认";
  }
  if (event.tool_name) {
    const tool = TOOL_LABELS[event.tool_name] ?? "执行一个行程工具步骤";
    if (event.event_type === "tool.started") return `正在${tool}`;
    if (event.event_type === "tool.completed") return `${tool}：已完成`;
    if (event.event_type === "tool.failed") return `${tool}：未完成`;
  }
  return EVENT_LABELS[event.event_type] ?? "收到一条 Hermes 运行事件";
}

function safeToolErrorMessage(event: NativeRuntimeEvent) {
  if (event.event_type !== "tool.failed") return null;
  const summary = event.result_summary;
  if (!summary || typeof summary !== "object" || Array.isArray(summary)) return null;
  const code = summary.error_code;
  return typeof code === "string" ? SAFE_TOOL_ERROR_MESSAGES[code] ?? null : null;
}

function safeToolName(value: string | null) {
  const name = value?.trim() ?? "";
  return /^[a-zA-Z][a-zA-Z0-9_.-]{0,63}$/.test(name) ? name : null;
}

function eventTime(value: NativeRuntimeEvent["timestamp"]) {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const parsed = typeof value === "number" ? value : Date.parse(value);
  if (!Number.isFinite(parsed)) return null;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(parsed);
}

function eventDuration(value: NativeRuntimeEvent["duration_ms"]) {
  if (value == null) return null;
  const milliseconds = Number(value);
  if (!Number.isFinite(milliseconds) || milliseconds < 0) return null;
  if (milliseconds < 1000) return `${Math.round(milliseconds)} 毫秒`;
  const seconds = milliseconds / 1000;
  return `${Number(seconds.toFixed(seconds >= 10 ? 0 : 1))} 秒`;
}

function stateText(
  status: string,
  connection: string,
  events: NativeRuntimeEvent[],
  stopState: "idle" | "sending" | "requested" | "failed" = "idle",
) {
  if (/^(completed|succeeded)$/i.test(status)) return "已完成";
  if (/^(failed|error)$/i.test(status)) return "运行失败";
  if (/^(stopped|cancelled|canceled)$/i.test(status)) return "已停止";
  if (stopState === "sending") return "正在发送停止请求";
  if (stopState === "requested") return "停止请求已提交，等待状态更新";
  if (stopState === "failed") return "停止状态待确认";
  const latestApproval = [...events].reverse().find((event) => event.event_type === "approval.required");
  if (latestApproval) {
    const approvalState = approvalStateForEvent(latestApproval);
    if (approvalState === "pending") return "等待你确认";
    if (approvalState === "approved") return "操作已获批准";
    if (approvalState === "closed") return "审批已结束";
    return "审批状态待确认";
  }
  if (/^(queued|pending|created)$/i.test(status)) return "等待运行";
  if (/^(running|in_progress|started)$/i.test(status)) {
    return connection === "connecting" || connection === "retrying"
      ? "运行中 · 正在同步事件"
      : "正在运行";
  }
  if (connection === "connecting" || connection === "retrying") return "正在同步运行记录";
  const lastToolEvent = [...events].reverse().find((event) => event.event_type.startsWith("tool."));
  if (lastToolEvent?.event_type === "tool.started") return "正在处理行程请求";
  if (lastToolEvent) return "等待运行状态更新";
  if (connection === "unavailable") return "事件连接暂不可用";
  return "已启动，等待工具事件";
}

export function MobileHermesRun({ journeyId, visible, globalComposer = false }: { journeyId: string; visible: boolean; globalComposer?: boolean }) {
  const [prompt, setPrompt] = useState("请检查当前行程，发现问题时给出处理建议。");
  const [requestState, setRequestState] = useState<RequestState>(() => readTravelerBearer() ? "idle" : "unauthorized");
  const [restoreState, setRestoreState] = useState<RestoreState>("idle");
  const [run, setRun] = useState<NativeHermesRunData | null>(null);
  const [runJourneyId, setRunJourneyId] = useState<string | null>(null);
  const currentRun = runJourneyId === journeyId ? run : null;
  const [expanded, setExpanded] = useState(false);
  const [stopState, setStopState] = useState<"idle" | "sending" | "requested" | "failed">("idle");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [bearerEpoch, setBearerEpoch] = useState(0);
  const restoreEpoch = useRef(0);
  const timeline = useNativeHermesTimeline({ journeyId, run: currentRun, enabled: visible });
  const initialNativeEvents = useMemo(
    () => currentRun
      ? currentRun.initial_events?.filter((event) =>
        event.source === "HERMES_NATIVE" && event.run_id === currentRun.run_id,
      ) ?? []
      : [],
    [currentRun],
  );
  const actualEvents = useMemo(
    () => mergeNativeEvents(
      timeline.events.filter((event) => event.source === "HERMES_NATIVE"),
      initialNativeEvents,
    ),
    [timeline.events, initialNativeEvents],
  );
  const orderedEvents = actualEvents.filter((event) =>
    event.event_type.startsWith("tool.") || Object.hasOwn(EVENT_LABELS, event.event_type),
  );
  const pendingApproval = pendingApprovalEvent(actualEvents);
  const visibleEvents = orderedEvents.filter((event, index) =>
    index >= orderedEvents.length - 12 ||
    RUN_MILESTONE_EVENTS.has(event.event_type) ||
    event === pendingApproval,
  );
  const isFixtureRun = Boolean(currentRun?.provider_key && /^(test|fixture)(?:[_-]|$)/i.test(currentRun.provider_key));

  useEffect(() => {
    if (runJourneyId && runJourneyId !== journeyId) {
      setRun(null);
      setRunJourneyId(null);
      setExpanded(false);
      setStopState("idle");
    }
  }, [journeyId, runJourneyId]);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (expanded && currentRun && timeline.authState !== "unauthorized") {
      if (!dialog.open) dialog.showModal();
    } else if (dialog.open) {
      dialog.close();
    }
  }, [expanded, currentRun?.run_id, timeline.authState]);

  useEffect(() => {
    const startingBearer = readTravelerBearer();
    if (!startingBearer) {
      setRun(null);
      setRunJourneyId(null);
      setRestoreState("idle");
      setExpanded(false);
      setStopState("idle");
      setRequestState("unauthorized");
      return;
    }
    setRequestState((current) => current === "unauthorized" ? "idle" : current);
    const unsubscribe = subscribeTravelerBearer((bearer) => {
      if (bearer === startingBearer) return;
      setRun(null);
      setRunJourneyId(null);
      setRestoreState("idle");
      setExpanded(false);
      setStopState("idle");
      setFailure(null);
      setRequestState("unauthorized");
      setBearerEpoch((epoch) => epoch + 1);
    });
    return unsubscribe;
  }, [journeyId, bearerEpoch]);

  useEffect(() => {
    if (!visible) return;
    const startingBearer = readTravelerBearer();
    if (!startingBearer) return;
    const epoch = ++restoreEpoch.current;
    setRestoreState("checking");
    void cityNexusApi.getLatestNativeHermesRun(journeyId).then((response) => {
      if (restoreEpoch.current !== epoch || readTravelerBearer() !== startingBearer) return;
      if (response.journey_id !== journeyId) {
        setRun(null);
        setRunJourneyId(null);
        setExpanded(false);
        setRestoreState("failed");
        setFailure("服务器返回的运行记录与当前行程不匹配；已隐藏该记录。");
        return;
      }
      const latest = response.run;
      if (!latest || latest.runtime_identity !== "HERMES_NATIVE_MCP" || !latest.run_id) {
        setRun(null);
        setRunJourneyId(null);
        setExpanded(false);
        setRestoreState("empty");
        return;
      }
      setRun(latest);
      setRunJourneyId(journeyId);
      setRestoreState("available");
      setRequestState("ready");
      // Restored history stays collapsed; a fresh signed Copilot response
      // opens the trace drawer for the run that it just bound.
      setExpanded(false);
    }).catch((caught) => {
      if (restoreEpoch.current !== epoch || readTravelerBearer() !== startingBearer) return;
      if (caught instanceof CityNexusApiError && [401, 403, 404].includes(caught.status)) {
        setRun(null);
        setRunJourneyId(null);
        setExpanded(false);
        setRestoreState("failed");
        setRequestState("unauthorized");
        setFailure("无权读取这条运行记录。");
        return;
      }
      setRestoreState("failed");
      setFailure("上一条助手记录读取失败，请刷新重试。");
    });
    return () => {
      if (restoreEpoch.current === epoch) restoreEpoch.current += 1;
    };
  }, [journeyId, visible, bearerEpoch]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    restoreEpoch.current += 1;
    const startingBearer = readTravelerBearer();
    const message = prompt.trim();
    if (!startingBearer) {
      setRequestState("unauthorized");
      setFailure("请重新进入行程后使用助手。");
      return;
    }
    if (!message || message.length > 1200 || requestState === "sending") return;
    setRequestState("sending");
    setRestoreState("checking");
    setFailure(null);
    setRun(null);
    setRunJourneyId(null);
    setExpanded(false);
    setStopState("idle");
    try {
      const response = await cityNexusApi.sendCopilotMessage(journeyId, message, "zh");
      if (readTravelerBearer() !== startingBearer) return;
      const actualRun = response.agent_run?.runtime_identity === "HERMES_NATIVE_MCP"
        && Boolean(response.agent_run.run_id)
        ? response.agent_run
        : null;
      setRun(actualRun);
      setRunJourneyId(actualRun ? journeyId : null);
      setRestoreState(actualRun ? "available" : "empty");
      setExpanded(Boolean(actualRun));
      setRequestState("ready");
    } catch (caught) {
      if (readTravelerBearer() !== startingBearer) return;
      if (caught instanceof CityNexusApiError && (caught.status === 401 || caught.status === 403 || caught.status === 404)) {
        setRun(null);
        setRunJourneyId(null);
        setExpanded(false);
        setRestoreState("failed");
        setRequestState("unauthorized");
        setFailure("无法读取这条运行记录。");
      } else {
        setRestoreState("failed");
        setRequestState("error");
        setFailure("请求结果待确认，请刷新运行记录。");
      }
    }
  };

  const stopRun = async () => {
    if (!currentRun || timeline.authState !== "authorized" || terminalRun(timeline.runState) || stopState === "sending" || stopState === "requested") return;
    const startingBearer = readTravelerBearer();
    if (!startingBearer) return;
    setStopState("sending");
    try {
      await cityNexusApi.stopNativeHermesRun(journeyId, currentRun.run_id);
      if (readTravelerBearer() !== startingBearer) return;
      // The POST only acknowledges a request; the run remains active in this UI
      // until the authenticated server timeline reports a terminal event.
      setStopState("requested");
    } catch (caught) {
      if (readTravelerBearer() !== startingBearer) return;
      if (caught instanceof CityNexusApiError && [401, 403, 404].includes(caught.status)) {
        setStopState("failed");
        setFailure("无法停止这次运行。");
      } else {
        setStopState("failed");
        setFailure("停止状态待确认，请刷新查看。");
      }
    }
  };

  const toolCount = actualEvents.filter((event) => event.event_type.startsWith("tool.")).length;
  const latestEvent = orderedEvents.at(-1);

  const composer = (<form className={globalComposer ? "rev-mission-chat-dock rev-v3-active-dock" : "rev-mobile-hermes-form"} aria-label="与当前旅行 Agent 对话" onSubmit={(event) => { window.dispatchEvent(new CustomEvent("citynexus:mission-panel", { detail: "timeline" })); void submit(event); }}>
        <label htmlFor="rev-mobile-hermes-prompt">你希望它检查什么</label>
        <textarea
          id="rev-mobile-hermes-prompt"
          value={prompt}
          maxLength={1200}
          rows={globalComposer ? 1 : 3}
          disabled={requestState === "sending" || requestState === "unauthorized"}
          onChange={(event) => setPrompt(event.target.value)}
          data-testid="rev-mobile-hermes-prompt"
        />
        <button type="submit" disabled={requestState === "sending" || requestState === "unauthorized" || !prompt.trim()} data-testid="rev-mobile-hermes-submit">
          <Send size={16} aria-hidden="true" />
          {requestState === "sending" ? "正在提交…" : globalComposer ? "发送 ↑" : "发送给行程助手"}
        </button>
      </form>);

  return (
    <section className="rev-mobile-hermes" data-testid="rev-mobile-hermes">
      <div className="rev-mobile-hermes-heading">
        <span className="rev-mobile-hermes-icon" aria-hidden="true"><Activity size={19} /></span>
        <div>
          <span className="rev-mobile-hermes-eyebrow">CITYNEXUS · AI 助手</span>
          <h2>让助手检查当前行程</h2>
        </div>
      </div>
      {globalComposer ? createPortal(composer, document.body) : composer}

      {failure && <p className="rev-mobile-hermes-message error" role="alert"><AlertCircle size={15} aria-hidden="true" />{failure}</p>}
      {visible && !currentRun && requestState !== "sending" && requestState !== "unauthorized" && (restoreState === "checking" || restoreState === "empty") && (
        <p className="rev-mobile-hermes-empty" role="status" data-testid="rev-mobile-hermes-empty-state">
          <CircleDashed size={15} aria-hidden="true" />
          {restoreState === "checking"
            ? "正在读取行程助手记录。"
            : "暂无助手运行记录。现场模型可能要几分钟，赶时间请直接用上面的调整卡。"}
        </p>
      )}

      {currentRun && (
        <div className="rev-mobile-hermes-run" data-testid="rev-mobile-hermes-run">
          <div className="rev-mobile-hermes-run-top">
            <span className="rev-mobile-hermes-run-symbol" aria-hidden="true">
              {timeline.authState === "unauthorized" ? <AlertCircle size={18} /> : <Wrench size={18} />}
            </span>
            <div>
              <strong role="status">
                {timeline.authState === "unauthorized"
                  ? "成员会话已变化，运行详情已清除"
                  : stateText(timeline.runState, timeline.connection, actualEvents, stopState)}
              </strong>
              <small>
                {timeline.authState === "unauthorized"
                  ? "重新登录以查看运行记录。"
                  : `${toolCount} 条${isFixtureRun ? "示例事件" : "工具事件"}${latestEvent && eventTime(latestEvent.timestamp) ? ` · 更新于 ${eventTime(latestEvent.timestamp)}` : ""}`}
              </small>
            </div>
            <button
              type="button"
              className="rev-mobile-hermes-toggle"
              aria-expanded={expanded}
              aria-label={expanded ? "收起轨迹面板" : "查看工作过程"}
              onClick={() => setExpanded((value) => !value)}
            >{expanded ? <X size={18} aria-hidden="true" /> : "查看工作过程"}</button>
          </div>
          <dialog
            ref={dialogRef}
            className="rev-mobile-hermes-sheet"
            aria-labelledby="rev-mobile-hermes-sheet-title"
            onCancel={(event) => { event.preventDefault(); setExpanded(false); }}
            onClose={() => setExpanded(false)}
            data-testid="rev-mobile-hermes-sheet"
          >
            <header className="rev-mobile-hermes-sheet-head">
              <div>
                <span className="rev-mobile-hermes-eyebrow">{isFixtureRun ? "测试数据" : "助手运行记录"}</span>
                <h3 id="rev-mobile-hermes-sheet-title">Hermes 工作过程</h3>
              </div>
              <button type="button" className="rev-mobile-hermes-close" aria-label="关闭工作过程" onClick={() => setExpanded(false)}>
                <X size={19} aria-hidden="true" />
              </button>
            </header>
            <div className="rev-mobile-hermes-sheet-body">
              {timeline.authState !== "unauthorized" && (
                <p className="rev-mobile-hermes-sheet-status" role="status">
                  {stateText(timeline.runState, timeline.connection, actualEvents, stopState)}
                </p>
              )}
              {timeline.authState !== "unauthorized" && (
                <>
                  {pendingApproval && (
                    <div className="rev-mobile-hermes-approval" role="status">
                      <span>有操作待确认。</span>
                      <a href="#journey-operator-operations">前往行程操作与授权审核 →</a>
                    </div>
                  )}
                  {stopState !== "idle" && (
                    <p className="rev-mobile-hermes-action" role="status">
                      {stopState === "sending" ? "正在发送停止请求…"
                        : stopState === "requested" ? "停止请求已提交，等待状态更新。"
                          : "停止状态待确认；刷新查看。"}
                    </p>
                  )}
                  {visibleEvents.length > 0 ? (
                    <ol className="rev-mobile-hermes-events" aria-label="Hermes 运行轨迹" aria-live="polite">
                      {visibleEvents.map((event, index) => {
                        const status = statusForMobileEvent(event);
                        const duration = eventDuration(event.duration_ms);
                        const timestamp = eventTime(event.timestamp);
                        const toolName = safeToolName(event.tool_name);
                        const toolErrorMessage = safeToolErrorMessage(event);
                        return (
                          <li key={`${event.sequence ?? ""}|${event.event_id ?? ""}|${event.event_type}|${index}`} className={"is-" + status}>
                            <span className="rev-mobile-hermes-event-mark" aria-hidden="true">
                              {status === "done" ? <Check size={14} /> : status === "active" ? <CircleDashed size={14} /> : <AlertCircle size={14} />}
                            </span>
                            <div className="rev-mobile-hermes-event-body">
                              <span className="rev-mobile-hermes-event-label">{safeEventLabel(event)}</span>
                              {toolErrorMessage && <small>{toolErrorMessage}</small>}
                              {toolName && <code className="rev-mobile-hermes-tool-name">{toolName}</code>}
                              {(duration || timestamp) && (
                                <span className="rev-mobile-hermes-event-meta">
                                  {timestamp && (
                                    <time dateTime={typeof event.timestamp === "string" ? event.timestamp : undefined}>
                                      {timestamp}
                                    </time>
                                  )}
                                  {duration && <small>{duration}</small>}
                                </span>
                              )}
                            </div>
                          </li>
                        );
                      })}
                    </ol>
                  ) : (
                    <p className="rev-mobile-hermes-empty"><CircleDashed size={15} aria-hidden="true" />{timeline.connection === "unavailable" ? "运行记录暂不可用，请刷新。" : "暂无工具事件。"}</p>
                  )}
                  {timeline.connection === "unavailable" && orderedEvents.length > 0 && (
                    <p className="rev-mobile-hermes-message">实时连接中断；当前显示已收到的事件。</p>
                  )}
                  {timeline.connection === "retrying" && <p className="rev-mobile-hermes-message">正在重新连接并同步运行记录…</p>}
                  {timeline.authState === "authorized" && timeline.runState.toLowerCase() !== "unknown" && !terminalRun(timeline.runState) && (
                    <button type="button" className="rev-mobile-hermes-stop" disabled={stopState === "sending" || stopState === "requested"} onClick={() => void stopRun()}>
                      {stopState === "sending" ? "正在停止…" : stopState === "requested" ? "已请求停止" : "停止本次运行"}
                    </button>
                  )}
                </>
              )}
              {timeline.authState === "unauthorized" && <p className="rev-mobile-hermes-message error">成员会话已变化，运行详情已清除。</p>}
            </div>
          </dialog>
        </div>
      )}
      {requestState === "unauthorized" && <p className="rev-mobile-hermes-message error"><AlertCircle size={15} aria-hidden="true" />运行记录仅对当前行程成员开放。</p>}
    </section>
  );
}
