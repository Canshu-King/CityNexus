import type { BootstrapDiscoveryCandidate } from "../../api/citynexus";

const WEEKDAYS: Record<string, string> = {
  Mo: "周一",
  Tu: "周二",
  We: "周三",
  Th: "周四",
  Fr: "周五",
  Sa: "周六",
  Su: "周日",
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function isTime(value: unknown, allowEndOfDay = false): value is string {
  return typeof value === "string" && (
    /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value) || (allowEndOfDay && value === "24:00")
  );
}

function formatDays(value: unknown): string | null {
  if (!Array.isArray(value) || value.some((day) => typeof day !== "string")) return null;
  const days = value as string[];
  if (days.length === 0) return null;
  if (days.length === 1 && days[0] === "*") return "每天";
  if (days.length === 5 && days.join(",") === "Mo,Tu,We,Th,Fr") return "周一至周五";
  if (days.length === 2 && days.join(",") === "Sa,Su") return "周末";
  if (days.some((day) => !WEEKDAYS[day])) return null;
  return days.map((day) => WEEKDAYS[day]).join("、");
}

function formatInterval(value: unknown): string | null {
  const interval = asRecord(value);
  if (!interval || !isTime(interval.open) || !isTime(interval.close, true)) return null;
  return `${interval.open}–${interval.close}`;
}

export function formatOpeningHours(value: unknown): string | null {
  const opening = asRecord(value);
  if (!opening) return null;
  if (opening.status === "CLOSED") return "来源标记为关闭";
  if (opening.status !== "NORMALIZED_VALID") return null;

  const weekdayIntervals = opening.weekday_intervals;
  if (Array.isArray(weekdayIntervals) && weekdayIntervals.length > 0) {
    const groups = weekdayIntervals.map((entry) => {
      const group = asRecord(entry);
      if (!group || !Array.isArray(group.intervals)) return null;
      const days = formatDays(group.days);
      const ranges = group.intervals.map(formatInterval);
      if (days === null || ranges.length === 0 || ranges.some((range) => range === null)) return null;
      return [days, ranges.join("、")].filter(Boolean).join(" ");
    });
    return groups.every((group) => group !== null) ? groups.join("；") : null;
  }

  const intervals = opening.intervals;
  if (Array.isArray(intervals) && intervals.length === 1) {
    const interval = asRecord(intervals[0]);
    const range = formatInterval(interval);
    const days = interval && interval.days !== undefined ? formatDays(interval.days) : "";
    if (range && days !== null) return [days, range].filter(Boolean).join(" ");
  }
  if (Array.isArray(intervals) && intervals.length > 1) return null;

  if (isTime(opening.open) && isTime(opening.close, true)) {
    if (opening.open === "00:00" && opening.close === "24:00") return "全天";
    return `${opening.open}–${opening.close}`;
  }
  return null;
}

export function formatCost(candidate: BootstrapDiscoveryCandidate): string {
  if (candidate.price_state === "FREE") return "免费";
  const evidence = candidate.cost_evidence;
  const amountMinor = evidence?.amount_minor;
  const grounded = evidence?.status === "KNOWN" || evidence?.status === "VERIFIED_PROVIDER";
  if (!grounded || typeof amountMinor !== "number" || !Number.isSafeInteger(amountMinor) || amountMinor < 0) {
    return "费用未知";
  }
  if (amountMinor === 0) {
    return evidence.evidence_basis === "OSM_FEE_NO" || evidence.status === "VERIFIED_PROVIDER" ? "免费" : "费用未知";
  }
  if (typeof evidence.currency !== "string" || !/^[A-Z]{3}$/.test(evidence.currency)) return "费用未知";

  try {
    const formatter = new Intl.NumberFormat("zh-CN", { style: "currency", currency: evidence.currency });
    const digits = formatter.resolvedOptions().maximumFractionDigits;
    return `费用：${formatter.format(amountMinor / 10 ** digits)}`;
  } catch {
    return "费用未知";
  }
}

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

