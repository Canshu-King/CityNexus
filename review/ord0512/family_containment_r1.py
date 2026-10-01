"""ORD-0512 -- is the candidate's red set contained in the base's, when the base itself moves?

Two runs of the *same* tip bytes, one instrument, one machine: 15 failed then 16 failed, and five test
titles differ between them (`reach`, `seeded-shape`, a Z2 phone arm in; two ORD-0497 arms out). So
"the candidate has fewer reds than base" is not a claim this lane may make, and neither is "base had
this one red". The only claim the numbers support is containment: every test that is red on the
candidate was red in at least one of the two base runs -- in which case this order's bytes added none.

usage: python ord0512_family_containment_r1.py <base1.log> <base2.log> <candidate.log>
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ord0512_family_diff_r1 import reds, totals  # noqa: E402


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    base1, base2, cand = (reds(path) for path in sys.argv[1:4])
    union = sorted(set(base1) | set(base2))
    report = {
        "base_run_1": {"totals": totals(sys.argv[1]), "red_titles": base1},
        "base_run_2": {"totals": totals(sys.argv[2]), "red_titles": base2},
        "candidate": {"totals": totals(sys.argv[3]), "red_titles": cand},
        "base_union_titles": union,
        "red_on_candidate_not_in_base_union": sorted(set(cand) - set(union)),
        "red_in_base_union_not_on_candidate": sorted(set(union) - set(cand)),
        "base_runs_disagree_on": sorted(set(base1) ^ set(base2)),
    }
    out = r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/family/containment_r1.json"
    io.open(out, "w", encoding="utf-8").write(json.dumps(report, indent=1))
    print("new_red_on_candidate=%d" % len(report["red_on_candidate_not_in_base_union"]))
    print("base_runs_disagree_on=%d" % len(report["base_runs_disagree_on"]))
    print("candidate_titles=%d base_union_titles=%d" % (len(cand), len(union)))
    print(f"WROTE={out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
