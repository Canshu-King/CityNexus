/* ORD-0476 slice 2 -- the footprint client: the two doors that are on the line.
 *
 * Paths carry the `/api/v1` prefix the runtime mounts, not the contract's own (`contracts/openapi.yaml`
 * lists `/journeys/{journey_id}/checkins`, and `tools/verify_openapi_parity.py` maps one onto the
 * other).  This is the trap the sibling order fell into one round ago: fetching the contract's path
 * gets the SPA fallback -- a 200 whose body is HTML -- and the screen reads that as its own failure.
 */

import type { components } from "../../generated/api";

export type CheckinStamp = components["schemas"]["JourneyCheckin"];

export const CHECKINS_PATH = (journeyId: string) =>
  `/api/v1/journeys/${encodeURIComponent(journeyId)}/checkins`;

/** The refusals this screen can say something honest about, read out of `error.reason_code`. */
export type CheckinRefusal =
  | "CHECKIN_DUPLICATE_STAMP"
  | "CHECKIN_JOURNEY_IN_RECYCLE_BIN"
  | "CHECKIN_ACTIVITY_NOT_IN_JOURNEY"
  | "CHECKIN_ACTIVITY_UNKNOWN"
  | "CHECKIN_PLACE_UNKNOWN"
  | "CHECKIN_TARGET_REQUIRED"
  | "CHECKIN_TARGET_AMBIGUOUS"
  | "UNRECOGNISED";

export type StampOutcome =
  | { kind: "stamped"; stamp: CheckinStamp }
  /* The code is kept as a *value this module switches on*, never rendered: an attribute slot counts
     as DOM under the exposure rule, and a machine token on a Chinese screen is the defect this
     project keeps having to fix. The screen answers with its own dictionary sentence. */
  | { kind: "refused"; refusal: CheckinRefusal; status: number }
  | { kind: "unreachable" };

export type ReadOutcome =
  | { kind: "read"; stamps: CheckinStamp[] }
  | { kind: "refused"; refusal: CheckinRefusal; status: number }
  | { kind: "unreachable" };

async function call(path: string, init?: RequestInit) {
  const response = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    return { ok: response.ok, status: response.status, body: null };
  }
  return { ok: response.ok, status: response.status, body };
}

/** The refusal name, from the envelope -- or `UNRECOGNISED`, which the screen shows as a gap. */
function refusalOf(body: unknown): { refusal: CheckinRefusal; status: number } {
  const error = (body as any)?.error;
  const code = typeof error?.reason_code === "string" ? error.reason_code : "";
  const known: CheckinRefusal[] = [
    "CHECKIN_DUPLICATE_STAMP",
    "CHECKIN_JOURNEY_IN_RECYCLE_BIN",
    "CHECKIN_ACTIVITY_NOT_IN_JOURNEY",
    "CHECKIN_ACTIVITY_UNKNOWN",
    "CHECKIN_PLACE_UNKNOWN",
    "CHECKIN_TARGET_REQUIRED",
    "CHECKIN_TARGET_AMBIGUOUS",
  ];
  return {
    refusal: (known as string[]).includes(code)
      ? (code as CheckinRefusal)
      : "UNRECOGNISED",
    status: 0,
  };
}

/** One tap on one stop. Nothing here is written locally: a stamp exists when the door says 201. */
export async function stampStop(journeyId: string, activityId: string): Promise<StampOutcome> {
  try {
    const answer = await call(CHECKINS_PATH(journeyId), {
      method: "POST",
      body: JSON.stringify({ activity_id: activityId }),
    });
    if (answer.ok && answer.body) {
      return { kind: "stamped", stamp: answer.body as CheckinStamp };
    }
    const { refusal } = refusalOf(answer.body);
    return { kind: "refused", refusal, status: answer.status };
  } catch {
    return { kind: "unreachable" };
  }
}

/** The trip's footprints, as the server holds them. */
export async function readCheckins(journeyId: string): Promise<ReadOutcome> {
  try {
    const answer = await call(CHECKINS_PATH(journeyId));
    if (answer.ok && Array.isArray(answer.body)) {
      return { kind: "read", stamps: answer.body as CheckinStamp[] };
    }
    const { refusal } = refusalOf(answer.body);
    return { kind: "refused", refusal, status: answer.status };
  } catch {
    return { kind: "unreachable" };
  }
}

/**
 * Which words a stamp points at. The server resolves the target on every read, so a stamp whose
 * activity has since been removed from the plan answers `activity_title: null` -- and this says
 * "the stop is gone" rather than showing an empty cell or reusing the place's name for it.
 */
export function stampLabel(stamp: CheckinStamp): string | null {
  if (stamp.target_kind === "ACTIVITY") return stamp.activity_title;
  return stamp.place_name;
}
