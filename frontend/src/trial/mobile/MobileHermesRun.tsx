import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
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

type RequestState = "idle" | "sending" | "ready" | "unauthorized" | "error";
type RestoreState = "idle" | "checking" | "empty" | "available" | "failed";

function terminalRun(status: string) {
  return /^(completed|succeeded|failed|error|stopped|cancelled|canceled)$/i.test(status);
}

function safeEventLabel(event: NativeRuntimeEvent) {
  if (event.tool_name) {
    const tool = TOOL_LABELS[event.tool_name] ?? "执行一个行程工具步骤";
    if (event.event_type === "tool.started") return `正在${tool}`;
    if (event.event_type === "tool.completed") return `${tool}：已完成`;
    if (event.event_type === "tool.failed") return `${tool}：未完成`;
  }
  return EVENT_LABELS[event.event_type] ?? "收到一条 Hermes 运行事件";
}

function eventTime(value: NativeRuntimeEvent["timestamp"]) {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const parsed = typeof value === "number" ? value : Date.parse(value);
  if (!Number.isFinite(parsed)) return null;
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(parsed);
}

function eventDuration(value: NativeRuntimeEvent["duration_ms"]) {
  if (value == null) return null;
  const milliseconds = Number(value);
  if (!Number.isFinite(milliseconds) || milliseconds < 0) return null;
  if (milliseconds < 1000) return `${Math.round(milliseconds)} 毫秒`;
  const seconds = milliseconds / 1000;
  return `${Number(seconds.toFixed(seconds >= 10 ? 0 : 1))} 秒`;
}

function stateText(status: string, connection: string, events: NativeRuntimeEvent[]) {
  if (/^(completed|succeeded)$/i.test(status)) return "已完成";
  if (/^(failed|error)$/i.test(status)) return "运行失败";
  if (/^(stopped|cancelled|canceled)$/i.test(status)) return "已停止";
  if (events.some((event) => event.event_type === "approval.required")) return "等待你确认";
  if (connection === "connecting" || connection === "retrying") return "正在连接真实运行事件";
  const lastToolEvent = [...events].reverse().find((event) => event.event_type.startsWith("tool."));
  if (lastToolEvent?.event_type === "tool.started") return "正在处理行程请求";
  if (lastToolEvent) return "等待服务器更新运行状态";
  if (connection === "unavailable") return "事件连接暂不可用";
  return "Hermes 已启动，等待首条工具事件";
}

