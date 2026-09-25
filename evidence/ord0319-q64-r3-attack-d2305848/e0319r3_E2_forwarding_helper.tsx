function serverReasonSentence(body: unknown): string | null {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  return null;
}
function wrap(b: unknown): string | null { return serverReasonSentence(b); }
export function X() { const s = wrap(body);
  return <code>{s}</code>; }
