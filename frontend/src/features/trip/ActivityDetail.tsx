/**
 * Activity detail — reference screen 08.
 *
 * Shows only provider-backed facts.  Anything the backend did not supply is
 * omitted rather than invented: there is no fabricated rating, ticket price,
 * opening time or "why we recommend this" copy.
 */

import { useLocale } from "../../i18n/LocaleContext";
import { englishCountNoun } from "../../lib/plural";
import { categoryLabel, roleLabel } from "../../i18n/travelerLabels";
import {
  activityDetailCopyLookup,
  type ActivityDetailCopyKey,
} from "./activityDetailCopy";
import { activityCoordinate } from "../../components/v8/MapPanel";
import type { ActivityCoordinate } from "../../app/v8Types";

type ActivityLike = {
  id: string;
  title: string;
  type?: string | null;
  /** Internal activity kind/role vocabulary (CHECK_OUT, MID_TRIP, …). */
  kind?: string | null;
  start_at: string;
  end_at: string;
  place_id?: string | null;
  /** ORD-0394: the place coordinate joined at read; distances are only claimed with it. */
  location?: ActivityCoordinate | null;
  protected?: boolean;
  travel_from_prev_min?: number | null;
  estimated_cost?: { amount_minor?: number; currency?: string } | null;
  /** KNOWN_FREE | KNOWN_PAID | UNKNOWN — whether the price is a real fact. */
  cost_status?: string | null;
  metadata?: {
    latitude?: number | null;
    longitude?: number | null;
    crs?: string | null;
    category?: string | null;
    /** Internal structural role (ARRIVAL, CHECK_IN, STAY, …). */
    role?: string | null;
    opening_hours?: { status?: string; raw?: string | null } | null;
    cost_evidence?: { status?: string; source?: string | null } | null;
    price_known?: boolean | null;
    semantic_key?: string | null;
  } | null;
};

