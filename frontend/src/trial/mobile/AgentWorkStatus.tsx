import { useEffect, useState } from "react";
import { Activity, ChevronDown, CircleAlert, CircleCheck, Clock3, ShieldCheck, Wrench } from "lucide-react";
import { cityNexusApi, type JourneyOperatorProjection } from "../../api/citynexus";
import { readTravelerBearer, subscribeTravelerBearer } from "../../lib/travelerSession";
import "./AgentWorkStatus.css";

type RequestState = "loading" | "ready" | "offline" | "unauthorized";
type OperatorState = JourneyOperatorProjection["state"];

const stateCopy: Record<OperatorState, { title: string; explanation: string }> = {
  OFF: { title: "行程照看未开启", explanation: "开启后会留意行程变化。" },
  WATCHING: { title: "正在留意行程变化", explanation: "行程监测中。" },
  INVESTIGATING: { title: "正在核对行程变化", explanation: "正在收集下一步所需信息。" },
  WAITING_FOR_APPROVAL: { title: "需要你确认下一步", explanation: "有操作待审核。" },
  APPLYING: { title: "正在执行已授权操作", explanation: "操作进行中。" },
  RECOVERED: { title: "行程问题已处理", explanation: "可展开查看处理记录。" },
  NEEDS_ATTENTION: { title: "有情况需要你关注", explanation: "查看行程动态了解原因。" },
  DEGRADED: { title: "部分服务暂不可用", explanation: "查看最新服务状态。" },
};

const auditCopy: Record<string, string> = {
  "operator.started": "行程监测已启动",
  "operator.stopped": "行程监测已暂停",
  "city.signal.incident.created": "发现一项行程变化",
  "guardian.mission.compiled": "已准备恢复步骤",
  "guardian.scan.started": "开始核对行程信息",
  "agent.action_approval.created": "有一项操作等待确认",
  "agent.action_approval.approved": "一项操作已获授权",
  "replan.accepted": "调整方案已正式接受",
  "agent.pending_action.resumed": "行程监测继续",
  "operator.external_agent_blocked": "Agent 服务未能正常连接",
  "agent.recovery_discovery.started": "正在查找其他解决办法",
  "agent.recovery_discovery.completed": "备选方案搜索已结束",
};

function safeTime(value: string): string | null {
  const time = Date.parse(value);
  if (!Number.isFinite(time)) return null;
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(time);
}

/**
 * Read-only, signed Operator WORK STATUS, not a synthetic Hermes AgentRun.
 *
 * Only existing GET /journeys/:id/operator is used. Never initiates an LLM,
 * consent, provider query, payment, plan change, approval or user action.
 * Hermes per-tool traces belong in a follow-up with an authenticated run ID.
 */