function selectionReadinessMessage(candidate: BootstrapDiscoveryCandidate, hasSource: boolean): string | null {
  if (candidate.selection_state === "READY_FOR_NATIVE_PLAN") return null;
  if (candidate.public_access_state === "RESTRICTED") return "来源标记为限制访问，请换个地点。";

  const labels: Record<string, string> = {
    OPENING_UNVERIFIED: "营业时间",
    COST_UNKNOWN: "费用",
    COST_UNVERIFIED: "费用",
    ACCESS_UNVERIFIED: "开放状态",
    ACCESS_RESTRICTED: "开放权限",
  };
  const missing = [...new Set((candidate.selection_blockers ?? []).map((item) => labels[item]).filter(Boolean))];
  const facts = missing.length > 0 ? `${missing.join("、")}信息` : "地点资料";
  const nextStep = hasSource ? "查看 OpenStreetMap 来源，或换个地点" : "换个地点";
  return `正式行程还缺${facts}。${nextStep}；私人散步仍可保存。`;
}

export function DiscoveryPlaceCard({
  candidate,
  chosenAs,
  busy,
  canStartJourney,
  onChoose,
  onStartJourney,
  onRefreshFacts,
}: {
  candidate: BootstrapDiscoveryCandidate;
  chosenAs: "第一站" | "第二站" | null;
  busy: boolean;
  canStartJourney: boolean;
  onChoose: (candidateId: string) => void;
  onStartJourney: (candidateId: string) => void;
  onRefreshFacts?: (candidateId: string) => void;
}) {
  const source = safeOsmSource(candidate.source_url);
  const provenance = candidate.provider_provenance === "TEST_PROVIDER"
    ? "测试地点"
    : candidate.provider_provenance === "LIVE_PROVIDER"
      ? "公开地图来源"
      : "来源待确认";
  const openingHours = formatOpeningHours(candidate.opening_hours);
  const hoursLabel = openingHours ? `营业时间：${openingHours}` : "营业时间未知";
  const costLabel = formatCost(candidate);
  const readinessMessage = selectionReadinessMessage(candidate, Boolean(source));
  const distance = typeof candidate.distance_m === "number" && Number.isFinite(candidate.distance_m)
    ? candidate.distance_m < 1000
      ? `约 ${Math.max(10, Math.round(candidate.distance_m / 10) * 10)} 米`
      : `约 ${(candidate.distance_m / 1000).toFixed(1)} 公里`
    : "距离未知";

  return (
    <article className={chosenAs ? "is-picked" : ""} data-testid="rev-quick-place-card">
      <button
        type="button"
        className="rev-quick-place-select"
        aria-pressed={Boolean(chosenAs)}
        disabled={busy || candidate.public_access_state === "RESTRICTED"}
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
          {hoursLabel} · {costLabel}
        </span>
      </button>
      {readinessMessage && (
        <p className="rev-quick-place-blocker" role="status" data-testid={`rev-quick-place-blocker-${candidate.candidate_id}`}>
          {readinessMessage}
        </p>
      )}
      {source && (
        <a href={source} rel="noopener noreferrer" target="_blank" className="rev-quick-place-source">
          查看 OpenStreetMap 来源 ↗
        </a>
      )}
      {source && onRefreshFacts && candidate.provider_provenance === "LIVE_PROVIDER" && (
        candidate.facts_status ? (
          <p className="rev-quick-place-blocker" role="status">
            {candidate.facts_status === "SUCCESS" ? "已读取地点详情，以上为来源提供的资料。" : "地点详情暂未响应，可查看来源或继续挑选地点。"}
          </p>
        ) : (
          <details className="rev-quick-place-blocker">
            <summary>补齐营业和费用资料</summary>
            <p>向 OpenStreetMap 查询这处地点的营业时间和费用。</p>
            <button type="button" className="rev-quick-text-btn" disabled={busy}
              onClick={() => onRefreshFacts(candidate.candidate_id)}
              data-testid={`rev-quick-facts-${candidate.candidate_id}`}>
              {busy ? "查询中…" : "查询地点详情"}
            </button>
          </details>
        )
      )}
      {(candidate.provider_key === "overpass" || candidate.provider_key === "photon") && (
        <a
          href="https://www.openstreetmap.org/copyright"
          rel="noopener noreferrer"
          target="_blank"
          className="rev-quick-place-attribution"
        >© OpenStreetMap contributors</a>
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
