"""Recompute lane E's ORD-0285 rollup from the measured sub-fields of its own receipt (6 arms).

Why: the receipt's `summary.derived_result` is a hand-written string and there is no top-level
machine rollup - a reader has to re-aggregate the three instrument blocks to check the sentence.
This ruler does that aggregation, so the verifier's signature is at least *internally* derivable.
It signs nothing itself and re-runs nothing: it only asks "do the readings in this file say what the
summary says they say?"

Usage: python receipt_consistency_o0285_r1.py <local copy of reverify_d2305848.json>
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BLOB = "47424f18eaea96d6977804e92f141c4afc052122"   # evidence/ord0285-cmdr-fix-reverify/reverify_d2305848.json
SUMMARY = "FIXES_VERIFIED (4/4) + NO_REGRESSION + 2 NEW SURFACES CLOSED"


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 5
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    A, B, C = d["instrument_A_r5"], d["instrument_B_r3"], d["instrument_C_runner_r2"]
    checks = [
        ("A01 A7 measured on r5 is a refusal (rc=4, CLAIM_WITH_NO_CELLS)",
         A["A7_both_directions"]["after_r5_measured_now"]["rc"] == 4
         and A["A7_both_directions"]["after_r5_measured_now"]["derived"] == "CLAIM_WITH_NO_CELLS"),
        ("A02 A9 camelCase cannot escape, and the key name is read back",
         A["A9_both_directions"]["after_r5_measured_now"]["rc"] == 4
         and A["A9_both_directions"]["after_r5_measured_now"].get("claim_key_used") == "crossGenerationClaim"),
        ("A03 all four bites carry a measured fixed-true field",
         sum([A["A7_both_directions"]["after_r5_measured_now"]["rc"] == 4,
              A["A9_both_directions"]["after_r5_measured_now"]["rc"] == 4,
              bool(B["old_vectors_rerun_via_classify"].get("B2_16hex_only", {}).get("fixed")),
              bool(C["C8_ref_tip_pinned"]["measured"].get("runner_receipts_have_ref_tip_read"))]) == 4),
        ("A04 no_regression: selftest all true and the arm count is 20",
         A["selftest"]["all_true"] is True and A["selftest"]["arms"] == 20),
        ("A05 the two new surfaces exist as MEASURED blocks, not prose",
         "new_surface_1_selftest_dispatch" in C and "my_run_1_tip" in C["C8_ref_tip_pinned"]["measured"]),
        ("A06 the verifier's two runs pinned DIFFERENT tips (so the pin is not a constant)",
         C["C8_ref_tip_pinned"]["measured"]["my_run_1_tip"] != C["C8_ref_tip_pinned"]["measured"]["my_run_2_tip"]),
        ("A07 summary string is the one this ruler was written against",
         d["summary"].get("derived_result") == SUMMARY),
    ]
    bad = 0
    for name, ok in checks:
        bad += 0 if ok else 1
        print(("GREEN  " if ok else "RED    ") + name)
    print("")
    print("arms=%d disagreements=%d" % (len(checks), bad))
    print("rollup in summary is INTERNALLY SUPPORTED" if bad == 0 else "ROLLUP_NOT_SUPPORTED_BY_READINGS")
    print("SCOPE: recomputation of one artifact's own fields. It does not re-run lane E's vectors against the")
    print("       instruments, and it adds no signature: the derived_result under summary remains lane E's.")
    print("NOTE:  a top-level machine-derived rollup field would make this ruler unnecessary - suggested for")
    print("       the next verifier receipt (it changes no verdict here).")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
