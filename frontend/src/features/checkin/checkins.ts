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
  /* The code is kept as a *value this module switches on*, never rendered into the traveller's
     sentence: a machine token on a Chinese screen is the defect this project keeps having to fix,
     so the screen answers with its own dictionary sentence.  ORD-0507 3 adds `technical` beside it:
     the server's own words do belong on screen, but in the 「技术详情」 fold, not in the sentence. */
  | {
      kind: "refused";
      refusal: CheckinRefusal;
      status: number;
      technical: CheckinTechnical;
    }
  | { kind: "unreachable" };

export type ReadOutcome =
  | { kind: "read"; stamps: CheckinStamp[] }
  | {
      kind: "refused";
      refusal: CheckinRefusal;
      status: number;
      technical: CheckinTechnical;
    }
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

/** The server's own words about a refusal, kept apart from the sentence the screen says.
    ORD-0507 3: a traveller reads human words; the reason code, status, message and details the
    door actually answered go into the 「技术详情」 fold, so the original is never lost and never
    stands in the traveller's sentence. */
export type CheckinTechnical = {
  reason_code: string;
  http_status: number;
  message: string | null;
  details: unknown;
};

function refusalOf(body: unknown): { refusal: CheckinRefusal; reason_code: string } {
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
    reason_code: code,
  };
}

/** What the door answered, verbatim: the fold must be able to name the shape it refuses to speak. */
function technicalOf(body: unknown, status: number, reason_code: string): CheckinTechnical {
  const error = (body as any)?.error;
  const message =
    typeof error?.message === "string" && error.message.length > 0
      ? error.message
      : typeof (body as any)?.detail === "string" && (body as any).detail.length > 0
        ? ((body as any).detail as string)
        : null;
  return { reason_code, http_status: status, message, details: error?.details ?? null };
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
    const { refusal, reason_code } = refusalOf(answer.body);
    return {
      kind: "refused",
      refusal,
      status: answer.status,
      technical: technicalOf(answer.body, answer.status, reason_code),
    };
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
    const { refusal, reason_code } = refusalOf(answer.body);
    return {
      kind: "refused",
      refusal,
      status: answer.status,
      technical: technicalOf(answer.body, answer.status, reason_code),
    };
  } catch {
    return { kind: "unreachable" };
  }
}

/** The dictionary key for a refusal, so the screen never has to know what a reason code looks like.
    ORD-0507 3: one key per named refusal, because "这一趟在回收站里" and "这一站不属于这趟" are two
    different facts and the traveller cannot act on one sentence that covers both. */
export function checkinRefusalKey(refusal: CheckinRefusal): string {
  const keys: Record<CheckinRefusal, string> = {
    CHECKIN_DUPLICATE_STAMP: "checkin.duplicate",
    CHECKIN_JOURNEY_IN_RECYCLE_BIN: "checkin.refused.bin",
    CHECKIN_ACTIVITY_NOT_IN_JOURNEY: "checkin.refused.not_in_journey",
    CHECKIN_ACTIVITY_UNKNOWN: "checkin.refused.activity_unknown",
    CHECKIN_PLACE_UNKNOWN: "checkin.refused.place_unknown",
    CHECKIN_TARGET_REQUIRED: "checkin.refused.target_required",
    CHECKIN_TARGET_AMBIGUOUS: "checkin.refused.target_ambiguous",
    UNRECOGNISED: "checkin.refused",
  };
  return keys[refusal];
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
