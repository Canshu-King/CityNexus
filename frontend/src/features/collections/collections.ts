import type { components } from "../../generated/api";
import { rejectionWithFacts, RejectionWithFacts } from "../../lib/rejectionFacts";

/**
 * ORD-0444 -- the three doors the collection shelf uses, in one file, so the screen cannot hide
 * what it asked the server for.
 *
 * All three are on the line in this same commit, and each is named by a line rather than by a
 * promise: `POST /api/v1/collections` (`backend/app/main.py:3211`), `GET /api/v1/collections`
 * (`backend/app/main.py:3252`) and `POST /api/v1/collections/{folder_id}/items`
 * (`backend/app/main.py:3273`), declared at `contracts/openapi.yaml:507` and
 * `contracts/openapi.yaml:555` and generated at `frontend/src/generated/api.ts:431` and
 * `frontend/src/generated/api.ts:449`.
 *
 * Two things this module deliberately does NOT do:
 *  - It does not build a shelf list out of client state. The screen renders what
 *    `GET /api/v1/collections` answered, in the order it was answered: shelves oldest-created first
 *    (`_collection_shelves`, `backend/app/main.py:3157`) and rows first-put-on first
 *    (`_collection_rows_by_folder`, `backend/app/main.py:3173`). A client-side re-sort would make
 *    the order a screen displays be a fact the server never stated.
 *  - It does not reach for a door the server has not got. There is no rename door and no
 *    remove-from-shelf door in this version, so nothing is exported here that would let a screen
 *    offer one -- ORD-0385's rule that copy may not exceed the mechanism applies to exports too.
 *
 * `POST /api/v1/collections/{folder_id}/items` is exported because the container needs a write door
 * to exist at all, and the counter-case is answered by name at that door. This order's screen is
 * read-only and calls only `readCollections` and `createCollection`; the 收藏 picker that calls
 * `addPlaceToCollection` is the other half of the capture chain and belongs to the sheet that owns
 * the multi-select (ORD-0435's three-exit row).
 */

/** The shelf list, and the one path that creates a shelf. Both are literal, matching the precedent
 *  in `features/trash/journeyTrash.ts:32`: a URL held in one place is what lets the next slice
 *  change the door without re-reading every screen. */
export const COLLECTIONS_LIST_PATH = "/collections";

/** A shelf as the server answers it. Typed from the contract rather than re-declared here, so the
 *  screen's rows and the server's schema cannot drift apart silently. */
export type CollectionShelf = components["schemas"]["CollectionFolder"];
export type CollectionRow = components["schemas"]["CollectionItem"];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) throw await rejectionWithFacts(response);
  // An answer with no body is not an empty list: `[]` and `null` mean different things to a
  // screen, and only one of them is something the server said.
  const text = await response.text();
  return (text ? JSON.parse(text) : null) as T;
}

export function itemPath(folderId: string): string {
  // `folder_id` is a plain string on the wire (`contracts/openapi.yaml:2000`), so it is escaped
  // rather than assumed to be uuid-shaped -- a shelf id that needed escaping is a malformed id,
  // and the door would answer it with `404 COLLECTION_FOLDER_NOT_FOUND`.
  return `/collections/${encodeURIComponent(folderId)}/items`;
}

export function readCollections(): Promise<CollectionShelf[]> {
  return request<CollectionShelf[]>(COLLECTIONS_LIST_PATH);
}

/** The one write this screen is allowed to make: name a shelf. It is the empty state's action. */
export function createCollection(name: string): Promise<CollectionShelf> {
  return request<CollectionShelf>(COLLECTIONS_LIST_PATH, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

/** Which place joins which shelf. Exported for the capture sheet; this screen does not call it. */
export function addPlaceToCollection(
  folderId: string,
  placeId: string,
  note?: string | null
): Promise<CollectionRow> {
  return request<CollectionRow>(itemPath(folderId), {
    method: "POST",
    body: JSON.stringify(note === undefined || note === null ? { place_id: placeId } : { place_id: placeId, note }),
  });
}

/**
 * Which condition refused, in the server's own token, read out of the parsed envelope.
 *
 * `error.reason_code` is where ORD-0101 put it (`backend/app/main.py:615` -- `http_error` forwards
 * `getattr(exc, "reason_code", null)`), and the three names this container answers with are
 * `COLLECTION_FOLDER_NOT_FOUND` (404), `PLACE_NOT_FOUND` (404) and `PLACE_ALREADY_IN_COLLECTION`
 * (409), each raised at its own line in `backend/app/main.py` (3307, 3315, 3344).
 *
 * Returning `null` is not a failure: it means this device did not read a name, and the screen then
 * says that instead of picking a sentence for a condition it cannot quote.
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

/** `error.details`, same envelope. The 409 carries the row that already won, and the screen quotes
 *  it rather than restating the traveller's own tap back at them. */
export function refusalDetails(cause: unknown): Record<string, unknown> | null {
  if (!(cause instanceof RejectionWithFacts)) return null;
  const envelope = cause.envelope;
  if (typeof envelope !== "object" || envelope === null) return null;
  const error = (envelope as Record<string, unknown>).error;
  if (typeof error === "object" && error !== null) {
    const details = (error as Record<string, unknown>).details;
    if (typeof details === "object" && details !== null) return details as Record<string, unknown>;
  }
  return null;
}

export { RejectionWithFacts };
