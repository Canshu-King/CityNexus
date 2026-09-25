export function Dbg2({body}: {body: {detail?: string} | null}) {
  return <code data-testid="dbg-detail">{body?.detail}</code>;
}
