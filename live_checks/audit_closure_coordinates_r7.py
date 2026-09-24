"""Audit tonight's signed closures: does every cited coordinate actually resolve on the readable branch?

I signed ORD-0271-A / ORD-0277 / ORD-0275 CLOSED and landed ORD-0272, so the thing to verify is not my prose
but the twelve objects I cited.  For each path I read the live object metadata off `commander/control` and
compare BOTH the blob sha1 and the byte size with what I declared.  A single FAIL means the closure cites a
coordinate nobody else can read, which is exactly the defect class I spent tonight fixing elsewhere.
"""
import sys
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
import read_remote_file as rr

CLAIMS = (
    # (path, declared blob, declared bytes, cited-by)
    ("live_checks/deploy_bundle_v2_draft_r4.py", "0686670743c079647aa678370aa5481562c4c0a8", 132623, "0271-A/0277"),
    ("live_checks/deploy_bundle.py", "149e9c6dbe6debcac92041bb192761c1cf1aa2a7", 106731, "0271-A in-service"),
    ("live_checks/test_ord0271a_debt3_r3.py", "cababfe9097b3d901730c37d13682a0310c6f20e", 25704, "0271-A DEBT-3"),
    ("live_checks/test_ord0271a_debt4_r3.py", "6adba3214e8946e5c496d5d394801445b5f1c70f", 12245, "0271-A DEBT-4"),
    ("live_checks/test_ord0277_generation_contract_r2.py", "47abf7d8305162b7aa0f79ae838ee42bd00429f9", 14530, "0277"),
    ("live_checks/publish_evidence_r5.py", "ea4416dbafa7ac84718c3d87bd56394fb5ca5f7b", 22464, "publisher"),
    ("live_checks/test_ord0275_publisher_guard_r4.py", "01d51ce035244c8bf620aaede474c2b85847703c", 22732, "0275 body"),
    ("live_checks/test_publisher_placeholder_value_scan_r2.py", "a67086eace45ce3a9fc3beace28bffb7d18dccec", 19038, "DEBT-1"),
    ("evidence/ord0271-a-gauge-fixtures/ord0271a_debt3_selftest_coldrun_r5.json", "40ed7864a39aaabeea56d76c0fc7cd2a60c37d49", 11293, "0271-A"),
    ("evidence/ord0271-a-gauge-fixtures/ord0271a_debt4_selftest_r6.json", "b16d2c27ac8bbe212b6ca64b2098a2d1fae564e0", 4068, "0271-A"),
    ("evidence/ord0271-a-gauge-fixtures/live_selftest_69arms_r4_gauge_0924_233853.json", "9cde913ccbf8c9c6d6459b54fc8a270e446456c8", 28852, "0271-A live"),
    ("evidence/ord0271-a-gauge-fixtures/live_preunion_ready_to_union_r4_gauge_0924_234113.json", "124619bd387493ef4ee5227a91f8b97a7f180cb1", 31425, "0271-A live"),
    ("evidence/ord0277-sw-registration/ord0277_generation_contract_selftest_r3.json", "0e0f646fc4a447408b0a584ffa863c0202e0e586", 5771, "0277"),
    ("evidence/ord0275-publisher-path-guard/ord0275_selftest_r4.json", "2a26fb34d335e6129c74ef645a60f05c6228e23e", 11232, "0275"),
    ("evidence/ord0272-reverify/commander_samegen_reverify_landed_dcae1bc9_r2.json", "31996a40d57c4f3c33f0e32ce02cdc5159993808", 16308, "0272 landing"),
    ("evidence/ord0272-reverify/verifier_derivation_d2305848.json", "221c6372db22c8ac1f9e02604055358758fe49d1", 8452, "0272 verifier"),
    ("evidence/ord0272-reverify/verifier_rederivation_followup_d2305848.json", "67a3f68797c6091d6f4426f3431dbca46eabc148", 7074, "0275/DEBT-4"),
    ("evidence/ord0271-a-gauge-fixtures/verifier_derivation_window_d2305848.json", "b657a289e885a2de2f6447b89eebae9a54a05be0", 12263, "0271-A verifier"),
    ("evidence/ord0271-a-gauge-fixtures/verifier_rederivation_r3_d2305848.json", "1bf501033c1caee202181c07ecd1cc9b0b568d31", 8021, "0271-A re-deriv"),
    ("live_checks/test_ord0275_publisher_guard_r5.py", "be0978863fbd76f19de7350d6e889b7bf8d38010", 26006, "0275 r5 (vacuous R cell fixed)"),
    ("evidence/ord0275-publisher-path-guard/ord0275_selftest_r5.json", "13881e29dc8fc21d157056ee6619ff46660629e9", 11919, "0275 r5 receipt"),
    ("live_checks/test_publisher_placeholder_value_scan_r3.py", "3f391bb0dffde7acb2802d78aca0602c5719def6", 21447, "DEBT-1 r3 (stale premise fixed)"),
    ("evidence/publisher-placeholder-scan-debt1/selftest_r3.json", "d74b61a9a7e19217d2f1f1d6cb762bebc2e8b12b", 9705, "DEBT-1 r3 receipt"),
    ("live_checks/generation_transfer_check.py", "47372706c6ffde2175155de175133e212aae651c", 10197, "Q24 validator r1"),
    ("evidence/generation-transfer-rule/selftest_v1.json", "24c87fa3bf42a69d0b9d7ac7998f781548061f23", 3946, "Q24 validator r1 selftest"),
    ("live_checks/generation_transfer_check_r2.py", "8a4006375750a9e6506994c0e089e4cd80b2ce63", 12770, "Q24 validator r2 (--check fixed)"),
    ("evidence/generation-transfer-rule/selftest_r2.json", "9cca976eeaf0463e7ff16cd8d3501eb52259acd1", 4641, "validator r2 selftest"),
    ("live_checks/generation_transfer_check_r3.py", "f124d8a432927b30f0384e16ae7dd80c6d4bad79", 15303, "Q25 claim_kind r3"),
    ("evidence/generation-transfer-rule/selftest_r3.json", "fb4e9b1cedac2f152bb758da05e61cf93800ea69", 6194, "validator r3 selftest"),
    ("live_checks/generation_transfer_check_r4.py", "32f717a9d4dfadaebd16a6bdaea34c8a289875c5", 18946, "validator r4 (offline judge + pinned controls)"),
    ("evidence/generation-transfer-rule/selftest_r4.json", "d3ce752c7d1192e90618d5ca2501e0ef4fe4c986", 8358, "validator r4 selftest"),
    ("evidence/generation-transfer-rule/ord0279_spec_r1.json", "b88d1889a47a88c7a2def5617335f97e3cc2c09d", 1187, "ORD-0279 spec"),
    ("evidence/generation-transfer-rule/ord0279_audit_r1.json", "a62d1acfcf2971b6178d03ac48365b5932e9e25e", 4176, "ORD-0279 cross-gen audit"),
    ("evidence/generation-transfer-rule/ord0279_spec_r2.json", "3b07b03f7fd16085e62fa4091ff2a3e13eb7631f", 1860, "ORD-0279 spec r2 (claim_kind)"),
    ("evidence/generation-transfer-rule/ord0279_audit_r2.json", "a9774ed4d2f6395fdac174a76577bbd0fbe646b8", 6010, "ORD-0279 audit r2"),
    ("live_checks/evidence_provenance_sweep.py", "32a68f0e08863f639c5693a3f309efe5cf1a4ed6", 5687, "evidence-lineage sweep instrument"),
    ("evidence/commander-evidence-sweep/provenance_r1.json", "be0140fca84f9d909962c09793830e701f432408", 61270, "sweep receipt"),
    ("evidence/t1-postunion-45b0a5e/deploy_green_r1.json", "f1748f4cef8b836e366bd179f7464d67d72e32ea", 74249, "T1 deploy GREEN"),
    ("evidence/t1-postunion-45b0a5e/preflight_preunion_named_gaps_r1.json", "f73844151f6847b8c2a863d52a651d4daae37d4f", 33477, "T1 PRE_UNION refusal"),
    ("evidence/t1-postunion-45b0a5e/preflight_receipt_r1.json", "dc1cf7150b701e3851a6a5132094a7bce6a5d6b4", 34158, "T1 preflight receipt"),
    ("evidence/t1-postunion-45b0a5e/postunion_refused_unauthenticated_probes_r1.json", "0c7a6e33df4ed143a0519bfd90d7b907f8cfe215", 35832, "T1 my own 401 failure"),
    ("evidence/ord0272-k8-f/stale_blob_probe_r1.json", "83642644fc9ad35746fbaa1bc0f134738026d394", 5366, "lane F probe"),
    ("evidence/ord0272-k8-hjp3-crossprocess/K8_XP_readings.json", "fbb154cf9ce598ad1d3a4241b0f2b96181f0037b", 6282, "lane HJ-P3 K8 cross-process"),
    ("evidence/ord0269-0273-gate-v6-e713510/verifier_derivation_d2305848.json", "47eda29379be4538e8001cc794e73253823b3a81", 7628, "red team v6 derivation"),
    ("evidence/ord0279x-hjp3-run/O0279X-2504_readings.json", "24a6a384e357449c7cc8f4de4a0f1d9b2759da63", 9483, "ORD-0279-X readings"),
    ("evidence/ord0272-k8-f/verifier_derivation_d2305848.json", "709f9c8f99314a6b1ce5096e5ee3008b884f3c85", 6211, "0272 K8 two-cell derivation (lane E)"),
    ("evidence/ord0269-0273-gate-v6-e713510/commander_samegen_0269_0273_45b0a5e_d2305848.json", "bd12f1fb08833b98ebd93b83d0a0fa94773bce9d", 3499, "0269/0273 same-generation gate rerun (lane E)"),
    ("evidence/ord0269-0273-gate-v7-45b0a5e/arms-v6-aef5765.json", "af2150a0e8097edd7e1be2c4a720f9e660f60b2a", 22591, "lane D arms (delivered as 16-hex prefix, resolved here)"),
    ("evidence/ord0269-0273-gate-v7-45b0a5e/gate-round-5b549be-with-landing-groups.json", "31eb62fb634a57450b90dbcfebf392f9725e7ed5", 20772, "lane D gate round + landing groups"),
    ("evidence/ord0269-0273-gate-v7-45b0a5e/manifest-5b549be.json", "e2bca6c975a95dcf6972463851ddcc11bda31d0c", 2997, "lane D manifest"),
    ("live_checks/dist_hardlink_scan.py", "ec3a3814bfb794e423e8fe27efe8b0671722de94", 9958, "hardlink scanner (named the white-page mechanism)"),
    ("evidence/commander-dist-hardlink-scan/scan_r1.json", "1ee0d991ff832b53734f67c5836b3c9bf28cf283", 11065, "real scan: 38 files / 35 hits / rc=3"),
    ("evidence/commander-dist-hardlink-scan/selftest_r1.txt", "37c2df0917c81cca4ea0f401d1b35cd33febb2b1", 497, "scanner selftest 5/5 (r1 was 3/5 on fixture bugs)"),
    ("live_checks/receipt_consistency_o0276_r1.py", "6d789e6856873f39b7cff18c7127d26c073e9d47", 5085, "ORD-0276 recomputation ruler"),
    ("evidence/ord0276-hjp3-cells/O0276-2505_readings.json", "3ec966e90bc14f20955ef3d10936a9ce5ca17f6b", 10906, "lane HJ-P3 ORD-0276 readings"),
    ("evidence/ord0276-hjp3-cells/RECEIPT_O0276-2505.md", "20ab8b3b231d10a9fabc6a2876343d8bf6f9ce85", 5718, "lane HJ-P3 ORD-0276 receipt"),
    ("evidence/ord0276-hjp3-cells/o0276_rig.py", "adadc49eda18c4bb9a3dae038daea4f0763f8b5f", 12808, "lane HJ-P3 ORD-0276 rig"),
    ("evidence/ord0276-hjp3-cells/o0276_face.py", "535853a65840e13ca7b544231ce25ea32a428d67", 2984, "lane HJ-P3 ORD-0276 face"),
    ("evidence/ord0276-hjp3-cells/shots_O0276-legacy-surface-clean-port.png", "512ff616c1256113dd7c9d4327554109d213516b", 18210, "lane HJ-P3 ORD-0276 shot (legacy surface)"),
    ("evidence/ord0276-hjp3-cells/shots_O0276-v8-surface-clean-port.png", "23f1ad6723b9b00ba6ceaa74cbad52e50635959f", 69332, "lane HJ-P3 ORD-0276 shot (v8 surface)"),
    ("live_checks/receipt_consistency_o0285_r1.py", "ed25f445392f246be9c63c23458e5a842b7f2066", 3495, "commander 06:5x (0285 rollup recomputation)"),
    ("live_checks/overnight_manifest_r1.py", "0a503cc936404bb6e1c8e4537fc6f0a27c1b8a79", 6635, "commander 07:0x (manifest generator)"),
    ("evidence/commander-overnight-manifest/manifest_r1.md", "fa82ef2674a09e1ec6c5a8025e74cbb319436780", 16386, "commander 07:0x (morning manifest)"),
    ("evidence/ord0285-cmdr-fix-reverify/reverify_d2305848.json", "47424f18eaea96d6977804e92f141c4afc052122", 6297, "lane E bus 5823334130 (ORD-0285 reverify)"),
    ("evidence/ord0288-shape-hjp3/SHAPE_ORD-0288.md", "072077ced7bd27fe1a355645ba8872024bfe6ba6", 7602, "lane HJ-P3 bus 5823596418 (ORD-0288 shape)"),
    ("evidence/ord0288-shape-hjp3/keyless_leg_facts.json", "d95a67195e870ac6bfbb6e6f1b68baf563062bae", 5011, "ENUMERATED(existence only, nobody declared this size): lane HJ-P3"),
    ("evidence/ord0288-shape-hjp3/o0288_facts.py", "a2ff782bfd3282e510fb64efc25493e69a7e50dd", 5163, "ENUMERATED(existence only, nobody declared this size): lane HJ-P3"),
    ("evidence/ord0288-shape-hjp3/route_and_key_facts.txt", "2de176ac963a6f0f26cf828c0f98d60ee049802f", 758, "ENUMERATED(existence only, nobody declared this size): lane HJ-P3"),
    ("evidence/ord0278-0253-on-landed-f86d24e/arms-v3-f86d24e.json", "a598db9d79a4a71ec8bccc6678265ab0d0083c3a", 16308, "ENUMERATED(existence only, nobody declared this size): lane D"),
    ("evidence/ord0278-0253-on-landed-f86d24e/gate-round-f86d24e-with-landing-groups.json", "c8125a918817d63e2a2d35829828b284980ebb4a", 35538, "ENUMERATED(existence only, nobody declared this size): lane D"),
    ("evidence/ord0274-reparent-laneB/ord0274_b2b_mutant_shapes.json", "6d36d7aba7a9da4c10d12522157642d59c888f2f", 6005, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/ord0274_b2b_runtime_tip45b0a5e.json", "e874c5be6920137b412993c700ea245b57e0b16d", 18478, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/ord0274_b2c_runtime_tip45b0a5e.json", "a8e4eff0001f883bf56b14c1ff70e4840dbae04b", 139671, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/ord0274_ident_selftest_tip45.json", "a68e70931b05a2c7f4742c9bd580d9071d6868d1", 3789, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/ord0274_q24_per_cell.json", "15ec650a3553030435a1390affdacfcae5e7038f", 9793, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/ord0274_reparent_ef277b2.patch", "69c3a9b9a28c660ed3396a5eea4dcaec60d26dd3", 3608, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/ord0274_reparent_erratum_ancestry.json", "19ce9e5d710ce679a275d64ad5ff2cfe39e2779a", 2101, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/ord0274_reparent_index.json", "ae8687f9f48605f5e05916bbd1556a92ab8a0eb6", 1583, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/ord0274_reparent_receipt.json", "a8bf252a1c5e45f39031308937e3e611c4cf3109", 21241, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/q274_q24_per_cell.py", "3400100503a46ad0f190a7dcb435316e420c2c89", 9933, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/q274sw_regression_equivalents.json", "542766561fc715a89086e0629b7a73cd27d9c206", 2011, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/reparent_gates.out", "5a468fb5c20d58d760c1607f782afeb8fb9ea906", 3390, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("evidence/ord0274-reparent-laneB/reparent_sweeps.out", "635bfb507c1092864b107eedf9f4e51d1de32fcf", 9468, "ENUMERATED(existence only, nobody declared this size): lane B"),
    ("live_checks/generation_transfer_check_r5.py", "f53fa1271af4f8e021de696f0c10a3e3c7be525f", 23459, "ORD-0283 A7/A9 fix (validator r5)"),
    ("evidence/generation-transfer-rule/selftest_r5.json", "595742f7ff4c65a7c474d8c754c08483404a2e21", 9317, "validator r5 selftest 20 arms"),
    ("live_checks/evidence_provenance_sweep_r3.py", "0dcda650419b159767f1144c19ffcdf245f3e3c0", 10069, "ORD-0283 B2/B3 fix (sweep r3)"),
    ("evidence/commander-instrument-fixes-ord0283/sweep_selftest_r1.txt", "c525d77d0fd1f06cc99b119b4cf64eedc9862ea3", 492, "sweep r3 classify selftest 8/8"),
    ("live_checks/audit_receipt_runner_r2.py", "0807bf6622bbefd5b551f8d2d40880e778a8b447", 4821, "ORD-0283 C8 fix (runner r2 pins ref_tip_read)"),
    ("evidence/commander-instrument-fixes-ord0283/before_after_r1.txt", "d60f9336aada20ae03c1cd419f47b66b580d3bf0", 1311, "before/after proof for A7+A9"),
    ("live_checks/audit_closure_coordinates_r4.py", "56bc2f18e8db144295c1836a489648f9ed3cb165", 10070, "ruler r4 (60 claims)"),
    ("evidence/commander-coordinate-audit/audit_r4_receipt_r1.json", "6dedf4e9be1db10d92c58e280220310467b89044", 24406, "ruler r4 receipt"),
    ("evidence/ord0283-cmdr-instruments-attack/attack_receipt_d2305848.json", "b4bdc3ddec46f0b82e08c7f77bc4fd6f73ed3021", 11900, "lane E ORD-0283 attack receipt"),
    ("live_checks/audit_closure_coordinates_r5.py", "c302dd9f376b5a4ff5e08fd3454030f17a82ee2c", 11384, "ruler r5 (69 claims)"),
    ("evidence/commander-coordinate-audit/audit_r5_receipt_r1.json", "258ac9f4710839f83279503b8b945fd442b98a7d", 28105, "ruler r5 receipt (first with ref_tip_read)"),
    ("live_checks/receipt_consistency_o0282_r1.py", "331a8b5651bb7dc015d9156769e6823431a82f0c", 3731, "ORD-0282 recomputation ruler"),
    ("evidence/ord0282-k8-landgen-f/ord0282_receipt.json", "f93312c9ae1871744b94c54df843b3d59f3a585c", 15288, "lane F landed-generation K8 receipt"),
    ("evidence/ord0282-k8-landgen-f/seam_face_readings.json", "eeedddaa26d7626623046b27de2a214181cdd81b", 20733, "lane F seam raw per-round readings"),
    ("evidence/ord0282-k8-landgen-f/landing_tree_proof.json", "ec98fd76ea580cab38bb4c8293fe4af3b4d096ef", 3214, "lane F tree proof (tip read before export)"),
    ("evidence/ord0282-k8-landgen-f/second_observer_r3_run.json", "b29eb8cd1df7f62535939b40adf4e024fdb9bd1b", 1009, "lane F re-run of my r3 ruler"),
    ("live_checks/bundle_selfreference_check_r1.py", "3878341a4dca3dff2127f6dbf99a131a93f4e4b7", 5009, "snapshot self-reference checker"),
    ("evidence/commander-dist-hardlink-scan/selfcheck_r1.json", "0d4f31938525447386fafdcd31dab1cc43f7c70e", 3210, "3 roots SELF_REFERENTIAL"),
    ("evidence/commander-dist-hardlink-scan/scan_r2_after_fix.json", "e115412298e6f269166f577f2cbb40c950e2bc5f", 345, "re-scan: hits 35 -> 0"),
    ("evidence/ord0281-shape-hjp3/O0281-SHAPE-2506_witness.json", "2e7fa49c1d58acc65cb6081c98caf7c4cd7a9f20", 4242, "lane HJ-P3 ORD-0281 witness"),
    ("evidence/ord0281-shape-hjp3/SHAPE_ORD-0281.md", "9adfeef7b1f9d88dd5bf164119e8c3823b14fb36", 9288, "lane HJ-P3 ORD-0281 shape"),
    ("evidence/ord0281-shape-hjp3/frontend_write_legs.json", "be11a160bee782c03cbeea01c0ff683f70a0e05c", 5375, "lane HJ-P3 write-leg inventory"),
    ("evidence/ord0281-shape-hjp3/o0281_silent_face.py", "741c65388dc81d852774924c9263926e0b6589a6", 3981, "lane HJ-P3 silent-origin face"),
    ("evidence/ord0281-shape-hjp3/offset_check.py", "3a77f40ce1b1875db35974d64dfe6e4f393424ea", 1909, "lane HJ-P3 offset reconciliation"),
)


def main():
    bad = 0
    for path, want, size, why in CLAIMS:
        try:
            meta = rr.get(f"{rr.API}/repos/{rr.REPO}/contents/{path}?ref={rr.BRANCH}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL  {path}\n      read error {type(exc).__name__}: {str(exc)[:90]}")
            bad += 1
            continue
        got, got_size = meta.get("sha"), meta.get("size")
        ok = got == want and got_size == size
        bad += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAIL'}  {path}  [{why}]")
        if not ok:
            print(f"      declared blob {want} size {size}  ||  remote blob {got} size {got_size}")
    print(f"\nclaims={len(CLAIMS)} failing={bad}  branch={rr.BRANCH}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
