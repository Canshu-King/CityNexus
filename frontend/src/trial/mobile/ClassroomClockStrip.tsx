import { useCallback, useEffect, useRef, useState } from "react";
import { travelerAuthHeaders } from "../../lib/travelerSession";
import { simulationApi, SimulationError, type SimulationRun } from "./simulationClient";
import "./ClassroomClockStrip.css";

/**
 * The classroom clock, on the journey screen itself.  The virtual time lives on
 * the server (`simulation_clocks`) so a reload keeps the hour; this strip only
 * reads it and asks the server to advance it.  It never touches the browser's
 * clock for the journey's own time, and the watermark stays on the strip.
 *
 * Once a SimulationRun exists that run owns the agenda: the same three buttons
 * drive `/simulation/runs/{id}/advance` (sequence CAS + idempotency key) and the
 * older clock/activity mutations are not sent at all, so two machines can never
 * push the same journey through two state machines at once.
 */

type ClockPayload = {
  journey_id: string;
  virtual_now: string;
  version: number;
  persisted: boolean;
  basis: string;
  current_activity_title: string | null;
  traveller: { latitude: number; longitude: number; coordinate_system?: string; label: string } | null;
};

const RUN_STATUS_TEXT: Record<string, string> = {
  RUNNING: "模拟进行中",
  PAUSED_FOR_GUARDIAN: "等待守护决策",
  GUARDIAN_RUNNING: "守护正在分析",
  PAUSED_FOR_ACCEPTANCE: "等待接受调整",
  PAUSED_MODEL_UNAVAILABLE: "现场模型不可用，已暂停",
  PAUSED_REQUIRES_MISSION: "缺少守护任务",
  SIMULATED_COMPLETED: "模拟行程已完成",
};

function stamp(value: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(date);
}

function runFailureText(caught: unknown): string {
  if (caught instanceof SimulationError) {
    if (caught.detail === "SIMULATION_NOT_RUNNING") return "模拟没有在推进：请到课堂控制台处理等待中的事件。";
    if (caught.detail === "SIMULATION_SEQUENCE_STALE") return "别的设备刚推进过，已刷新到最新一步，请再按一次。";
    if (caught.status === 409) return "这一步和当前模拟状态对不上，已刷新，请再按一次。";
    if (caught.status === 401 || caught.status === 403) return "这台设备现在没有推进模拟的权限。";
  }
  return "模拟没有推进（请求没有完成）。";
}

