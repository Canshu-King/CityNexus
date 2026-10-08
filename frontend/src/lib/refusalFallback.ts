/**
 * One home for the sentence a screen may say when a step failed and no usable answer arrived.
 *
 * The exception-to-DOM channel is the one place a product prints words it did not write, so what a
 * screen is allowed to say here is fixed rather than composed per screen: only what *this device*
 * knows at the moment it caught the failure -- whether an answer came at all, and with what status
 * and content type.  An upstream sentence is never the wording (Q64=1), and `error.message` is not
 * a safe stand-in for "our own words", because whichever helper threw decides what that string
 * carries -- since Q64=1 that includes whatever the server's body happened to say.
 *
 * This shape existed as a local function inside one screen and was hand-copied into three others
 * (`LiveRecovery`, `PlanComparison`, `HotelsPanel` each wrote the same zh/en pair inline), which is
 * how a channel with one rule ends up with four slightly different ones.  It lives here now so a
 * screen has one outlet to ask, and a new screen cannot invent its own.
 *
 * Returns null when the failure is none of the device-known verdicts; the caller then keeps its own
 * fallback rather than this file guessing at it.
 */

import { isOriginResponseUnusable } from "./failureAttribution";
import { isReadDeadlineMissed } from "./readDeadline";

/**
 * The unreachable-server verdict: a read deadline this device set, or the `TypeError` `fetch` throws
 * when the origin never answered.  Both say the same thing to the traveller, and neither is the
 * server's words.
 */
export function unreachableServerSentence(zh: boolean): string {
  return zh
    ? "连不上服务器，请重试。"
    : "Could not reach the server. Try again.";
}

/**
 * The verdict this device knows, in the traveller's words, or null when it knows nothing about this
 * failure.  `V8Rejection` (an answered HTTP refusal) stays with the screen that owns it because only
 * that screen carries the refusal's own facts; this outlet covers the two verdicts that are shared
 * across every screen and were being copied by hand.
 */
export function deviceKnownRefusalSentence(error: unknown, zh: boolean): string | null {
  const unusable = isOriginResponseUnusable(error);
  if (unusable) {
    return zh
      ? `服务器答了 HTTP ${error.status}，可带回来的不是这一屏能用的数据（Content-Type: ${error.content_type ?? "未知"}）。`
      : `The server answered HTTP ${error.status}, but not with data this screen can use (Content-Type: ${error.content_type ?? "unknown"}).`;
  }
  if (isReadDeadlineMissed(error) || error instanceof TypeError) {
    return unreachableServerSentence(zh);
  }
  return null;
}
