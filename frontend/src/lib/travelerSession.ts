/* Issue #31 A / ORD-0687 -- the signed traveller this tab speaks for.
 *
 * Why this file exists: Issue #27 could only stop caching, because nothing on this line could
 * say *who* is looking.  The server can now answer that (`GET /api/v1/travelers/session`), and
 * the create door hands back a short-lived signed token for the traveller it just made.  This
 * module is the only place that token is allowed to live on the client.
 *
 * The rules, and the reason each one is here:
 *
 *  - memory + `sessionStorage` only.  Never `localStorage`, never IndexedDB, never a URL, never
 *    a log line: a bearer is more sensitive than the chat text whose leak started all this, and
 *    `localStorage` survives a person handing the phone to the next one.  `sessionStorage` dies
 *    with the tab, which is the boundary we can actually hold.
 *  - the token is never trusted as an identity.  `travelerId` is only usable after the server
 *    repeats it back; a stored pair that the door refuses is dropped on the spot, together with
 *    every Agent record this tab was holding -- those belong to the person who just left.
 *  - there is no "give me a token for this id" path here, because there is no such door on the
 *    server.  If the session is gone, the honest state is `EXPIRED`/`NONE`, not a new anonymous
 *    traveller wearing the old trip.
 */

const SESSION_KEY = "citynexus.v8.traveler.session";

export type SignedSession = {
  travelerId: string;
  token: string;
  /** Seconds since the epoch, as the server signed it; null when it did not say. */
  expiresAt: number | null;
};

export type SessionVerdict =
  | "SIGNED"
  | "NOT_CONFIGURED"
  | "MISCONFIGURED"
  | "EXPIRED"
  | "UNSIGNED"
  | "REFUSED";

let current: SignedSession | null = null;
let lastVerdict: SessionVerdict = "UNSIGNED";

function store(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    // Private mode / disabled storage: the session stays in memory for this tab, which is
    // strictly safer than failing the whole flow because a browser refuses to persist.
    return null;
  }
}

/** Read whatever this tab held before a reload. Never a promise, never a network call. */
export function restoreSignedSession(): SignedSession | null {
  if (current) return current;
  const bag = store();
  if (!bag) return null;
  try {
    const raw = bag.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<SignedSession>;
    if (typeof parsed?.travelerId !== "string" || typeof parsed?.token !== "string") return null;
    const expiresAt = typeof parsed.expiresAt === "number" ? parsed.expiresAt : null;
    if (expiresAt !== null && expiresAt * 1000 <= Date.now()) {
      bag.removeItem(SESSION_KEY);
      lastVerdict = "EXPIRED";
      return null;
    }
    current = { travelerId: parsed.travelerId, token: parsed.token, expiresAt };
    return current;
  } catch {
    bag?.removeItem(SESSION_KEY);
    return null;
  }
}

/**
 * Take the token the create door handed back.
 *
 * `session_state` is what the server says about its own verifier: `SIGNED` means a token is
 * here, `NOT_CONFIGURED`/`MISCONFIGURED` mean "identity is off / broken on this deployment", and
 * the client must keep working without pretending to know who the person is.
 */
export function adoptSignedSession(answer: unknown): SignedSession | null {
  if (!answer || typeof answer !== "object") return null;
  const body = answer as Record<string, unknown>;
  const travelerId = typeof body.id === "string" ? body.id : null;
  const token = typeof body.access_token === "string" ? body.access_token : null;
  const state = typeof body.session_state === "string" ? body.session_state : "NOT_CONFIGURED";
  if (state === "NOT_CONFIGURED") lastVerdict = "NOT_CONFIGURED";
  else if (state === "MISCONFIGURED") lastVerdict = "MISCONFIGURED";
  if (!travelerId || !token) {
    // An id without a credential is not an identity: keep it out of the session so no later
    // code mistakes "we know a uuid" for "the server vouched for this person".
    return current;
  }
  current = { travelerId, token, expiresAt: null };
  lastVerdict = "SIGNED";
  store()?.setItem(SESSION_KEY, JSON.stringify(current));
  return current;
}

export function signedTravelerId(): string | null {
  return restoreSignedSession()?.travelerId ?? null;
}

export function sessionVerdict(): SessionVerdict {
  return lastVerdict;
}

/** Headers for a request. Empty when this tab is anonymous -- callers must not send a stub. */
export function signedBearerHeaders(): Record<string, string> {
  const session = restoreSignedSession();
  return session ? { Authorization: `Bearer ${session.token}` } : {};
}

