const SESSION_KEY = "citynexus.traveler.bearer";
const TRAVELER_ID_KEY = "citynexus.traveler.session-id";
const CHANGE_EVENT = "citynexus.traveler.bearer.changed";

export type TravelerSessionIdentity = {
  bearer: string;
  travelerId: string;
};

/**
 * The bearer is the credential. A paired session-local traveler id is only a
 * navigation hint and never grants access or replaces server authorization.
 */
export function readTravelerBearer(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

/**
 * Read the locally paired identity only as a session convenience. The server
 * still verifies the opaque bearer and decides every private Journey read.
 */
export function readTravelerIdentity(): TravelerSessionIdentity | null {
  if (typeof window === "undefined") return null;
  try {
    const bearer = window.sessionStorage.getItem(SESSION_KEY);
    const travelerId = window.sessionStorage.getItem(TRAVELER_ID_KEY);
    return bearer && travelerId ? { bearer, travelerId } : null;
  } catch {
    return null;
  }
}

export function storeTravelerBearer(token: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(SESSION_KEY, token);
  window.sessionStorage.removeItem(TRAVELER_ID_KEY);
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
}

export function storeTravelerIdentity(token: string, travelerId: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(SESSION_KEY, token);
  window.sessionStorage.setItem(TRAVELER_ID_KEY, travelerId);
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
}

export function clearTravelerBearer(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(SESSION_KEY);
  window.sessionStorage.removeItem(TRAVELER_ID_KEY);
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
}

/**
 * Same-tab sessionStorage writes do not emit the browser storage event. Poll
 * the opaque bearer as a small privacy boundary and also listen for the
 * explicit events emitted by the session helpers.
 */
export function subscribeTravelerBearer(listener: (bearer: string | null) => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  let previous = readTravelerBearer();
  const check = () => {
    const next = readTravelerBearer();
    if (next === previous) return;
    previous = next;
    listener(next);
  };
  const onSignal = () => check();
  window.addEventListener(CHANGE_EVENT, onSignal);
  window.addEventListener("storage", onSignal);
  const interval = window.setInterval(check, 100);
  return () => {
    window.removeEventListener(CHANGE_EVENT, onSignal);
    window.removeEventListener("storage", onSignal);
    window.clearInterval(interval);
  };
}

export function travelerAuthHeaders(): Record<string, string> {
  const token = readTravelerBearer();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
