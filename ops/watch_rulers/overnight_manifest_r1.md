# CityNexus overnight evidence manifest (machine-generated - do not hand-edit the table)

- built at 2026-09-25T07:01:35+0800 from `audit_r6_receipt.json` (instrument `live_checks/audit_closure_coordinates_r6.py`, blob `1939c68404fc6fde4d496f200930cf56a54aa84b`)
- branch `commander/control` @ tip `d1c2f527c65765f15e2447d5ff97fb1adc868c7e` (read when the receipt was produced)
- cells read: **84**, resolving byte-for-byte: **84**, failing: **0**, overall: `ALL_COORDINATES_RESOLVE`

## What each cited coordinate is

| repo path | declared blob (40) | bytes | cited by | resolves |
|---|---|---|---|---|
| `live_checks/deploy_bundle_v2_draft_r4.py` | `0686670743c079647aa678370aa5481562c4c0a8` | 132623 | 0271-A/0277 | OK |
| `live_checks/deploy_bundle.py` | `149e9c6dbe6debcac92041bb192761c1cf1aa2a7` | 106731 | 0271-A in-service | OK |
| `live_checks/test_ord0271a_debt3_r3.py` | `cababfe9097b3d901730c37d13682a0310c6f20e` | 25704 | 0271-A DEBT-3 | OK |
| `live_checks/test_ord0271a_debt4_r3.py` | `6adba3214e8946e5c496d5d394801445b5f1c70f` | 12245 | 0271-A DEBT-4 | OK |
| `live_checks/test_ord0277_generation_contract_r2.py` | `47abf7d8305162b7aa0f79ae838ee42bd00429f9` | 14530 | 0277 | OK |
| `live_checks/publish_evidence_r5.py` | `ea4416dbafa7ac84718c3d87bd56394fb5ca5f7b` | 22464 | publisher | OK |
| `live_checks/test_ord0275_publisher_guard_r4.py` | `01d51ce035244c8bf620aaede474c2b85847703c` | 22732 | 0275 body | OK |
| `live_checks/test_publisher_placeholder_value_scan_r2.py` | `a67086eace45ce3a9fc3beace28bffb7d18dccec` | 19038 | DEBT-1 | OK |
| `evidence/ord0271-a-gauge-fixtures/ord0271a_debt3_selftest_coldrun_r5.json` | `40ed7864a39aaabeea56d76c0fc7cd2a60c37d49` | 11293 | 0271-A | OK |
| `evidence/ord0271-a-gauge-fixtures/ord0271a_debt4_selftest_r6.json` | `b16d2c27ac8bbe212b6ca64b2098a2d1fae564e0` | 4068 | 0271-A | OK |
| `evidence/ord0271-a-gauge-fixtures/live_selftest_69arms_r4_gauge_0924_233853.json` | `9cde913ccbf8c9c6d6459b54fc8a270e446456c8` | 28852 | 0271-A live | OK |
| `evidence/ord0271-a-gauge-fixtures/live_preunion_ready_to_union_r4_gauge_0924_234113.json` | `124619bd387493ef4ee5227a91f8b97a7f180cb1` | 31425 | 0271-A live | OK |
| `evidence/ord0277-sw-registration/ord0277_generation_contract_selftest_r3.json` | `0e0f646fc4a447408b0a584ffa863c0202e0e586` | 5771 | 0277 | OK |
| `evidence/ord0275-publisher-path-guard/ord0275_selftest_r4.json` | `2a26fb34d335e6129c74ef645a60f05c6228e23e` | 11232 | 0275 | OK |
| `evidence/ord0272-reverify/commander_samegen_reverify_landed_dcae1bc9_r2.json` | `31996a40d57c4f3c33f0e32ce02cdc5159993808` | 16308 | 0272 landing | OK |
| `evidence/ord0272-reverify/verifier_derivation_d2305848.json` | `221c6372db22c8ac1f9e02604055358758fe49d1` | 8452 | 0272 verifier | OK |
| `evidence/ord0272-reverify/verifier_rederivation_followup_d2305848.json` | `67a3f68797c6091d6f4426f3431dbca46eabc148` | 7074 | 0275/DEBT-4 | OK |
| `evidence/ord0271-a-gauge-fixtures/verifier_derivation_window_d2305848.json` | `b657a289e885a2de2f6447b89eebae9a54a05be0` | 12263 | 0271-A verifier | OK |
| `evidence/ord0271-a-gauge-fixtures/verifier_rederivation_r3_d2305848.json` | `1bf501033c1caee202181c07ecd1cc9b0b568d31` | 8021 | 0271-A re-deriv | OK |
| `live_checks/test_ord0275_publisher_guard_r5.py` | `be0978863fbd76f19de7350d6e889b7bf8d38010` | 26006 | 0275 r5 (vacuous R cell fixed) | OK |
| `evidence/ord0275-publisher-path-guard/ord0275_selftest_r5.json` | `13881e29dc8fc21d157056ee6619ff46660629e9` | 11919 | 0275 r5 receipt | OK |
| `live_checks/test_publisher_placeholder_value_scan_r3.py` | `3f391bb0dffde7acb2802d78aca0602c5719def6` | 21447 | DEBT-1 r3 (stale premise fixed) | OK |
| `evidence/publisher-placeholder-scan-debt1/selftest_r3.json` | `d74b61a9a7e19217d2f1f1d6cb762bebc2e8b12b` | 9705 | DEBT-1 r3 receipt | OK |
| `live_checks/generation_transfer_check.py` | `47372706c6ffde2175155de175133e212aae651c` | 10197 | Q24 validator r1 | OK |
| `evidence/generation-transfer-rule/selftest_v1.json` | `24c87fa3bf42a69d0b9d7ac7998f781548061f23` | 3946 | Q24 validator r1 selftest | OK |
| `live_checks/generation_transfer_check_r2.py` | `8a4006375750a9e6506994c0e089e4cd80b2ce63` | 12770 | Q24 validator r2 (--check fixed) | OK |
| `evidence/generation-transfer-rule/selftest_r2.json` | `9cca976eeaf0463e7ff16cd8d3501eb52259acd1` | 4641 | validator r2 selftest | OK |
| `live_checks/generation_transfer_check_r3.py` | `f124d8a432927b30f0384e16ae7dd80c6d4bad79` | 15303 | Q25 claim_kind r3 | OK |
| `evidence/generation-transfer-rule/selftest_r3.json` | `fb4e9b1cedac2f152bb758da05e61cf93800ea69` | 6194 | validator r3 selftest | OK |
| `live_checks/generation_transfer_check_r4.py` | `32f717a9d4dfadaebd16a6bdaea34c8a289875c5` | 18946 | validator r4 (offline judge + pinned controls) | OK |
| `evidence/generation-transfer-rule/selftest_r4.json` | `d3ce752c7d1192e90618d5ca2501e0ef4fe4c986` | 8358 | validator r4 selftest | OK |
| `evidence/generation-transfer-rule/ord0279_spec_r1.json` | `b88d1889a47a88c7a2def5617335f97e3cc2c09d` | 1187 | ORD-0279 spec | OK |
| `evidence/generation-transfer-rule/ord0279_audit_r1.json` | `a62d1acfcf2971b6178d03ac48365b5932e9e25e` | 4176 | ORD-0279 cross-gen audit | OK |
| `evidence/generation-transfer-rule/ord0279_spec_r2.json` | `3b07b03f7fd16085e62fa4091ff2a3e13eb7631f` | 1860 | ORD-0279 spec r2 (claim_kind) | OK |
| `evidence/generation-transfer-rule/ord0279_audit_r2.json` | `a9774ed4d2f6395fdac174a76577bbd0fbe646b8` | 6010 | ORD-0279 audit r2 | OK |
| `live_checks/evidence_provenance_sweep.py` | `32a68f0e08863f639c5693a3f309efe5cf1a4ed6` | 5687 | evidence-lineage sweep instrument | OK |
| `evidence/commander-evidence-sweep/provenance_r1.json` | `be0140fca84f9d909962c09793830e701f432408` | 61270 | sweep receipt | OK |
| `evidence/t1-postunion-45b0a5e/deploy_green_r1.json` | `f1748f4cef8b836e366bd179f7464d67d72e32ea` | 74249 | T1 deploy GREEN | OK |
| `evidence/t1-postunion-45b0a5e/preflight_preunion_named_gaps_r1.json` | `f73844151f6847b8c2a863d52a651d4daae37d4f` | 33477 | T1 PRE_UNION refusal | OK |
| `evidence/t1-postunion-45b0a5e/preflight_receipt_r1.json` | `dc1cf7150b701e3851a6a5132094a7bce6a5d6b4` | 34158 | T1 preflight receipt | OK |
| `evidence/t1-postunion-45b0a5e/postunion_refused_unauthenticated_probes_r1.json` | `0c7a6e33df4ed143a0519bfd90d7b907f8cfe215` | 35832 | T1 my own 401 failure | OK |
| `evidence/ord0272-k8-f/stale_blob_probe_r1.json` | `83642644fc9ad35746fbaa1bc0f134738026d394` | 5366 | lane F probe | OK |
| `evidence/ord0272-k8-hjp3-crossprocess/K8_XP_readings.json` | `fbb154cf9ce598ad1d3a4241b0f2b96181f0037b` | 6282 | lane HJ-P3 K8 cross-process | OK |
| `evidence/ord0269-0273-gate-v6-e713510/verifier_derivation_d2305848.json` | `47eda29379be4538e8001cc794e73253823b3a81` | 7628 | red team v6 derivation | OK |
| `evidence/ord0279x-hjp3-run/O0279X-2504_readings.json` | `24a6a384e357449c7cc8f4de4a0f1d9b2759da63` | 9483 | ORD-0279-X readings | OK |
| `evidence/ord0272-k8-f/verifier_derivation_d2305848.json` | `709f9c8f99314a6b1ce5096e5ee3008b884f3c85` | 6211 | 0272 K8 two-cell derivation (lane E) | OK |
| `evidence/ord0269-0273-gate-v6-e713510/commander_samegen_0269_0273_45b0a5e_d2305848.json` | `bd12f1fb08833b98ebd93b83d0a0fa94773bce9d` | 3499 | 0269/0273 same-generation gate rerun (lane E) | OK |
| `evidence/ord0269-0273-gate-v7-45b0a5e/arms-v6-aef5765.json` | `af2150a0e8097edd7e1be2c4a720f9e660f60b2a` | 22591 | lane D arms (delivered as 16-hex prefix, resolved here) | OK |
| `evidence/ord0269-0273-gate-v7-45b0a5e/gate-round-5b549be-with-landing-groups.json` | `31eb62fb634a57450b90dbcfebf392f9725e7ed5` | 20772 | lane D gate round + landing groups | OK |
| `evidence/ord0269-0273-gate-v7-45b0a5e/manifest-5b549be.json` | `e2bca6c975a95dcf6972463851ddcc11bda31d0c` | 2997 | lane D manifest | OK |
| `live_checks/dist_hardlink_scan.py` | `ec3a3814bfb794e423e8fe27efe8b0671722de94` | 9958 | hardlink scanner (named the white-page mechanism) | OK |
| `evidence/commander-dist-hardlink-scan/scan_r1.json` | `1ee0d991ff832b53734f67c5836b3c9bf28cf283` | 11065 | real scan: 38 files / 35 hits / rc=3 | OK |
| `evidence/commander-dist-hardlink-scan/selftest_r1.txt` | `37c2df0917c81cca4ea0f401d1b35cd33febb2b1` | 497 | scanner selftest 5/5 (r1 was 3/5 on fixture bugs) | OK |
| `live_checks/receipt_consistency_o0276_r1.py` | `6d789e6856873f39b7cff18c7127d26c073e9d47` | 5085 | ORD-0276 recomputation ruler | OK |
| `evidence/ord0276-hjp3-cells/O0276-2505_readings.json` | `3ec966e90bc14f20955ef3d10936a9ce5ca17f6b` | 10906 | lane HJ-P3 ORD-0276 readings | OK |
| `evidence/ord0276-hjp3-cells/RECEIPT_O0276-2505.md` | `20ab8b3b231d10a9fabc6a2876343d8bf6f9ce85` | 5718 | lane HJ-P3 ORD-0276 receipt | OK |
| `evidence/ord0276-hjp3-cells/o0276_rig.py` | `adadc49eda18c4bb9a3dae038daea4f0763f8b5f` | 12808 | lane HJ-P3 ORD-0276 rig | OK |
| `evidence/ord0276-hjp3-cells/o0276_face.py` | `535853a65840e13ca7b544231ce25ea32a428d67` | 2984 | lane HJ-P3 ORD-0276 face | OK |
| `evidence/ord0276-hjp3-cells/shots_O0276-legacy-surface-clean-port.png` | `512ff616c1256113dd7c9d4327554109d213516b` | 18210 | lane HJ-P3 ORD-0276 shot (legacy surface) | OK |
| `evidence/ord0276-hjp3-cells/shots_O0276-v8-surface-clean-port.png` | `23f1ad6723b9b00ba6ceaa74cbad52e50635959f` | 69332 | lane HJ-P3 ORD-0276 shot (v8 surface) | OK |
| `live_checks/generation_transfer_check_r5.py` | `f53fa1271af4f8e021de696f0c10a3e3c7be525f` | 23459 | ORD-0283 A7/A9 fix (validator r5) | OK |
| `evidence/generation-transfer-rule/selftest_r5.json` | `595742f7ff4c65a7c474d8c754c08483404a2e21` | 9317 | validator r5 selftest 20 arms | OK |
| `live_checks/evidence_provenance_sweep_r3.py` | `0dcda650419b159767f1144c19ffcdf245f3e3c0` | 10069 | ORD-0283 B2/B3 fix (sweep r3) | OK |
| `evidence/commander-instrument-fixes-ord0283/sweep_selftest_r1.txt` | `c525d77d0fd1f06cc99b119b4cf64eedc9862ea3` | 492 | sweep r3 classify selftest 8/8 | OK |
| `live_checks/audit_receipt_runner_r2.py` | `0807bf6622bbefd5b551f8d2d40880e778a8b447` | 4821 | ORD-0283 C8 fix (runner r2 pins ref_tip_read) | OK |
| `evidence/commander-instrument-fixes-ord0283/before_after_r1.txt` | `d60f9336aada20ae03c1cd419f47b66b580d3bf0` | 1311 | before/after proof for A7+A9 | OK |
| `live_checks/audit_closure_coordinates_r4.py` | `56bc2f18e8db144295c1836a489648f9ed3cb165` | 10070 | ruler r4 (60 claims) | OK |
| `evidence/commander-coordinate-audit/audit_r4_receipt_r1.json` | `6dedf4e9be1db10d92c58e280220310467b89044` | 24406 | ruler r4 receipt | OK |
| `evidence/ord0283-cmdr-instruments-attack/attack_receipt_d2305848.json` | `b4bdc3ddec46f0b82e08c7f77bc4fd6f73ed3021` | 11900 | lane E ORD-0283 attack receipt | OK |
| `live_checks/audit_closure_coordinates_r5.py` | `c302dd9f376b5a4ff5e08fd3454030f17a82ee2c` | 11384 | ruler r5 (69 claims) | OK |
| `evidence/commander-coordinate-audit/audit_r5_receipt_r1.json` | `258ac9f4710839f83279503b8b945fd442b98a7d` | 28105 | ruler r5 receipt (first with ref_tip_read) | OK |
| `live_checks/receipt_consistency_o0282_r1.py` | `331a8b5651bb7dc015d9156769e6823431a82f0c` | 3731 | ORD-0282 recomputation ruler | OK |
| `evidence/ord0282-k8-landgen-f/ord0282_receipt.json` | `f93312c9ae1871744b94c54df843b3d59f3a585c` | 15288 | lane F landed-generation K8 receipt | OK |
| `evidence/ord0282-k8-landgen-f/seam_face_readings.json` | `eeedddaa26d7626623046b27de2a214181cdd81b` | 20733 | lane F seam raw per-round readings | OK |
| `evidence/ord0282-k8-landgen-f/landing_tree_proof.json` | `ec98fd76ea580cab38bb4c8293fe4af3b4d096ef` | 3214 | lane F tree proof (tip read before export) | OK |
| `evidence/ord0282-k8-landgen-f/second_observer_r3_run.json` | `b29eb8cd1df7f62535939b40adf4e024fdb9bd1b` | 1009 | lane F re-run of my r3 ruler | OK |
| `live_checks/bundle_selfreference_check_r1.py` | `3878341a4dca3dff2127f6dbf99a131a93f4e4b7` | 5009 | snapshot self-reference checker | OK |
| `evidence/commander-dist-hardlink-scan/selfcheck_r1.json` | `0d4f31938525447386fafdcd31dab1cc43f7c70e` | 3210 | 3 roots SELF_REFERENTIAL | OK |
| `evidence/commander-dist-hardlink-scan/scan_r2_after_fix.json` | `e115412298e6f269166f577f2cbb40c950e2bc5f` | 345 | re-scan: hits 35 -> 0 | OK |
| `evidence/ord0281-shape-hjp3/O0281-SHAPE-2506_witness.json` | `2e7fa49c1d58acc65cb6081c98caf7c4cd7a9f20` | 4242 | lane HJ-P3 ORD-0281 witness | OK |
| `evidence/ord0281-shape-hjp3/SHAPE_ORD-0281.md` | `9adfeef7b1f9d88dd5bf164119e8c3823b14fb36` | 9288 | lane HJ-P3 ORD-0281 shape | OK |
| `evidence/ord0281-shape-hjp3/frontend_write_legs.json` | `be11a160bee782c03cbeea01c0ff683f70a0e05c` | 5375 | lane HJ-P3 write-leg inventory | OK |
| `evidence/ord0281-shape-hjp3/o0281_silent_face.py` | `741c65388dc81d852774924c9263926e0b6589a6` | 3981 | lane HJ-P3 silent-origin face | OK |
| `evidence/ord0281-shape-hjp3/offset_check.py` | `3a77f40ce1b1875db35974d64dfe6e4f393424ea` | 1909 | lane HJ-P3 offset reconciliation | OK |

