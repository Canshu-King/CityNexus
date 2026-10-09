"""Extend the closure-coordinate audit with everything cited on the ledger/bus after 04:0x.

Why: `audit_closure_coordinates.py` is the instrument that answers "does every coordinate I have quoted in a
CLOSED/LANDED decision still resolve byte-for-byte on the branch".  It only checks what is IN the list, so a
growing list is the point - tonight I cited ~20 new blobs (validator r1-r4, its receipts, the T1 deploy
evidence, and three lane deliveries I accepted) and none of them were covered.
"""
import ast
import io
import re

P = "audit_closure_coordinates.py"
s = io.open(P, encoding="utf-8", newline="\n").read()

NEW = '''    ("live_checks/test_ord0275_publisher_guard_r5.py", "be0978863fbd76f19de7350d6e889b7bf8d38010", 26006, "0275 r5 (vacuous R cell fixed)"),
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
    ("live_checks/evidence_provenance_sweep.py", "PENDING_SWEEP_BLOB", 0, "evidence-lineage sweep instrument"),
    ("evidence/commander-evidence-sweep/provenance_r1.json", "be0140fca84f9d909962c09793830e701f432408", 61270, "sweep receipt"),
    ("evidence/t1-postunion-45b0a5e/deploy_green_r1.json", "f1748f4cef8b836e366bd179f7464d67d72e32ea", 74249, "T1 deploy GREEN"),
    ("evidence/t1-postunion-45b0a5e/preflight_preunion_named_gaps_r1.json", "f73844151f6847b8c2a863d52a651d4daae37d4f", 33477, "T1 PRE_UNION refusal"),
    ("evidence/t1-postunion-45b0a5e/preflight_receipt_r1.json", "dc1cf7150b701e3851a6a5132094a7bce6a5d6b4", 34158, "T1 preflight receipt"),
    ("evidence/t1-postunion-45b0a5e/postunion_refused_unauthenticated_probes_r1.json", "0c7a6e33df4ed143a0519bfd90d7b907f8cfe215", 35832, "T1 my own 401 failure"),
    ("evidence/ord0272-k8-f/stale_blob_probe_r1.json", "83642644fc9ad35746fbaa1bc0f134738026d394", 5366, "lane F probe"),
    ("evidence/ord0272-k8-hjp3-crossprocess/K8_XP_readings.json", "fbb154cf9ce598ad1d3a4241b0f2b96181f0037b", 6282, "lane HJ-P3 K8 cross-process"),
    ("evidence/ord0269-0273-gate-v6-e713510/verifier_derivation_d2305848.json", "47eda29379be4538e8001cc794e73253823b3a81", 7628, "red team v6 derivation"),
    ("evidence/ord0279x-hjp3-run/O0279X-2504_readings.json", "24a6a384e357449c7cc8f4de4a0f1d9b2759da63", 9483, "ORD-0279-X readings"),
'''

marker = 'CLAIMS = (\n'
i = s.index(marker) + len(marker)
# insert after the existing entries: find the closing ")\n" of the tuple
close = s.index("\n)\n", i)
s = s[:close] + "\n" + NEW.rstrip("\n") + s[close:]

ast.parse(s)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
n = len(re.findall(r'^\s*\("', s, re.M))
print("patched", P, "; claim-looking lines:", n)
