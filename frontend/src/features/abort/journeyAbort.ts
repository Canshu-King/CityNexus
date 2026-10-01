/* ORD-0505: the 中止 door, typed from the contract rather than re-declared here.
 *
 * `abortJourney` is the only write; the reason it carries is stored in `journeys.cancelled_reason`
 * (`backend/db/schema.sql`), so the screen never becomes the only place the why exists.  No
 * `Idempotency-Key`: the backend decides from the durable `status`, and a replayed tap answers
 * `JOURNEY_ABORT_ALREADY_CANCELLED` -- the door that does take the header replays a computation.
 */
import type { components } from "../../generated/api";
import { rejectionWithFacts, refusalReasonCode, type RejectionWithFacts } from "../../lib/rejectionFacts";

export const ABORT_PATH = (journeyId: string) => `/journeys/${encodeURIComponent(journeyId)}/abort`;

export type AbortedJourney = components["schemas"]["Journey"];
export type AbortRejection = RejectionWithFacts;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) throw await rejectionWithFacts(response);
  return (await response.json()) as T;
}

export function abortJourney(
  journeyId: string,
  facts: { reason: string; requestedBy: string },
): Promise<AbortedJourney> {
  return request<AbortedJourney>(ABORT_PATH(journeyId), {
    method: "POST",
    body: JSON.stringify({ reason: facts.reason, requested_by: facts.requestedBy }),
  });
}

export { refusalReasonCode };
