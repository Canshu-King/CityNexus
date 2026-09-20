
_measured 2026-09-20T12:41:36.530Z (proxy 4489 -> preview 4490)_


_measured 2026-09-20T12:52:13.430Z (proxy 4489 -> preview 4490)_


_measured 2026-09-20T12:55:01.415Z (proxy 4489 -> preview 4490)_


_measured 2026-09-20T13:00:08.392Z (proxy 4489 -> preview 4490)_


_measured 2026-09-20T13:04:39.576Z (proxy 4489 -> preview 4490)_

| budget | cached first | 4 s delay | case A (network wins) | 10.5 s delay | case B (fell back) |
|---|---|---|---|---|---|
| 8s | 0ms @1789909494151 | 4000ms @1789909498177, 4023ms wall | PASS | 10500ms @1789909508702, 10528ms wall | FAIL |

| budget | cached first | 4 s delay | case A (network wins) | 12.5 s delay | case B (fell back) |
|---|---|---|---|---|---|
| 10s | 0ms @1789909524131 | 4000ms @1789909528171, 4039ms wall | PASS | 12500ms @1789909540708, 12530ms wall | FAIL |

