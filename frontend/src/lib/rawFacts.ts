/**
 * What this device measured on a response, before it tried to understand any of it.
 *
 * Q64=1 (arbiter): an upstream sentence may not reach the DOM, so the technical facts a screen may
 * still show are *this device's own readings* -- the status it saw, the media type the answer
 * carried, how many octets it was.  Field names are labels; the values are the answer's own,
 * unedited.  This is the shape `PlanWithAiSheet.tsx` was accepted with under ORD-0302 b5, lifted out
 * of that one sheet so the three ORD-0325 fixes do not each re-implement it.
 */

export type RawFacts = {
  http_status: number | null;
  content_type: string | null;
  bytes: number | null;
};

export function measureRawFacts(
  response: { status: number; headers: { get(name: string): string | null } },
  rawText: string,
): RawFacts {
  return {
    http_status: response.status,
    content_type: response.headers.get("content-type"),
    bytes: new TextEncoder().encode(rawText).length,
  };
}

/**
 * Read an answered response exactly once and keep both halves: the text, so a machine token can be
 * read out of it, and the measurement, so the screen can show what it never received.
 */
export async function readResponseFacts(
  response: {
    status: number;
    headers: { get(name: string): string | null };
    text(): Promise<string>;
  },
): Promise<{ text: string; facts: RawFacts }> {
  const text = await response.text();
  return { text, facts: measureRawFacts(response, text) };
}

/**
 * `response.json().catch(() => null)` was the only way these screens looked at a refusal, and that
 * one line collapsed zero bytes, an HTML document and a plain sentence into the same `null`
 * (ORD-0263).  Parsing by hand from the same text the byte count measured keeps the two apart.
 */
export function parseJsonOrNull(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/** The three whitelisted lines, in the order the screen prints them. */
export function rawFactLines(facts: RawFacts): string[] {
  return [
    `http_status=${facts.http_status ?? ""}`,
    `content-type=${facts.content_type ?? ""}`,
    `bytes=${facts.bytes ?? ""}`,
  ];
}

/**
 * The condition a refusal names for itself, matched against a list this screen already knows.
 *
 * Some raise sites put the name in the envelope (`error.code`); some prefix it inside the human
 * sentence (`detail: "STAY_ITINERARY_CONFLICT: ..."`).  Both cases are a token, so the token is what
 * is compared and the sentence is what is dropped -- scanning the answer's text rather than one
 * assumed path is what keeps a re-shaped envelope from silently turning every conflict back into a
 * generic refusal.
 */
export function namedCodeIn(text: string, known: readonly string[]): string | null {
  for (const token of text.match(/\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b/g) ?? []) {
    if (known.includes(token)) return token;
  }
  return null;
}
