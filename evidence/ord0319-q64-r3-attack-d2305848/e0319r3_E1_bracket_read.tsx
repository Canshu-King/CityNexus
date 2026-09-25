function serverReasonSentence(body: unknown): string | null {
  const d = body["detail"];
  if (typeof d === "string" && d) return d;
  return null;
}
export function X() { const r = {failureReason: note(serverReasonSentence(body))};
  return <code>{r.failureReason.text}</code>; }
