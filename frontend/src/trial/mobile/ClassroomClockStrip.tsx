import { useCallback, useEffect, useState } from "react";
import { travelerAuthHeaders } from "../../lib/travelerSession";
import { simulationApi } from "./simulationClient";
import "./ClassroomClockStrip.css";

/**
 * The classroom clock, on the journey screen itself.  The virtual time lives on
 * the server (`simulation_clocks`) so a reload keeps the hour; this strip only
 * reads it and asks the server to advance it.  It never touches the browser's
 * clock for the journey's own time, and the watermark stays on the strip.
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

function stamp(value: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(date);
}

export function ClassroomClockStrip({ journeyId, visible }: { journeyId: string; visible: boolean }) {
  const [clock, setClock] = useState<ClockPayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [wallClock, setWallClock] = useState(() => new Date());
  const [stopNote, setStopNote] = useState<string | null>(null);
  const [journeyDone, setJourneyDone] = useState(false);
  const [runOwned, setRunOwned] = useState(false);

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
      // Once a SimulationRun exists the run owns the agenda; this strip must not
      // advance the same journey through the older state machine.
      setRunOwned(Boolean(runCurrent && runCurrent.available && runCurrent.run));
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

  const advance = async (minutes: number) => {
    if (!clock || busy || journeyDone) return;
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
    if (busy) return;
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

  if (!visible || !clock) return null;
  return (
    <section className="rev-classroom-clock" data-testid="rev-classroom-clock" aria-label="课堂时空模拟">
      <strong>课堂时空模拟｜不是实际定位或真实灾情</strong>
      <span data-testid="rev-clock-virtual">模拟时间：{stamp(clock.virtual_now)} · 服务器第 {clock.version} 版</span>
      <span data-testid="rev-clock-wall">现实演示时间：{stamp(wallClock.toISOString())}</span>
      {clock.current_activity_title && <span>当前站：{clock.current_activity_title}</span>}
      {journeyDone && <span data-testid="rev-clock-done">模拟行程已完成 · 不是实际到场</span>}
      {runOwned && (
        <span data-testid="rev-clock-handoff">这趟行程已交给课堂控制台推进（模拟执行），这里的时钟按钮暂停使用。</span>
      )}
      <div className="rev-classroom-clock-actions">
        <button type="button" disabled={busy || journeyDone || runOwned} data-testid="rev-clock-plus30" onClick={() => void advance(30)}>+30 分钟</button>
        <button type="button" disabled={busy || journeyDone || runOwned} data-testid="rev-clock-plus60" onClick={() => void advance(60)}>+1 小时</button>
        <button type="button" disabled={busy || journeyDone || runOwned} data-testid="rev-clock-next" onClick={() => void advanceStop()}>到下一站</button>
      </div>
      {stopNote && <span data-testid="rev-clock-next-note">{stopNote}</span>}
    </section>
  );
}
