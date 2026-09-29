"""Requirement 3 asks for the door to be re-run against the commit that already landed, so measure that commit.

`arm_verdicts_real_pair.json` compares the tip against the candidate ref (`6336b0e4...`). The thing the
commander named is the landed merge (`527f471b...`), which is a different tree than the ref it came from,
so it gets its own reading rather than an inference from the ref.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exposure_arm_proposal_r1 import TIP, R4_LANDED, measure, touched_files, verdict  # noqa: E402

WORK = os.path.dirname(os.path.abspath(__file__))


def main():
    tip = measure(TIP, "tip")
    landed = measure(R4_LANDED, "landed")
    v = verdict(tip["cells"], landed["cells"], touched_files(TIP, R4_LANDED))
    ti = sorted({c["id"] for c in tip["cells"]})
    ci = sorted({c["id"] for c in landed["cells"]})
    out = {"tip_rev": TIP, "landed_rev": R4_LANDED, "ruler_blob": tip["ruler_blob"],
           "tip_cells": len(tip["cells"]), "landed_cells": len(landed["cells"]),
           "tip_ids": ti, "landed_ids": ci,
           "id_set_difference_landed_minus_tip": sorted(set(ci) - set(ti)),
           "id_set_difference_tip_minus_landed": sorted(set(ti) - set(ci)),
           "door_view_growth": v["door_as_written_growth_by_file_and_rule"],
           "identity_count_growth": v["by_cell_identity_count_growth"],
           "identity_set_new_ids": v["identity_set_only_new_ids"],
           "cells_already_on_the_line_in_touched_files":
               {k: n for k, n in v["cells_already_on_the_line_in_touched_files"].items() if n},
           "candidate_touched_file_count": len(v["candidate_touched_files"])}
    io.open(os.path.join(WORK, "landed_recheck_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
