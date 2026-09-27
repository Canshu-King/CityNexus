# ORD-0367  acceptance note (commander, 2026-09-28 ~00:47 +08)

What this order is: the i18n copy-register pass plus the design-token tier work that the
conversation `be19052c-d805-448a-b11e-46d53633d45b` delivered on branch
`review/Q-pitravel-token-tiers`. The commander re-measured everything below instead of
trusting that lane's own summary.

## Coordinates (all full 40-hex, all resolvable with `git cat-file` in `D:/moodle/CityNexus`)

- authoritative tip before the landing: `baaa07117003320292d76a5f0c383952071b7364`
- lane candidate tip:                 `031e381e0f2c6412ac63a7f1314c0951c5609125`
- re-cut onto the tip, and the new authoritative tip: `4ef864cfa49b805e3d41b7f079f5fb4184ccec3d`
- merged tree of the re-cut:          `cacb483db09e994f103dd222291006df6646cc3e`
- `frontend/src/design-tokens.css` on the landing generation: `ce95d9bb0d3765f1077ae293dc049ff3ca74cdd9`
- `frontend/src/i18n/LocaleContext.tsx` on the landing generation: `cb80ad55d7c1626a74ef73299fcadf43c4b1f094`
- ruler `tools/cnx_copy_tiers_r1.py`: `b9d2300773da37a098b8e8995d662face9063a9f`
- ruler `tools/cnx_token_tiers_r1.py`: `47bf6317d4dd7fc2fbb35c6bbc35b591640ae870`

## Why the re-cut was clean

- measured blob equality between the authoritative tip and **the lane's own base commit** `6ee21eddba60303e8f0f46907df9501ee0149e6e`, each read with `git rev-parse <rev>:<path>`:
  - `design-tokens.css`: tip `6f7ba871d9d57c41b9060b7098def7a8ae396c19` vs base `6f7ba871d9d57c41b9060b7098def7a8ae396c19` -> equal `true`
  - `LocaleContext.tsx`: tip `f7272db5ff16ba367563e746f3054c41ea078ffa` vs base `f7272db5ff16ba367563e746f3054c41ea078ffa` -> equal `true`
- conclusion is read off those two cells, not asserted: both files untouched between base and tip -> `true`; when true, the candidate introduces them with no merge at all.
  the re-cut independently proved per-file blob equality and wrote it to `D:/moodle/_qoder_cmdr_ref_20260921/tonight_tiers/recut_ord0367.json`
- relationship as read by the landing gate, field by field, from `land_ord0367.json`:
  - `verdict` = `READY_TO_LAND`
  - `mode` = `LAND`

## Ruler runs the commander performed personally

Both rulers were run twice: once against the real bytes, once with `--mutant`, which injects
defects that the ruler must catch. A ruler that cannot catch its own injected defects is
itself the defect, so the mutant arm is part of the evidence, not decoration.

### `tools/cnx_token_tiers_r1.py`

| cell | measured |
|---|---|
| `PARITY` | 69 (token,scope) baseline readings re-resolved |
| `TIERS` | inline rgba() remaining inside :root theme blocks: 0 |
| `LADDER_USED` | tint tiers defined 10, unreferenced 0 |
| `CONSTANT_DUP` | tokens re-declared identically in the dark block: 0 |
| `CONSTANT_IN_DARK` | --cn-always-* present inside :root[data-theme=dark]: 0 |
- mutant arm: 4 injected defects caught (`M1_value_moved`, `M2_inline_alpha`, `M3_always_in_dark`, `M4_identical_not_always`)
- raw outputs in this directory: `ruler_token_tiers_real.txt` (real bytes) and `ruler_token_tiers_mutant.txt` (`--mutant`)
- cells printed: 5

### `tools/cnx_copy_tiers_r1.py`

