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
