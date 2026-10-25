import { useEffect, useState } from "react";
import { simulationApi, type SimulationCities, type SimulationCurrent } from "./simulationClient";
import "./ClassroomPresenterPanel.css";

/**
 * Read-only presenter view for Codex's SimulationRun contract. It renders nothing
 * while the endpoints are not deployed (the current backend answers 404), so the
 * classroom screen keeps its existing shape until the backend lands.
 */
export function ClassroomPresenterPanel({ journeyId, visible }: { journeyId: string; visible: boolean }) {
  const [cities, setCities] = useState<SimulationCities | null>(null);
  const [current, setCurrent] = useState<SimulationCurrent | null>(null);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    void (async () => {
      try {
        const [nextCities, nextCurrent] = await Promise.all([
          simulationApi.cities(journeyId, 17),
          simulationApi.current(journeyId),
        ]);
        if (cancelled) return;
        if (!nextCities.available && !nextCurrent.available) {
          setHidden(true);
          return;
        }
        setCities(nextCities.available ? nextCities : null);
        setCurrent(nextCurrent);
      } catch {
        if (!cancelled) setHidden(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [journeyId, visible]);

  if (!visible || hidden || (!cities && !current)) return null;
  const eligible = cities?.cities.filter((city) => city.status === "ELIGIBLE_CAPTURED_SNAPSHOT") ?? [];
  const blocked = cities?.cities.filter((city) => city.status !== "ELIGIBLE_CAPTURED_SNAPSHOT") ?? [];
  const run = current && current.available ? current.run : null;

  return (
    <section className="rev-presenter" data-testid="rev-presenter" aria-label="演示者控制台">
      <strong>演示者控制台（课堂）</strong>
      {cities && (
        <>
          <span data-testid="rev-presenter-seed">随机种子 {cities.seed} · 可用城市 {eligible.length} 座</span>
          {eligible.length > 0 && (
            <span data-testid="rev-presenter-eligible">{eligible.map((city) => city.city_code).join(" · ")}</span>
          )}
          {blocked.length > 0 && (
            <span data-testid="rev-presenter-blocked">
              {blocked.map((city) => `${city.city_code}（缺 ${city.missing.length} 项）`).join(" · ")}
            </span>
          )}
        </>
      )}
      <span data-testid="rev-presenter-run">
        {run ? `模拟 run ${run.status} · 第 ${run.sequence} 步 · ${run.virtual_now}` : "模拟 run 尚未开始"}
      </span>
      <small>只读：推进与事件注入按 SimulationRun 契约接入，后端未部署时不出现。</small>
    </section>
  );
}
