# Revolution R30 — Consent Epoch Shock Recovery Result

## Verdict

**PROVEN** by the generated machine verdict:

- 19 `PROVEN`
- 0 `NOT_PROVEN`
- 0 `CONTRADICTED`

Machine verdict: `output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json`

Live receipt: `output/revolution-r30-live-20261006/R30_LIVE_RECEIPT.json`

R29 is inherited from the submitted `output/revolution-r29-live-20261005/R29_MACHINE_VERDICT.json` (`13 PROVEN / 0 NOT_PROVEN / 0 CONTRADICTED`); R30 reads that baseline and does not rerun R29.

## Causal closure

The live Journey completed the R29 disagreement and mediator renewal up to the
point where E1 was resolved but not consumed. An unrelated provider observation
left the E1 epoch unchanged. A `DISRUPTED` CitySignal fixture then went through
the server pipeline and produced provider observations plus CitySignal Events.
The selected plan remained a candidate, but its decision-material fingerprint
and authority epoch changed.

The old resolved child was resumed through the normal Agent and approval path.
Its continuation reached the mutation core and failed closed with
`COLLECTIVE_CONSENT_EPOCH_STALE`; no E1 proposal or sibling became active.

The post-shock external Agent inspected the current Journey, called
`request_replan`, and opened a fresh server-owned collective decision. Two
authenticated Journey principals answered the new proposal, producing E2.
The protected C4 anchor and current execution cursor survived, and exactly one
fresh recovery proposal was accepted on the same Journey.

## Live identifiers

- Journey: `aad03817-3081-4eec-ae09-ba14cd797b23`
- E1 mediator mission: `1bae64d3-69c2-4a5c-b6a5-e683f26597e5`
- E1 selected proposal: `fda97b80-c584-4506-8be8-378ebacf3ded`
- E1 epoch: `ec0eeff16a47a088ff0c37d5ab556b3d6762f6d77956debcc8b247ea2e272b5d`
- Fresh decision mission: `f005df16-5fb3-4d0c-ab62-d647bb43309e`
- E2 selected proposal: `e3cbd4ae-c7c4-4618-abd2-9eb9971056da`
- E2 epoch: `2fb97a954a6420bd052194339992949a1d01e89a2026fa0596864504b9811ac3`
- Active recovery plan: `1ff44d2b-67a0-444f-99f2-16d34d9ccc08`

No physical travel is claimed. The proof covers durable product state,
provider-backed evidence, external Agent tool traces, authenticated responses,
core rejection, and exactly-once plan acceptance.

## Stop rule

R30 is closed for this consent-epoch contract. No R30.1 receipt pass was added.
