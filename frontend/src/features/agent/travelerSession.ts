const SESSION_KEY = "citynexus.traveler.bearer";

/**
 * The browser stores only the opaque signed bearer. Member identity is always
 * resolved by the server from that token; no member_id or role in web storage
 * is treated as authority.
 */
export function readTravelerBearer(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

export function storeTravelerBearer(token: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(SESSION_KEY, token);
}

export function clearTravelerBearer(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(SESSION_KEY);
}

export function travelerAuthHeaders(): Record<string, string> {
  const token = readTravelerBearer();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