export function ClassroomClockStrip({ journeyId, visible }: { journeyId: string; visible: boolean }) {
  const [clock, setClock] = useState<ClockPayload | null>(null);
  const [run, setRun] = useState<SimulationRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [wallClock, setWallClock] = useState(() => new Date());
  const [stopNote, setStopNote] = useState<string | null>(null);
  const [journeyDone, setJourneyDone] = useState(false);
  const pending = useRef(false);

  const read = useCallback(async () => {
    try {
      const [response, journeyResponse, runCurrent] = await Promise.all([
        fetch(`/api/v1/demo/simulation-clock/${journeyId}`, {
          headers: { Accept: "application/json", ...travelerAuthHeaders() },
        }),
        fetch(`/api/v1/journeys/${journeyId}`, {
          headers: { Accept: "application/json", ...travelerAuthHeaders() },
        }),
        simulationApi.current(journeyId).catch(() => null),
      ]);
      setClock(response.ok ? (await response.json() as ClockPayload) : null);
      if (journeyResponse.ok) {
        const journey = await journeyResponse.json() as { status?: string };
        setJourneyDone(journey.status === "COMPLETED");
      }
      setRun(runCurrent && runCurrent.available ? runCurrent.run : null);
    } catch {
      setClock(null);
    }
  }, [journeyId]);

  useEffect(() => {
    if (!visible) return;
    void read();
    const timer = window.setInterval(() => void read(), 10_000);
    return () => window.clearInterval(timer);
  }, [visible, read]);

  useEffect(() => {
    if (!visible) return;
    const timer = window.setInterval(() => setWallClock(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, [visible]);

  const freshRun = useCallback(async (): Promise<SimulationRun | null> => {
    const current = await simulationApi.current(journeyId).catch(() => null);
    const next = current && current.available ? current.run : null;
    setRun(next);
    return next;
  }, [journeyId]);

  const advanceRun = async (target: SimulationRun, minutes?: number) => {
    if (busy) return;
    if (target.status !== "RUNNING") {
      setStopNote("模拟没有在推进：请到课堂控制台处理等待中的事件。");
      return;
    }
    setBusy(true);
    try {
      const next = await simulationApi.advance(journeyId, target.run_id, target.sequence, minutes);
      if (next) {
        setRun(next);
        window.dispatchEvent(new CustomEvent("citynexus:simulation-run", { detail: next }));
        setStopNote(minutes ? `已把模拟时间推进 ${minutes} 分钟` : `已推进到下一步（第 ${next.sequence} 步）`);
      } else {
        setStopNote("这台后端还没有模拟执行接口。");
      }
    } catch (caught) {
      setStopNote(runFailureText(caught));
      await read();
    } finally {
      setBusy(false);
    }
  };

  const advanceToNextStop = async (target: SimulationRun) => {
    if (target.status !== "RUNNING") {
      setStopNote("模拟没有在推进：请到课堂控制台处理等待中的事件。");
      return;
    }
    setBusy(true);
    let current = target;
    try {
      for (let step = 0; step < 8 && current.status === "RUNNING"; step += 1) {
        const next = await simulationApi.advance(journeyId, current.run_id, current.sequence);
        if (!next) {
          setStopNote("这台后端还没有模拟执行接口。");
          return;
        }
        current = next;
        setRun(next);
        window.dispatchEvent(new CustomEvent("citynexus:simulation-run", { detail: next }));
        const last = next.history[next.history.length - 1] as { event?: string } | undefined;
        if (last?.event === "SIM_ACTIVITY_COMPLETED" || next.status !== "RUNNING") break;
      }
      setStopNote(current.status === "SIMULATED_COMPLETED"
        ? "两日模拟已走完（不是实际到场）"
        : current.status === "RUNNING"
          ? `已走到下一站（第 ${current.sequence} 步）`
          : `模拟停在「${RUN_STATUS_TEXT[current.status] ?? current.status}」，请到课堂控制台处理。`);
    } catch (caught) {
      setStopNote(runFailureText(caught));
      await read();
    } finally {
      setBusy(false);
    }
  };

  const advance = async (minutes: number) => {
    if (busy || pending.current) return;
    pending.current = true;
    try {
      await advanceOnce(minutes);
    } finally {
      pending.current = false;
    }
  };

  const advanceOnce = async (minutes: number) => {
    // The run may have been created moments ago by the console on the same screen;
    // reading `/runs/current` before choosing the path keeps this button from sending
    // the retired clock mutation, which the backend now refuses.
    const target = run ?? await freshRun();
    if (target) {
      await advanceRun(target, minutes);
      return;
    }
    if (!clock || journeyDone) return;
    setBusy(true);
    try {
      const response = await fetch(`/api/v1/demo/simulation-clock/${journeyId}/advance`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json", ...travelerAuthHeaders() },
        body: JSON.stringify({ minutes, expected_version: clock.version }),
      });
      if (response.ok) {
        setClock(await response.json() as ClockPayload);
        setStopNote(`已把模拟时间推进 ${minutes} 分钟`);
      } else {
        await read();
        setStopNote(`时间没有推进（http_status=${response.status}）`);
      }
    } catch {
      await read();
      setStopNote("时间没有推进（请求没有完成）");
    } finally {
      setBusy(false);
    }
  };

  const advanceStop = async () => {
    if (busy || pending.current) return;
    pending.current = true;
    try {
      await advanceStopOnce();
    } finally {
      pending.current = false;
    }
  };

  const advanceStopOnce = async () => {
    const target = run ?? await freshRun();
    if (target) {
      await advanceToNextStop(target);
      return;
    }
    setBusy(true);
    setStopNote("正在推进…");
    try {
      const twinResponse = await fetch(`/api/v1/journeys/${journeyId}/twin`, { headers: { Accept: "application/json", ...travelerAuthHeaders() } });
      const twin = twinResponse.ok ? (await twinResponse.json() as { current_activity_id?: string | null }) : null;
      const activityId = twin?.current_activity_id;
      if (!activityId) {
        setStopNote("没有正在进行的活动");
        return;
      }
      // The classroom taps the same state machine a traveller would, but declares
      // SIMULATED_STATE_TRANSITION so nothing here claims physical presence.
      const steps = ["depart", "arrive", "begin", "complete"] as const;
      let lastStatus = 0;
      let completed = false;
      for (const step of steps) {
        const response = await fetch(`/api/v1/journeys/${journeyId}/activities/${activityId}/${step}`, {
          method: "POST",
          headers: { Accept: "application/json", "Content-Type": "application/json", ...travelerAuthHeaders() },
          body: JSON.stringify({ truth_kind: "SIMULATED_STATE_TRANSITION" }),
        });
        lastStatus = response.status;
        if (step === "complete") completed = response.ok;
      }
      let aligned = "";
      if (completed) {
        const twinAfterResponse = await fetch(`/api/v1/journeys/${journeyId}/twin`, { headers: { Accept: "application/json", ...travelerAuthHeaders() } });
        const twinAfter = twinAfterResponse.ok
          ? (await twinAfterResponse.json() as { current_activity_id?: string | null; active_plan_version_id?: string | null })
          : null;
        if (twinAfter?.active_plan_version_id && twinAfter.current_activity_id) {
          const planResponse = await fetch(`/api/v1/plans/${twinAfter.active_plan_version_id}`, { headers: { Accept: "application/json", ...travelerAuthHeaders() } });
          if (planResponse.ok) {
            const plan = await planResponse.json() as { activities?: Array<{ id?: string; start_at?: string }> };
            const stop = (plan.activities ?? []).find((activity) => activity.id === twinAfter.current_activity_id);
            const stopMs = stop?.start_at ? Date.parse(stop.start_at) : Number.NaN;
            const clockMs = Date.parse(clock.virtual_now);
            // A next stop can fall on the following day; the clock must follow it or the
            // strip would show a 12/04 station under a 12/03 time.
            if (Number.isFinite(stopMs) && Number.isFinite(clockMs) && stopMs > clockMs) {
              const advanced = await fetch(`/api/v1/demo/simulation-clock/${journeyId}/advance`, {
                method: "POST",
                headers: { Accept: "application/json", "Content-Type": "application/json", ...travelerAuthHeaders() },
                body: JSON.stringify({ minutes: Math.ceil((stopMs - clockMs) / 60000), expected_version: clock.version }),
              });
              if (advanced.ok) {
                setClock(await advanced.json() as ClockPayload);
                aligned = "；时钟已对齐到这一站";
              }
            }
          }
        }
      }
      await read();
      setStopNote(completed ? `已按模拟执行走到下一站${aligned}` : `推进未完成（最后一次 http_status=${lastStatus}）`);
    } catch {
      setStopNote("推进请求没有完成");
    } finally {
      setBusy(false);
    }
  };

  if (!visible || (!clock && !run)) return null;
  const done = run ? run.status === "SIMULATED_COMPLETED" : journeyDone;
  const running = !run || run.status === "RUNNING";
  const statusLine = run
    ? `模拟时间：${stamp(run.virtual_now)} · 执行第 ${run.sequence} 步 · ${RUN_STATUS_TEXT[run.status] ?? run.status}`
    : `模拟时间：${stamp(clock!.virtual_now)} · 服务器第 ${clock!.version} 版`;
  return (
    <section className="rev-classroom-clock" data-testid="rev-classroom-clock" aria-label="课堂时空模拟">
      <strong>课堂时空模拟｜不是实际定位或真实灾情</strong>
      <span data-testid="rev-clock-virtual">{statusLine}</span>
      <span data-testid="rev-clock-wall">现实演示时间：{stamp(wallClock.toISOString())}</span>
      {!run && clock?.current_activity_title && <span>当前站：{clock.current_activity_title}</span>}
      {run && <span data-testid="rev-clock-run">同一条模拟执行接管了这趟行程（run 序列按服务端为准）</span>}
      {done && <span data-testid="rev-clock-done">模拟行程已完成 · 不是实际到场</span>}
      {run && run.status !== "RUNNING" && !done && (
        <span data-testid="rev-clock-paused">模拟已暂停：请到课堂控制台处理等待中的事件。</span>
      )}
      <div className="rev-classroom-clock-actions">
        <button type="button" disabled={busy || done || !running} data-testid="rev-clock-plus30" onClick={() => void advance(30)}>+30 分钟</button>
        <button type="button" disabled={busy || done || !running} data-testid="rev-clock-plus60" onClick={() => void advance(60)}>+1 小时</button>
        <button type="button" disabled={busy || done || !running} data-testid="rev-clock-next" onClick={() => void advanceStop()}>到下一站</button>
      </div>
      {stopNote && <span data-testid="rev-clock-next-note">{stopNote}</span>}
    </section>
  );
}