function clock(iso: string, timeZone: string): string {
  try {
    return new Intl.DateTimeFormat("en-GB", {
      timeZone,
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).format(new Date(iso));
  } catch {
    return iso.slice(11, 16);
  }
}

function dayLabel(iso: string, locale: string, timeZone: string): string {
  try {
    return new Intl.DateTimeFormat(locale.startsWith("zh") ? "zh-CN" : "en-GB", {
      timeZone,
      weekday: "long",
      month: "short",
      day: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}

function minutesBetween(start: string, end: string): number | null {
  const a = Date.parse(start);
  const b = Date.parse(end);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.max(0, Math.round((b - a) / 60000));
}

export function ActivityDetail({
  activity,
  timeZone,
  onBack,
  onShowOnMap,
  onAskCopilot,
  nearby,
  onOpenNearby,
}: {
  activity: ActivityLike;
  timeZone: string;
  onBack: () => void;
  onShowOnMap: () => void;
  onAskCopilot: () => void;
  nearby: ActivityLike[];
  onOpenNearby: (id: string) => void;
}) {
  const { locale, t } = useLocale();
  const zh = locale.startsWith("zh");
  const say = (key: ActivityDetailCopyKey) => activityDetailCopyLookup(locale, key);
  const meta = activity.metadata ?? {};

  // Truthfulness: only call other stops "nearby" when they are actually
  // spatially close.  Otherwise say plainly that they are other stops on the
  // same trip.  Distance is straight-line metres from the real coordinates.
  const nearbyRadiusM = 1500;
  const origin = activityCoordinate(activity);
  const distanceM = (item: ActivityLike): number | null => {
    const at = activityCoordinate(item);
    if (!origin || !at) return null;
    const scale = 111_320;
    const dy = (Number(at.latitude) - Number(origin.latitude)) * scale;
    const dx =
      (Number(at.longitude) - Number(origin.longitude)) * scale *
      Math.cos((Number(origin.latitude) * Math.PI) / 180);
    return Math.hypot(dx, dy);
  };
  const withDistance = nearby
    .map((item) => ({ item, m: distanceM(item) }))
    .filter((entry): entry is { item: ActivityLike; m: number } => entry.m != null)
    .sort((a, b) => a.m - b.m);
  const nearbyAreClose =
    origin != null &&
    withDistance.length > 0 &&
    withDistance.some((entry) => entry.m <= nearbyRadiusM);
  const nearbyOrdered = nearbyAreClose
    ? withDistance.filter((entry) => entry.m <= nearbyRadiusM).map((entry) => entry.item)
    : nearby;
  const duration = minutesBetween(activity.start_at, activity.end_at);
  const hasCoords = origin != null;
  const opening = meta.opening_hours ?? null;
  const openingKnown = opening?.status && opening.status !== "UNKNOWN";
  const cost = activity.estimated_cost;
  const amountMinor = cost?.amount_minor ?? 0;
  // Three truthful states.  Deriving "known" from amount > 0 reported a free
  // attraction as "price unavailable" and could present a paid place as free.
  const costStatus = String(activity.cost_status ?? "").toUpperCase();
  const knownFree = costStatus === "KNOWN_FREE";
  const knownPaid = costStatus === "KNOWN_PAID" || (!costStatus && amountMinor > 0);

  const durationText =
    duration == null
      ? null
      : duration >= 60
        ? zh
          ? `${Math.floor(duration / 60)} 小时${duration % 60 ? ` ${duration % 60} 分` : ""}`
          : `${Math.floor(duration / 60)}h${duration % 60 ? ` ${duration % 60}m` : ""}`
        : zh
          ? `${duration} 分钟`
          : `${duration} ${englishCountNoun(duration, "minute")}`;

  return (
    <section className="v8-page activity-detail" data-testid="activity-detail">
      <button type="button" className="activity-back" data-testid="activity-back" onClick={onBack}>
        ← {say("activity.backToItinerary")}
      </button>

      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">
            {dayLabel(activity.start_at, locale, timeZone)} ·{" "}
            {clock(activity.start_at, timeZone)}–{clock(activity.end_at, timeZone)}
          </p>
          <h1 data-testid="activity-title">{activity.title}</h1>
          <p className="v8-lede">
            {activity.protected
              ? say("activity.stopConfirmed")
              : say("activity.stopOpen")}
          </p>
        </div>
      </div>

      <dl className="trial-review activity-facts">
        {durationText && (
          <div>
            <dt>{say("activity.factDuration")}</dt>
            <dd data-testid="activity-duration">{durationText}</dd>
          </div>
        )}
        {activity.travel_from_prev_min != null && activity.travel_from_prev_min > 0 && (
          <div>
            <dt>{say("activity.factTravelFromPrev")}</dt>
            <dd>
              {zh
                ? `${activity.travel_from_prev_min} 分钟`
                : `${activity.travel_from_prev_min} ${englishCountNoun(activity.travel_from_prev_min, "minute")}`}
            </dd>
          </div>
        )}
        <div>
          <dt>{say("activity.factCost")}</dt>
          <dd data-testid="activity-cost" data-cost-status={
            knownFree ? "KNOWN_FREE" : knownPaid ? "KNOWN_PAID" : "UNKNOWN"
          }>
            {knownFree
              ? say("activity.costFree")
              : knownPaid
                ? `${cost?.currency ?? ""} ${Math.round(amountMinor / 100)}`
                : zh
                  ? "暂无价格"
                  : "Price unavailable"}
          </dd>
        </div>
        <div>
          <dt>{say("activity.factHours")}</dt>
          {/* ORD-0345 shape call: this value is the place record's own `opening_hours.raw` -- supplier
              content the traveller is asking for, not a rejection's sentence. It stays, but it is no
              longer unattributed: the line names whose words they are, and Q70 anchors the element with
              the contract field it comes from. The ruler may still flag the shape; the readings say
              what this is rather than leaving it to a name-match. */}
          <dd
            data-testid="activity-hours"
            {...(openingKnown && opening?.raw ? { "data-cnx-field": "opening_hours.raw" } : {})}
          >
            {openingKnown
              ? `${opening?.raw || t("detail.hoursProvided")}${opening?.raw ? t("detail.hoursProviderText") : ""}`
              : zh
                ? "暂无数据"
                : "Not available"}
          </dd>
        </div>
        {meta.category && (
          <div>
            <dt>{say("activity.factCategory")}</dt>
            <dd data-testid="activity-category">{categoryLabel(meta.category, zh)}</dd>
          </div>
        )}
        {(activity.kind || activity.type || meta.role) && (
          <div>
            <dt>{say("activity.factKind")}</dt>
            <dd data-testid="activity-kind">
              {roleLabel(activity.kind || activity.type || meta.role, zh)}
            </dd>
          </div>
        )}
        <div>
          <dt>{say("activity.factLocation")}</dt>
          <dd data-testid="activity-location">
            {hasCoords
              ? `${origin.latitude.toFixed(4)}, ${origin.longitude.toFixed(4)}${
                  origin.coordinate_system ? ` ${origin.coordinate_system}` : ""
                }`
              : say("activity.noCoords")}
          </dd>
        </div>
      </dl>

      <div className="activity-actions">
        <button
          type="button"
          className="v8-primary-button"
          data-testid="activity-map"
          onClick={onShowOnMap}
          disabled={!hasCoords}
        >
          {say("activity.showOnMap")}
        </button>
        <button
          type="button"
          className="v8-outline-button"
          data-testid="activity-ask"
          onClick={onAskCopilot}
        >
          {say("activity.askCopilot")}
        </button>
      </div>

      {nearby.length > 0 && (
        <section className="activity-nearby" data-testid="activity-nearby">
          <h2>
            {nearbyAreClose
              ? say("activity.nearbyStops")
              : say("activity.otherStops")}
          </h2>
          <p className="v8-muted" data-testid="activity-nearby-note">
            {nearbyAreClose
              ? zh
                ? `都在约 ${nearbyRadiusM} 米范围内，按直线距离排列。`
                : `All within about ${nearbyRadiusM} m, ordered by straight-line distance.`
              : say("activity.otherStopsNote")}
          </p>
          <ul>
            {nearbyOrdered.slice(0, 5).map((item) => {
              const metres = withDistance.find((entry) => entry.item.id === item.id)?.m;
              return (
                <li key={item.id}>
                  <button type="button" onClick={() => onOpenNearby(item.id)}>
                    <span>{item.title}</span>
                    {metres != null && (
                      <small className="activity-nearby-distance">
                        {metres < 1000
                          ? zh
                            ? `${Math.round(metres)} 米`
                            : `${Math.round(metres)} ${englishCountNoun(Math.round(metres), "metre")}`
                          : zh
                            ? `${(metres / 1000).toFixed(1)} 公里`
                            : `${(metres / 1000).toFixed(1)} km`}
                      </small>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </section>
  );
}