export function AgentWorkStatus({
  journeyId,
  visible,
}: {
  journeyId: string;
  visible: boolean;
}) {
  const [snapshot, setSnapshot] = useState<JourneyOperatorProjection | null>(null);
  const [requestState, setRequestState] = useState<RequestState>("loading");
  const [detailsOpen, setDetailsOpen] = useState(false);

  useEffect(() => {
    if (!visible) return;
    const startingBearer = readTravelerBearer();
    let cancelled = false;
    let inFlight = false;
    let epoch = 0;

    setSnapshot(null);
    setRequestState(startingBearer ? "loading" : "unauthorized");

    const current = () => !cancelled && !!startingBearer && readTravelerBearer() === startingBearer;

    const refresh = async () => {
      if (!current() || inFlight || document.visibilityState === "hidden") return;
      inFlight = true;
      const requestEpoch = ++epoch;
      try {
        const response = await cityNexusApi.getJourneyOperator(journeyId);
        if (!current() || requestEpoch !== epoch) return;
        if (response.journey_id !== journeyId) {
          setSnapshot(null);
          setRequestState("offline");
          return;
        }
        setSnapshot(response);
        setRequestState("ready");
      } catch {
        if (!current() || requestEpoch !== epoch) return;
        // Keep already confirmed last status, marked stale. Never invent a
        // current activity or claim the Agent is still working while offline.
        setRequestState("offline");
      } finally {
        inFlight = false;
      }
    };

    const unsubscribe = subscribeTravelerBearer((bearer) => {
      if (bearer === startingBearer) return;
      epoch += 1;
      setSnapshot(null);
      setRequestState("unauthorized");
    });

    void refresh();
    const interval = window.setInterval(() => { void refresh(); }, 10_000);
    const onVisible = () => { if (document.visibilityState === "visible") void refresh(); };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      cancelled = true;
      epoch += 1;
      unsubscribe();
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [journeyId, visible]);

  if (!visible) return null;
  const copy = snapshot ? stateCopy[snapshot.state] ?? stateCopy.DEGRADED : null;
  const pending = snapshot?.approval?.required === true;
  const lastAudits = (snapshot?.timeline ?? [])
    .filter((event) => typeof event.kind === "string" && Object.hasOwn(auditCopy, event.kind))
    .slice(-5)
    .reverse();
  const status = requestState === "unauthorized"
    ? "会话已改变，请重新进入行程"
    : requestState === "offline"
      ? "工作动态暂时断线"
      : requestState === "loading"
        ? "正在读取行程动态…"
        : copy?.title ?? "暂时没有可用的行程动态";

  return (
    <section className="rev-agent-work-status" data-testid="rev-mobile-agent-work">
      <div className="rev-agent-work-top">
        <span className="rev-agent-work-symbol" aria-hidden="true"><Activity size={20} strokeWidth={2} /></span>
        <div className="rev-agent-work-title">
          <span className="rev-agent-work-eyebrow">CITYNEXUS · 工作动态</span>
          <strong role="status">{status}</strong>
        </div>
        {requestState === "ready" && snapshot && (
          <span className={"rev-agent-work-state " + (pending ? "needs-approval" : "")}>
            {pending ? "待你审核" : snapshot.enabled ? "行程已连接" : "未启用"}
          </span>
        )}
      </div>
      {requestState === "offline" && (
        <p className="rev-agent-work-note" role="status">
          {snapshot ? "显示上次读取记录；当前无法连接服务器。" : "服务器暂不可用。"}
        </p>
      )}
      {requestState === "ready" && snapshot && (
        <p className="rev-agent-work-note">{copy?.explanation}</p>
      )}
      {pending && requestState === "ready" && (
        <p className="rev-agent-work-approval"><ShieldCheck size={16} aria-hidden="true" />有操作待审核，请在下方确认。</p>
      )}
      <details
        className="rev-agent-work-detail"
        open={detailsOpen}
        onToggle={(event) => setDetailsOpen(event.currentTarget.open)}
      >
        <summary>
          <Wrench size={15} aria-hidden="true" />
          {snapshot ? "查看最近工作记录" : "关于工作动态"}
          <ChevronDown size={16} aria-hidden="true" className="rev-agent-work-chevron" />
        </summary>
        {lastAudits.length > 0 ? (
          <ol className="rev-agent-work-timeline">
            {lastAudits.map((event, index) => (
              <li key={event.kind + "|" + event.at + "|" + index}>
                <CircleCheck size={16} aria-hidden="true" />
                <span>{auditCopy[event.kind]}</span>
                <small><Clock3 size={12} aria-hidden="true" />{safeTime(event.at) ?? "时间未提供"}</small>
              </li>
            ))}
          </ol>
        ) : (
          <p className="rev-agent-work-empty">
            {snapshot ? "暂无操作记录。" : "连接行程后查看工作记录。"}
          </p>
        )}
        {snapshot?.operations && (
          <p className="rev-agent-work-evidence">
            行程操作：{snapshot.operations.completed_action_count} / {snapshot.operations.planned_action_count} 项
          </p>
        )}
      </details>
      {requestState === "unauthorized" && <p className="rev-agent-work-note"><CircleAlert size={14} aria-hidden="true" />请返回探索页重新登录当前行程。</p>}
    </section>
  );
}
