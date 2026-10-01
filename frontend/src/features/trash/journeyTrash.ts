import type { components } from "../../generated/api";
import {
  refusalReasonCode,
  rejectionWithFacts,
  RejectionWithFacts,
} from "../../lib/rejectionFacts";

/**
 * ORD-0402 slice 2 -- the two doors the recycle-bin screen uses, in one file, so the screen itself
 * renders and cannot hide what it asked the server for.
 *
 * BOTH DOORS ARE ON THE LINE NOW. The write door landed with ORD-0399:
 * `POST /api/v1/journeys/{journey_id}/undelete` (`backend/app/main.py:3305`), no `Idempotency-Key` --
 * the durable column decides whether the write happens -- answering `409 JOURNEY_NOT_DELETED` rather
 * than reporting a success that did not occur (`backend/app/main.py:3348`). The read door landed
 * with ORD-0402 slice 1 at `backend/app/main.py:3390`: `GET /api/v1/recycle-bin/journeys`, declared in
 * `contracts/openapi.yaml:724` and generated at `frontend/src/generated/api.ts:466`, each row
 * carrying the stored `deleted_at` and `bin_state` = `IN_RECYCLE_BIN`
 * (`backend/app/schemas.py:271` and `:272`) -- so this screen never has to conclude "it was deleted"
 * from the trip being missing from `GET /api/v1/journeys`, which keeps its own `deleted_at IS NULL`
 * promise (`backend/app/main.py:3196`).
 *
 * The name this file chose is the name slice 1 shipped, so the constant below needed no edit when the
 * door arrived; that is the point of keeping the URL in one place. The reason for not using
 * `/journeys/discarded` still stands and was measured, not guessed (see
 * `review/ord0402/stack_receipt_r1.json`, key `shadowed_collection_name`): the landed
 * `GET /api/v1/journeys/{journey_id}` door is declared earlier in `app.main`, so a one-segment
 * collection name under `/journeys/` is swallowed by it and answers 422 with
 * `loc: ["path","journey_id"]`, `type: "uuid_parsing"`, `message_key: "validation.not_an_id"` (the
 * server's own receipt for that answer was `CNX-TWXNJHE2`).
 *
 * One thing the screen inherits rather than decides: slice 1 orders the list newest-deletion first
 * (`backend/app/main.py:3413`), and the panel renders the array as answered, so the order a traveller
 * sees is the server's order, not a client-side re-sort.
 */
export const TRASH_LIST_PATH = "/recycle-bin/journeys";

/** A binned trip, typed from the contract rather than re-declared here: slice 1 shipped
 *  `RecycleBinJourney` into the generated client (`frontend/src/generated/api.ts:3107`), so the
 *  screen's rows and the server's schema cannot drift apart silently. The guards in the panel stay
 *  anyway -- a model says what the server intends to send, not what this response did send. */
export type DiscardedJourney = components["schemas"]["RecycleBinJourney"];

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
 * ORD-0535 -- one discard or one 找回, as the audit projection answers it.
 *
 * `GET /api/v1/journeys/{id}/history` is an existing door and this screen only reads it: the door
 * passes an action it does not recognise straight through as `event_type`, and both
 * `journey.deleted` and `journey.undeleted` are unrecognised, so the sequence arrives in the
 * server's own order (`order_by(AuditLog.created_at)`) without anything here re-sorting it.
 * `deleted_at` is what the discard wrote into the log from ORD-0535 onward; rows older than that
 * carry none, which is why the screen has a separate sentence for the log's own moment.
 */
export type DiscardEvent = {
  event_type: string;
  timestamp: string | null;
  deleted_at: string | null;
};

export async function readDiscardSequence(journeyId: string): Promise<DiscardEvent[]> {
  const rows = await request<Array<Record<string, unknown>>>(
    `/journeys/${encodeURIComponent(journeyId)}/history`,
  );
  return rows
    .filter((row) => row["event_type"] === "journey.deleted" || row["event_type"] === "journey.undeleted")
    .map((row) => {
      const facts = (row["facts"] ?? {}) as Record<string, unknown>;
      return {
        event_type: String(row["event_type"]),
        timestamp: typeof row["timestamp"] === "string" ? String(row["timestamp"]) : null,
        deleted_at: typeof facts["deleted_at"] === "string" ? String(facts["deleted_at"]) : null,
      };
    });
}

/**
 * Which condition refused, in the server's own token.
 *
 * ORD-0465: the reading itself moved to `lib/rejectionFacts.ts`, where the second screen that needs it
 * can reach it without importing this feature. It is re-exported under the name this panel already
 * imports, so the one copy stays the one copy and nothing here changed what it answers.
 */
export { refusalReasonCode };

export { RejectionWithFacts };
