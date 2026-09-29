# ORD-0473 r2 — the same defect measured against the line I deliver into

The authoritative tip moved while r1 was being written: `4037cb331ea00b83124316d40329762fa1131689` was
read back before I started, `0dabe64223036391a6c25561a6b606e1533f3704` was read back when I wrote the
delivery block. This branch is recut onto the latter. Nothing in the two files this order touches
moved between those tips:

```
frontend/src/app/V8Experience.tsx  4037cb33 -> 3c03ec82b11931c9d7927423234113188c42c1ae
                                    0dabe642 -> 3c03ec82b11931c9d7927423234113188c42c1ae
frontend/src/styles.css            4037cb33 -> ee5ef1b9adbd1c2cf7adaaa1ae8f64e1e63c3ff4
                                    0dabe642 -> ee5ef1b9adbd1c2cf7adaaa1ae8f64e1e63c3ff4
```

so the recut applies with zero conflicts and the fix itself carries the same two blobs as r1
(`903a673c37949bf4a7937961792bcad377d9f2f5` and `d0e229338842c14f7f0650ebeab1d761a844d249`).
What did move on the line is `frontend/src/i18n/LocaleContext.tsx` (+6 keys, one lane's ORD-0436 work),
which is why the two label anchors in the block are re-measured here rather than carried over:

```
frontend/src/i18n/LocaleContext.tsx:174   "shell.openNav":  "Open navigation"
frontend/src/i18n/LocaleContext.tsx:175   "shell.closeNav": "Close navigation"
frontend/src/i18n/LocaleContext.tsx:1209  "shell.openNav":  "打开导航"
frontend/src/i18n/LocaleContext.tsx:1210  "shell.closeNav": "关闭导航"
```

Both arms were rebuilt from `git archive` of the delivered tip and of its recut — the two build logs ship
here as `readings/build_before2_info.json` and `readings/build_after2_info.json`, each carrying the
`export_blob_equality` proof that the export holds the tip's bytes — and `npm run typecheck`
(`tsc -p tsconfig.check.json --noEmit`) exits 0 on the recut bytes: `readings/typecheck_after2_r1.txt`.

## Before / after at 390 px x 844 px on the delivered line

Full dump: `readings/compare_arms2_r1.txt`.

| reading | before `0dabe642` @ `:4834` | after `a808fc34` @ `:4835` |
|---|---|---|
| toggle box | 46 px x 27 px at (17, 19) | 46 px x 44 px at (17, 11) |
| toggle centre hit while the drawer is open | `v8-kicker`, `self=false` | `v8-mobile-menu`, `self=true` |
| second press closes the drawer | `false` — `TimeoutError` at 6,000 ms | `true` |
| drawer rows rendered | 16 | 16 |
| rows whose own centre hit-tests to themselves | 16 / 16 | 16 / 16 |
| rows that change route or on-screen heading | 15 / 16 | 15 / 16 |
| row box height | 41 px | 44 px |
| drawer `scrollTop` to reach the last row | 0 -> 268 px of 1,112 px | 0 -> 371 px of 1,215 px |
| last row after that scroll | y 779..820 px, centre (150, 800) px, hit `SELF` | y 776..820 px, centre (150, 798) px, hit `SELF` |
| `.v8-mobile-nav` band | top 768 px, height 76 px, `z-index` 10 | same |
| SCREAMING_SNAKE tokens on the open-drawer screen | 0 | 0 |
| toggle glyph / rendered word / accessible name | `≡` / 菜单 / 打开导航 in every state (press 2 never lands) | closed `≡` / 菜单 / 打开导航 -> open `×` / 菜单 / 关闭导航 -> closed again `≡` |
| closed by the drawer's 关闭 / by Escape / by the backdrop | `true` / `true` / `false` | `true` / `true` / `false` |
| `pageerror` | 0 | 0 |

The one row that does not change the screen is `今天`, pressed while already on `/v8/hub`.
`回收站` and `成员与权限` change route (`/v8/trash`, `/v8/access`) and expose no `h1`/`h2` on **both**
generations — the reading for those two cells is empty on the line, before and after, so it is not this
order's break.

## Desktop arm on the delivered line

`readings/desktop_before2_1280.json` and `readings/desktop_after2_1280.json` are the same reading on both
generations: the toggle is `display: none` with box 0 px x 0 px, no drawer exists, the sidebar's 14 rows
behave alike (of the 4 pressed, 3 change route or heading; the fourth is `今天`, already current), 0
`pageerror`.

## Facade identity for these two arms

`readings/facade_identity_arms_r1.json` is r1's pair; `readings/facade_identity_arms2_r1.json` is this
pair — before arm `:4834` serving `/assets/index-DmHYey4y.js`, after arm `:4835` serving
`/assets/index-BxouWOlo.js`, each entry name taken from that arm's own `index.html`, and for both the
served bytes' sha1 equals the disk file's sha1 (index 1,200 bytes; entry asset 1,488,860 bytes on the
before arm and 1,488,884 bytes on the after arm).

## Why r1's files stay

The r1 set (`readings/walk_before_390.json`, `..._after_390.json`, cells/glyphs/desktop for the same pair,
`compare_390_r1.txt`) was measured against `4037cb331ea00b83124316d40329762fa1131689` and
`bc1c643ff279ec4800b873c40d71a71a5e03bfb2`, both still published on the r1 ref
`refs/heads/review/df90a7d5-ord0473-drawer-r1`. Published paths are not rewritten here; this file and the
`*2*` readings are the new names for the new base.

## What this order deliberately did not change

The backdrop is still not a usable exit, on both arms: at a 390 px viewport the drawer is
`min(300px, 84vw)` = 300 px wide, so the backdrop's own centre (195, 422) px falls inside the panel and a
press there times out. Narrowing the panel or moving its origin is a geometry call, not a toggle fix.
The toggle now closes, so the traveller is no longer dependent on that strip.

No acceptance-suite spec was added: `frontend/playwright.config.ts:70` starts its own backend with
`cwd: "../backend"` inside the shared working tree and depends on the `real-seed` project, which this
order's stack rules forbid me to reach into. The four instruments in this directory take a facade base URL
as their first argument, so the whole set replays against any generation.
