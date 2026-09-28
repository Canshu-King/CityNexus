/**
 * ORD-0436 -- the doors this screen reads, in one file, so what it claims and what it asked the
 * server are separable.
 *
 * Two of the three are on the line today and are named by their server-side position:
 *  - `GET /api/v1/journeys` -- `backend/app/main.py:2955`, the list door ORD-0383 slice 1 kept.
 *  - `GET /api/v1/journeys/{id}/agent-feed` -- `backend/app/main.py:7407`, the activity stream that
 *    reads `audit_logs` for one trip.
 * The third is not on the line: the member, visibility and invitation state belongs to ORD-0434's
 * sharing layer, and it has no path to call yet. This module does not guess one. The panel asks it
 * the same question the other two get, gets `null` back, and says "this server has no such door"
 * instead of showing an empty roster that would read as "nobody shares this trip" -- a missing
 * answer and an empty answer are different facts, and the second one is a claim this tree has no
 * source for.
 */
import { rejectionWithFacts, RejectionWithFacts } from "../../lib/rejectionFacts";

export const JOURNEY_LIST_PATH = "/journeys";
export const ACTIVITY_FEED_SUFFIX = "/agent-feed";
export const ACCESS_DOOR_PATH = "/access";

export type JourneySummary = {
  id: string;
  title: string;
  city_code?: string;
  status?: string;
};

export type ActivityEvent = {
  id: string;
  timestamp: string;
  event_type: string;
  summary: string;
  actor_type?: string | null;
  actor_id?: string | null;
  /** Whose row an action touched. The feed does not send this today, and the panel says so out loud
   *  rather than filling it from `actor_id` -- who tapped is not who changed. */
  member_name?: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) throw await rejectionWithFacts(response);
  return (await response.json()) as T;
}

export function readJourneys(): Promise<JourneySummary[]> {
  return request<JourneySummary[]>(JOURNEY_LIST_PATH);
}

/** The server's `summary` is deliberately not trusted for the words on screen: for an action the
 *  projection does not know it derives a capitalised English phrase out of the token
 *  (`backend/app/main.py:7390`), which is a machine name wearing a sentence. The screen keeps the
 *  token in the details face and says its own sentence from `accessVocabulary.ts`. */
export function readActivity(journeyId: string): Promise<ActivityEvent[]> {
  return request<{ events: ActivityEvent[] }>(
    `/journeys/${encodeURIComponent(journeyId)}${ACTIVITY_FEED_SUFFIX}?limit=50`,
  ).then((answer) => answer.events);
}

/** `null` means "this device did not get an answer to ask with" -- the door is absent, not empty. */
export type AccessState = {
  door: "present";
  roles: Record<string, unknown> | null;
  visibility: string | null;
  members: unknown[] | null;
  invitations: { used: number | null; cap: number | null; ttl_hours: number | null } | null;
};

export async function readAccessState(journeyId: string): Promise<AccessState | null> {
  try {
    const answer = await request<Record<string, unknown>>(
      `/journeys/${encodeURIComponent(journeyId)}${ACCESS_DOOR_PATH}`,
    );
    const invitations = answer.invitations;
    const quota =
      invitations && typeof invitations === "object"
        ? (invitations as Record<string, unknown>)
        : null;
    const numberOrNull = (value: unknown): number | null =>
      typeof value === "number" && Number.isFinite(value) ? value : null;
    return {
      door: "present",
      roles: (answer.roles as Record<string, unknown>) ?? null,
      visibility: typeof answer.visibility === "string" ? answer.visibility : null,
      members: Array.isArray(answer.members) ? answer.members : null,
      invitations: quota
        ? {
            used: numberOrNull(quota.used ?? quota.member_count),
            cap: numberOrNull(quota.cap ?? quota.limit),
            ttl_hours: numberOrNull(quota.ttl_hours ?? quota.valid_hours),
          }
        : null,
    };
  } catch (cause) {
    const status = cause instanceof RejectionWithFacts ? cause.http_status : null;
    if (status === 404 || status === 405 || status === 501) return null;
    throw cause;
  }
}

export { RejectionWithFacts };
