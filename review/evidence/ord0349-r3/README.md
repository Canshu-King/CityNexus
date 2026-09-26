# ORD-0349-r3 readings (lane N1)

Re-parent of ORD-0349 onto `refs/heads/mirror/integration-frontend-apple-pass1` at
`824fca398d27db4c0078407b42e544c84048d3dd`, plus the re-derivation of the pixel arm that the
commander found red.

## The red, reproduced before it was touched

`reading-before-fix-red.json`: exit_code 1, 5 passed / 1 failed, failing node
`e2e/qoder-ord0349-two-legs-two-sentences.spec.ts` "the two legs render as two pictures", on my
stack, backend up, my own run id and `_*.db`.  `log-before-fix-red.txt` carries the Playwright call
log: `locator.screenshot` -> `attempting scroll into view action` -> `element is not stable`, retried
until the 60 s test timeout.  Same shape as the commander's reading.

## What was actually moving

The instrument itself.  `probe-document-growth.spec.txt` is the throwaway probe and
`probe-document-growth.txt` its verbatim console lines: on a backend-up page, 12 consecutive
animation frames, document height / node count / the alert's document y --

| condition | document height per frame | nodes | alert y |
| --- | --- | --- | --- |
| no override | 1832 1831 1830 1830 1830 1830 1830 1830 1830 1830 1830 1830 | 362 throughout | 1940.83 -> 1939.77, settles |
| with the `position: static` override the r2 spec injected | 1926 1926 2139 2451 3075 3387 3699 4011 4635 4947 5259 5883 | 347 -> 363, then 363 throughout | 1985.03 -> 5940.06, never settles |

No nodes are appended in the second row -- the count holds at 363 while the height keeps growing, so
it is the layout expanding, not content arriving.  Forcing `position: static` on everything dissolves
the containment ORD-0338 ruling 甲 relies on (CTA as a grid row, `.cn-onboarding__scroll` as the only
scroller), and the scroller grows instead of clipping.  Note the first row also drifts by ~1 px while
the reveal settles: that is why the arm waits for its own box to repeat rather than assuming it did.

## The re-derived shot

`shotAlert()` now: names the scroller that owns the alert and aligns the alert's top to that
scroller's top; requires its own box to repeat across a pair of animation frames, ceiling 20 tries;
refuses to shoot unless the alert is fully inside both the scroller and the viewport; and crops by
that box instead of asking Playwright to scroll a moving element into view.  `scrollBottom = 0` was
tried first and rejected: after 甲 the alert can sit below the container's client box at 0, and that
clip boundary is a function of sentence length -- the thing under test.

The two claims and their wording are unchanged; `test("the shot is taken from the alert's own box…")`
only records where each picture came from (`shot-geometry-backend.json`).

## Readings

| file | exit_code | counts |
| --- | --- | --- |
| `reading-before-fix-red.json` | 1 | 5 passed / 1 failed |
| `reading-after-fix-backend.json` | 0 | 7 passed |
| `reading-after-fix-backend-rerun.json` | 0 | 7 passed, byte-identical hashes to the row above |
| `reading-after-fix-own-config.json` | 0 | 6 passed (the order's own config, no backend) |
| `reading-red-collapse-backend.json` | 1 | 5 passed / 2 failed -- counterexample below |
| `reading-signed-gates-control-tip.json` | 1 | 9 passed / 3 failed, on a bare tree at the tip |
| `reading-signed-gates-my-tree.json` | 1 | 9 passed / 3 failed, on this delivery |

The signed-gate pair fails on the same three nodeids in both trees: `ord0273-text`,
`ord0273-text-en`, `ord0278-negative-refused`.  Those are pre-existing on the line; this delivery
adds none.

## Counterexample

`reading-red-collapse-backend.json` + `pixels-red-collapse.json` +
`log-red-collapse-backend.txt`: setting the zh-CN `trial.sealedNoAnswer` value back to the answered
sentence -- one working-tree line, never committed, tree clean afterwards -- reddens `sentences` and
`pixels` together, in the backend-up environment.  `separated` reads false in that file.

## Reproduce

```
# backend up (this is where the red lived)
npx playwright test --config playwright.config.ts \
  e2e/qoder-ord0349-two-legs-two-sentences.spec.ts --reporter=line --workers=1
# the order's own config, no backend
CITYNEXUS_ORD0349_PORT=5102 npx playwright test --config playwright.ord0349-S1.config.ts \
  e2e/qoder-ord0349-two-legs-two-sentences.spec.ts --reporter=line --workers=1
```

## One coordinate I cannot resolve

The commander's log blob `8ce9f0e79a5389dd4440a1961b7d8d9d43c09817` does not exist in this
repository for me: `git cat-file -t` fails both before and after fetching
`cmdr/land-ord0349-recut-r2`, the mirror branch and this lane's ref.  His `03d7cc95…` recut commit
and the intermediate `725bb7d4…` do resolve, and all five of my source blobs are byte-identical in
`03d7cc95…`.
