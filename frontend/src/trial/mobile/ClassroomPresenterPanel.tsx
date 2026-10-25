import { useCallback, useEffect, useState } from "react";
import { travelerAuthHeaders } from "../../lib/travelerSession";
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
  GUARDIAN_REQUESTED: "守护已接手",
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
          const progress = await progressResponse.json() as {
            proposals?: Array<{ status?: string }>;
            guardian_runs?: Array<{ proposal_id?: string | null }>;
          };
          setAcceptanceHasProposal(Boolean(
            (progress.proposals ?? []).some((item) => item.status === "PRESENTED")
            || (progress.guardian_runs ?? []).some((item) => Boolean(item.proposal_id)),
          ));
        } else {
          setAcceptanceHasProposal(false);
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
    let cancelled = false;
    const tick = () => {
      void refresh().catch(() => {
        if (!cancelled) setHidden(true);
      });
    };
    tick();
    // The clock strip on the same screen advances the same run; without polling this
    // panel would keep showing the hour it saw on mount while the strip moves on.
    const timer = window.setInterval(tick, 10_000);
    return () => {
      cancelled = true;
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
        {run?.status === "PAUSED_FOR_ACCEPTANCE" && acceptanceHasProposal && (
          <button type="button" disabled={busy} onClick={() => act(() => simulationApi.resume(journeyId, run.run_id, run.sequence))}>
            继续模拟
          </button>
        )}
        {run?.status === "PAUSED_MODEL_UNAVAILABLE" && (
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

      {run?.status === "PAUSED_FOR_ACCEPTANCE" && !acceptanceHasProposal && (
        <p className="rev-presenter-note" data-testid="rev-presenter-acceptance-note">
          守护没有交出可接受的提案（进度里看不到提案 id）；这条模拟解不开，请重启课堂演示（双击启动器）。
        </p>
      )}

      {run?.status === "PAUSED_MODEL_UNAVAILABLE" && (
        <p className="rev-presenter-note" data-testid="rev-presenter-model-note">
          现场模型没有接上；同一起事件要在下方守护屏上处理，处理完再按上面的继续。
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
          {run.history.slice(-3).map((step, index) => (
            <li key={`${step.sequence ?? index}`}>
              {EVENT_TEXT[String(step.event)] ?? "推进"} · {shortTime(step.virtual_now)}
            </li>
          ))}
        </ol>
      )}

      <p className="rev-presenter-truth">模拟时钟与模拟 GPS 推进；不生成设备到场证明，也不把模拟说成实际到访。</p>
    </section>
  );
}
