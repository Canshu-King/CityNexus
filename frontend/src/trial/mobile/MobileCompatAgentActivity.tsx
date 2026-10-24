import { useEffect, useRef, useState } from "react";
import { Activity, CircleAlert, CircleCheck, CircleDashed, Send, Wrench } from "lucide-react";
import {
  CityNexusApiError,
  cityNexusApi,
  type MobileCompatAgentLatest,
  type MobileCompatAgentRun,
} from "../../api/citynexus";
import { readTravelerBearer, subscribeTravelerBearer } from "../../lib/travelerSession";
import "./MobileCompatAgentActivity.css";

const TOOL_LABELS: Record<string, string> = {
  inspect_journey: "检查当前行程",
  inspect_twin: "核对行程状态",
  list_replans: "读取已有调整建议",
};

type LoadState = "loading" | "ready" | "offline" | "unauthorized";

function isTerminal(status: string) {
  return status !== "RUNNING" && status !== "UNKNOWN";
}

function stateLabel(run: MobileCompatAgentRun | null, configured: boolean, aiDisabled: boolean) {
  if (!run) return aiDisabled ? "AI 暂未开启" : configured ? "AI 当前没有执行中的任务" : "AI 尚未连接";
  if (run.status === "RUNNING") return "AI 正在检查行程";
  if (run.status === "FAILED_EXTERNAL") return "AI 请求失败";
  if (run.status === "PARTIAL") return "行程检查未完成";
  if (!run.tool_call_recorded) return "没有工具调用记录";
  if (run.tool_steps.some((step) => step.status === "FAILED")) return "行程检查未完成";
  return "行程检查已完成";
}

function safeTime(value: string | null | undefined) {
  if (!value) return null;
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return null;
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(parsed);
}

