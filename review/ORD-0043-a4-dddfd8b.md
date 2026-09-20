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

## 4. Option (A) landed -- ruling `5749925104`

Commit `047e748`. The six mechanisms the ruling named, each where the ruling put it:

| mechanism | file | evidence it is real |
|---|---|---|
| `SW_VERSION` | `public/sw.js` | `citynexus-recovery-m3-a4-v1`, answered over a MessageChannel |
| recovery worker | `public/sw.js` | A4's file, with `precacheRecoveryShell()` and the activate-side legacy purge |
| `updateViaCache: "none"` | `src/main.tsx` | production registration, plus `registration.update()` and the one-time `controllerchange` reload |
| narrowed `navigateFallbackDenylist` | `vite.config.ts` | A4's three-entry list; per-route check in section 1 |
| versioned cache names | `vite.config.ts` | `runtimeCacheVersion = "m3-a4-v1"` on both runtime caches |
| `clientsClaim` / `skipWaiting`, worker out of SWR | `vite.config.ts` | both flags set; `["script","style","image","font"]`, no `worker` |

Kept, as the ruling asked: `preview.proxy`, and the document budget set from the measured
tunnel percentiles rather than the branch's candidate value.

**A4's own gate: `2 collected / 2 passed / 0 failed` under `--config playwright.sw.config.ts`**
(0 passed / 2 failed before this commit). Under the default project the same two tests report
**skipped**, on purpose: they assert a lifecycle the dev server never registers, and
`playwright.config.ts` belongs to `8c66aa92`, so the spec declares its own project with a
reason string rather than this lane editing someone else's config.

Answer to the question the verdict asked -- is "the old worker upgrades automatically" truly
green or skipped? -- **truly green in the project that can prove it, skipped by name in the one
that cannot.** It is not counted as a pass under dev.

## 5. Kills for the landing -- `review/ord43-kill-table.txt`

| mutant | node | result |
|---|---|---|
| drop the path test from the HTML guard | `sw-never-answers-script-with-html` | KILLED: "an online .js request ... was passed through as text/html" |
| activate deletes every cache but its own | `sw-activate-keeps-foreign-caches` | KILLED: "deleted caches it does not own: [citynexus-pages-m3-a4-v1, ...]" |
| activate deletes nothing | `sw-activate-keeps-foreign-caches` | KILLED: "the retired cache names A4-1 lists survived activation" |
| code requests network-only, exactly as A4 writes it | `sw-offline-boot-serves-cached-code` | **KILLED: "offline code requests were refused instead of served from cache"** |

The last row is the one to read carefully, because it is the only place this landing is **not**
byte-for-byte A4: `public/sw.js` may serve a cached module when the cached bytes really are
code (never when they are a document). This lane already shipped that network-only shape once
and watched an offline reload fail to start -- `real-world-trip-operations-v9` went red, and
the gate above is what grew out of fixing it. The deviation is therefore recorded, gated, and
reversible in one line: if the arbiter wants byte-fidelity ahead of that gate, say so and it
goes, together with the offline boot it protects.
