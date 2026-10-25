import { useEffect, useRef, useState } from "react";
import { Activity, Clock3, RefreshCw, ShieldCheck } from "lucide-react";
import { cityNexusApi, type GuardianStream } from "../../api/citynexus";
import type { ReplanProposal } from "../../contracts/replan";
import { readTravelerBearer, subscribeTravelerBearer } from "../../lib/travelerSession";
import "./GuardianRealityPanel.css";

type RequestState = "idle" | "loading" | "ready" | "offline" | "unauthorized";
type StreamEntry = GuardianStream["stream"][number];

const eventLabels: Record<string, string> = {
  TRAFFIC_DELAY: "交通出现延误",
  CLOSURE: "地点或路段暂停服务",
  WEATHER: "天气情况发生变化",
  SCHEDULE_DELAY: "行程时间需要调整",
  OPPORTUNITY_WINDOW: "出现新的出行时机",
  SERVICE_UNAVAILABLE: "一项服务暂不可用",
  USER_CHANGE: "行程已更新",
  OTHER: "行程情况更新",
};

const eventStatusLabels: Record<string, string> = {
  DETECTED: "待处理",
  OPEN: "待处理",
  ACTIVE: "处理中",
  ACKNOWLEDGED: "已查看",
  RESOLVED: "已处理",
  IGNORED: "已忽略",
};

const severityLabels: Record<string, string> = {
  INFO: "提示",
  MINOR: "轻微",
  MAJOR: "重要",
  CRITICAL: "紧急",
};

const impactStatusLabels: Record<string, string> = {
  ASSESSED: "影响已评估",
  COMPLETED: "影响已评估",
  UNCERTAIN: "影响待核实",
  UNRESOLVED: "影响待核实",
  RECOVERY_REQUIRED: "需要调整行程",
  NO_ACTION: "暂不需要调整",
};

const decisionLabels: Record<string, string> = {
  NO_ACTION: "暂不调整",
  WATCH: "继续留意",
  RECOVERY_REQUIRED: "需要调整行程",
  PREEMPTIVE_RECOVERY: "提前准备备选方案",
};

const actionStatusLabels: Record<string, string> = {
  NO_ACTION: "暂不需要处理",
  MODEL_NO_ACTION: "暂不需要处理",
  MISSION_REQUIRED: "等待行程任务信息",
  PLANNING: "正在整理调整方案",
  PROPOSAL_PRESENTED: "调整方案已生成，等待查看",
  APPROVAL_PENDING: "等待你确认",
  COMPLETED: "处理已完成",
  EXECUTED: "已执行获准的操作",
  UNRESOLVED: "问题仍待解决",
  RETRYABLE_FAILURE: "上一步未完成",
  NO_FEASIBLE_RECOVERY: "暂未找到可行调整",
};

const reasonLabels: Record<string, string> = {
  TRAFFIC_DELAY: "交通延误",
  CLOSURE: "地点或路段暂停服务",
  WEATHER: "天气变化",
  SCHEDULE_DELAY: "行程时间变化",
  SERVICE_UNAVAILABLE: "服务不可用",
  OPPORTUNITY_WINDOW: "出行时机变化",
  USER_CHANGE: "行程更新",
};

const providerLabels: Record<string, string> = {
  openstreetmap: "OpenStreetMap",
  osm: "OpenStreetMap",
  overpass: "OpenStreetMap",
  photon: "Photon 地图数据",
  nominatim: "Nominatim 地图数据",
  amap: "高德地图",
  gaode: "高德地图",
  system: "CityNexus",
};

const provenanceLabels: Record<string, string> = {
  PROVIDER_VERIFIED: "外部来源已核实",
  USER_REPORTED: "来自你提供的信息",
  SYSTEM_DERIVED: "系统整理",
  SIMULATED: "模拟记录",
  TEST_PROVIDER: "测试记录",
  LIVE_PROVIDER: "实时来源",
};

function timeLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds)) return null;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(milliseconds);
}

function label(map: Record<string, string>, value: string, fallback: string): string {
  return Object.hasOwn(map, value) ? map[value] : fallback;
}

function pulseLabel(status: string): string {
  const labels: Record<string, string> = {
    RUNNING: "正在检查",
    QUEUED: "等待检查",
    COMPLETED: "检查已完成",
    FAILED: "检查未完成",
    CANCELLED: "检查已停止",
  };
  return label(labels, status, "已有检查记录");
}

function recoveryStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    OPEN: "正在处理",
    COMMITTED: "调整方案已确认",
    SUPERSEDED: "已进入新一轮调整",
    ABANDONED: "本轮已结束",
  };
  return label(labels, status, "恢复状态已记录");
}

/** A fixture signal is a classroom injection, never a venue's own closure notice. */
const SCENARIO_PROVIDER = /fixture|city-signal/i;

function sourceLabel(provider: string, provenance: string): string {
  if (SCENARIO_PROVIDER.test(provider)) {
    return "模拟供应商信号 · 课堂注入，非景区官方公告";
  }
  const safeProvider = providerLabels[provider.toLowerCase()] ?? "行程记录";
  const safeProvenance = label(provenanceLabels, provenance, "来源已记录");
  return `${safeProvider} · ${safeProvenance}`;
}

function triggerEntries(snapshot: GuardianStream): StreamEntry[] {
  const ids = new Set(snapshot.recovery_epoch?.triggering_event_ids ?? []);
  return snapshot.stream.filter(({ observation }) => ids.has(observation.id));
}

/** What this proposal changes, in the traveller's own words; counts stand in for missing names. */
function pendingProposalSentence(proposal: ReplanProposal, titles: Record<string, string>): string {
  const parts: string[] = [];
  const removed = proposal.diff.removed.map((key) => titles[key]).filter((value): value is string => Boolean(value));
  if (proposal.diff.removed.length > 0) {
    parts.push(removed.length > 0 ? `移除${removed.join("、")}` : `移除 ${proposal.diff.removed.length} 站`);
  }
  const added = proposal.diff.added.map((key) => titles[key]).filter((value): value is string => Boolean(value));
  if (proposal.diff.added.length > 0) {
    parts.push(added.length > 0 ? `加入${added.join("、")}` : `加入 ${proposal.diff.added.length} 站`);
  }
  const travel = proposal.diff.travel_delta_min;
  if (typeof travel === "number" && travel !== 0) {
    parts.push(travel < 0 ? `路上少 ${Math.abs(travel)} 分钟` : `路上多 ${travel} 分钟`);
  }
  return parts.length > 0 ? `${parts.join("；")}。` : "这一版调整了行程安排。";
}

