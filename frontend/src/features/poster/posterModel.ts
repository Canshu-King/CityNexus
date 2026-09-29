/**
 * ORD-0472 — what one long picture of this journey contains.
 *
 * The model reads the same `V8Data` object the itinerary tab renders and reuses that screen's own
 * day grouping, so every stop on the poster is a stop the traveller can already see on the panel.
 * It asks the network nothing and it invents no day, no name and no time: a count the server does
 * not answer with is carried as `null` and shown as unknown, never filled in here.
 *
 * No copy lives in this file. Sentences belong to `i18n/LocaleContext.tsx` (both sides), and the
 * one day-total sentence is imported from `features/progress/journeyProgress.ts`, which is already
 * its only owner.
 */
import { cityCodeLabel } from "../../lib/displayVocabulary";
import { journeyProgress, type JourneyProgress } from "../progress/journeyProgress";
import { clock, groupActivitiesByDay } from "../trip/TripItinerary";
import type { V8Data } from "../../app/v8Types";

export type PosterStop = {
  /** Start and end in the trip's own zone, formatted the way the itinerary formats them. */
  from: string;
  to: string;
  title: string;
};

export type PosterDay = {
  key: string;
  label: string;
  stops: PosterStop[];
};

export type TripPoster = {
  title: string;
  city: string;
  /** The server's day count for the trip shape; `null` means the shape answers nothing. */
  dayTotal: number | null;
  /** Kept whole so the poster quotes the panel's own progress sentence instead of a paraphrase. */
  progress: JourneyProgress;
  days: PosterDay[];
  stopTotal: number;
};

export function buildTripPoster(data: V8Data, locale: string): TripPoster | null {
  const plan = data.active_plan;
  if (!plan) return null;
  const timeZone = data.journey.timezone || "UTC";
  const grouped = groupActivitiesByDay(plan.activities, timeZone, locale);
  if (grouped.length === 0) return null;

  const days = grouped.map((day) => ({
    key: day.key,
    label: day.label,
    stops: day.activities.map((activity) => ({
      from: clock(activity.start_at, timeZone),
      to: clock(activity.end_at, timeZone),
      title: activity.title,
    })),
  }));

  /* The headline count is the projection the panel quotes, not a recount of these buckets: a plan
     can hold fewer days than the trip is long, and the poster must not silently pick the other
     number. Same owner, same input, same answer as `TripItinerary.tsx`. */
  const progress = journeyProgress({
    serverDayCount: data.journey.temporal_shape?.day_count ?? null,
    days: grouped.map((day) => ({
      key: day.key,
      activityIds: day.activities.map((activity) => activity.id),
    })),
    activities: (plan.activities ?? []).map((activity) => ({
      id: activity.id,
      status: activity.status,
    })),
    currentActivityId: plan.current_activity_id ?? null,
  });

  return {
    title: data.journey.title,
    city: cityCodeLabel(data.journey.city_code, locale),
    dayTotal: progress.day_total,
    progress,
    days,
    stopTotal: days.reduce((total, day) => total + day.stops.length, 0),
  };
}
