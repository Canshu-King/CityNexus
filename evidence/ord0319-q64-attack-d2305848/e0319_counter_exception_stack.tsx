export function Dbg3({err}: {err: Error}) {
  return <div data-testid="dbg-stack">{`${err.name}: ${err.message}
${err.stack}`}</div>;
}
