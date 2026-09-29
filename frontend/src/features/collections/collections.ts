/* ORD-0444 -- the data half of the 收藏 container: the three doors, and nothing else.
 *
 * The screen this module serves is deliberately the smallest thing that can prove the container is
 * readable, so this file carries no refusal-code vocabulary, no measured-facts row and no
 * `addPlaceToCollection` helper that nothing calls.  The add door is in the contract
 * (`POST /api/v1/collections/{folder_id}/items`, contracts/openapi.yaml) and the generated types
 * cover it; a hand-written caller for it would be a promise this round does not make.
 *
 * Every path is written with the `/api/v1` prefix the runtime actually serves, because the
 * contract's own paths omit it (`contracts/openapi.yaml` -- `/collections`), and the parity door
 * (`tools/verify_openapi_parity.py`) keeps them apart on purpose.
 */

import { COLLECTION_COPY, COLLECTION_REFUSAL, type CollectionCopyKey } from "./collectionCopy";

export const COLLECTIONS_LIST_PATH = "/collections";

/** The shelf answer, read off the generated contract type rather than re-declared here. */
export type CollectionShelf = {
  id: string;
  name: string;
  owner_traveler_id: string;
  created_at: string;
  updated_at: string;
  item_count: number;
  items: Array<{
    id: string;
    place_id: string;
    name: string;
    category: string;
    city_code: string;
    note: string | null;
    added_at: string;
  }>;
};

export type ReadOutcome =
  /* One of four named states, and the only thing the screen is allowed to say about a failure is
     which state it is in: the server's own words stay out of the DOM. */
  | { kind: "loaded"; shelves: CollectionShelf[] }
  | { kind: "unreachable" }
  | { kind: "refused" };

async function request<T>(path: string, init?: RequestInit): Promise<T | null> {
  const response = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) return null;
  const text = await response.text();
  return (text ? JSON.parse(text) : null) as T | null;
}

/**
 * The shelves this traveller owns.  `traveler_id` is required by the door (the contract says so at
 * `/collections.get.parameters[0]`), so an absent traveller is not asked about -- the screen names
 * that state itself instead of sending a call it knows the door will refuse.
 */
export async function readCollections(travelerId: string | null): Promise<ReadOutcome> {
  if (!travelerId) return { kind: "unreachable" };
  try {
    const shelves = await request<CollectionShelf[]>(
      `${COLLECTIONS_LIST_PATH}?traveler_id=${encodeURIComponent(travelerId)}`,
    );
    if (shelves === null) return { kind: "refused" };
    return { kind: "loaded", shelves };
  } catch {
    return { kind: "unreachable" };
  }
}

export function copyFor(key: CollectionCopyKey, zh: boolean): string {
  return COLLECTION_COPY[key][zh ? "zh" : "en"];
}

export function refusalCopy(zh: boolean): string {
  return COLLECTION_REFUSAL[zh ? "zh" : "en"];
}