export function GuardianRealityPanel({
  journeyId,
  visible = false,
  active = false,
}: {
  journeyId: string;
  visible?: boolean;
  active?: boolean;
}) {
  const [snapshot, setSnapshot] = useState<{
    journeyId: string;
    bearer: string;
    value: GuardianStream;
  } | null>(null);
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [identityRevision, setIdentityRevision] = useState(0);
  const requestEpoch = useRef(0);

  useEffect(() => {
    const epoch = ++requestEpoch.current;
    setSnapshot(null);
    if (!visible) {
      setRequestState("idle");
      return () => { requestEpoch.current += 1; };
    }

    const startingBearer = readTravelerBearer();
    setRequestState(startingBearer ? "loading" : "unauthorized");
    const unsubscribe = subscribeTravelerBearer((bearer) => {
      if (bearer === startingBearer) return;
      requestEpoch.current += 1;
      setSnapshot(null);
      setRequestState(bearer ? "loading" : "unauthorized");
      setIdentityRevision((revision) => revision + 1);
    });

    if (startingBearer) {
      void cityNexusApi.getGuardianStream(journeyId).then((response) => {
        if (requestEpoch.current !== epoch || readTravelerBearer() !== startingBearer) return;
        if (response.journey_id !== journeyId) {
          setRequestState("offline");
          return;
        }
        setSnapshot({ journeyId, bearer: startingBearer, value: response });
        setRequestState("ready");
      }).catch(() => {
        if (requestEpoch.current !== epoch || readTravelerBearer() !== startingBearer) return;
        setRequestState("offline");
      });
    }

    return () => {
      requestEpoch.current += 1;
      unsubscribe();
    };
  }, [journeyId, visible, identityRevision]);

  useEffect(() => {
    if (!visible || !active || requestState !== "ready" || !readTravelerBearer()) return;
    const timer = window.setTimeout(() => setIdentityRevision((revision) => revision + 1), 10_000);
    return () => window.clearTimeout(timer);
  }, [visible, active, requestState, identityRevision]);

  const [proposal, setProposal] = useState<{ value: ReplanProposal; titles: Record<string, string> } | null>(null);
  const [proposalState, setProposalState] = useState<"idle" | "loading" | "ready" | "acting" | "done" | "error">("idle");
  const [proposalNote, setProposalNote] = useState("");
  const proposalRef = useRef<HTMLElement | null>(null);
  const loadingRef = useRef<HTMLParagraphElement | null>(null);

  useEffect(() => {
    if (!visible || requestState !== "ready" || !readTravelerBearer()) return;
    if (proposal !== null || proposalState === "acting" || proposalState === "done") return;
    let cancelled = false;
    setProposalState("loading");
    void cityNexusApi.listReplans(journeyId).then(async (items) => {
      // The list can hold a node from an older trip change. When a simulation run
      // is paused on an event, prefer the proposal bound to that event; otherwise
      // fall back to the newest PRESENTED node.
      type PausedRun = { run_id?: string; state?: { pending_event_id?: string | null } | null };
      const current = await fetch(
        `/api/v1/journeys/${journeyId}/simulation/runs/current`,
        {
          headers: { Accept: "application/json", Authorization: `Bearer ${readTravelerBearer()}` },
          cache: "no-store",
        },
      ).then((response) => (response.ok ? response.json() : null)).catch(() => null) as
        | (PausedRun & { run?: PausedRun | null })
        | null;
      // This endpoint answers with the bare run row, not a wrapper; accept both.
      const run = current ? (current.run ?? current) : null;
      const pendingEventId = run?.state?.pending_event_id ?? null;
      let pausedProposalId: string | null = null;
      if (run?.run_id) {
        const progress = await fetch(
          `/api/v1/journeys/${journeyId}/simulation/runs/${run.run_id}/progress`,
          {
            headers: { Accept: "application/json", Authorization: `Bearer ${readTravelerBearer()}` },
            cache: "no-store",
          },
        ).then((response) => (response.ok ? response.json() : null)).catch(() => null) as
          | { proposals?: Array<{ id?: string; status?: string }> }
          | null;
        pausedProposalId = (progress?.proposals ?? []).find(
          (item) => item.status === "PRESENTED" && typeof item.id === "string",
        )?.id ?? null;
      }
      const presented = items.filter((item) => item.status === "PRESENTED");
      const candidate =
        (pausedProposalId ? presented.find((item) => item.id === pausedProposalId) : undefined)
        ?? (pendingEventId ? presented.find((item) => item.trigger_event_id === pendingEventId) : undefined)
        ?? presented[0];
      // When the paused run's own proposal is not in this list, offering another
      // event's node would move the wrong plan. Say where the adjustment lives.
      if (pendingEventId && !presented.some(
        (item) => item.id === pausedProposalId || item.trigger_event_id === pendingEventId,
      )) {
        if (!cancelled) {
          setProposalState("idle");
          setProposalNote("当前模拟事件的调整在课堂控制台接受；这里没有与它对应的建议。");
        }
        return;
      }
      if (!candidate) {
        if (!cancelled) setProposalState("idle");
        return;
      }
      let titles: Record<string, string> = {};
      try {
        const plan = await cityNexusApi.getPlan(candidate.base_plan_version_id);
        titles = Object.fromEntries(plan.activities.map((activity) => [
          activity.place_id ?? activity.city_service_id ?? activity.title,
          activity.title,
        ]));
      } catch {
        titles = {};
      }
      if (!cancelled) {
        setProposal({ value: candidate, titles });
        setProposalState("ready");
        // The card can sit below the fold on a phone; bring it into view once so
        // pressing 行程守护 actually shows the decision instead of its heading.
        window.requestAnimationFrame(() => {
          // Measured on a 1280×900 projector: the card lands a hundred pixels below the fold,
          // and the fixed composer covers its buttons once it only just enters view. Centre it
          // on every shape, then re-centre while the plan titles and map settle: pressing the
          // guardian button three seconds after entry used to scroll against a shorter page.
          const bring = () => proposalRef.current?.scrollIntoView({ block: "center" });
          bring();
          window.setTimeout(bring, 400);
          window.setTimeout(bring, 1000);
        });
      }
    }).catch(() => {
      if (!cancelled) {
        setProposalState("error");
        setProposalNote("这次没能读到调整方案，可以稍后刷新。");
      }
    });
    return () => { cancelled = true; };
  }, [journeyId, visible, requestState, proposal, proposalState]);

  useEffect(() => {
    // The panel opens low in the page; without this the "reading" line sits under the composer
    // and a slow /replans looks like a press that did nothing.
    if (proposalState !== "loading" || proposal) return;
    window.requestAnimationFrame(() => loadingRef.current?.scrollIntoView({ block: "center" }));
  }, [proposalState, proposal]);

  const settleProposal = async (decision: "accept" | "reject") => {
    if (!proposal || proposalState === "acting") return;
    setProposalState("acting");
    setProposalNote("");
    try {
      if (decision === "accept") {
        await cityNexusApi.acceptReplan(proposal.value.id, `guardian-accept-${proposal.value.id.slice(0, 8)}`);
        // The accepted plan replaces the page; without this the viewport stays near where the
        // card sat and the first-stop change happens thousands of pixels above the screen.
        window.requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: "auto" }));
      } else {
        await cityNexusApi.rejectReplan(proposal.value.id, `guardian-reject-${proposal.value.id.slice(0, 8)}`);
      }
      setProposal(null);
      setProposalState("done");
      setProposalNote(decision === "accept" ? "行程已按这份调整更新。" : "已保留原来的安排。");
      window.dispatchEvent(new CustomEvent("citynexus:mission-refresh"));
      setIdentityRevision((revision) => revision + 1);
      if (decision === "accept") {
        // The plan this screen was built from no longer exists; reload so every
        // panel (including LiveRecovery's itinerary line) reads the new active
        // plan instead of leaving the traveller on a stale first stop.
        window.setTimeout(() => window.location.reload(), 1200);
      }
    } catch {
      setProposalState("error");
      setProposalNote(decision === "accept"
        ? "这次没能更新行程，可以再试一次。"
        : "这次没能记下你的选择，可以再试一次。");
    }
  };

  if (!visible) return null;

  const currentBearer = readTravelerBearer();
  const currentSnapshot = snapshot?.journeyId === journeyId && snapshot.bearer === currentBearer
    ? snapshot.value
    : null;
  const state = !currentBearer ? "unauthorized" : requestState;
  const hasRecords = Boolean(currentSnapshot && currentSnapshot.stream.length > 0);
  const triggers = currentSnapshot ? triggerEntries(currentSnapshot) : [];

  return (
    <section className="rev-guardian-panel" data-testid="rev-guardian-reality-panel" aria-label="行程守护记录">
      <header className="rev-guardian-panel-head">
        <span className="rev-guardian-panel-icon" aria-hidden="true"><ShieldCheck size={18} /></span>
        <div>
          <strong>行程守护</strong>
          <span>检查记录与处理进展</span>
        </div>
        <button type="button" aria-label="刷新行程守护记录" disabled={state === "loading"}
          onClick={() => setIdentityRevision((revision) => revision + 1)}><RefreshCw size={16} /></button>
      </header>

      {state === "loading" && <p className="rev-guardian-state" role="status">正在读取守护记录…</p>}
      {state === "unauthorized" && <p className="rev-guardian-state" role="status">请登录后查看当前行程的守护记录。</p>}
      {state === "offline" && <p className="rev-guardian-state" role="status">行程守护记录暂时无法读取。</p>}

      {state === "ready" && currentSnapshot && (
        <>
          <div className="rev-guardian-summary" role="status">
            {hasRecords ? (
              <>
                <span>{currentSnapshot.counts.events} 项变化</span>
                <span>{currentSnapshot.counts.impacts} 项影响</span>
                <span>{currentSnapshot.counts.actions} 项行动</span>
              </>
            ) : (
              <span>行程守护还没有检查记录</span>
            )}
            <span className="rev-guardian-watch-state">
              {currentSnapshot.watch.latest_pulse
                ? pulseLabel(currentSnapshot.watch.latest_pulse.status)
                : currentSnapshot.status === "WATCH_NOT_RUNNING"
                  ? "当前没有运行中的守护检查"
                  : "已读取到守护记录"}
            </span>
          </div>

          {currentSnapshot.watch.configured && (
            <p className="rev-guardian-configured">守护规则已设置</p>
          )}
          {currentSnapshot.watch.last_observed_at && (
            <p className="rev-guardian-last-seen">
              <Clock3 size={13} aria-hidden="true" />
              最近记录：{timeLabel(currentSnapshot.watch.last_observed_at) ?? "时间未提供"}
            </p>
          )}

          {currentSnapshot.recovery_epoch && (
            <section className="rev-guardian-epoch" aria-label="当前恢复轮次">
              <div className="rev-guardian-epoch-head">
                <strong>当前恢复第 {currentSnapshot.recovery_epoch.generation} 轮</strong>
                <span>{recoveryStatusLabel(currentSnapshot.recovery_epoch.status)}</span>
              </div>
              <div className="rev-guardian-trigger-list">
                <span>触发记录</span>
                {triggers.length > 0 ? (
                  <ul>
                    {triggers.map(({ observation }) => (
                      <li key={observation.id}>
                        {label(eventLabels, observation.event_type, "行程变化")}
                        {timeLabel(observation.detected_at) ? ` · ${timeLabel(observation.detected_at)}` : ""}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <small>{currentSnapshot.recovery_epoch.triggering_event_ids.length} 条记录</small>
                )}
              </div>
            </section>
          )}

          {proposalState === "loading" && !proposal && (
            <p ref={loadingRef} className="rev-guardian-proposal-loading" role="status" data-testid="rev-guardian-proposal-loading">
              正在读取调整建议…
            </p>
          )}
          {proposal && (
            <section ref={proposalRef} className="rev-guardian-proposal" data-testid="rev-guardian-proposal" aria-label="调整建议">
              <strong>找到一份可行的调整</strong>
              <p data-testid="rev-guardian-proposal-diff">{pendingProposalSentence(proposal.value, proposal.titles)}</p>
              <small className="rev-guardian-proposal-origin" data-testid="rev-guardian-proposal-origin">
                {proposal.value.source_agent_run_id
                  ? "Agent 生成 · 服务器留有运行记录"
                  : "规则引擎生成 · 不是大模型现场推理"}
              </small>
              <div className="rev-guardian-proposal-actions">
                <button type="button" data-testid="rev-guardian-accept-replan"
                  disabled={proposalState === "acting"} onClick={() => void settleProposal("accept")}>
                  {proposalState === "acting" ? "正在更新行程…" : "接受这份调整"}
                </button>
                <button type="button" data-testid="rev-guardian-reject-replan"
                  disabled={proposalState === "acting"} onClick={() => void settleProposal("reject")}>暂不调整</button>
              </div>
            </section>
          )}
          {proposalNote && (
            <p className="rev-guardian-proposal-note" role="status" data-testid="rev-guardian-proposal-note">{proposalNote}</p>
          )}

          {hasRecords && (
            <ol className="rev-guardian-events">
              {currentSnapshot.stream.map(({ observation, impact, proposed_action }) => (
                <li className="rev-guardian-event" key={observation.id} data-testid="rev-guardian-event">
                  <div className="rev-guardian-event-title">
                    <Activity size={15} aria-hidden="true" />
                    <strong>{label(eventLabels, observation.event_type, "行程变化")}</strong>
                    <span>{label(severityLabels, observation.severity, "待评估")}</span>
                  </div>
                  <div className="rev-guardian-event-meta">
                    <span>{label(eventStatusLabels, observation.status, "状态已记录")}</span>
                    <span>{sourceLabel(observation.provider, observation.provenance)}</span>
                    <time>{timeLabel(observation.detected_at) ?? "时间未提供"}</time>
                  </div>
                  {impact && (
                    <div className="rev-guardian-linked-state">
                      <strong>{impact.uncertain
                        ? "影响待核实"
                        : label(impactStatusLabels, impact.status, "行程影响已记录")}</strong>
                      {impact.reason_codes.length > 0 && (
                        <span>{impact.reason_codes
                          .map((code) => reasonLabels[code])
                          .filter((value): value is string => Boolean(value))
                          .join(" · ") || "相关因素待核实"}</span>
                      )}
                    </div>
                  )}
                  {proposed_action && (
                    <div className="rev-guardian-linked-state rev-guardian-action">
                      <strong>{label(decisionLabels, proposed_action.decision, "处理建议已记录")}</strong>
                      <span>{label(actionStatusLabels, proposed_action.action_status, "处理进度已记录")}</span>
                      {proposed_action.completed_at && (
                        <time>完成于 {timeLabel(proposed_action.completed_at) ?? "时间未提供"}</time>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  );
}