## Orders and what they mean now

- **ORD-0269 / ORD-0273** - `CLOSED` - authority: arbiter bus stamp 5823570235 (Q29=①), scope sentence: gate re-run on landed 45b0a5e2; the 9 reverse-mutation kills stay candidate-generation aef5765c facts, not re-run
- **ORD-0271-A / ORD-0277 / ORD-0275 / ORD-0268** - `CLOSED` - authority: earlier arbiter rulings + red-team derivations (see ledger blocks; coordinates in the table below)
- **ORD-0272** - `OPEN` - authority: arbiter bus stamp 5823570235 (Q34=①): seam face is a landed-generation fact (ORD-0282), but the authoritative line has no regression carrier yet -> blocked on ORD-0287
- **ORD-0274** - `CANDIDATE VERIFIED-FORM, awaiting derivation` - authority: commander re-read: compare 45b0a5e2...ef277b2 = ahead 3 / behind 0 (ff-able), 4 files +116/-9; derived_result belongs to lane HJ-P1 via ORD-0290
- **ORD-0276** - `ACCEPTED` - authority: commander recomputation receipt_consistency_o0276_r1 = 14 arms ALL_AGREE; user visibility stays the lane's own NO_PIXEL_READING, not promoted
- **ORD-0279 / ORD-0279-X** - `ACCEPTED / CLOSED` - authority: validator GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1 (Q24=①, Q25=①) + the cross-gen audit cells
- **ORD-0280** - `DISPATCHED (write window opened)` - authority: commander 号令 block 06:5x: three dirty spots in PlanWithAiSheet.tsx, label semantics untouched, fix model is the repo's own simulationAdapter pattern
- **ORD-0281** - `SHAPE ACCEPTED, no product code yet` - authority: arbiter Q33=①: this order now covers the keyed leg only; the unkeyed leg split out as ORD-0288
- **ORD-0282** - `ACCEPTED` - authority: commander recomputation receipt_consistency_o0282_r1 = 10 arms ALL_AGREE; K8 seam flip is now a landed-generation reading (guard 416ea4f2 vs mutant 784599fd, 6 rounds, blob-checked per round)
- **ORD-0283 / ORD-0285** - `BITES CLOSED (4/4 verified)` - authority: lane E's own reverify receipt (derived_result: FIXES_VERIFIED 4/4), re-checked by commander's receipt_consistency_o0285_r1 = 7 arms agree
- **ORD-0287** - `OPEN via Q35=②` - authority: carrier cannot be ported (product symbol absent on the landed line, counted by both lanes); route now = a guard regression test that depends only on the authoritative line
- **ORD-0288 / ORD-0289 / ORD-0290** - `DISPATCHED` - authority: 0288 = unkeyed write leg (shape @HJ-P3, code @D); 0289 = AST-based write-leg census on two generations (@F); 0290 = five-arm derived_result for lane B's candidate (@HJ-P1)
- **HARDLINK_SNAPSHOT_PROHIBITION_V1** - `IN EFFECT (Q32=①)` - authority: lane copies only; every generation swap runs dist_hardlink_scan.py and names hits without blocking the served line

## How to re-run the checks yourself (read-only; no tokens are ever printed)

```text
python live_checks/audit_closure_coordinates_r6.py                 # every coordinate above, byte-for-byte
python live_checks/audit_receipt_runner_r2.py <that ruler> <out.json>   # same, plus a tip-pinned receipt
python live_checks/generation_transfer_check_r5.py --selftest            # 20 arms, offline judge + live read-back
python live_checks/dist_hardlink_scan.py --selftest
python live_checks/receipt_consistency_o0276_r1.py / python live_checks/receipt_consistency_o0282_r1.py / ..._o0285_r1.py
```

Scope note carried from the ruler: resolving a coordinate proves the object is readable and
byte-equal to what was cited. It does NOT prove the numbers inside a receipt are true - those
are judged by the verifier receipts and the recomputation rulers named above.
