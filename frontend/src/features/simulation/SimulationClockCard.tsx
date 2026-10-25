import { useCallback, useEffect, useState } from "react";
import { travelerAuthHeaders } from "../../lib/travelerSession";

/**
 * Classroom sandbox clock (first cut).  The virtual time lives on the server
 * (`simulation_clocks`, one row per journey) so a reload shows the same hour; this card only
 * reads it and asks the server to advance it.  It never touches `Date.now()` for the journey's
 * own time, and it never claims the simulated position is a physical one.
 */

type ClockPayload = {
  journey_id: string;
  virtual_now: string;
  version: number;
  persisted: boolean;
  basis: string;
  journey_status: string;
  current_activity_title: string | null;
  current_activity_status: string | null;
  traveller: { latitude: number; longitude: number; coordinate_system: string; label: string; source: string } | null;
};

const stamp = (value: string): string => {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(date);
};

export function SimulationClockCard({ journeyId, zh }: { journeyId: string | null; zh: boolean }) {
  const [clock, setClock] = useState<ClockPayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [realNow, setRealNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setRealNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const read = useCallback(async () => {
    if (!journeyId) return;
    try {
      const response = await fetch(`/api/v1/demo/simulation-clock/${journeyId}`, { headers: { Accept: "application/json", ...travelerAuthHeaders() } });
      if (!response.ok) {
        setClock(null);
        setError(response.status === 404 ? (zh ? "这个栈没有开课堂模拟（服务器门禁为关）。" : "Simulation is off on this stack.") : `HTTP ${response.status}`);
        return;
      }
      setClock(await response.json() as ClockPayload);
      setError(null);
    } catch (failure) {
      setError(String(failure).slice(0, 120));
    }
  }, [journeyId, zh]);

  useEffect(() => { void read(); }, [read]);

  const advance = async (minutes: number) => {
    if (!journeyId || !clock || busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/demo/simulation-clock/${journeyId}/advance`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json", ...travelerAuthHeaders() },
        body: JSON.stringify({ minutes, expected_version: clock.version }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(`${response.status} ${String((body as { error?: { message?: string } }).error?.message ?? "")}`.trim());
        await read();
        return;
      }
      setClock(body as ClockPayload);
    } catch (failure) {
      setError(String(failure).slice(0, 120));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="cn-sim-clock" data-testid="sim-clock" aria-label={zh ? "模拟时钟" : "Simulation clock"}
      style={{ border: "1px solid var(--cn-line, #d6d3c8)", borderRadius: 10, padding: "10px 12px", margin: "8px 0", background: "rgba(255,255,255,.6)" }}>
      <p role="note" style={{ margin: 0, fontSize: 12, letterSpacing: ".02em", color: "#7a5b1e" }}>
        {zh ? "课堂时空模拟｜不是实际定位或真实灾情" : "Classroom sandbox | not a real location or live hazard"}
      </p>
      {!journeyId && <p role="status">{zh ? "还没有选中的行程。" : "No journey selected yet."}</p>}
      {journeyId && !clock && !error && <p role="status">{zh ? "正在读服务器上的模拟时间…" : "Reading the simulated time…"}</p>}
      {error && <p role="alert" data-testid="sim-clock-error">{error}</p>}
      {clock && (
        <>
          <p style={{ margin: "6px 0 2px", fontSize: 18, fontVariantNumeric: "tabular-nums" }} data-testid="sim-clock-value">
            {zh ? "模拟旅行时间：" : "Simulated trip time: "}{stamp(clock.virtual_now)}
          </p>
          <p style={{ margin: 0, fontSize: 12, color: "#5b5b5b" }}>
            {zh ? "现实演示时间：" : "Real demo time: "}{realNow.toLocaleTimeString("zh-CN", { hour12: false })}
            {zh ? ` · 服务器记在第 ${clock.version} 版` : ` · server version ${clock.version}`}
            {clock.persisted ? (zh ? " · 刷新仍在" : " · persisted") : (zh ? " · 尚未推进" : " · not advanced yet")}
          </p>
          <p style={{ margin: "4px 0", fontSize: 13 }}>
            {clock.current_activity_title
              ? (zh ? `当前站：${clock.current_activity_title}（${clock.current_activity_status ?? "未知"}）` : `Current stop: ${clock.current_activity_title} (${clock.current_activity_status ?? "unknown"})`)
              : (zh ? "当前站：尚未开始执行" : "Current stop: execution has not started")}
          </p>
          {clock.traveller && (
            <p style={{ margin: "2px 0", fontSize: 12, color: "#31506b" }} data-testid="sim-clock-traveller">
              {zh
                ? `模拟旅客：${clock.traveller.label} · ${clock.traveller.latitude.toFixed(4)}, ${clock.traveller.longitude.toFixed(4)}（${clock.traveller.coordinate_system}，模拟位置）`
                : `Simulated traveller: ${clock.traveller.label} · ${clock.traveller.latitude.toFixed(4)}, ${clock.traveller.longitude.toFixed(4)} (${clock.traveller.coordinate_system}, simulated)`}
            </p>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
            <button type="button" data-testid="sim-clock-advance-30" disabled={busy} onClick={() => void advance(30)}>
              {busy ? (zh ? "正在推进…" : "Advancing…") : (zh ? "+30 分钟" : "+30 min")}
            </button>
            <button type="button" data-testid="sim-clock-advance-60" disabled={busy} onClick={() => void advance(60)}>
              {zh ? "+1 小时" : "+1 hour"}
            </button>
            <button type="button" data-testid="sim-clock-refresh" disabled={busy} onClick={() => void read()}>
              {zh ? "刷新时间" : "Refresh"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
