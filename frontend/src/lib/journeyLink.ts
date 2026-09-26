/**
 * ORD-0357 — the journey link a traveller can actually take out of the phone.
 *
 * ORD-0351 made `/v8/<journey uuid>` a real entry point, but the only place that URL is ever written
 * is `V8Experience.tsx`'s `history.pushState`, and on a phone the address bar is hidden -- so the
 * traveller could open a journey and still had no way to hand its link to anyone.
 *
 * The URL is built from `window.location.origin` rather than a constant: the same bundle answers on a
 * lane port, the phone tunnel and a filed domain, and a hard-coded base would be wrong on two of the
 * three.  It lives here, away from the component, because all three failure shapes have to be judged
 * without standing in front of a browser to revoke a permission.
 */

export type JourneyLinkFailure = "NO_JOURNEY" | "INSECURE_CONTEXT" | "CLIPBOARD_UNAVAILABLE";

export type JourneyLinkEnv = {
  journeyId: string;
  origin: string;
  clipboardAvailable: boolean;
  isSecureContext: boolean;
};

/* One shape, not a discriminated union: this tree is type-checked with `strict: false`
   (`tsconfig.check.json`), where narrowing on an `ok: true | false` discriminant does not hold. */
export type JourneyLinkOutcome = {
  ok: boolean;
  /** The link this attempt was about -- null only when there is no journey, so "the clipboard refused"
      keeps holding a real link and "no journey" never holds a pseudo one. */
  url: string | null;
  failure: JourneyLinkFailure | null;
};

/** Null, never a link with an empty tail: `/v8/` opens the hub, which is not the traveller's journey. */
export function buildJourneyLinkUrl(journeyId: string, origin: string): string | null {
  const id = String(journeyId ?? "").trim();
  if (id === "") return null;
  return new URL(`/v8/${id}`, origin).href;
}

/**
 * Ordered by what the traveller can act on, and deliberately not collapsed into one sentence: the
 * clipboard refusing is this device's permission, the journey missing is the product's state, and
 * saying one for the other is the defect R2 names.
 */
export function journeyLinkFailure(env: JourneyLinkEnv): JourneyLinkFailure | null {
  if (buildJourneyLinkUrl(env.journeyId, env.origin) === null) return "NO_JOURNEY";
  if (!env.isSecureContext) return "INSECURE_CONTEXT";
  if (!env.clipboardAvailable) return "CLIPBOARD_UNAVAILABLE";
  return null;
}

/** `write` is injected so "the browser rejected the write" is a leg that can be measured, not assumed. */
export async function copyJourneyLink(
  env: JourneyLinkEnv,
  write: (text: string) => Promise<void>,
): Promise<JourneyLinkOutcome> {
  const url = buildJourneyLinkUrl(env.journeyId, env.origin);
  if (url === null) return { ok: false, url: null, failure: "NO_JOURNEY" };
  if (!env.isSecureContext) return { ok: false, url, failure: "INSECURE_CONTEXT" };
  if (!env.clipboardAvailable) return { ok: false, url, failure: "CLIPBOARD_UNAVAILABLE" };
  try {
    await write(url);
  } catch {
    return { ok: false, url, failure: "CLIPBOARD_UNAVAILABLE" };
  }
  return { ok: true, url, failure: null };
}
