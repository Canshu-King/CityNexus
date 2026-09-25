function serverReasonSentence(body: unknown): string | null {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  return null;
}
export function X() { const out = {failureReason: failureNote(
  serverReasonSentence(body), "fb")};
  return <code>{(out.failureReason || {}).text}</code>; }