export function MobileCompatAgentActivity({
  journeyId,
  visible,
  aiDisabled,
}: {
  journeyId: string;
  visible: boolean;
  aiDisabled: boolean;
}) {
  const [snapshot, setSnapshot] = useState<MobileCompatAgentLatest | null>(null);
  const [run, setRun] = useState<MobileCompatAgentRun | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [bearerEpoch, setBearerEpoch] = useState(0);
  const visibleRef = useRef(visible);
  visibleRef.current = visible;

  useEffect(() => {
    const startingBearer = readTravelerBearer();
    let cancelled = false;
    if (!startingBearer) {
      setSnapshot(null);
      setRun(null);
      setLoadState("unauthorized");
      return;
    }
    setSnapshot(null);
    setRun(null);
    setMessage(null);
    setLoadState("loading");
    const unsubscribe = subscribeTravelerBearer((bearer) => {
      if (bearer === startingBearer) return;
      setSnapshot(null);
      setRun(null);
      setLoadState("unauthorized");
      setMessage(null);
      setSending(false);
      setBearerEpoch((epoch) => epoch + 1);
    });
    if (!visible) {
      return () => {
        cancelled = true;
        unsubscribe();
      };
    }
    void cityNexusApi.getLatestMobileCompatRun(journeyId).then((latest) => {
      if (cancelled || readTravelerBearer() !== startingBearer) return;
      setSnapshot(latest);
      setRun(latest.run);
      setLoadState("ready");
    }).catch((error: unknown) => {
      if (cancelled || readTravelerBearer() !== startingBearer) return;
      setLoadState(error instanceof CityNexusApiError && [401, 403].includes(error.status)
        ? "unauthorized"
        : "offline");
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [journeyId, bearerEpoch, visible]);

  useEffect(() => {
    if (!visible || !run || run.status !== "RUNNING") return;
    const startingBearer = readTravelerBearer();
    if (!startingBearer) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "hidden" || readTravelerBearer() !== startingBearer) return;
      void cityNexusApi.getMobileCompatRun(journeyId, run.request_id).then((current) => {
        if (cancelled || readTravelerBearer() !== startingBearer) return;
        setRun(current);
      }).catch(() => undefined);
    }, 4000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [journeyId, run?.request_id, run?.status, visible]);

  const startRun = async () => {
    const startingBearer = readTravelerBearer();
    if (!startingBearer || sending || (run && !isTerminal(run.status))) return;
    setSending(true);
    setMessage(null);
    try {
      const created = await cityNexusApi.startMobileCompatRun(journeyId, crypto.randomUUID());
      if (readTravelerBearer() !== startingBearer) return;
      setRun(created);
      setExpanded(true);
    } catch (error) {
      if (readTravelerBearer() !== startingBearer) return;
      if (error instanceof CityNexusApiError && [401, 403].includes(error.status)) {
        setLoadState("unauthorized");
        setRun(null);
      } else {
        // The server commits the run binding before the provider request. A read
        // can recover the exact run after a browser timeout without sending again.
        if (!visibleRef.current) {
          setMessage("AI 请求没有完成。");
          return;
        }
        try {
          const latest = await cityNexusApi.getLatestMobileCompatRun(journeyId);
          if (readTravelerBearer() === startingBearer && latest.run) {
            setSnapshot(latest);
            setRun(latest.run);
            setExpanded(true);
          } else {
            setMessage("AI 请求没有完成。");
          }
        } catch {
          setMessage("AI 请求没有完成。");
        }
      }
    } finally {
      setSending(false);
    }
  };

  if (!visible) return null;
  const recordedSteps = run?.tool_steps ?? [];

  return (
    <section className="rev-mobile-compat-agent" data-testid="rev-mobile-compat-agent">
      <div className="rev-mobile-compat-agent-head">
        <span className="rev-mobile-compat-agent-icon" aria-hidden="true"><Activity size={18} /></span>
        <div className="rev-mobile-compat-agent-title">
          <span>行程助手</span>
          <strong role="status">
            {loadState === "unauthorized" ? "请重新进入行程" : loadState === "offline" ? "服务连接失败" : loadState === "loading" ? "正在读取记录" : stateLabel(run, snapshot?.configured === true, aiDisabled)}
          </strong>
        </div>
      </div>
      {loadState === "ready" && snapshot?.configured && !aiDisabled && (
        <div className="rev-mobile-compat-agent-controls">
          <span>点击后把这趟行程的信息交给助手</span>
          <button type="button" onClick={() => void startRun()} disabled={sending || Boolean(run && !isTerminal(run.status)) || loadState !== "ready"} data-testid="rev-mobile-compat-agent-start">
            {sending ? <CircleDashed size={15} aria-hidden="true" /> : <Send size={15} aria-hidden="true" />}
            {sending ? "正在请求" : "检查行程"}
          </button>
        </div>
      )}
      {loadState === "ready" && !snapshot?.configured && !run && (
        <p className="rev-mobile-compat-agent-message" role="status" data-testid="rev-mobile-compat-agent-empty">
          暂无助手运行记录。
        </p>
      )}
      {message && <p className="rev-mobile-compat-agent-message" role="alert"><CircleAlert size={15} aria-hidden="true" />{message}</p>}
      <details className="rev-mobile-compat-agent-tech"><summary>高级信息</summary><span>WB2API · 行程助手通道</span></details>
      {run && (
        <div className="rev-mobile-compat-agent-detail">
          <button type="button" className="rev-mobile-compat-agent-toggle" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>
            <Wrench size={15} aria-hidden="true" />
            {expanded ? "收起工作记录" : "查看工作记录"}
            {run.tool_call_recorded && <span>{run.tool_steps.length} 条工具记录</span>}
          </button>
          {expanded && (
            <div className="rev-mobile-compat-agent-events" data-testid="rev-mobile-compat-agent-events">
              {recordedSteps.length > 0 ? (
                <ol>
                  {recordedSteps.map((step) => (
                    <li key={step.sequence_no + ":" + step.tool_name}>
                      {step.status === "COMPLETED" ? <CircleCheck size={15} aria-hidden="true" /> : <CircleAlert size={15} aria-hidden="true" />}
                      <span>{TOOL_LABELS[step.tool_name] ?? "行程检查"}</span>
                      <time>{safeTime(step.completed_at ?? step.created_at) ?? ""}</time>
                    </li>
                  ))}
                </ol>
              ) : (
                <p>{run.verification === "MODEL_NOT_VERIFIED" ? "尚无工具记录。" : "正在读取工作记录。"}</p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
