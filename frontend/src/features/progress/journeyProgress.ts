/**
 * ORD-0438 — the journey's progress, expressed as one contract instead of a second counting system.
 *
 * The two claims this answers, and where each number already lives:
 *   共几天        <- `journey.temporal_shape.day_count`, projected by the server.  ORD-0063 ruled the
 *                    span must not be rounded into days on the client (that called an 08:00-20:00
 *                    trip "2 天" and then divided the budget by a day nobody stored), and a null there
 *                    means the stored window cannot be ordered at all -- which shows as unknown, never
 *                    as 1.  This module keeps that rule and is the only place the itinerary's headline
 *                    gets its number from.
 *   已完成几处     <- `active_plan.activities[].status`, judged with `TERMINAL_ACTIVITY_STATES` from
 *                    `lib/executionWindow.ts` rather than a local list, because a third definition of
 *                    "this stop is over" is exactly the second system this order forbids.  "Completed"
 *                    is reported separately from "settled": a skipped or cancelled stop is over, but it
 *                    was not walked, and the traveller can tell those apart from the count.
 *   第几天        <- the day group that holds the cursor activity.  Groups come in as an argument: the
 *                    grouping rule belongs to the screen that draws the day strip, not to a second copy.
 *
 * There is deliberately no percentage.  `api/citynexus.ts` records the same decision on the
 * preparation surface -- the backend refuses to invent a denominator, and a percentage would be one.
 *
 * Copy lives here for the reason `lib/pretripChecklist.ts` gives: `LocaleContext.tsx` is under
 * concurrent edit by other lanes.
 */
import { TERMINAL_ACTIVITY_STATES } from "../../lib/executionWindow";
import { dictionaryCopy, dictionaryText } from "../../i18n/LocaleContext";

export type ProgressActivity = { id: string; status: string };
export type ProgressDayGroup = { key: string; activityIds: string[] };

export type JourneyProgress = {
  day_total: number | null;
  day_total_source: "server_temporal_shape" | "server_has_no_shape" | "no_activities";
  day_of: number | null;
  day_of_basis: "cursor_group" | "cursor_unreadable" | "no_cursor";
  completed_count: number;
  settled_count: number;
  planned_total: number;
};

export function journeyProgress(input: {
  serverDayCount: number | null | undefined;
  days: ProgressDayGroup[];
  activities: ProgressActivity[];
  currentActivityId: string | null | undefined;
}): JourneyProgress {
  const { serverDayCount, days, activities, currentActivityId } = input;
  const settled = activities.filter((item) => TERMINAL_ACTIVITY_STATES.has(item.status));
  const cursorGroup = currentActivityId
    ? days.findIndex((group) => group.activityIds.includes(currentActivityId))
    : -1;
  return {
    day_total: typeof serverDayCount === "number" ? serverDayCount : null,
    day_total_source: activities.length === 0
      ? "no_activities"
      : typeof serverDayCount === "number" ? "server_temporal_shape" : "server_has_no_shape",
    day_of: cursorGroup >= 0 ? cursorGroup + 1 : null,
    day_of_basis: cursorGroup >= 0
      ? "cursor_group"
      : currentActivityId ? "cursor_unreadable" : "no_cursor",
    completed_count: activities.filter((item) => item.status === "COMPLETED").length,
    settled_count: settled.length,
    planned_total: activities.length,
  };
}

/**
 * The same facts as one sentence, in the shape the order asked for: an empty counter reads as a
 * contract -- what has to happen before it moves -- and never as "no data".  The day position leads
 * whenever the server's cursor can be placed, because "已走到第几天" and "已完成几处" are two different
 * claims and a single branch that hides one behind the other would answer only half the order.  Every
 * clause names the fact that would change it, so nothing here can be read as "everything is fine".
 */
export function progressContractCopy(p: JourneyProgress, zh: boolean): string {
  if (p.planned_total === 0) {
    return dictionaryCopy(zh ? "zh-CN" : "en", "progress.none.scheduled");
  }
  const skipped = p.settled_count - p.completed_count;
  const parts: string[] = [];
  if (p.day_total === null) {
    parts.push(dictionaryCopy(zh ? "zh-CN" : "en", "progress.day.total.blank"));
  } else if (p.day_of === null) {
    parts.push(dictionaryText(zh ? "zh-CN" : "en", "progress.day.total.only", { count: p.day_total }));
  } else {
    parts.push(dictionaryText(zh ? "zh-CN" : "en", "progress.day.of.total", { day: p.day_of, total: p.day_total }));
  }
  if (p.completed_count === 0) {
    parts.push(dictionaryText(zh ? "zh-CN" : "en", "progress.stop.none.walked", { count: p.planned_total }));
  } else {
    parts.push(dictionaryText(zh ? "zh-CN" : "en", "progress.stop.completed", { completed: p.completed_count, total: p.planned_total })
      + (skipped > 0 ? dictionaryText(zh ? "zh-CN" : "en", "progress.stop.skipped.clause", { count: skipped }) : (zh ? "。" : ".")));
  }
  return parts.join(zh ? "" : " ");
}

/** Why the day position is blank, in the traveller's words rather than a null. */
export function dayOfGapCopy(p: JourneyProgress, zh: boolean): string | null {
  if (p.day_of !== null || p.planned_total === 0) return null;
  return dictionaryCopy(zh ? "zh-CN" : "en",
    p.day_of_basis === "no_cursor" ? "progress.day.gap.no.cursor" : "progress.day.gap.stale.cursor");
}
