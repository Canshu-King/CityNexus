/**
 * Trip itinerary — the answer to "我整个旅行是什么？每天怎么安排？"
 *
 * Built from the authoritative active plan's activities, grouped by the
 * traveller's local date.  It deliberately does NOT depend on a stay option
 * being selected: a journey with a plan always has an itinerary.
 *
 * Long trips use a week selector rather than a 39-item horizontal day strip
 * (design corrections §8).  Missing data is shown as missing.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { readCheckins, stampStop } from "../checkin/checkins";
import type { CheckinRefusalFacts } from "../checkin/checkins";
import {
  CHECKIN_COPY,
  CHECKIN_REFUSAL_COPY,
  formatStampedMoment,
  wordsFor,
} from "../checkin/checkinCopy";
import "../checkin/footprint.css";
import { CollectInto } from "../collections/CollectInto";
import { calendarRefusalKey, exportJourneyCalendar } from "./calendarExport";
import { roleLabel, disruptionLabel } from "../../i18n/travelerLabels";
import {
  dayOfGapCopy,
  journeyProgress,
  progressContractCopy,
} from "../progress/journeyProgress";
import type { V8Data } from "../../app/v8Types";

type Activity = V8Data["active_plan"] extends null
  ? never
  : NonNullable<V8Data["active_plan"]>["activities"][number];

type DayGroup = {
  key: string;      // YYYY-MM-DD
  label: string;    // human label
  activities: Activity[];
};

function localDateKey(iso: string, timeZone: string): string {
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}

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

function minutesBetween(start: string, end: string): number | null {
  const a = Date.parse(start);
  const b = Date.parse(end);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.max(0, Math.round((b - a) / 60000));
}

function dayLabel(key: string, index: number, locale: string): string {
  const date = new Date(`${key}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) return key;
  try {
    return new Intl.DateTimeFormat(locale.startsWith("zh") ? "zh-CN" : "en-GB", {
      weekday: "short",
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    }).format(date);
  } catch {
    return `Day ${index + 1}`;
  }
}

export function TripItinerary({
  data,
  onOpenCopilot,
  onOpenActivity,
}: {
  data: V8Data;
  onOpenCopilot: () => void;
  onOpenActivity: (activityId: string) => void;
}) {
  const { locale, t } = useLocale();
  const zh = locale.startsWith("zh");
  const plan = data.active_plan;
  const tz = data.journey.timezone || "UTC";

  /* Ported from the Qoder tree (ORD-0476 slice 2 + ORD-0500 + ORD-0510), with this screen's own
     vocabulary: the button's two words stay inline here, as every other label on this screen does,
     instead of going through `t("checkin.*")`.  This branch's app dictionary carries no 打卡 keys,
     and `t()` answers an absent key with the key itself -- which would paint `checkin.buttonAria`
     on a Chinese screen.  The refusal sentences come from `checkinCopy.ts`, which is keyed by state
     name and interpolates the label defined two lines below, so a sentence can only ever name a word
     the traveller actually sees. */
  const stampButtonLabel = zh ? "打卡" : "Check in";
  const stampedButtonLabel = zh ? "已打卡" : "Stamped";

  /* Which stops already carry a footprint is read from `GET /api/v1/journeys/{id}/checkins`, never
     remembered from a tap: a stop shows 已打卡 only because the read returned that row.  The map is
     keyed by the door's own `target_key` so this screen holds no second copy of a stamp. */
  const journeyId = data.journey.id;
  const [stamped, setStamped] = useState<Record<string, string>>({});
  const [pendingStop, setPendingStop] = useState<string | null>(null);
  /* One notice per stop, keyed by the stop that was pressed.  A single screen-wide string here made a
     double tap on one stop say "already stamped" under every stop on the day. */
  const [stopNotices, setStopNotices] = useState<Record<string, string>>({});

  /* ORD-0496/0525, ported.  Unlike the 打卡 labels two blocks above, these nine sentences go through
     the app dictionary (`calendar.*`), because `calendarExport.ts` hands the screen a *key*
     (`calendarRefusalKey`) rather than a sentence -- switching a refusal to an inline ternary here
     would mean rewriting that module and its test arms.  The keys were added in their own dictionary
     branches, so none of them can answer with a raw key: `t()` echoing an absent key is exactly the
     defect the 打卡 note above records. */
  const [calendarNotice, setCalendarNotice] = useState<string | null>(null);
  const [calendarPending, setCalendarPending] = useState(false);

  const exportCalendar = async () => {
    setCalendarPending(true);
    setCalendarNotice(null);
    const answer = await exportJourneyCalendar(journeyId);
    if (answer.kind === "exported") {
      setCalendarNotice(t("calendar.done", { events: answer.events }));
    } else if (answer.kind === "refused") {
      setCalendarNotice(t(calendarRefusalKey(answer.refusal)));
    } else {
      setCalendarNotice(t("calendar.unreachable"));
    }
    setCalendarPending(false);
  };

  const reloadStamps = useCallback(async () => {
    const answer = await readCheckins(journeyId);
    if (answer.kind !== "read") return;
    const next: Record<string, string> = {};
    for (const stamp of answer.stamps) next[stamp.target_key] = stamp.id;
    setStamped(next);
  }, [journeyId]);

  useEffect(() => {
    void reloadStamps();
  }, [reloadStamps]);

  /** The words for one refusal, in this screen's own vocabulary, never the server's token. */
  const refusalWords = (facts: CheckinRefusalFacts): string => {
    if (facts.refusal === "CHECKIN_DUPLICATE_STAMP") {
      /* Point at the stamp that won.  The door sends the instant; the uuid it also sends is a machine
         word and stays off this screen. */
      return facts.existingStampedAt
        ? wordsFor(CHECKIN_COPY.duplicateAt, zh, {
            moment: formatStampedMoment(facts.existingStampedAt, zh),
          })
        : wordsFor(CHECKIN_COPY.duplicateNoMoment, zh);
    }
    const key = CHECKIN_REFUSAL_COPY[facts.refusal];
    if (key) return wordsFor(CHECKIN_COPY[key], zh, { button: stampButtonLabel });
    if (facts.status === 0) return wordsFor(CHECKIN_COPY.unreachable, zh);
    return wordsFor(CHECKIN_COPY.unexpected, zh, { status: String(facts.status) });
  };

  const stampThisStop = async (activityId: string) => {
    setPendingStop(activityId);
    setStopNotices((current) => {
      const next = { ...current };
      delete next[activityId];
      return next;
    });
    const answer = await stampStop(journeyId, activityId);
    if (answer.kind === "stamped") {
      setStamped((current) => ({ ...current, [answer.stamp.target_key]: answer.stamp.id }));
      // Read back rather than trusting the 201's own body for what the trip now holds.
      await reloadStamps();
    } else if (answer.kind === "refused") {
      /* The server's answer taken as the fact it is: 409 means a stamp is already on file, so the row
         is re-read and shown instead of overwritten -- and said in this screen's words, because a
         reason code on a Chinese screen is the defect this project keeps having to fix. */
      setStopNotices((current) => ({ ...current, [activityId]: refusalWords(answer.facts) }));
      await reloadStamps();
    } else {
      setStopNotices((current) => ({
        ...current,
        [activityId]: wordsFor(CHECKIN_COPY.unreachable, zh),
      }));
    }
    setPendingStop(null);
  };

  const days = useMemo<DayGroup[]>(() => {
    const activities = plan?.activities ?? [];
    const buckets = new Map<string, Activity[]>();
    for (const activity of [...activities].sort((a, b) => a.start_at.localeCompare(b.start_at))) {
      const key = localDateKey(activity.start_at, tz);
      const list = buckets.get(key) ?? [];
      list.push(activity);
      buckets.set(key, list);
    }
    return [...buckets.entries()].map(([key, items], index) => ({
      key,
      label: dayLabel(key, index, locale),
      activities: items,
    }));
  }, [plan, tz, locale]);

  /* ORD-0438: one owner for the two counts a traveller reads as progress.  The day total comes from the
     server's projection, the same number Today quotes, so this screen no longer re-derives a second one
     from its own grouping; the grouping stays in charge of what it was always the only reader of --
     which day holds the cursor. */
  const progress = useMemo(
    () =>
      journeyProgress({
        serverDayCount: data.journey.temporal_shape?.day_count ?? null,
        days: days.map((day) => ({ key: day.key, activityIds: day.activities.map((a) => a.id) })),
        activities: (plan?.activities ?? []).map((a) => ({ id: a.id, status: a.status })),
        currentActivityId: plan?.current_activity_id ?? null,
      }),
    [data.journey.temporal_shape, days, plan],
  );

  const [activeDay, setActiveDay] = useState(0);

  if (!plan || days.length === 0) {
    return (
      <section className="v8-page" data-testid="trip-itinerary-empty">
        <div className="v8-page-intro compact">
          <div>
            <p className="v8-kicker">{zh ? "行程" : "Trips"}</p>
            <h1>{zh ? "还没有可看的行程" : "No itinerary yet"}</h1>
            <p className="v8-lede">
              {zh
                ? "这个行程还没有选定的方案。先让 AI 帮你规划，选定方案后这里会显示逐日安排。"
                : "This trip has no chosen plan yet. Ask the AI to plan it, then pick a plan and the day-by-day itinerary appears here."}
            </p>
          </div>
        </div>
        <button type="button" className="v8-primary-button" onClick={onOpenCopilot}>
          {zh ? "AI 帮我规划" : "Plan my trip with AI"}
        </button>
      </section>
    );
  }

  // Long trips: a week strip rather than one chip per day.
  const weeks = Math.ceil(days.length / 7);
  const showWeeks = days.length > 7;
  const [week, setWeek] = useState(0);
  const visible = showWeeks ? days.slice(week * 7, week * 7 + 7) : days;

  return (
    <section className="v8-page" data-testid="trip-itinerary">
      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">{zh ? "行程" : "Trips"}</p>
          <h1 data-testid="trip-day-total">
            {progress.day_total === null
              ? zh
                ? "天数未知"
                : "length unknown"
              : zh
                ? `${progress.day_total} 天行程`
                : `${progress.day_total}-day itinerary`}
          </h1>
          <p className="v8-lede">
            {zh
              ? "逐日安排。已确认的预订会被标记为受保护。"
              : "Day by day. Confirmed bookings are marked as protected."}
          </p>
          <p className="v8-lede" data-testid="trip-progress-contract">
            {progressContractCopy(progress, zh)}
          </p>
          {dayOfGapCopy(progress, zh) && (
            <p className="v8-lede" data-testid="trip-progress-daygap">
              {dayOfGapCopy(progress, zh)}
            </p>
          )}
          {/* ORD-0525: the itinerary's own way out to a calendar app.  A quiet button rather than a
             primary one on purpose -- this screen already carries the traveller's primary calls to
             action, and a download is not louder than choosing what to do next. */}
          <button
            type="button"
            className="v8-quiet-button"
            data-testid="calendar-export"
            disabled={calendarPending}
            onClick={() => void exportCalendar()}
          >
            {calendarPending ? t("calendar.busy") : t("calendar.export")}
          </button>
          {calendarNotice && (
            <p className="v8-lede" data-testid="calendar-export-notice">
              {calendarNotice}
            </p>
          )}
        </div>
      </div>

      {showWeeks && weeks > 1 && (
        <div className="trip-week-strip" data-testid="trip-week-strip">
          {Array.from({ length: weeks }, (_, index) => (
            <button
              key={index}
              type="button"
              className={index === week ? "active" : ""}
              onClick={() => {
                setWeek(index);
                setActiveDay(0);
              }}
            >
              {zh ? `第 ${index + 1} 周` : `Week ${index + 1}`}
            </button>
          ))}
        </div>
      )}

      <div className="trip-day-strip" data-testid="trip-day-strip">
        {visible.map((day, index) => {
          const globalIndex = showWeeks ? week * 7 + index : index;
          return (
            <button
              key={day.key}
              type="button"
              className={globalIndex === activeDay ? "active" : ""}
              data-testid={`trip-day-${globalIndex}`}
              onClick={() => setActiveDay(globalIndex)}
            >
              <span>{day.label}</span>
              <small>
                {zh ? `${day.activities.length} 项` : `${day.activities.length} stops`}
              </small>
            </button>
          );
        })}
      </div>

      {visible.map((day, index) => {
        const globalIndex = showWeeks ? week * 7 + index : index;
        if (globalIndex !== activeDay) return null;
        return (
          <div className="trip-day-detail" key={day.key} data-testid="trip-day-detail">
            {day.activities.map((activity) => {
              const duration = minutesBetween(activity.start_at, activity.end_at);
              const isCurrent = plan.current_activity_id === activity.id;
              const disruption = plan.disruptions?.find(
                (event) => event.affected_activity_id === activity.id,
              );
              const disrupted = Boolean(disruption);
              return (
                <article
                  key={activity.id}
                  className={`trip-stop${activity.protected ? " protected" : ""}${
                    isCurrent ? " current" : ""
                  }${disrupted ? " disrupted" : ""}`}
                  data-testid="trip-stop"
                  role="button"
                  tabIndex={0}
                  aria-label={`${zh ? "查看详情" : "View details"}: ${activity.title}`}
                  onClick={() => onOpenActivity(activity.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onOpenActivity(activity.id);
                    }
                  }}
                >
                  <div className="trip-stop-time">
                    <b>{clock(activity.start_at, tz)}</b>
                    <small>{clock(activity.end_at, tz)}</small>
                  </div>
                  <div className="trip-stop-body">
                    <b>{activity.title}</b>
                    <div className="trip-stop-meta">
                      {duration != null && (
                        <span>
                          {duration >= 60
                            ? zh
                              ? `${Math.floor(duration / 60)} 小时${duration % 60 ? ` ${duration % 60} 分` : ""}`
                              : `${Math.floor(duration / 60)}h${duration % 60 ? ` ${duration % 60}m` : ""}`
                            : zh
                              ? `${duration} 分钟`
                              : `${duration} min`}
                        </span>
                      )}
                      {activity.type && activity.type !== "visit" && (
                        <span className="trip-stop-type">{roleLabel(activity.type, zh)}</span>
                      )}
                      {activity.protected && (
                        <span className="trip-stop-protected" data-testid="trip-stop-protected">
                          {zh ? "已确认 · 受保护" : "Confirmed · protected"}
                        </span>
                      )}
                      {disrupted && (
                        <span className="trip-stop-disrupted">
                          {disruption
                            ? disruptionLabel(disruption.type, zh)
                            : zh
                              ? "受影响"
                              : "Affected"}
                        </span>
                      )}
                      {isCurrent && (
                        <span className="trip-stop-current">{zh ? "当前" : "Now"}</span>
                      )}
                      {/* This was decoration (`aria-hidden`) inside a row that claims `role="button"`
                          while itself containing real controls -- nested interactive content, which a
                          keyboard and a screen reader both refuse.  The row still answers a tap;
                          「详情」 is now the control it always read as. */}
                      <button
                        type="button"
                        className="trip-stop-more"
                        data-testid="trip-stop-details"
                        aria-label={`${zh ? "查看详情" : "View details"}: ${activity.title}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          onOpenActivity(activity.id);
                        }}
                      >
                        {zh ? "详情 ›" : "Details ›"}
                      </button>
                      {/* The tap that makes a footprint.  It stops propagation because the row around it
                          is itself an entry point, and a control whose click is swallowed by its own row
                          is not an entry a traveller reaches.  Its state comes from the read above, not
                          from local optimism. */}
                      <button
                        type="button"
                        className="cn-stop-checkin"
                        data-testid="stop-checkin"
                        data-state={stamped[`activity:${activity.id}`] ? "stamped" : "fresh"}
                        disabled={pendingStop === activity.id}
                        aria-label={`${
                          stamped[`activity:${activity.id}`] ? stampedButtonLabel : stampButtonLabel
                        }: ${activity.title}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          void stampThisStop(activity.id);
                        }}
                      >
                        {stamped[`activity:${activity.id}`] ? stampedButtonLabel : stampButtonLabel}
                      </button>
                    </div>
                    {stopNotices[activity.id] ? (
                      <p
                        className="cn-stop-checkin__notice"
                        data-testid="stop-checkin-notice"
                        role="status"
                      >
                        {stopNotices[activity.id]}
                      </p>
                    ) : null}
                    {/* The way into the container: the wrapper, not the control, stops propagation.
                        Nothing here remembers the write -- the line under it is drawn from a fresh
                        `GET /api/v1/collections`, the way the footprint above it is.  The shelf scope
                        comes from this device's signed credential, so no traveller id is passed. */}
                    <div
                      className="cn-stop-collect-host"
                      onClick={(event) => event.stopPropagation()}
                      onKeyDown={(event) => event.stopPropagation()}
                    >
                      <CollectInto placeId={activity.place_id ?? null} placeTitle={activity.title} />
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        );
      })}
    </section>
  );
}
