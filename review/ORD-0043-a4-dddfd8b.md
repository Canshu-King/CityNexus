# ORD-0043 — A4 at `dddfd8b`, run against this lane's tree

Harness: `review/doc-fallback-delay.mjs` (patches the budget, builds production, serves it
behind a document-delaying stamping proxy, measures, restores `vite.config.ts` byte-exact —
`restored vite.config.ts 42362e559017 -> 42362e559017 OK`).
Run log: `review/doc-timeout-run.log`. Latency samples: `review/tunnel-latency-n20.txt`.

## 1. A4's own gate, at the new tip

Landed the three files that do not collide with anything (new paths):
`frontend/playwright.sw.config.ts`, `frontend/e2e/qoder-sw-lifecycle.spec.ts`,
`frontend/docs/SW_LIFECYCLE_ACCEPTANCE.md` (its real prefix is `.../frontend/docs/`, not
`docs/` — the first fetch reported 404 for that reason).

```
--list  : 2 tests in 1 file
run     : 0 passed / 2 failed
  1. "old recovery worker upgrades to the generated production worker…" (20.4s)
     TimeoutError at qoder-sw-lifecycle.spec.ts:83 — waiting for the page's controller to
     become /v10-sw.js. This lane's production registration (main.tsx:1687) registers
     /v10-sw.js without `updateViaCache: "none"`, without the one-time controllerchange
     reload, and without purging legacy caches, so an already-installed /sw.js is never
     displaced.
  2. "recovery worker is version-queryable and never supplies HTML…" (5.2s)
     page.evaluate: "service worker version reply timed out" — this lane's public/sw.js has
     no CITYNEXUS_SW_GET_VERSION handler.
```

Both reds are the two A4 semantics that this lane never shipped, so the gate is measuring
the gap correctly rather than failing on its own wiring.

The narrowed denylist at `dddfd8b` is checked and correct: `/v8`, `/v8/hub`, `/v8/live`,
`/v8/trips/1.5`, `/v8/map?z=3` all keep the navigation fallback; `/api/…`, `/assets/…`,
`/sw.js`, `/v10-sw.js`, `/manifest.webmanifest`, `/favicon.svg`, `/*.css` are denied. The
`/\.[a-zA-Z0-9]+$/` over-broad pattern from the void tip is gone.

## 2. The document budget, measured in two separate columns

Document navigation only, against the live public entry the user is on (20 unauthenticated
`GET /v8/live`, so DNS + TLS + tunnel + auth-proxy are all traversed):

```
min 0.84s   p50 1.59s   p90 3.88s   p95 10.47s   max 20.93s
4 of 20 above 3s · 2 of 20 above 8s
loopback floor for the same document: p50 0.9ms / p95 21ms  → the server is never the tail
```

API / provider operation latency is a different column and is not admitted into this number:
the backend lane measured one stay search at 120.86s on the provider chain. A4's doc
justifies 8s partly from "a valid user operation at roughly 3.6 seconds", which is that other
column. By the arbiter's own rule — 10s only if measured document P95 ≥ 8s — the measurement
answers: **P95 = 10.47s, so 8s is below a real tenth of navigations and 10s is the value the
data supports.**

## 3. Behaviour of the budget itself — one case passes, one does not reproduce

| budget | case A: 4 s-delayed document | case B: (budget + 2.5 s)-delayed document |
|---|---|---|
| 8s  | PASS — fresh network document served (`delay=4000` stamp) | **not reproduced** — browser received the late network document (`delay=10500`) |
| 10s | PASS — fresh network document served (`delay=4000` stamp) | **not reproduced** — browser received the late network document (`delay=12500`) |

The stamp records the delay that was in force when the proxy produced that exact document, so
"which answer did the browser get" is read off the DOM, not inferred.

Case A is the one that mattered for the 3s-era stale-shell bug and it holds at both values.

Case B does not fire at either budget, and the proxy log shows one network document request
per reload in each case, so the navigation went to the network and waited for it. Two
candidate mechanisms remain open and I am not going to pick one without evidence: either
this build's `NetworkFirst` timeout never arms for a navigation (the emitted worker does
carry `networkTimeoutSeconds:10` and the `/v8/` document route, so the option is not lost at
build time), or a navigation-preload path returns the late network response regardless.

**What this costs me, stated plainly:** part of ORD-0036 (c) claimed the document timeout was
now backed by a measured value, and the value is indeed measured — but its protective effect
on a real navigation is **unproven** by this harness. I am not treating "the number is in the
generated worker" as "the behaviour works", and the follow-up belongs to this lane:
make case B reproducible (or prove it cannot happen) before anyone cites 10s as a guard.
