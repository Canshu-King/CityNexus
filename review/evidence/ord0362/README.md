# ORD-0362 (lane N1) -- what the old/next shell may and may not require of the capability payload

Parent = `refs/heads/mirror/integration-frontend-apple-pass1` at the time of measurement, recorded in
`step1_backport_ancestry.json` as `tip`.

## Requirement 1 -- the 11 named, and what "cherry-pick onto the current tip" yields

`step1_backport_ancestry.json` holds all eleven with their full 40-hex, the ORD-0245 receipt's own
verdict onto the phone baseline, ancestry against the tip, and a present-at-tip witness (the first
substantive added line of each commit, searched for in the tip's copy of that file).

**Result: all eleven are ancestors of the tip and every witness line is present at it.**
`cherry_pick_onto_tip_would_be` reads `EMPTY` for all eleven. They were candidates for a
backport *onto the phone baseline* `53fe8e8…`; three days of landings have since put them into the
line itself, so there is nothing left to carry onto the current tip.

Sources of truth, cited rather than re-typed:

| what | where |
| --- | --- |
| the classification of 25 candidates | `commander/control` blob `3f060dc10f89…` (`evidence/ord0245/ord0245_backport_classification.json`) |
| the 16->26 key jump, 12 endpoints x 2 trees | `commander/control` blob `20b83a3959f6…` (`evidence/ord0245/ord0245_payload_diff.json`) |
| this lane's per-item ancestry proof | `step1_backport_ancestry.json` here |

The twelve diverged commits were not touched by this lane, in this tree or any other.

## Requirement 2 -- the candidate

The candidate on this ref is the tip plus the payload gate only. It carries **zero** backported
commits, because of the measurement above. It is not a smaller version of what was asked for; it is
the same deliverable with its contents determined by a reading, and the reading is published here.

## Requirement 3 -- the gate, measured only on the payload

`payload_shape_tip.json`: the server's own answer at this tip, measured on a disposable store of this
lane's, on 端口 6110, three queries. The route's key set is data-dependent, so each answer is
recorded separately and the union is labelled as such -- `29` union, `27` on the HYDRATABLE answer,
`29` on the two UNAVAILABLE ones, `80` flattened paths.

`key_split_tip.json`: which of those keys the shipped consumer actually reads. Nine
(`capability`, `reason_code`, `recommended_action`, `missing_categories`, `coverage`, `candidates`,
`retryable`, `pending_destination_label`, `query`) appear as `capability?.<name>` in
`DestinationPreparationPanel.tsx`; the remaining eighteen do not appear in the component at all. This
is what makes the two arms mean something: "new" and "old" are decided by the reader, not by a
vintage guess.

`frontend/e2e/qoder-ord0362-old-shell-payload-compat.spec.ts` shows the same destination twice:
A gets the server's answer untouched, B gets it reshaped and additionally carries three field names
no server has ever sent. The gate claims A and B are the same screen -- verdict, visible sentence,
pressable actions, and no error that A does not also have.

| run | shape | keys removed | exit_code | counts | verdict/text identical |
| --- | --- | --- | --- | --- | --- |
| `reading-o362b-default.json` | drop-all-unread | 18 | 0 | 2 passed | yes |
| `reading-o362b-armnew.json` | drop-one, `pending_label_fidelity` | 1 | 0 | 2 passed | yes |
| `reading-o362b-armold.json` | drop-one, `capability` | 1 | 1 | 1 passed / 1 failed | no (`HYDRATABLE` -> `""`) |
| `reading-o362-affected.json` | with ORD-0193's own gate | 18 | 0 | 7 passed | yes |

The per-run `screen-*.json` files carry the observed key list, exactly what B dropped, what was
injected, and both screens as text. `o362b-armold` is the ordered red arm: same procedure, the only
difference is which key the run names, and the gate goes red on the payload rather than on the
instrument.

## What this gate does not claim

* It does not put an old bundle on a phone. The pair it measures is this generation's shell against
  a payload of a shape it may meet (half its keys absent, extra fields present).
* The reverse pair -- a shell of the `53fe8e8…` vintage against today's payload -- has no consumer
  for this route to break: that tree ships `RealCityDiscoveryPanel.tsx` and no
  `DestinationPreparationPanel.tsx`, measured with `git ls-tree` at that commit. A claim that the old
  shell "eats" this payload would therefore be vacuous, and is not made here.
* No product code changed in this delivery; no write endpoint was added or called. Lane ports: 端口
  5100 with 端口 6100 for the gate, 端口 6110 for the standalone measurement.
