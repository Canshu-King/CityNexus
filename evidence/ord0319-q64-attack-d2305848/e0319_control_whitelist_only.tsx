export function Ctl({r}: {r: {http_status: number; content_type: string; body_bytes: number; response_received: boolean; elapsed_ms: number; request_id: string}}) {
  return (<pre>{`http_status=${r.http_status}
`}{`content-type=${r.content_type}
`}{`bytes=${r.body_bytes}
`}{`received=${r.response_received}
`}{`elapsed=${r.elapsed_ms}
`}{`request_id=${r.request_id}`}</pre>);
}
