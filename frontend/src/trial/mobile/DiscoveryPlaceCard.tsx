import type { BootstrapDiscoveryCandidate } from "../../api/citynexus";

function safeOsmSource(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      !["www.openstreetmap.org", "openstreetmap.org"].includes(url.hostname) ||
      url.username || url.password ||
      !/^\/(node|way|relation)\/[1-9][0-9]*$/.test(url.pathname)
    ) return null;
    return url.toString();
  } catch {
    return null;
  }
}

export function DiscoveryPlaceCard({
  candidate,
  chosenAs,
  busy,
  canStartJourney,
  onChoose,
  onStartJourney,
}: {
  candidate: BootstrapDiscoveryCandidate;
  chosenAs: "第一站" | "第二站" | null;
  busy: boolean;
  canStartJourney: boolean;
  onChoose: (candidateId: string) => void;
  onStartJourney: (candidateId: string) => void;
}) {
  const source = safeOsmSource(candidate.source_url);
  const provenance = candidate.provider_provenance === "TEST_PROVIDER"
    ? "测试地点"
    : candidate.provider_provenance === "LIVE_PROVIDER"
      ? "公开地图来源"
      : "来源待确认";
  const distance = typeof candidate.distance_m === "number" && Number.isFinite(candidate.distance_m)
    ? candidate.distance_m < 1000
      ? `约 ${Math.max(10, Math.round(candidate.distance_m / 10) * 10)} 米`
      : `约 ${(candidate.distance_m / 1000).toFixed(1)} 公里`
    : null;

  return (
    <article className={chosenAs ? "is-picked" : ""} data-testid="rev-quick-place-card">
      <button
        type="button"
        className="rev-quick-place-select"
        aria-pressed={Boolean(chosenAs)}
        onClick={() => onChoose(candidate.candidate_id)}
        data-testid={`rev-quick-select-${candidate.candidate_id}`}
      >
        <span className="rev-quick-place-topline">
          <span className="rev-quick-pick">{chosenAs ?? "＋ 选择地点"}</span>
          <span className={`rev-place-provenance ${candidate.provider_provenance === "LIVE_PROVIDER" ? "is-live" : ""}`}>
            {provenance}
          </span>
        </span>
        <strong>{candidate.name}</strong>
        <span className="rev-quick-place-meta">
          {candidate.category}{distance ? ` · ${distance}` : ""}
        </span>
        <span className="rev-quick-place-facts">
          营业与费用信息待补充
        </span>
      </button>
      {source && (
        <a href={source} rel="noopener noreferrer" target="_blank" className="rev-quick-place-source">
          查看 OpenStreetMap 来源 ↗
        </a>
      )}
      {canStartJourney && candidate.selection_state === "READY_FOR_NATIVE_PLAN" && (
        <button
          type="button"
          className="rev-quick-formal"
          disabled={busy}
          onClick={() => onStartJourney(candidate.candidate_id)}
          data-testid={`rev-quick-formal-${candidate.candidate_id}`}
        >想创建正式行程？继续并确认计划 →</button>
      )}
    </article>
  );
}
