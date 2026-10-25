import { useCallback, useEffect, useState } from "react";
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

  const read = useCallback(async () => {
    try {
      const response = await fetch(`/api/v1/demo/simulation-clock/${journeyId}`, {
        headers: { Accept: "application/json" },
      });
      setClock(response.ok ? (await response.json() as ClockPayload) : null);
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

  const advance = async (minutes: number) => {
    if (!clock || busy) return;
    setBusy(true);
    try {
      const response = await fetch(`/api/v1/demo/simulation-clock/${journeyId}/advance`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ minutes, expected_version: clock.version }),
      });
      if (response.ok) setClock(await response.json() as ClockPayload);
      else void read();
    } catch {
      void read();
    } finally {
      setBusy(false);
    }
  };

  if (!visible || !clock) return null;
  return (
    <section className="rev-classroom-clock" data-testid="rev-classroom-clock" aria-label="课堂时空模拟">
      <strong>课堂时空模拟｜不是实际定位或真实灾情</strong>
      <span data-testid="rev-clock-virtual">模拟时间：{stamp(clock.virtual_now)} · 服务器第 {clock.version} 版</span>
      {clock.current_activity_title && <span>当前站：{clock.current_activity_title}</span>}
      <div className="rev-classroom-clock-actions">
        <button type="button" disabled={busy} data-testid="rev-clock-plus30" onClick={() => void advance(30)}>+30 分钟</button>
        <button type="button" disabled={busy} data-testid="rev-clock-plus60" onClick={() => void advance(60)}>+1 小时</button>
      </div>
    </section>
  );
}
