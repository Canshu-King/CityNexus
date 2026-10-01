"""ORD-0477 r3 -- is any red on the rebased candidate a red this order caused?

The claim a candidate gets judged on is not "my own arms pass" but "I added no red to the line". The
only honest way to say that on this tree is a set difference against the tip measured the same night,
with the same flags, in a second pass, because the suite has arms that flip between runs (measured here:
the tip's own two passes differ). So:

  stable reds      = present in both passes of a side
  flappers         = present in exactly one pass of a side
  new reds         = candidate reds (either pass) that are in neither tip pass
  gone reds        = tip reds (either pass) that are in neither candidate pass

`verdict NO_NEW_REDS` requires the new-reds set to be empty. Anything else is named, not smoothed.

usage: python ord0477_suite_red_sets_r3.py
"""
from __future__ import annotations

import json
import pathlib
import re

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
OUT = LANE / "run/ord0477_suite_red_sets_r3.json"
LOGS = {
    ("tip", 1): LANE / "run/ord0477_suite_tipcut_7862c6de_pass1.txt",
    ("tip", 2): LANE / "run/ord0477_suite_tipcut_7862c6de_pass2.txt",
    ("candidate", 1): LANE / "run/ord0477_suite_ord0477cut_7862c6de_pass1.txt",
    ("candidate", 2): LANE / "run/ord0477_suite_ord0477cut_7862c6de_pass2.txt",
}
LINE = re.compile(r"^(FAILED|ERROR)\s+(\S+)")


def reds(path: pathlib.Path) -> dict[str, str]:
    found: dict[str, str] = {}
    summary = ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = LINE.match(line)
        if match:
            found[match.group(2)] = match.group(1)
        if " passed" in line and ("failed" in line or "error" in line):
            summary = line.strip()
    found["__summary__"] = summary
    return found


def main() -> int:
    readings = {}
    for (side, index), path in LOGS.items():
        if not path.exists():
            raise SystemExit("REFUSE: %s does not exist yet -- no set difference without both passes" % path)
        readings["%s_pass%d" % (side, index)] = reds(path)

    def arms(key: str) -> set[str]:
        return {k for k in readings[key] if k != "__summary__"}

    tip_union = arms("tip_pass1") | arms("tip_pass2")
    cand_union = arms("candidate_pass1") | arms("candidate_pass2")
    new_reds = sorted(cand_union - tip_union)
    gone_reds = sorted(tip_union - cand_union)
    stable_tip = sorted(arms("tip_pass1") & arms("tip_pass2"))
    stable_cand = sorted(arms("candidate_pass1") & arms("candidate_pass2"))
    flapping_tip = sorted(arms("tip_pass1") ^ arms("tip_pass2"))
    flapping_cand = sorted(arms("candidate_pass1") ^ arms("candidate_pass2"))

    report = {
        "measure": "python -m pytest tests -q --continue-on-collection-errors, two passes per side, "
                   "same interpreter (backend/.venv, 3.12.14), same stripped env, tip snap and candidate tree",
        "summaries": {key: value["__summary__"] for key, value in readings.items()},
        "counts": {
            key: len(arms(key)) for key in readings
        },
        "stable_tip_reds": stable_tip,
        "stable_candidate_reds": stable_cand,
        "flapping_tip": flapping_tip,
        "flapping_candidate": flapping_cand,
        "new_reds_this_order_caused": new_reds,
        "gone_reds_on_the_candidate": gone_reds,
        "verdict": "NO_NEW_REDS" if not new_reds else "NEW_REDS_PRESENT",
    }
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    # the console gets the reading, not the whole set; a GBK console cannot print every node id
    lines = [
        "tip pass1 %d, pass2 %d; candidate pass1 %d, pass2 %d" % (
            len(arms("tip_pass1")), len(arms("tip_pass2")),
            len(arms("candidate_pass1")), len(arms("candidate_pass2")),
        ),
        "stable tip %d, stable candidate %d" % (len(stable_tip), len(stable_cand)),
        "flapping tip %s, flapping candidate %s" % (flapping_tip, flapping_cand),
        "new reds caused by this order: %s" % (new_reds or "none"),
        "verdict %s" % report["verdict"],
        "wrote %s" % OUT,
    ]
    import sys
    sys.stdout.buffer.write(("\n".join(lines) + "\n").encode("utf-8", "replace"))
    return 0 if not new_reds else 1


if __name__ == "__main__":
    raise SystemExit(main())
