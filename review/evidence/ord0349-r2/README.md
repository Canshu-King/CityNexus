# ORD-0349-r2 readings (lane N1)

Re-parent of `review/S1-ord0349-two-legs-two-sentences` (`d1b82c8b`, base `046fc987`) onto the
authoritative tip. `git cherry-pick` merged `frontend/src/app/V8Experience.tsx` without conflict:
the line moved that file at the `Hub` continuation block, ORD-0349 moved the `V8Experience()`
sealed-demo catch block, and the two hunk ranges do not touch. No hand merge, no shipped assertion
edited.

## Files here

| file | what it is |
| --- | --- |
| `reading-green.json` | the order's own spec on this tree, first run |
| `reading-green-rerun.json` | the same spec again, fresh run id, to show the reading repeats |
| `green-pixels.json` | the per-leg screenshot hashes from the rerun (`control_stable`, `separated`) |
| `green-leg-kinds.json` | the four leg shapes and the `evidence_kind` the shipped classifier gives them |
| `reading-red-collapse.json` | red-by-design: both legs collapsed back onto one sentence |
| `red-arm-pixels.json` | that same run's pixel witness (`separated: false`) |
| `red-arm-leg-kinds.json` | classifier kinds under the collapsed copy (unchanged, as expected) |
| `reading-shipped-gates-merged.json` | three already-signed gates, on this tree |
| `reading-shipped-gates-control-tip.json` | the same three gates, on a second tree at the tip with no ORD-0349 |

## Reproduce without any lane-private script

From `frontend/`, with `DEEPSEEK_API_KEY` and `OPENAI_API_KEY` removed from the child environment
(names only are ever recorded):

```
CITYNEXUS_ORD0349_PORT=5102 \
CITYNEXUS_EVIDENCE_DIR=<wt>/review/evidence/arm-rerun \
npx playwright test --config playwright.ord0349-S1.config.ts \
  e2e/qoder-ord0349-two-legs-two-sentences.spec.ts --reporter=line --workers=1
```

The three signed gates need the backend, so they go through the default config with the
authoritative variables set (`CITYNEXUS_E2E_AUTHORITATIVE=1`, `CITYNEXUS_E2E_PORT`,
`CITYNEXUS_BACKEND_PORT`, `CITYNEXUS_PYTHON`, `CITYNEXUS_DATABASE_URL` pointing at a fresh
`_<run id>.db`, `CITYNEXUS_E2E_RUN_ID`, `CITYNEXUS_AI_ENABLED=false`):

```
npx playwright test --config playwright.config.ts \
  e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts \
  e2e/qoder-ord0344b-sentence-move-keeps-attribution.spec.ts \
  e2e/qoder-continuation-resume-carries-identity.spec.ts \
  --reporter=line --workers=1
```

## Note on the red arm

The red arm is a working-tree edit to `frontend/src/i18n/LocaleContext.tsx` line 778 only, setting
the `trial.sealedNoAnswer` zh-CN value to the `trial.sealedUnreadable` sentence. It is not a commit
and it is not in this ref; `git status --porcelain` was empty again afterwards. The spec's own
expectations were not modified in any arm.
