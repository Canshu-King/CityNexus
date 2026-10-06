"""Recompute lane F's ORD-0282 verdict from the per-round readings in its own receipt (offline, 9 arms).

Usage: python receipt_consistency_o0282_r1.py [--path <local copy of ord0282_receipt.json>]
Exit 0 = the declared verdict is what the readings give; 1 = disagreement; 2 = artifact unreadable.
Like the o0276 ruler this judges *internal* consistency only: it does not re-run the two processes,
and it signs no `derived_result` (B-1 - closure belongs to the verifier).
"""
import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BLOB = "f93312c9ae1871744b94c54df843b3d59f3a585c"
GUARD_BLOB = "416ea4f210e967130710a900cdecd20e7a1b5eca"
MUTANT_BLOB = "784599fdb406b4242c2d202868b5eefd10861287"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="_incoming_o282.json")
    a = ap.parse_args()
    try:
        d = json.load(open(a.path, encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print("ARTIFACT_UNREADABLE", type(exc).__name__, str(exc)[:120])
        return 2
    rows = d["criterion_4_readings_seam_face"]
    dv = d["criterion_4_derived"]
    g = [r for r in rows if r["state"] == "guard"]
    m = [r for r in rows if r["state"] == "mutant"]
    checks = []

    def ck(name, a_, b_):
        checks.append((name, a_ == b_, a_, b_))

    ck("A01 guard rounds exist (>=3)", len(g) >= 3, True)
    ck("A02 mutant rounds exist (>=3)", len(m) >= 3, True)
    ck("A03 guard A_bytes_survive all true == declared list", [r["A_bytes_survive"] for r in g], dv["guard_A_bytes_survive"])
    ck("A04 mutant A_bytes_survive all false == declared list", [r["A_bytes_survive"] for r in m], dv["mutant_A_bytes_survive"])
    ck("A05 guard B_overwritten_rows == declared", [r["B_overwritten_rows"] for r in g], dv["guard_B_overwrote_rows"])
    ck("A06 mutant B_overwritten_rows == declared", [r["B_overwritten_rows"] for r in m], dv["mutant_B_overwrote_rows"])
    ck("A07 per-round main.py blob matches the state it claims",
       [(r["state"] == "guard") == (r["main_blob_at_round"] == GUARD_BLOB) for r in rows], [True] * len(rows))
    ck("A08 no round ran on the mutant blob while claiming guard",
       any(r["state"] == "guard" and r["main_blob_at_round"] == MUTANT_BLOB for r in g), False)
    ck("A09 detector never blind & pids distinct every round",
       (all(r["detector_selftest_sees_change"] for r in rows), all(r["three_distinct_pids"] for r in rows)),
       (dv["detector_never_blind"], dv["pids_ok"]))
    # the verdict itself, re-derived from scratch (not compared to a string F typed)
    flip = bool(len(g) >= 3 and len(m) >= 3
                and all(r["A_bytes_survive"] for r in g) and all(r["B_overwritten_rows"] == 0 for r in g)
                and all(not r["A_bytes_survive"] for r in m) and all(r["B_overwritten_rows"] >= 1 for r in m))
    ck("A10 verdict recomputed from readings == declared verdict",
       ("FLIP_OBSERVED" if flip else "NO_FLIP_OR_INSUFFICIENT"),
       dv["K8_SEAM_ON_LANDED_GENERATION"])
    bad = 0
    for name, ok, got, want in checks:
        bad += 0 if ok else 1
        print(f"{'GREEN' if ok else 'RED  '}  {name}")
        if not ok:
            print(f"        readings-side {str(got)[:110]}  !=  declared {str(want)[:110]}")
    print(f"\narms={len(checks)} disagreements={bad}")
    print("INTERNAL_CONSISTENCY " + ("ALL_AGREE" if bad == 0 else "MISMATCH"))
    print("SCOPE: recomputation inside one artifact. Does not re-run the two processes, does not confirm the "
          "named throwaway dbs existed, and signs no derived_result (closure belongs to the verifier, B-1).")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
