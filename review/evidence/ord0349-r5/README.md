# ORD-0349-r5 readings (lane N1)

Parent = `6fd43627e717a97ea779da866eb4546b8acb9deb`, the authoritative line as read by
`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`.

The line moved four times while this order was open (`38277c4e…` -> `824fca39…` -> `7e728268…` ->
this).  `7e728268…` was where ORD-0341 landed on the same `catch` statement and forced a hand merge;
the commit between that and this tip is ORD-0355 and is **backend-only** -- every one of its 10 files
is under `backend/`, and none of them is a file this delivery or this instrument reads.  The five
product/test blobs on this ref are byte-identical to the r4 ref, so this re-parent changes the
parent, not the content.

## Readings on this tree

| file | exit_code | counts |
| --- | --- | --- |
| `reading-union-merge-backend.json` | 0 | 7 passed |
| `reading-union-merge-backend-rerun.json` | 0 | 7 passed |
| `reading-union-merge-own-config.json` | 0 | 6 passed, no backend |
| `reading-red-collapse-backend.json` | 1 | 5 passed / 2 failed -- `sentences` and `pixels` |
| `reading-signed-gates-control-tip.json` | 0 | 23 passed, four signed gates on a bare tree at the same tip |
| `reading-signed-gates-my-tree.json` | 0 | 23 passed, same four gates on this delivery |

`pixels-union-backend.json` hashes `e816f46a…` / `ee587279…` -- the same two values the r3 and r4 arms
produced on their bases, which is the determinism claim after the shot was re-derived.  Lane ports were
端口 5100 with 端口 6100, and 端口 5102 for the no-backend config; the control tree used 端口 5103.

## Where the cause and the probe live

The blanket `position: static !important` that was making this arm hang, and the 12-frame
height/node trace that names it as the mover, are archived on the r3 ref
(`refs/heads/review/N1-ord0349-two-legs-two-sentences-r3`) under
`review/evidence/ord0349-r3/probe-document-growth.txt` together with the probe source and the
before-fix reading.