/**
 * Drop the credential and everything that belonged to the person who just left.
 *
 * The Agent caches are cleared here on purpose: the moment identity changes, a transcript or a
 * tool timeline still on screen is somebody else's.  `reason` is a machine word for the log
 * label, never the token and never the traveller's text.
 */
export function clearSignedSession(reason: "signed-out" | "refused" | "expired" | "switched" = "signed-out"): void {
  current = null;
  lastVerdict = reason === "expired" ? "EXPIRED" : "UNSIGNED";
  try {
    store()?.removeItem(SESSION_KEY);
  } catch {
    /* nothing to forget: memory is already cleared, which is the part that matters */
  }
  void import("./agentSessionCache").then(({ clearAgentSessionCaches }) => clearAgentSessionCaches()).catch(() => undefined);
}

/** The shell's saved pointer -- "which trip to open on this device" (`app/V8Experience.tsx`). */
const JOURNEY_POINTER_KEY = "citynexus.v8.journey_id";

/** Reason codes that say *this credential* is the problem (from `backend/app/traveler_principal.py`). */
const CREDENTIAL_REFUSALS = new Set([
  "TRAVELER_CREDENTIALS_MISSING",
  "TRAVELER_CREDENTIALS_INVALID",
  "TRAVELER_CREDENTIALS_EXPIRED",
  "TRAVELER_PRINCIPAL_NOT_FOUND",
]);

/** Reason codes that say the credential is fine but the *pointer* is somebody else's trip. */
const SCOPE_REFUSALS = new Set(["JOURNEY_POINTER_NOT_OURS", "TRAVELER_NOT_PRINCIPAL"]);

export function refusalReasonCode(body: unknown): string | null {
  const error = (body as { error?: { reason_code?: unknown; code?: unknown } } | null)?.error;
  const reason = error?.reason_code;
  return typeof reason === "string" ? reason : null;
}

/**
 * Act on a rejected request the way the *reason* says, not the way the status number says.
 *
 * Two very different refusals arrive as 401/403, and treating them alike would be a new defect:
 *
 *  - the credential itself is bad (expired, forged, or names a traveller who is gone) -- the
 *    person is no longer verified, so the token and every Agent record it was holding go;
 *  - the credential is good and the device's saved journey pointer is not theirs -- the person
 *    stays signed in, but the pointer and that trip's Agent records are somebody else's and
 *    come off the device. Logging a traveller out because the phone still held an old uuid
 *    would punish the one person this rule is trying to protect.
 *
 * Anything else (a 404, a 422, a 503 about the server's own configuration) leaves the session
 * alone: those are not statements about who is holding the phone.
 */
export function observeRejection(status: number, reasonCode: string | null): void {
  if (reasonCode && SCOPE_REFUSALS.has(reasonCode)) {
    try {
      window.localStorage.removeItem(JOURNEY_POINTER_KEY);
    } catch {
      /* a pointer we could not remove is still refused by the server, which is the real gate */
    }
    void import("./agentSessionCache")
      .then(({ clearAgentSessionCaches }) => clearAgentSessionCaches())
      .catch(() => undefined);
    return;
  }
  if (status === 401 || (reasonCode && CREDENTIAL_REFUSALS.has(reasonCode))) {
    clearSignedSession(status === 401 ? "expired" : "refused");
  }
}

/**
 * Ask the server who this tab is, and believe the server.
 *
 * `ask` is injected so this module stays free of the app's fetch wrappers (and so a test can
 * drive every branch without a network).  A refusal that names a credential problem clears the
 * session; a transport failure keeps it, because "the wifi blinked" must not log a person out.
 */
export async function verifySignedSession(
  ask: (headers: Record<string, string>) => Promise<{ status: number; body: unknown }>,
): Promise<SignedSession | null> {
  const session = restoreSignedSession();
  if (!session) return null;
  const answer = await ask(signedBearerHeaders());
  if (answer.status === 200) {
    const body = answer.body as Record<string, unknown> | null;
    const confirmed = typeof body?.traveler_id === "string" ? body.traveler_id : null;
    const expires = typeof body?.expires_at === "number" ? body.expires_at : session.expiresAt;
    if (confirmed && confirmed !== session.travelerId) {
      // The door answered for someone else: that is a leak waiting to happen, not a mismatch
      // to paper over.  Forget everything this tab holds.
      clearSignedSession("switched");
      lastVerdict = "REFUSED";
      return null;
    }
    current = { ...session, expiresAt: expires ?? null };
    lastVerdict = "SIGNED";
    store()?.setItem(SESSION_KEY, JSON.stringify(current));
    return current;
  }
  if (answer.status === 401 || answer.status === 403) {
    clearSignedSession(answer.status === 401 ? "expired" : "refused");
    return null;
  }
  return session;
}
