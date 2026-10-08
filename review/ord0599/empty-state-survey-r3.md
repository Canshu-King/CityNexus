# ORD-0599 r3 — the rest of the empty-state surface, surveyed

Why this exists: r2 fixed the two screens and the regression their specs caught. This is the
next layer out — every other state that answers an empty read with nothing to press — so the
next cell does not survey it again and so nobody mistakes a ruled-out screen for an oversight.

**The bar** (from the order): a screen qualifies only when all three hold.
1. The read answered, the set is genuinely empty (not a failure, not a loading state).
2. There is a real, reachable destination the traveller could be moved to.
3. No control that already sits on that screen does that job.

Anything missing (1) is a different defect class. Anything missing (2) has no honest button —
a button that goes nowhere is the fake this project keeps paying to remove.

## Changed (r1 + r2)

| screen | route | action | lands on |
|---|---|---|---|
| footprints | `/v8/footprints` | 打开行程去打卡 | `/v8/trips` |
| recycle bin | `/v8/trash` | 回到我的行程 | `/v8/trips` |

## Surveyed and ruled out — with the reason, not a shrug

| screen | testid | why it is not a gap |
|---|---|---|
| itinerary | `trip-itinerary-empty` | already the reference implementation: why + `v8-primary-button` to `import` (or copilot), swapping which door is primary when the catalogue is empty |
| pending set | `pending-empty` | already why + `pending-empty-action` to `discover` + re-read |
| pre-trip checklist | `pretrip-empty` | already carries `pretrip-empty-action` |
| access — trips | `access-trips-empty` | **ORD-0538 rules this one no action on purpose, with numbers**: with nothing listed the shell paints its own onboarding, and with a reference it paints the failure view. A button here could not be tapped, tested, or refused. |
| access — activity/roles/grants/roster | `access-activity-empty` et al. | all four already render `emptyAction(...)` |
| recycle bin — no viewer | `trash-no-viewer` | not an empty set: the screen does not know whose bin to ask for. An action cannot fix an absent identity. |
| stay explorer | `stay-no-options` | already has `stay-generate`, which makes the real server call |
| hotels | `hotels-empty` | states no data was returned and refuses to invent a price card; the destination (choose a city first) is not a route |
| plan version history | `history-empty` | genuine tell-only, but the honest destination is the planner and this panel's scope carries no `navigate` — wiring it means opening `app/V8Experience.tsx`, the 4.6k-line shell. Left alone rather than paid for with a hot-file edit. |
| abort — no reason | `journey-abort-empty-reason` | the server answered and named no reason. That is the fact; inventing one is the defect class this repo keeps removing. |
| inbox queue | `inbox-pending-empty` | sits directly under the paste form that fills it; the fix is a re-paste, not navigation |
| poi import — nothing extracted | `poi-import-empty` | same: the form that produced it is on the same screen, and `poi-import-open-plan` already exists |
| discovery batch | `v13-discovery-batch-empty` | `discovery.finishBatch` — the primary action — is directly above it |
| spend | `spend-empty` | names the count of unpriced lines, so "no total yet" and "nothing to look at" stay distinct |
| shared journey | `shared-plan-empty` | public read-only view at `/v8/shared/<token>`; there is no owned app to navigate into |
| shared poster | `shared-poster-plan-empty` | same |

## What a future cell should know

- `PendingSetPanel` and `TripItinerary` are the two in-tree references to copy — reason line,
  then `v8-primary-button`, then `data-contrast-role="control"`.
- `data-contrast-role="control"` is not decoration: ORD-0509's ruler judges a control by the role
  it declares, and an interactive element carrying its own test identity with no role is a finding.
- The state sentence must stay alone inside its `data-testid`. ORD-0530's `answered_empty` arm
  asserts `toBe` (equality) on that block's text. Folding the reason and the button inside it
  turned that arm red — the spec was right.