export function MobileHermesRun({ journeyId, visible }: { journeyId: string; visible: boolean }) {
  const [prompt, setPrompt] = useState("请检查当前行程和受保护安排，并给出安全的调整建议；只生成方案，不预订、不付款，也不修改行程。");
  const [requestState, setRequestState] = useState<RequestState>(() => readTravelerBearer() ? "idle" : "unauthorized");
  const [restoreState, setRestoreState] = useState<RestoreState>("idle");
  const [reply, setReply] = useState<string | null>(null);
  const [replyMode, setReplyMode] = useState<"AI" | "FALLBACK" | null>(null);
  const [run, setRun] = useState<NativeHermesRunData | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [stopState, setStopState] = useState<"idle" | "sending" | "requested" | "failed">("idle");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [bearerEpoch, setBearerEpoch] = useState(0);
  const restoreEpoch = useRef(0);
  const timeline = useNativeHermesTimeline({ journeyId, run, enabled: visible });
  const actualEvents = useMemo(
    () => mergeNativeEvents(timeline.events.filter((event) => event.source === "HERMES_NATIVE")),
    [timeline.events],
  );
  const orderedEvents = actualEvents.filter((event) =>
    event.event_type.startsWith("tool.") || Object.hasOwn(EVENT_LABELS, event.event_type),
  );
  const isFixtureRun = Boolean(run?.provider_key && /^(test|fixture)(?:[_-]|$)/i.test(run.provider_key));
  const reasoningSummary = run?.mission_id && typeof run.reasoning_summary === "string" && run.reasoning_summary.trim()
    ? run.reasoning_summary
    : null;
  const pendingApproval = [...actualEvents].reverse().find((event) =>
    event.event_type === "approval.required"
    && Boolean(event.approval_id)
    && String(event.approval_status ?? "PENDING").toUpperCase() === "PENDING",
  );

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (expanded && run && timeline.authState !== "unauthorized") {
      if (!dialog.open) dialog.showModal();
    } else if (dialog.open) {
      dialog.close();
    }
  }, [expanded, run?.run_id, timeline.authState]);

  useEffect(() => {
    const startingBearer = readTravelerBearer();
    if (!startingBearer) {
      setRun(null);
      setRestoreState("idle");
      setReply(null);
      setReplyMode(null);
      setExpanded(false);
      setStopState("idle");
      setRequestState("unauthorized");
      return;
    }
    setRequestState((current) => current === "unauthorized" ? "idle" : current);
    const unsubscribe = subscribeTravelerBearer((bearer) => {
      if (bearer === startingBearer) return;
      setRun(null);
      setRestoreState("idle");
      setReply(null);
      setReplyMode(null);
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
        setRestoreState("failed");
        setFailure("服务器返回的运行记录与当前行程不匹配；已隐藏该记录。");
        return;
      }
      const latest = response.run;
      if (!latest || latest.runtime_identity !== "HERMES_NATIVE_MCP" || !latest.run_id) {
        setRun(null);
        setRestoreState("empty");
        return;
      }
      setRun(latest);
      setRestoreState("available");
      setRequestState("ready");
      // Restored history stays collapsed; a fresh signed Copilot response
      // opens the trace drawer for the run that it just bound.
      setExpanded(false);
    }).catch((caught) => {
      if (restoreEpoch.current !== epoch || readTravelerBearer() !== startingBearer) return;
      if (caught instanceof CityNexusApiError && [401, 403].includes(caught.status)) {
        setRun(null);
        setRestoreState("failed");
        setRequestState("unauthorized");
        setFailure("当前签名成员无权恢复这条运行记录；已隐藏运行详情。");
        return;
      }
      setRestoreState("failed");
      setFailure("暂时无法恢复上一条运行记录；没有因此启动新的 AI 任务。");
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
      setFailure("当前行程没有有效的签名成员会话，请重新进入行程后再试。");
      return;
    }
    if (!message || message.length > 1200 || requestState === "sending") return;
    setRequestState("sending");
    setRestoreState("checking");
    setFailure(null);
    setReply(null);
    setReplyMode(null);
    setRun(null);
    setExpanded(false);
    setStopState("idle");
    try {
      const response = await cityNexusApi.sendCopilotMessage(journeyId, message, "zh");
      if (readTravelerBearer() !== startingBearer) return;
      setReply(response.message);
      setReplyMode(response.mode);
      const actualRun = response.agent_run?.runtime_identity === "HERMES_NATIVE_MCP"
        && Boolean(response.agent_run.run_id)
        ? response.agent_run
        : null;
      setRun(actualRun);
      setRestoreState(actualRun ? "available" : "empty");
      setExpanded(Boolean(actualRun));
      setRequestState("ready");
    } catch (caught) {
      if (readTravelerBearer() !== startingBearer) return;
      if (caught instanceof CityNexusApiError && (caught.status === 401 || caught.status === 403)) {
        setRun(null);
        setRestoreState("failed");
        setRequestState("unauthorized");
        setFailure("服务器没有确认当前签名成员身份，已隐藏本次运行记录。");
      } else {
        setRestoreState("failed");
        setRequestState("error");
        setFailure("请求没有完成；没有创建可展示的 Hermes 运行。请检查行程连接后重试。");
      }
    }
  };

  const stopRun = async () => {
    if (!run || timeline.authState !== "authorized" || terminalRun(timeline.runState) || stopState === "sending" || stopState === "requested") return;
    const startingBearer = readTravelerBearer();
    if (!startingBearer) return;
    setStopState("sending");
    try {
      await cityNexusApi.stopNativeHermesRun(journeyId, run.run_id);
      if (readTravelerBearer() !== startingBearer) return;
      // The POST only acknowledges a request; the run remains active in this UI
      // until the authenticated server timeline reports a terminal event.
      setStopState("requested");
    } catch (caught) {
      if (readTravelerBearer() !== startingBearer) return;
      if (caught instanceof CityNexusApiError && [401, 403, 404].includes(caught.status)) {
        setStopState("failed");
        setFailure("当前签名成员没有这条运行的停止权限；运行状态仍以服务器记录为准。");
      } else {
        setStopState("failed");
        setFailure("CityNexus 没有确认停止请求；运行状态仍以服务器记录为准。");
      }
    }
  };

  const toolCount = actualEvents.filter((event) => event.event_type.startsWith("tool.")).length;
  const latestEvent = orderedEvents.at(-1);

  return (
    <section className="rev-mobile-hermes" data-testid="rev-mobile-hermes">
      <div className="rev-mobile-hermes-heading">
        <span className="rev-mobile-hermes-icon" aria-hidden="true"><Activity size={19} /></span>
        <div>
          <span className="rev-mobile-hermes-eyebrow">CITYNEXUS · AI 助手</span>
          <h2>让助手检查当前行程</h2>
        </div>
        <span className="rev-mobile-hermes-mode">仅生成建议</span>
      </div>
      <form className="rev-mobile-hermes-form" onSubmit={(event) => { void submit(event); }}>
        <label htmlFor="rev-mobile-hermes-prompt">你希望它检查什么</label>
        <textarea
          id="rev-mobile-hermes-prompt"
          value={prompt}
          maxLength={1200}
          rows={3}
          disabled={requestState === "sending" || requestState === "unauthorized"}
          onChange={(event) => setPrompt(event.target.value)}
          data-testid="rev-mobile-hermes-prompt"
        />
        <button type="submit" disabled={requestState === "sending" || requestState === "unauthorized" || !prompt.trim()} data-testid="rev-mobile-hermes-submit">
          <Send size={16} aria-hidden="true" />
          {requestState === "sending" ? "正在提交…" : "发送给行程助手"}
        </button>
      </form>

      {failure && <p className="rev-mobile-hermes-message error" role="alert"><AlertCircle size={15} aria-hidden="true" />{failure}</p>}
      {visible && !run && requestState !== "sending" && requestState !== "unauthorized" && (restoreState === "checking" || restoreState === "empty") && (
        <p className="rev-mobile-hermes-empty" role="status" data-testid="rev-mobile-hermes-empty-state">
          <CircleDashed size={15} aria-hidden="true" />
          {restoreState === "checking"
            ? "正在查看这趟行程是否有可恢复的助手运行。"
            : "当前没有正在执行的 Hermes 任务。连接就绪不代表任务已经开始；只有服务器创建了真实运行后，这里才会显示工具轨迹。"}
        </p>
      )}
      {reply && (
        <div className="rev-mobile-hermes-reply" data-testid="rev-mobile-hermes-reply">
          <b>{replyMode === "AI" ? "助手回复" : "规则回退回复"}</b>
          <p>{reply}</p>
          {!run && <small>本次没有创建 Hermes 工具运行，因此下面不会显示为 AgentRun。</small>}
        </div>
      )}

      {run && (
        <div className="rev-mobile-hermes-run" data-testid="rev-mobile-hermes-run">
          <div className="rev-mobile-hermes-run-top">
            <span className="rev-mobile-hermes-run-symbol" aria-hidden="true">
              {timeline.authState === "unauthorized" ? <AlertCircle size={18} /> : <Wrench size={18} />}
            </span>
            <div>
              <strong role="status">
                {timeline.authState === "unauthorized"
                  ? "签名会话已变化，已清除运行详情"
                  : stateText(timeline.runState, timeline.connection, actualEvents)}
              </strong>
              <small>
                {timeline.authState === "unauthorized"
                  ? "重新登录后才能读取本次行程的私人运行记录。"
                  : `${toolCount} 条${isFixtureRun ? "测试夹具工具事件" : "服务器工具事件"}${latestEvent && eventTime(latestEvent.timestamp) ? ` · 更新于 ${eventTime(latestEvent.timestamp)}` : ""}`}
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
                <span className="rev-mobile-hermes-eyebrow">{isFixtureRun ? "TEST_FIXTURE · 仅用于界面验收" : "签名服务器运行记录"}</span>
                <h3 id="rev-mobile-hermes-sheet-title">Hermes 工作过程</h3>
              </div>
              <button type="button" className="rev-mobile-hermes-close" aria-label="关闭工作过程" onClick={() => setExpanded(false)}>
                <X size={19} aria-hidden="true" />
              </button>
            </header>
            <div className="rev-mobile-hermes-sheet-body">
              {timeline.authState !== "unauthorized" && (
                <p className="rev-mobile-hermes-sheet-status" role="status">
                  {stateText(timeline.runState, timeline.connection, actualEvents)}
                </p>
              )}
              {timeline.authState !== "unauthorized" && (
                <>
                  <section className="rev-mobile-hermes-reason" aria-label="工作思路与判断依据">
                    <b>工作思路 / 判断依据</b>
                    <p>{reasoningSummary ?? "暂无可公开判断说明"}</p>
                    <small>只显示与本次签名运行绑定的服务器安全摘要，不包含模型私有思维链。</small>
                  </section>
                  {pendingApproval && (
                    <p className="rev-mobile-hermes-approval" role="status">
                      此运行有一项待确认操作。请在下方行程恢复中心查看并授权；此轨迹面板不会替你审批。
                    </p>
                  )}
                  {stopState !== "idle" && (
                    <p className="rev-mobile-hermes-action" role="status">
                      {stopState === "sending" ? "正在向 CityNexus 发送停止请求…"
                        : stopState === "requested" ? "停止请求已送达；等待服务器事件确认最终状态。"
                          : "停止请求未确认；当前状态仍以服务器记录为准。"}
                    </p>
                  )}
                  {orderedEvents.length > 0 ? (
                    <ol className="rev-mobile-hermes-events" aria-label="Hermes 工具调用记录" aria-live="polite">
                      {orderedEvents.slice(-12).map((event, index) => {
                        const status = statusForNativeEvent(event);
                        const duration = eventDuration(event.duration_ms);
                        return (
                          <li key={`${event.sequence ?? ""}|${event.event_id ?? ""}|${event.event_type}|${index}`} className={"is-" + status}>
                            <span className="rev-mobile-hermes-event-mark" aria-hidden="true">
                              {status === "done" ? <Check size={14} /> : status === "active" ? <CircleDashed size={14} /> : <AlertCircle size={14} />}
                            </span>
                            <span className="rev-mobile-hermes-event-label">{safeEventLabel(event)}</span>
                            {duration && <small>{duration}</small>}
                            {eventTime(event.timestamp) && <time dateTime={typeof event.timestamp === "string" ? event.timestamp : undefined}>{eventTime(event.timestamp)}</time>}
                          </li>
                        );
                      })}
                    </ol>
                  ) : (
                    <p className="rev-mobile-hermes-empty"><CircleDashed size={15} aria-hidden="true" />{timeline.connection === "unavailable" ? "当前拿不到服务器运行事件；不会补造进度。" : "服务端尚未返回工具事件，等待真实运行记录。"}</p>
                  )}
                  {timeline.connection === "unavailable" && orderedEvents.length > 0 && (
                    <p className="rev-mobile-hermes-message">实时连接中断；已收到的记录仅保留在本页内存中。</p>
                  )}
                  {timeline.connection === "retrying" && <p className="rev-mobile-hermes-message">连接中断，正在重新连接并与服务器历史记录合并。</p>}
                  {timeline.authState === "authorized" && timeline.runState.toLowerCase() !== "unknown" && !terminalRun(timeline.runState) && (
                    <button type="button" className="rev-mobile-hermes-stop" disabled={stopState === "sending" || stopState === "requested"} onClick={() => void stopRun()}>
                      {stopState === "sending" ? "正在停止…" : stopState === "requested" ? "已请求停止" : "停止本次运行"}
                    </button>
                  )}
                  <p className="rev-mobile-hermes-footnote">
                    {isFixtureRun
                      ? "当前事件来自界面测试夹具，不能证明真实 Hermes 已运行。正式运行只显示服务器事件和安全名称，不展示工具参数或原始返回。"
                      : "显示签名服务器返回的 Hermes 事件和安全名称；不显示工具参数或原始返回。运行仅可提出建议，不会自动预订、付款或修改行程。"}
                  </p>
                </>
              )}
              {timeline.authState === "unauthorized" && <p className="rev-mobile-hermes-message error">签名成员权限已变化，私人运行详情已清除。</p>}
            </div>
          </dialog>
        </div>
      )}
      {requestState === "unauthorized" && <p className="rev-mobile-hermes-message error"><AlertCircle size={15} aria-hidden="true" />此功能只对当前签名行程成员开放。</p>}
    </section>
  );
}
