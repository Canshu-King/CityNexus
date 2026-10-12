# CityNexus Revolution Lab R6 — node official-web boundary

## Execution binding

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Product execution source: `f09379fc460752b0980c1aafc08c097c6cf752a6`
- Final experimental/test commit: `b4cd8ad46e79189b32d1b1382d35173d5a59925a`
- Product calls were made with a clean worktree before and after the test-only
  commit; the test commit does not alter runtime behavior.

## Exact source under test

- Provider identity: `overpass:node/5042033121`
- Place: `real-place-bcd9c9f324751168d422a06b`
- Nominatim extratag website: `http://jump.szjlxx.cn/?park=wsy`
- Resolved page: `https://wap.lotsmall.cn/vue/detail/ticket?id=8187&productCode=park2021051111555676069&m_id=1939`

## Live source probe

The extratag URL returned HTTP 200 HTML, but contained no structured or visible
opening/cost facts. Navigating it with a real browser followed the redirect to:

```text
https://wap.lotsmall.cn/vue/login?m_id=1939&loginWay=1
```

The rendered page was titled `用户登录` and showed phone/email and password
fields. The captured network trace contains the redirect/login requests; no
authenticated page or ticket facts were used.

The static page's incidental numeric strings are not evidence. They are not
bound facts and were not promoted.

## Product result

The prior exact `/facts/acquire` receipt and the final readback remain:

```text
Nominatim: ACQUIRED, matched_provider_entity=true
official_web: NO_STRUCTURED_FACTS, acquired=0
search_source: UNCONFIGURED, attempted=false
opening_hours.status = UNKNOWN
cost_evidence.status = UNKNOWN
known_opening_count = 0
known_cost_count = 0
```

The final product page on `/v8/hub` rendered:

```text
pending_rows = 18
unknown_opening_rows = 18
unknown_cost_rows = 18
identity = overpass · overpass:node/5042033121
```

The active plan version and Twin stayed unchanged. No plan, booking, payment,
or selection write occurred.

## Regression gate

Added `test_official_html_parser_keeps_login_shell_as_no_structured_facts` to
the Revolution R77 recovery tests. It asserts that a HTTP 200 login shell is
still `NO_STRUCTURED_FACTS` with UNKNOWN opening and cost.

Focused result:

```text
53 passed, 1 warning
```

The warning is the existing Starlette/httpx deprecation warning.

## Exact current blocker

The node has a confirmed provider identity but no publicly accessible,
structured, source-bound opening or cost evidence. The official ticket page is
login-gated, and the search source is not configured. Therefore the honest
current state is:

```text
identity = known
opening = UNKNOWN
cost = UNKNOWN
selectability impact = unresolved facts remain unresolved
```

The nearby `overpass:way/44679452` official facts remain isolated to that way;
same-name or nearby geometry is not an admissible substitute.

## Agent/runtime disclosure

No new DeepSeek or Hermes execution was used for this deterministic source
boundary. Runtime remains DeepSeek configured-but-unverified and Hermes
unavailable. Machine receipts outrank agent narration.

## Next bounded experiment

Configure a real search-source adapter in the isolated lab, or obtain an
operator-approved public source for this exact node. Query only
`overpass:node/5042033121`; any result for the way or for a same-name first
result must remain rejected. If no bound source returns structured facts,
leave the node UNKNOWN and keep it out of authoritative selectable coverage.
