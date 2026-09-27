# Transport and tunnel readings (lane N2)

Taken on 2026-09-28 from this lane. `curl` with `HTTP_PROXY`/`HTTPS_PROXY` removed and
`NO_PROXY='*'`, so these are direct connections, not proxy-routed.

## Tunnel

| probe | path | http_code \| bytes \| content_type | stderr |
|---|---|---|---|
| old tunnel + creds | `/api/v1/health` | 000|0| | curl: (7) Failed to connect to jets-saints-tomatoes-eric.trycloudflare |
| old tunnel + creds | `/` | 000|0| | curl: (7) Failed to connect to jets-saints-tomatoes-eric.trycloudflare |
| old tunnel anonymous | `/api/v1/health` | 000|0| | curl: (7) Failed to connect to jets-saints-tomatoes-eric.trycloudflare |
| new tunnel + creds | `/api/v1/health` | 000|0| | curl: (7) Failed to connect to calendar-engineering-surveys-london.try |
| new tunnel + creds | `/` | 000|0| | curl: (7) Failed to connect to calendar-engineering-surveys-london.try |
| new tunnel anonymous | `/api/v1/health` | 000|0| | curl: (7) Failed to connect to calendar-engineering-surveys-london.try |

## Local proxy ports

`netstat -ano` gave 1125 lines.
- rows containing `127.0.0.1:7892`: 0 (the address the shell HTTP(S)_PROXY names)
- rows containing `127.0.0.1:7897` with state LISTENING:
  - none at this moment (the port that answered on 2026-09-26 is not listening now)

Direct HTTPS to github.com was attempted on the default TLS port; the two transport
failures recorded in my earlier hand-off blocks are reproduced only as: connection reset when no
proxy is set, and "failed to connect" when the proxy address is dead. Both are the same cause:
this box has no direct github egress and the proxy variables point at a port nobody listens on.
