/**
 * ORD-0528 — "share this picture" without opening a second door.
 *
 * The poster is a rendering of a journey, so sharing it means handing somebody a link to the same
 * journey with the poster form asked for on the other end. That is exactly what the share family on
 * the line already does: `POST /api/v1/journeys/{id}/share-grants` mints the grant and its token, and
 * `GET /api/v1/journeys/{id}/share-grants` lists what the server believes exists. No new write
 * endpoint is added here, and no second token store.
 *
 * The one thing this file refuses to do is report success from the create answer. A 201 is this
 * device's claim about a write; the fact the traveller reads on screen is that the *list* door, read
 * back after the write, carries the row. If the list does not answer, or answers without the row, the
 * outcome is a named non-confirmation and the sheet says so. The row identity printed on screen
 * (`grant_id`) is read out of that list answer, not out of the create answer, and the read-back door
 * `shareGrantRead.ts` types its rows without a `token`, so the only string this file takes from the
 * create answer is the token itself -- which is what the link is assembled from.
 */
import { createShareGrant } from "../access/accessDoors";
import { readShareGrants } from "../inbox/shareGrantRead";
import { refusalReasonCode, RejectionWithFacts } from "../../lib/rejectionFacts";

/** The address segment that asks for the poster form of a shared trip. */
export const POSTER_SHARE_FORM = "poster";

/** The tier the poster link is opened at: the same one the trip share uses for a copyable link. */
export const POSTER_SHARE_VISIBILITY = "LINK_READ";

export function posterSharePath(token: string): string {
  return `/v8/shared/${encodeURIComponent(token)}/${POSTER_SHARE_FORM}`;
}

export type PosterShareOutcome =
  | {
      state: "CONFIRMED";
      grant_id: string;
      path: string;
      rows_read: number;
    }
  | {
      state: "NOT_CONFIRMED";
      reason:
        | "CREATE_REFUSED"
        | "NO_TOKEN"
        | "NOT_IN_SERVER_READ"
        | "REVOKED_IN_SERVER_READ"
        | "READ_NOT_ANSWERED";
      http_status: number | string;
      detail: string;
    };

/**
 * Create the grant, then ask the server what grants exist and look for the row it just made.
 *
 * `travelerId` is the trip's own traveller, read off the payload the screen was given -- the door
 * takes this as a self-reported signature, so sending anything else would be inventing an identity.
 */
export async function sharePosterLink(
  journeyId: string,
  travelerId: string,
): Promise<PosterShareOutcome> {
  let created;
  try {
    created = await createShareGrant(journeyId, {
      visibility: POSTER_SHARE_VISIBILITY,
      created_by: travelerId,
      expires_at: null,
    });
  } catch (error) {
    /* Read the number off the object the door actually throws. `RejectionWithFacts` carries
       `http_status`; a `.status` probe here would answer `undefined` for every real refusal and the
       screen would print "状态码 unreachable" about a server that did answer with a number. That is
       what the first run of this arm caught: the stubbed 403 read back as unreachable. */
    const refused = error instanceof RejectionWithFacts ? error.http_status : "unreachable";
    return {
      state: "NOT_CONFIRMED",
      reason: "CREATE_REFUSED",
      http_status: refused,
      detail: refusalReasonCode(error as never) ?? "UNNAMED_REFUSAL",
    };
  }

  if (!created.token) {
    /* The grant may well exist -- the create door just did not hand back what opens it. That is a
       non-confirmation for this screen, because the thing it is about to claim is "here is a link",
       and a link with no minted token in it is a sentence about a door nobody can walk through. */
    return {
      state: "NOT_CONFIRMED",
      reason: "NO_TOKEN",
      /* Not `201`: the door that made this call returns the parsed body and drops the status, so the
         only honest value here is that no number was carried up to this layer. Writing 201 would be
         the screen quoting a response it never measured. */
      http_status: "not_carried_by_door",
      detail: created.id,
    };
  }

  /* The list door throws on a refusal it cannot classify (a 500, a 403), and an exception escaping
     here would leave the sheet reading "Asking the server…" for ever with the button disabled -- a
     control that swallowed the answer. So this leg is wrapped too, and a refusal on the read side is
     its own named non-confirmation. */
  let read;
  try {
    read = await readShareGrants(journeyId);
  } catch (error) {
    return {
      state: "NOT_CONFIRMED",
      reason: "READ_NOT_ANSWERED",
      http_status: error instanceof RejectionWithFacts ? error.http_status : "unreachable",
      detail: refusalReasonCode(error as never) ?? "UNNAMED_REFUSAL",
    };
  }
  if (read.state !== "ANSWERED") {
    return {
      state: "NOT_CONFIRMED",
      reason: "READ_NOT_ANSWERED",
      http_status: read.http_status,
      detail: "",
    };
  }
  const row = read.rows.find((candidate) => candidate.id === created.id);
  if (!row) {
    return {
      state: "NOT_CONFIRMED",
      reason: "NOT_IN_SERVER_READ",
      http_status: read.http_status,
      detail: created.id,
    };
  }
  if (row.revoked_at) {
    return {
      state: "NOT_CONFIRMED",
      reason: "REVOKED_IN_SERVER_READ",
      http_status: read.http_status,
      detail: row.id,
    };
  }

  return {
    state: "CONFIRMED",
    grant_id: row.id,
    path: posterSharePath(created.token),
    rows_read: read.rows.length,
  };
}
