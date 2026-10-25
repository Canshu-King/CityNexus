import { useCallback, useEffect, useState } from "react";
import { travelerAuthHeaders } from "../../lib/travelerSession";
import { cityNexusApi } from "../../api/citynexus";
import { simulationApi, SimulationError, type SimulationCities, type SimulationRun } from "./simulationClient";
import "./ClassroomPresenterPanel.css";

/**
 * Teacher-facing console for Codex's SimulationRun contract. It renders nothing
 * while the endpoints are not deployed, so today's classroom screen keeps its
 * existing shape; once they land the same panel becomes the presenter's controls.
 */

const STATUS_TEXT: Record<string, string> = {
  NOT_STARTED: "尚未开演",
  RUNNING: "模拟进行中",
  PAUSED_FOR_GUARDIAN: "等待守护决策",
  GUARDIAN_RUNNING: "守护正在分析",
  PAUSED_FOR_ACCEPTANCE: "等待接受调整",
  PAUSED_MODEL_UNAVAILABLE: "现场模型不可用，已暂停",
  PAUSED_REQUIRES_MISSION: "缺少守护任务",
  SIMULATED_COMPLETED: "模拟行程已完成",
};

const EVENT_TEXT: Record<string, string> = {
  SIM_STARTED: "开演",
  SIM_DEPARTURE: "出发",
  SIM_ARRIVAL: "到达",
  SIM_EXPERIENCE: "游览",
  SIM_ACTIVITY_COMPLETED: "完成一站",
  SIM_SCENE_INJECTED: "注入事件",
  SIMULATED_COMPLETED: "两日走完",
  SIM_PLAN_CHANGED: "计划已按守护调整",
  SIM_RESUMED: "继续模拟",
  GUARDIAN_REQUESTED: "守护已接手",
  GUARDIAN_RESULT: "守护已交出建议",
  GUARDIAN_UNAVAILABLE: "守护模型不可用",
};

const MISSING_TEXT: Record<string, string> = {
  VERIFIED_CITY_ADCODE_REQUIRED: "城市身份未核实",
  AT_LEAST_5_ACQUIRED_POI_REQUIRED: "真实来源地点不足五处",
  AT_LEAST_3_CAPTURED_ROUTES_REQUIRED: "真捕获路线不足三条",
};

const ERROR_TEXT: Record<string, string> = {
  SIMULATION_NOT_RUNNING: "模拟没有在推进，先处理等待中的事件。",
  SIMULATION_EVENT_REQUIRES_SIGNED_RESOLUTION: "这件事要在守护屏上按原生产品流程解决，再继续。",
  SIMULATION_SEQUENCE_STALE: "读数已经变了，请刷新后再按。",
  SIMULATION_SCENE_ACTIVITY_INVALID: "只能给当前或之后的一站注入事件。",
  SIMULATION_SCENE_ALREADY_APPLIED: "这件事已经注入过。",
  USE_SIMULATION_RUN_ADVANCE: "这个行程已经由模拟执行接管，请用这块控制台推进。",
  DEMO_PRESENTER_REQUIRED: "这台设备不是演示主机，控制台只在本机可用。",
  JOURNEY_EXECUTION_UPDATE_REQUIRED: "当前会话没有推进执行的权限。",
};

function shortTime(value: unknown): string {
  if (typeof value !== "string") return "";
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(value);
  return match ? `${match[2]}-${match[3]} ${match[4]}:${match[5]}` : value;
}

function missingText(missing: string[]): string {
  return missing.map((code) => MISSING_TEXT[code] ?? "来源条件未满足").join("、");
}

function errorText(caught: unknown): string {
  if (caught instanceof SimulationError) {
    return ERROR_TEXT[caught.detail] ?? ERROR_TEXT[caught.code]
      ?? (caught.status === 409 ? "这一步和当前模拟状态对不上，请先刷新。" : "这一步没有成功，请刷新后再试。");
  }
  return "网络没有回应，请刷新后再试。";
}

type PlanStop = { id?: string; title?: string; status?: string; start_at?: string };

