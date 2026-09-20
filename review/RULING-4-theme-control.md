# Ruling ④ closing -- the theme choice, and who was allowed to make it

Lane `e345b9d6` (M3-B). Commit `0e21a4f` (control + gate), `9f55b6f` (dev/prod gate split),
driver `review/ruling4_theme_kill_drivers.py`, table `review/ruling4-kill-table.txt`.

## What was missing

Ruling ④ asked for an in-app System / Light / Dark choice, persisted, resolved from
`<html data-theme>`, defaulting to the OS for anyone who never chose. ORD-0035/0036 shipped
the contract, the persistence, the default and the both-theme legibility gates -- and no
control. `grep -rn "applyTheme" src/ --include=*.tsx` returned nothing outside `main.tsx`'s
boot call: the stored key could only be written by a test. So a traveller could not choose
at all, which is the half of the ruling that mattered to them.

## What ships now

A `System → Light → Dark → System` cycle button in the topbar action row, next to the
language switch, reusing the existing `v9-language` class so the mobile tap-target rule and
the desktop density rule both apply unchanged. No navigation structure was touched.
The label names the choice you are on; the aria-label says what pressing it will do.
Clicking writes through `setThemeChoice` (theme.ts), so persistence and the root attribute
come from the single module that owns them rather than from a second copy.

## The gate

`e2e/qoder-theme-contract.spec.ts :: theme-control-cycles-all-three-choices`
(390px, OS emulated light throughout):

- the control is visible and measures >= 44px tall;
- before any click the root follows the OS (`light`) and the button says `system`;
- five clicks walk light → dark → system → light → dark, and at each one the root attribute
  and the button's own `data-theme-choice` must agree with what was just chosen;
- the set of choices the cycle passed through must be all three, not two;
- the **painted** ink of the Today heading must differ between the light and dark steps -- a
  control that flips an attribute while the screen stays the same is the cover-up the ruling
  names;
- after the last click, a reload must still say `dark` on the root and still hold
  `citynexus.theme = "dark"`.

Evidence written by the node: `review/evidence/ui-overnight/theme-control.json`.

## Kills

| mutant | expectation it breaks | result |
|---|---|---|
| `onClick={cycleTheme}` → a dead handler | the control does nothing | KILLED — "the control's own label disagrees with what it applied (wanted light)" |
| `dark: "system"` → `dark: "light"` (a two-state toggle wearing three words) | all three choices offered | KILLED — "…disagrees with what it applied (wanted system)" |
| `setThemeChoice(next)` → `void next` (never applies or persists) | the root must change on click | KILLED — "after choosing dark the root said \"light\" ([\"light\",\"light\"])" |

Each case replaced exactly one anchor, ran the whole theme file, and restored
`V8Experience.tsx` to the HEAD baseline (sha `383f9d13…` verified after every run).

## The gate that had to be moved, not softened

Landing A4's `e2e/qoder-sw-lifecycle.spec.ts` made the default suite report 2 reds, which
would have looked like product regressions and were not: that file proves a production
service-worker lifecycle, and the default project runs Vite dev, where `main.tsx` registers
the checked-in dev worker and never `/v10-sw.js`. The gate cannot pass there and must not be
made to "pass" by deleting it.

It now detects a dev document and skips itself with a reason that names the project which
does run it. Verified in both directions:

```
--config playwright.sw.config.ts   →  2 executed, 2 failed   (the merge gap this lane is
                                        still waiting on a ruling for, unchanged)
default project (npm run dev)      →  2 skipped, 1 passed    (the real-seed setup)
```

`playwright.config.ts` is `8c66aa92`'s file and was not touched; the exclusion lives in the
spec that needs it. If the owner prefers a project-level `testMatch` instead, that is a
one-line change on their side and this self-skip can come out.
