# ORD-0473 — the phone's 「菜单」 toggle: locate by sentinels, then fix

Lane `df90a7d5`. Authoritative tip this work is against: `4037cb331ea00b83124316d40329762fa1131689`
(`refs/heads/mirror/integration-frontend-apple-pass1`, read back with
`env -u HTTP_PROXY -u HTTPS_PROXY git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`).
Product bytes delivered: `bc1c643ff279ec4800b873c40d71a71a5e03bfb2` on
`refs/heads/review/df90a7d5-ord0473-drawer-r1`; this evidence commit is the branch tip after it and
carries zero product bytes (`frontend/src` blobs are identical between the two — see
`readings/blob_parity_r1.txt`).

## 1. Locating arm — six sentinels, one build (`readings/sentinel_probe_390_r2.json`)

One bundle built from `4af2780ac05aea35a6accc2df52db9a3d66d111f` (tip + probe only) carrying six
*different* tokens, one per suspect link, at 390 px x 844 px:

| token | link it proves | on screen? |
|---|---|---|
| `C1GEN-A1` | the running bundle is this build | yes |
| `B1CLK` / `clicks=1` | the button's `onClick` ran | yes |
| `C2TRUE` / `navOpen` | the state flipped and committed | yes |
| `D3DWR` | the `{navOpen && …}` drawer branch mounted | yes |
| `D4ROWS=16` | the rows rendered, and how many | yes |
| `D5BDP` | the backdrop mounted | yes |

So the *open* half of the chain was never broken at this generation. What broke is the way back:
after the drawer opens, `document.elementFromPoint` at the toggle's own centre
(`[40, 33]`) returns the drawer's `.v8-kicker`, not the button (`self=false`), and a second press
times out. The handler only ever passed `true`, so it had no close path to begin with.

## 2. Before / after at 390 px x 844 px (`readings/compare_390_r1.txt`)

| reading | before `4037cb3…` | after `bc1c643f…` |
|---|---|---|
| toggle box | 46 px x 27 px at (17, 19) | 46 px x 44 px at (17, 11) |
| toggle centre hit while open | `.v8-kicker`, `self=false` | `.v8-mobile-menu`, `self=true` |
| 2nd press closes the drawer | `false` (`TimeoutError` after 6,000 ms) | `true` |
| drawer rows rendered | 16 | 16 (same labels, nothing folded away) |
| row box height | 41 px | 44 px |
| rows whose own centre hit-tests to themselves | 16 / 16 | 16 / 16 |
| rows that change route or screen text on press | 15 / 16 | 15 / 16 |
| closed by the drawer's 关闭 | `true` | `true` |
| closed by Escape | `true` | `true` |
| closed by the backdrop | `false` | `false` (unchanged — see §4) |
| `pageerror` count | 0 | 0 |

The single non-changing row is `今天` while already on `/v8/hub` — the same screen, so nothing moves.

## 3. Screen cells

1. drawer appears: 16 of 16 declared rows render words (`今天 … 我的`), `aria-expanded=true`;
2. the count moves with the interaction: rows on screen 16 → 0 on the second press (after arm),
   while the before arm stays at 16 through the same press;
3. versus the fixed bottom band: `.v8-mobile-nav` top edge 768 px, height 76 px, `z-index` 10 while
   `#v8-nav-drawer` is `z-index` 46 — the last row after scrolling the drawer sits at y 776..820 px,
   inside that band's range, and its centre point (150, 798) still hit-tests to itself;
4. machine tokens inside the drawer screen: 0 SCREAMING_SNAKE matches in the rendered body text.

Toggle glyph, read as computed `::after` content and rendered words
(`readings/glyphs_summary_r1.txt`): closed `≡` / 菜单 / `打开导航` → open `×` / 菜单 / `关闭导航` →
closed again `≡`. Both directions announce themselves.

## 4. Desktop arm and what this order did not touch

At 1280 px x 720 px (`readings/desktop_before_1280.json`, `readings/desktop_after_1280.json`) the
toggle is `display: none` with box 0 px x 0 px and the drawer is absent on both generations, and the
sidebar's 14 rows behave identically before and after (3 of 4 change route or heading; the fourth is
`今天`, already current).

Left alone on purpose, and named rather than hidden:

* the backdrop is not a usable exit — at a 390 px viewport the drawer is `min(300px, 84vw)` wide, so
  the backdrop's own centre (195, 422) falls *inside* the panel; `elementFromPoint` returns the
  drawer and a press on it times out on both generations. Fixing it means narrowing the panel or
  moving its origin, which is a geometry call for the commander.
* `回收站` and `成员与权限` change route (`/v8/trash`, `/v8/access`) but expose no `h1`/`h2`, so the
  heading reading for those two cells is empty on both generations — a copy question on those
  screens, not a navigation break.
* no acceptance-suite spec was added: `playwright.config.ts` starts its own backend with
  `cwd: "../backend"` in the shared working tree and depends on the `real-seed` project, which this
  order's stack rules forbid me to reach into. The four instruments in this directory are the
  re-runnable proof instead; each takes a facade base URL as its argument.

## 5. Stack this was measured on

* backend `:8745` — `readings/stack_backend.json`: spawned pid 38744, the listening pid is its
  child 38756 (`uv` venv stub re-execs `cpython-3.12.14`), command line names this port and the
  module path, `GET /api/v1/journeys` answered `http 200` with 477 bytes, database
  `D:/moodle/_qoder_n4_ord0473_20260930/n4_ord0473.db` — my own 7,213,056-byte backup taken from the
  shared preview DB opened `mode=ro`. The shared file was never written and `demo/reset` was never
  called.
* before arm facade `:4832` serving `/assets/index-DZLLFMy5.js`, after arm facade `:4833` serving
  `/assets/index-1Pu11QLU.js` — entry names taken from each arm's own `index.html`, and for both
  arms the served bytes' sha1 equals the disk file's sha1 (`readings/facade_identity_arms_r1.json`).
* both bundles built by `cmdr_build_bundle_r1.py --sha <40 hex>` from `git archive`, so the tree
  other lanes have dirty never enters the build. `npm run typecheck`
  (`tsc -p tsconfig.check.json --noEmit`) exits 0 on the delivered bytes —
  `readings/typecheck_after_r1.txt`.