| cell | measured |
|---|---|
| `REGISTER_PARITY` | 611 bilingual keys: 611 agree, 0 clash |
| `NO_GROWTH` | 15 values changed; zh gained chars: 0, en over +8: 0 |
| `ASSERTIONS_STILL_HIT` | 11 keys edited against 213 e2e text assertions; 0 would lose their target |
| `REMAINDER_REPORT` | en hard words 5->1 | zh hard words 6->2 (not gated) |
- mutant arm: 3 injected defects caught (`K1_register_clash`, `K2_zh_grew`, `K3_pinned_key_touched`)
- raw outputs in this directory: `ruler_copy_tiers_real.txt` (real bytes) and `ruler_copy_tiers_mutant.txt` (`--mutant`)
- cells printed: 4

## The claim the commander checked independently of the ruler

The ruler's own anti-coupling cell is `ASSERTIONS_STILL_HIT`. The commander re-checked the
underlying fact by hand, because a disjunctive e2e assertion was already known to be lurking:

- `hub.continuationUnconfirmable` is quoted verbatim by two e2e files
  (`qoder-continuation-owner.spec.ts:30`, `qoder-continuation-resume-carries-identity.spec.ts:31`).
- that line is present once in the baseline and once in the candidate, and the two are
  byte-identical: `true` (candidate line text length in code points: `68`)

## Landing and the phone generation

- landing gate receipt: `land_ord0367.json` -- tip_after `4ef864cfa49b805e3d41b7f079f5fb4184ccec3d` -- both GitHub routes agree: `True`
- deploy receipt: `deploy_4ef864cfa49b805e3d41b7f079f5fb4184ccec3d_0928_003811.json` -- overall `GREEN` -- switched files `["index.html", "manifest.webmanifest", "sw.js", "v10-sw.js", "workbox-6923124b.js"]`
- phone-side probe `_phone_chain_0038.json`: overall `DEPLOYED_AND_BYTE_IDENTICAL_ON_PHONE_SIDE` at `2026-09-28 00:39:00 +0800`, generation under test `4ef864cfa49b805e3d41b7f079f5fb4184ccec3d`, assets probed `3`
  - `all_200` = `True`
  - `all_bytes_equal_to_disk` = `True`
  - `no_asset_served_as_html` = `True`
  - `js_content_type_correct` = `True`
  - `every_named_asset_present_on_disk` = `True`
  - measured `/assets/index-BEEP22s_.js`: http `200`, content type `text/javascript`, served `1277883` B vs disk `1277883` B, sha256 match: `true`
  - measured `/assets/index-DpqSOpMP.css`: http `200`, content type `text/css`, served `185505` B vs disk `185505` B, sha256 match: `true`
  - measured `/v10-sw.js`: http `200`, content type `text/javascript`, served `2055` B vs disk `2055` B, sha256 match: `true`
- the probe states its own limit, verbatim: `Transport-level identity only (status, content type, bytes). It does not prove the app renders or that a traveller can finish a plan - that is the walkthrough gate.`
- credential handling recorded by the probe: `auth read from the file by path; value never printed nor stored in this artifact`

## What is NOT claimed here

- No backend test suite was run for this order: the landing gate records `test_exit=NOT_MEASURED` and `collect_exit=NOT_MEASURED` because `--tests` was not passed. The candidate carries no `backend/` file.
- The tunnel host rotates. The address used for this swap is recorded in the deploy receipt
  and in `D:/moodle/_qoder_preview_20260920/run/tunnel_url.txt`; the previous address was
  archived, not deleted.
- Durations from the previous generation do not transfer (standing rule Q25).

## Follow-up defect the commander found while verifying this generation

Searching the *deployed* asset rather than the source found a hardcoded fallback that the
copy ruler cannot see, because the ruler only reads `LocaleContext.tsx`:

```
... body ?? (flag ? "确认失败" : "Approval failed")
```

Named sites from a scan of the pure authoritative tree (`git archive` export, not a working
tree): `frontend/src/features/agent/CopilotDock.tsx:364`, `:384`, `:415`;
`frontend/src/features/execution/LiveRecovery.tsx:238`;
`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:805`.
A wider scan of bare nullish fallbacks found 78 sites, all of them English literals, which
means a Chinese reader is shown English whenever a server body is missing. Order
`ORD-0370` was dispatched for both counts.

