# ORD-0349-r4 readings (lane N1)

The line moved twice while this lane worked.  `824fca39…` (the base the commander named) gained
ORD-0341 and ORD-0345, and ORD-0341 edited **the same catch statement** ORD-0349 edits.  This is the
first base where a hand merge is unavoidable, so it was merged by hand and then measured.

## The union

At `frontend/src/app/V8Experience.tsx` in the sealed-demo `catch`:

| order | what it wanted | how |
| --- | --- | --- |
| ORD-0341 (甲) | the failure's technical facts must reach the attribution channel, because Q71 took the `data-*` carriers away | `recordAttribution(classifyReadFailure(error), "wizard.sealedDemo.enter")` |
| ORD-0349 | the two legs must not share one sentence | pick `trial.sealedUnreadable` or `trial.sealedNoAnswer` from `attribution.evidence_kind` |

Both classify the same error, so one `classifyReadFailure` result serves both, and the sink name is
the one the shipped gate quotes: `wizard.sealedDemo.enter`.  ORD-0349's first cut used
`shell.sealedDemo.entryRead`; that name is not used here, because the gate's assertion text at
`frontend/e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts:441` names the other one, and
writing the record twice under two contexts would invent a second sink.  Nothing new is printed into
visible text: the only visible change is which registered i18n key is chosen.

## Readings, on this tree

| file | exit_code | counts |
| --- | --- | --- |
| `reading-union-merge-backend.json` | 0 | 7 passed |
| `reading-union-merge-backend-rerun.json` | 0 | 7 passed, byte-identical hashes |
| `reading-union-merge-own-config.json` | 0 | 6 passed (no backend) |
| `reading-red-collapse-backend.json` | 1 | 5 passed / 2 failed (`sentences`, `pixels`) |
| `reading-signed-gates-control-tip.json` | 0 | 23 passed, four signed gates on a bare tree at `7e728268…` |
| `reading-signed-gates-my-tree.json` | 0 | 23 passed, same four gates on this delivery |

`SUMMARY.json` recomputes those numbers from the rows beside it.  The gate set is
`qoder-sealed-failure-speaks-and-offers-retry` (which carries the ORD-0341 telemetry node that reads
`window.citynexusAttribution`), `qoder-continuation-resume-carries-identity`,
`qoder-ord0344b-sentence-move-keeps-attribution`, `qoder-ord0338-wizard-gap-clearance`.
The three nodeids that were red on `824fca39…` and `38277c4e…` (`ord0273-text`, `ord0273-text-en`,
`ord0278-negative-refused`) are green on `7e728268…` -- ORD-0341 re-derived them onto the non-DOM
channel.  The lane's own pixel arm is unaffected by that: `pixels-union-backend.json` hashes exactly
as it did on the r3 base.

## What is carried from r3

`frontend/e2e/qoder-ord0349-two-legs-two-sentences.spec.ts` is the r3 shot (align the alert to the top
of `.cn-onboarding__scroll`, require its own box to repeat across a pair of animation frames within a
ceiling of 20, refuse to shoot unless it is inside both the scroller and the viewport, crop by that
box).  The blanketed `position: static !important` stays deleted; the probe that proved it was the
mover is archived on the r3 ref, `refs/heads/review/N1-ord0349-two-legs-two-sentences-r3`, in
`review/evidence/ord0349-r3/probe-document-growth.txt`.

## Reproduce

```
npx playwright test --config playwright.config.ts \
  e2e/qoder-ord0349-two-legs-two-sentences.spec.ts --reporter=line --workers=1
npx playwright test --config playwright.config.ts \
  e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts \
  e2e/qoder-continuation-resume-carries-identity.spec.ts \
  e2e/qoder-ord0344b-sentence-move-keeps-attribution.spec.ts \
  e2e/qoder-ord0338-wizard-gap-clearance.spec.ts --reporter=line --workers=1
```

Both need the authoritative environment; lane ports were 端口 5100 with 端口 6100, and 端口 5102 for
the no-backend config.
