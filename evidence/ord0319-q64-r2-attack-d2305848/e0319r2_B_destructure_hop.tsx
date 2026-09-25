function serverReasonSentence(body: unknown): string | null {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  return null;
}
export function X() { const sentence = serverReasonSentence(body);
  return <code>{sentence}</code>; }
