import { rejectionWithFacts, RejectionWithFacts } from "../../lib/rejectionFacts";

/**
 * ORD-0402 slice 2 -- the two doors the recycle-bin screen uses, in one file, so the screen itself
 * renders and cannot hide what it asked the server for.
 *
 * THE WRITE DOOR IS REAL AND LANDED. `POST /api/v1/journeys/{journey_id}/undelete` is on the
 * authority line (`backend/app/main.py:2999` at 97766b2dfd7a5a7668f6750e3bc13b698c416975), takes no
 * `Idempotency-Key` -- the durable column decides whether the write happens -- and answers
 * `409 JOURNEY_NOT_DELETED` rather than reporting a success that did not occur
 * (`backend/app/main.py:3033`).
 *
 * THE READ DOOR IS NOT BUILT YET, and this is the one line in this feature that depends on
 * ORD-0402 slice 1. Nothing on the authority line can enumerate binned trips today:
 * `GET /api/v1/journeys` filters `deleted_at IS NULL` (`backend/app/main.py:2951`) and its docstring
 * makes that a promise, and `journey_schema()` does not emit `deleted_at` at all
 * (`backend/app/services.py:382`, `backend/app/schemas.py:239`), so no payload on this tree says
 * "this trip is in the bin". The panel therefore has to have a name for the door, and the name has
 * to be one place. When slice 1 lands, change `TRASH_LIST_PATH` and the two field names below --
 * nothing else in this feature reads a URL.
 *
 * What slice 1 was told to provide, restated here so the shapes can be compared rather than
 * guessed at review time: every row carries `deleted_at` with its raw value, and a named state that
 * says the row is in the bin -- so this screen never infers "it was deleted" from "it is missing
 * from the other list".
 *
 * Why this name rather than `/journeys/discarded`, measured on this lane's private stack (see
 * `review/ord0402/stack_receipt_r1.json`, key `shadowed_collection_name`): the landed
 * `GET /api/v1/journeys/{journey_id}` door is declared earlier in `app.main`, so a one-segment
 * collection name under `/journeys/` is swallowed by it and answers 422 with
 * `loc: ["path","journey_id"]`, `type: "uuid_parsing"`, `message_key: "validation.not_an_id"` (the
 * server's own receipt for that answer was `CNX-TWXNJHE2`). Such a name is reachable only if it is
 * declared before that door; `/recycle-bin/journeys` cannot be shadowed by it.
 */
export const TRASH_LIST_PATH = "/recycle-bin/journeys";

/** A binned trip, as this screen needs it. Declared here rather than taken from
 *  `frontend/src/generated/api.ts` for the reason `PlanVersionHistoryPanel.tsx:20` documents: the
 *  committed generated file has no such path yet, and regenerating it here would fold other orders'
 *  drift into this diff. */
export type DiscardedJourney = {
  id: string;
  title: string;
  city_code?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  status?: string | null;
  /** slice 1's raw value, not a re-derived one. `null` here means the server did not answer. */
  deleted_at?: string | null;
  /** the server's own word for "in the bin" (`IN_RECYCLE_BIN` is what this file expects until told
   *  otherwise); absent means the row cannot be shown as binned. */
  bin_state?: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) throw await rejectionWithFacts(response);
  return (await response.json()) as T;
}

export function readDiscardedJourneys(): Promise<DiscardedJourney[]> {
  return request<DiscardedJourney[]>(TRASH_LIST_PATH);
}

/** The 找回 write. Returns the trip as the server now holds it (`response_model=JourneySchema`). */
export function undeleteJourney(journeyId: string): Promise<{ id: string; title: string }> {
  return request<{ id: string; title: string }>(
    `/journeys/${encodeURIComponent(journeyId)}/undelete`,
    { method: "POST" },
  );
}

/**
 * Which condition refused, in the server's own token, read out of the parsed envelope.
 *
 * `error.reason_code` is where ORD-0101 put it (`backend/app/main.py:598` -- `http_error` forwards
 * `getattr(exc, "reason_code", null)`), and the two names this door can answer with are
 * `JOURNEY_NOT_DELETED` (409) and `JOURNEY_NOT_FOUND` (404). Returning `null` is not a failure: it
 * means this device did not read a name, and the screen then says so instead of picking a sentence.
 */
export function refusalReasonCode(cause: unknown): string | null {
  if (!(cause instanceof RejectionWithFacts)) return null;
  const envelope = cause.envelope;
  if (typeof envelope !== "object" || envelope === null) return null;
  const error = (envelope as Record<string, unknown>).error;
  if (typeof error === "object" && error !== null) {
    const code = (error as Record<string, unknown>).reason_code;
    if (typeof code === "string" && code.trim()) return code;
  }
  const top = (envelope as Record<string, unknown>).reason_code;
  return typeof top === "string" && top.trim() ? top : null;
}

export { RejectionWithFacts };