export function ClassroomPresenterPanel({ journeyId, visible }: { journeyId: string; visible: boolean }) {
  const [cities, setCities] = useState<SimulationCities | null>(null);
  const [run, setRun] = useState<SimulationRun | null>(null);
  const [stops, setStops] = useState<PlanStop[]>([]);
  const [available, setAvailable] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [slowNote, setSlowNote] = useState<string | null>(null);
  const [acceptanceHasProposal, setAcceptanceHasProposal] = useState(false);
  const [guardianOutcome, setGuardianOutcome] = useState<{ code?: string; error_code?: string } | null>(null);
  const [simulationProposal, setSimulationProposal] = useState<{ id: string } | null>(null);
  const [pendingResolved, setPendingResolved] = useState(false);

  const refresh = useCallback(async () => {
    const [nextCities, nextCurrent] = await Promise.all([
      simulationApi.cities(journeyId, 17),
      simulationApi.current(journeyId),
    ]);
    if (!nextCities.available && !nextCurrent.available) {
      setHidden(true);
      return;
    }
    setAvailable(true);
    setCities(nextCities.available ? nextCities : null);
    if (nextCurrent.available) {
      setRun(nextCurrent.run);
      if (nextCurrent.run) {
        // PAUSED_FOR_ACCEPTANCE is only resumable when a proposal is actually
        // visible to the progress projection; otherwise the button can only 409.
        const progressResponse = await fetch(
          `/api/v1/journeys/${journeyId}/simulation/runs/${nextCurrent.run.run_id}/progress`,
          { headers: { Accept: "application/json", ...travelerAuthHeaders() }, cache: "no-store" },
        ).catch(() => null);
        if (progressResponse?.ok) {
          try {
            const progress = await progressResponse.json() as {
              proposals?: Array<{ id?: string; status?: string }>;
              guardian_runs?: Array<{ proposal_id?: string | null }>;
              guardian_outcome?: { code?: string; error_code?: string } | null;
              readiness?: { pending_event_id?: string | null };
              events?: Array<{ id?: string; status?: string }>;
            };
            setAcceptanceHasProposal(Boolean(
              (progress.proposals ?? []).some((item) => item.status === "PRESENTED")
              || (progress.guardian_runs ?? []).some((item) => Boolean(item.proposal_id)),
            ));
            // The projection knows why an attempt produced no proposal; without it the
            // console says "analysing" forever after a failed model request.
            setGuardianOutcome(progress.guardian_outcome ?? null);
            const presented = (progress.proposals ?? []).find(
              (item) => item.status === "PRESENTED" && typeof item.id === "string",
            );
            setSimulationProposal(presented?.id ? { id: presented.id } : null);
            const pendingId = progress.readiness?.pending_event_id ?? null;
            const pendingEvent = (progress.events ?? []).find((item) => item.id === pendingId);
            // Resume is refused until the pending event itself is resolved; a presented
            // proposal alone is not a resume key.
            setPendingResolved(Boolean(
              pendingEvent && (pendingEvent.status === "RESOLVED" || pendingEvent.status === "IGNORED"),
            ));
          } catch {
            // Keep the last reading; one bad payload must not hide the resume key.
          }
        }
      }
      const planId = typeof nextCurrent.run?.state?.plan_version_id === "string"
        ? nextCurrent.run.state.plan_version_id
        : "";
      if (planId) {
        const response = await fetch(`/api/v1/plans/${planId}`, {
          headers: { Accept: "application/json", ...travelerAuthHeaders() },
          cache: "no-store",
        });
        if (response.ok) {
          const plan = (await response.json()) as { activities?: PlanStop[] };
          setStops(plan.activities ?? []);
        }
      }
    }
  }, [journeyId]);

  useEffect(() => {
    const listener = (event: Event) => {
      const detail = (event as CustomEvent<SimulationRun>).detail;
      if (detail?.run_id) setRun(detail);
    };
    window.addEventListener("citynexus:simulation-run", listener);
    return () => window.removeEventListener("citynexus:simulation-run", listener);
  }, []);

  useEffect(() => {
    if (!visible) return;
    const tick = () => {
      // A transient network error must not hide the console; refresh() itself
      // hides only when both endpoints answer 404/405 (not deployed).
      void refresh().catch(() => {});
    };
    tick();
    // The clock strip on the same screen advances the same run; without polling this
    // panel would keep showing the hour it saw on mount while the strip moves on.
    const timer = window.setInterval(tick, 10_000);
    return () => {
      window.clearInterval(timer);
    };
  }, [visible, refresh]);

  const act = async (action: () => Promise<SimulationRun | null>, slow?: string) => {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    setSlowNote(slow ?? null);
    try {
      const next = await action();
      if (next) setRun(next);
      await refresh();
    } catch (caught) {
      setMessage(errorText(caught));
    } finally {
      setSlowNote(null);
      setBusy(false);
    }
  };

  if (!visible || hidden || !available) return null;
  const blocked = cities?.cities.filter((city) => city.status !== "ELIGIBLE_CAPTURED_SNAPSHOT") ?? [];
  const shortOfCity = (cities?.eligible_count ?? 0) < (cities?.required ?? 0);
  const missing = Array.from(new Set(blocked.flatMap((city) => city.missing)));
  const completedIds = Array.isArray(run?.state?.completed_activity_ids)
    ? (run.state.completed_activity_ids as unknown[]).map(String)
    : [];
  const currentStop = stops
    .filter((stop) => stop.id && !completedIds.includes(stop.id) && stop.status !== "COMPLETED")
    .sort((a, b) => (a.start_at ?? "").localeCompare(b.start_at ?? ""))[0];

  const inject = (eventType: string, delayMinutes: number) => {
    if (!run || !currentStop?.id) return;
    void act(() => simulationApi.scene(journeyId, run.run_id, run.sequence, {
      scene_id: `${eventType.toLowerCase()}-${Date.now()}`,
      event_type: eventType,
      activity_id: currentStop.id,
      ...(delayMinutes ? { delay_minutes: delayMinutes } : {}),
    }));
  };

  return (
    <section className="rev-presenter" data-testid="rev-presenter" aria-label="演示者控制台">
      <header>
        <strong>课堂控制台 · 模拟执行</strong>
        <span className="rev-presenter-status" data-testid="rev-presenter-run">
          {run ? `${STATUS_TEXT[run.status] ?? run.status} · ${shortTime(run.virtual_now)}` : "尚未开演"}
        </span>
      </header>

      {cities && (!run || run.status === "NOT_STARTED") && (
        <p className="rev-presenter-cities" data-testid="rev-presenter-cities">
          随机城市池：可用 {cities.eligible_count} 座，标准要 {cities.required} 座；这趟演示用行程自己的城市，仍可开演。
          {shortOfCity && missing.length > 0 && <small> · 池子还差：{missingText(missing)}</small>}
        </p>
      )}

      <div className="rev-presenter-actions">
        {(!run || run.status === "NOT_STARTED") && (
          <button type="button" disabled={busy} onClick={() => act(() => simulationApi.start(journeyId, 17))}>
            开演（模拟两日）
          </button>
        )}
        {run?.status === "RUNNING" && (
          <span className="rev-presenter-hint" data-testid="rev-presenter-advance-hint">
            推进用上面的「课堂时空模拟」三个键；这里只管事件、守护和恢复。
          </span>
        )}
        {run?.status === "PAUSED_FOR_GUARDIAN" && (
          <button
            type="button"
            disabled={busy}
            onClick={() => act(
              () => simulationApi.guardian(journeyId, run.run_id, run.sequence),
              "守护正在分析：接上模型时实测要四分钟左右；没接模型会一直停在等待。请别重复按。",
            )}
          >
            交给守护助手
          </button>
        )}
        {run?.status === "PAUSED_FOR_ACCEPTANCE" && simulationProposal && !pendingResolved && (
          <button
            type="button"
            disabled={busy}
            onClick={() => act(async () => {
              await cityNexusApi.acceptReplan(
                simulationProposal.id,
                `classroom-accept-${simulationProposal.id.slice(0, 8)}`,
              );
              return null;
            }, "正在把这份调整写进计划；可能要几十秒，别重复按。")}
          >
            接受这次事件的调整
          </button>
        )}
        {run?.status === "PAUSED_FOR_ACCEPTANCE" && pendingResolved && (
          <button type="button" disabled={busy} onClick={() => act(() => simulationApi.resume(journeyId, run.run_id, run.sequence))}>
            继续模拟
          </button>
        )}
        {run?.status === "PAUSED_MODEL_UNAVAILABLE" && pendingResolved && (
          <button type="button" disabled={busy} onClick={() => act(() => simulationApi.resume(journeyId, run.run_id, run.sequence))}>
            事件处理完了，继续模拟
          </button>
        )}
        <button type="button" disabled={busy} onClick={() => act(async () => null)}>
          刷新读数
        </button>
      </div>

      {run?.status === "RUNNING" && currentStop?.id && (
        <div className="rev-presenter-scenes" data-testid="rev-presenter-scenes">
          <span>
            给「{currentStop.title ?? "当前这一站"}」注入模拟事件
            <small> · 模拟事件，不是景区官方公告</small>
          </span>
          <div className="rev-presenter-scene-actions">
            <button type="button" disabled={busy} onClick={() => inject("CLOSURE", 0)}>闭馆</button>
            <button type="button" disabled={busy} onClick={() => inject("WEATHER", 0)}>下雨</button>
            <button type="button" disabled={busy} onClick={() => inject("SCHEDULE_DELAY", 30)}>延误半小时</button>
          </div>
        </div>
      )}

      {run?.status === "SIMULATED_COMPLETED" && (
        <p className="rev-presenter-done" data-testid="rev-presenter-done">
          两日模拟走完，这趟行程已封存。再演一遍请重启课堂演示（双击启动器）。
        </p>
      )}

      {run?.status === "GUARDIAN_RUNNING" && guardianOutcome?.code === "EXTERNAL_FAILED" && (
        <p className="rev-presenter-note" data-testid="rev-presenter-guardian-failed">
          守护模型这次请求失败了，没有交出建议。刷新读数不会重试；要重来请重启课堂演示（双击启动器）。
        </p>
      )}
      {run?.status === "GUARDIAN_RUNNING" && guardianOutcome?.code === "AGENT_UNRESOLVED" && (
        <p className="rev-presenter-note" data-testid="rev-presenter-guardian-unresolved">
          守护没有解出可执行的调整；刷新读数不会让它继续。要重来请重启课堂演示（双击启动器）。
        </p>
      )}
      {run?.status === "GUARDIAN_RUNNING" && guardianOutcome?.code === "MODEL_NOT_CONFIGURED" && (
        <p className="rev-presenter-note" data-testid="rev-presenter-guardian-unconfigured">
          这台演示机没有接上守护模型，请求不会自己完成；请重启课堂演示，或让管理员配好模型。
        </p>
      )}
      {run?.status === "PAUSED_FOR_ACCEPTANCE" && simulationProposal && !pendingResolved && (
        <p className="rev-presenter-note" data-testid="rev-presenter-acceptance-step">
          这次事件已经有一份可接受的调整；先按上面的「接受这次事件的调整」，事件落定后才能继续。
        </p>
      )}
      {run?.status === "PAUSED_FOR_ACCEPTANCE" && pendingResolved && (
        <p className="rev-presenter-note" data-testid="rev-presenter-resolved-note">
          这次事件已经落定，可以继续模拟。
        </p>
      )}
      {run?.status === "PAUSED_FOR_ACCEPTANCE" && acceptanceHasProposal && !simulationProposal && (
        <p className="rev-presenter-note" data-testid="rev-presenter-proposal-mismatch">
          进度里记着提案编号，但看不到可接受的内容；请重启课堂演示（双击启动器）。
        </p>
      )}
      {run?.status === "PAUSED_FOR_ACCEPTANCE" && !acceptanceHasProposal && (
        <p className="rev-presenter-note" data-testid="rev-presenter-acceptance-note">
          守护没有交出可接受的提案（进度里看不到提案 id）；这条模拟解不开，请重启课堂演示（双击启动器）。
        </p>
      )}

      {run?.status === "PAUSED_MODEL_UNAVAILABLE" && (
        <p className="rev-presenter-note" data-testid="rev-presenter-model-note">
          {guardianOutcome?.code === "EXTERNAL_FAILED"
            ? "现场模型这次请求失败了，没有交出建议。先在下方守护屏看有没有和这次事件对应的调整；没有就重启课堂演示（双击启动器）。"
            : "现场模型没有接上；同一起事件要在下方守护屏上处理，处理完这里才会出现继续。"}
        </p>
      )}

      {run?.status === "PAUSED_REQUIRES_MISSION" && (
        <p className="rev-presenter-note" data-testid="rev-presenter-mission-note">
          这趟行程还没有守护任务，模拟停在这里；先到「行程守护」建一个任务，再回来刷新。
        </p>
      )}

      {slowNote && <p className="rev-presenter-note" data-testid="rev-presenter-slow">{slowNote}</p>}

      {message && <p className="rev-presenter-message" data-testid="rev-presenter-message">{message}</p>}

      {run && run.history.length > 0 && (
        <ol className="rev-presenter-history" data-testid="rev-presenter-history">
          {run.history.slice(-5).map((step, index) => (
            <li key={`${index}-${String(step.event)}-${shortTime(step.virtual_now)}`}>
              {EVENT_TEXT[String(step.event)] ?? "推进"} · {shortTime(step.virtual_now)}
            </li>
          ))}
        </ol>
      )}

      <p className="rev-presenter-truth">模拟时钟与模拟 GPS 推进；不生成设备到场证明，也不把模拟说成实际到访。</p>
    </section>
  );
}
