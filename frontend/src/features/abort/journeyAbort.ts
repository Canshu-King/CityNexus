import type { components } from "../../generated/api";
import { RejectionWithFacts, rejectionWithFacts } from "../../lib/rejectionFacts";

/**
 * ORD-0464: the one door that moves a trip into the recycle bin, and the reason that rides with it.
 *
 * The reason is not a second call. `DELETE /api/v1/journeys/{journey_id}` (`backend/app/main.py:2984`)
 * takes the survey as its own body and writes the trip's `deleted_at` and one `journey_outcome_events`
 * row in the same transaction, so there is no window where the screen knows a cause that the server
 * never recorded, or the reverse.
 *
 * Three shapes leave this file and two of them reach the server:
 *   `{ answered: true, codes, note }`  -> DECLARED
 *   `{ answered: false }`              -> SKIPPED_BY_TRAVELER
 *   no body at all                    -> NOT_ASKED, which no client can *claim* in a payload; it is
 *                                         only ever what an absent body proves (`answered` is required,
 *                                         `additionalProperties: false` in `contracts/openapi.yaml`).
 * That last line is why `abortJourney` has no "just delete it" overload: a screen that stops asking
 * must delete by not sending this function at all, not by sending a word that means the same thing.
 */
export type JourneyAbortCode = components["schemas"]["JourneyAbortCode"];
export type AbortAnswer =
  | { answered: true; codes: JourneyAbortCode[]; note: string | null }
  | { answered: false };

/** Kept in sync with `contracts/openapi.yaml` (`JourneyAbortRequest.note.maxLength`).  A second source
 *  is a real risk, so `qoder-ord0464` gate arm A4 reads the yaml and asserts this number. */
export const ABORT_NOTE_MAX_LENGTH = 200;

async function request(path: string, init?: RequestInit): Promise<void> {
  const response = await fetch(`/api/v1${path}`, {
    method: "DELETE",
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
    ...init,
  });
  /* 204 has no body by definition; reading one would be the failure, not the success. */
  if (!response.ok) throw await rejectionWithFacts(response);
}

export function abortJourney(journeyId: string, answer: AbortAnswer): Promise<void> {
  return request(`/journeys/${encodeURIComponent(journeyId)}`, {
    body: JSON.stringify(answer),
  });
}

/** What the server actually holds as this trip's binning reason, or `null` when it holds none.
 *
 *  The screen renders from this rather than from what the traveller just pressed, so "刷新后还在" is
 *  the same code path as "按下之后": the sentence is read off `GET .../outcomes`, not remembered in
 *  React state.  Three answers, kept three:
 *    reason_state DECLARED           -> the codes the traveller ticked, in the traveller's order
 *    reason_state SKIPPED_BY_TRAVELER -> an answer: they were asked and chose not to say
 *    reason_state NOT_ASKED          -> this server never got the question, which is not a saying-no
 *    no reason_state at all (ABSENT)  -> a row written before this order existed: no cause is held
 *  `ABSENT` is deliberately its own arm rather than a `null`: a legacy row whose payload carries no
 *  `reason_state` is what a pre-ORD-0464 binning looks like, and the screen must not upgrade it into
 *  "the traveller declined to answer" (ORD-0355's `NULL` rule again).  It is named, not nullable,
 *  because this project type-checks with `strict: false` (`frontend/tsconfig.typecheck.json`), where a
 *  `null` discriminant collapses the union and stops narrowing the other arms.
 */
export type AbortRecord =
  | { state: "DECLARED"; codes: JourneyAbortCode[] }
  | { state: "SKIPPED_BY_TRAVELER" }
  | { state: "NOT_ASKED" }
  | { state: "ABSENT" };

async function readOutcomes(journeyId: string): Promise<AbortRecord | null> {
  const response = await fetch(`/api/v1/journeys/${encodeURIComponent(journeyId)}/outcomes`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw await rejectionWithFacts(response);
  const body = (await response.json()) as { events?: unknown[] };
  const events = Array.isArray(body.events) ? body.events : [];
  let latest: AbortRecord | null = null;
  for (const raw of events) {
    if (typeof raw !== "object" || raw === null) continue;
    const event = raw as Record<string, unknown>;
    if (event.event_type !== "JOURNEY_DELETED") continue;
    const payload = (typeof event.payload === "object" && event.payload !== null
      ? event.payload
      : {}) as Record<string, unknown>;
    const state = payload.reason_state;
    if (state === "DECLARED") {
      const codes = Array.isArray(payload.codes) ? (payload.codes as JourneyAbortCode[]) : [];
      latest = { state: "DECLARED", codes };
    } else if (state === "SKIPPED_BY_TRAVELER") {
      latest = { state: "SKIPPED_BY_TRAVELER" };
    } else if (state === "NOT_ASKED") {
      latest = { state: "NOT_ASKED" };
    } else {
      latest = { state: "ABSENT" };
    }
  }
  return latest;
}

export function readAbortRecord(journeyId: string): Promise<AbortRecord | null> {
  return readOutcomes(journeyId);
}

/** Which named refusal this device was answered with, or `null` when the answer carried no name.
 *  A 422 from this door puts the name in `error.details.errors[].type`, not in `error.reason_code`,
 *  because it is pydantic's cross-field validator answering (`abort_answer_without_codes` /
 *  `abort_skip_with_codes`) or the field checks behind it. `null` is not a failure to read: it means
 *  the screen must say it did not get a name, and pick no sentence. */
export function abortRefusalType(cause: unknown): string | null {
  if (!(cause instanceof RejectionWithFacts)) return null;
  const envelope = cause.envelope;
  if (typeof envelope !== "object" || envelope === null) return null;
  const error = (envelope as Record<string, unknown>).error;
  if (typeof error !== "object" || error === null) return null;
  const record = error as Record<string, unknown>;
  const reason = record.reason_code;
  if (typeof reason === "string" && reason.trim()) return reason;
  const details = record.details;
  if (typeof details === "object" && details !== null) {
    const errors = (details as Record<string, unknown>).errors;
    if (Array.isArray(errors) && errors.length > 0) {
      const first = errors[0] as Record<string, unknown>;
      if (typeof first.type === "string" && first.type.trim()) return first.type;
      if (typeof first.message_key === "string" && first.message_key.trim()) {
        return first.message_key;
      }
    }
  }
  return null;
}

export function abortReceipt(cause: unknown): string | null {
  if (!(cause instanceof RejectionWithFacts)) return null;
  const envelope = cause.envelope;
  if (typeof envelope !== "object" || envelope === null) return null;
  const error = (envelope as Record<string, unknown>).error;
  if (typeof error !== "object" || error === null) return null;
  const receipt = (error as Record<string, unknown>).error_receipt_id;
  return typeof receipt === "string" && receipt.trim() ? receipt : null;
}

export { RejectionWithFacts };
