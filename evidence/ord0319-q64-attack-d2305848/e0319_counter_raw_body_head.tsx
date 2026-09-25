export function Dbg({r}: {r: {body_head: string}}) {
  return <pre data-testid="dbg-body">{`body=${r.body_head}`}</pre>;
}
