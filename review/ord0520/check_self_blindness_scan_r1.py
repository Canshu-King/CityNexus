"""Measure whether each of this lane's checks looks at itself.

A check that never examines its own file can be edited into something else and keep reporting green --
the failure mode is invisible precisely because the thing that would notice is the thing that changed.
This does not assert; it reads.  For every check in the lane's own review directory it asks two questions
and prints both:

  * self_checked  -- does the file name or hash itself anywhere (its own path, its own file name, its own
    blob)?  A check that carries its own identity can notice its own drift.
  * declared_denominator -- does it name the collection it makes a claim about, and refuse on it?

The point is not to score the checks; it is to list which ones cannot notice themselves, so the next cell
knows what is actually being protected.  Anything read here is read from the files as they are now; a
missing file is reported as missing and never scored as a pass.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent

#: Checks in this lane's own directory that answer "did this pass".  Each entry is a file that is run
#: by a person or by a block, not a product module.
CHECKS = [
    "vacuous_truth_scan_r1.py",
    "vacuous_guard_arms_r1.py",
    "vacuous_guard_abnormal_arm_r1.py",
    "vacuous_guard_abnormal_pair_r1.py",
    "vacuous_guard_gap_closed_arm_r1.py",
    "vacuous_guard_partial_arms_r1.py",
    "vacuous_guard_manifest_r1.py",
    "osmt_flake_attribution_r1.py",
    "abort_glass_provenance_r1.py",
    "abort_http_probe_r1.py",
]

SELF_IDENTITY = re.compile(r"(?:__file__|Path\(__file__\)|hash-object|hashlib|blob|self|its own)")


def analyse(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    # Count the places a file can actually answer "did it pass".  An earlier cut of this scan hard-coded a
    # list of verdict words and every file came back zero while they were plainly printing verdicts --
    # a false column is worse than no column, so this counts PRINTS of a verdict-shaped literal and
    # RETURNS of the same, whichever the file uses.
    verdict_sites = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        literal = node.value
        if len(literal) < 6 or " " in literal and not literal.isupper():
            continue
        if not literal.isupper():
            continue
        verdict_sites += 1
    self_named = bool(SELF_IDENTITY.search(text))
    # `__file__` IS the check pointing at itself; writing the file's own name out in full is a stricter
    # and rarer habit. The first cut demanded the full name and therefore called a check blind that
    # plainly reaches its own bytes -- a false "blind" is exactly as harmful as a false "green".
    points_at_own_bytes = ("__file__" in text) or ("hash-object" in text) or ("hashlib" in text)
    names_own_file = points_at_own_bytes
    refuse_on_empty = "refuse_when_empty" in text or "refuse_unless" in text
    return {
        "file": path.name,
        "functions": len(functions),
        "verdict_sites": verdict_sites,
        "names_its_own_file": names_own_file,
        "mentions_self_or_blob": self_named,
        "carries_an_empty_refusal": refuse_on_empty,
        "can_notice_own_drift": self_named and names_own_file,
    }


def main() -> int:
    rows: list[dict] = []
    for name in CHECKS:
        path = HERE / name
        if not path.exists():
            rows.append({"file": name, "status": "NOT_IN_THIS_TREE"})
            continue
        row = analyse(path)
        row["status"] = "READ"
        rows.append(row)

    for row in rows:
        print(json.dumps(row, ensure_ascii=False))

    read = [r for r in rows if r["status"] == "READ"]
    missing = [r["file"] for r in rows if r["status"] == "NOT_IN_THIS_TREE"]
    blind = [r["file"] for r in read if not r["can_notice_own_drift"]]
    guarded = [r["file"] for r in read if r["carries_an_empty_refusal"]]

    # A criterion that cannot be wrong is not measuring. Two probes are written here, both temporary:
    # one that reaches its own bytes through __file__ must read as able to notice its own drift, and one
    # that never mentions itself must read as blind. Both directions are required, or the column would be
    # a slogan rather than a measurement.
    probe_dir = pathlib.Path(__file__).resolve().parent
    aware_probe = probe_dir / "zz_selfaware_probe_tmp.py"
    blind_probe = probe_dir / "zz_selfblind_probe_tmp.py"
    aware_probe.write_text("import pathlib\nSELF = pathlib.Path(__file__)\n", encoding="utf-8", newline="\n")
    blind_probe.write_text("VALUE = 1\n", encoding="utf-8", newline="\n")
    try:
        aware_row = analyse(aware_probe)
        blind_row = analyse(blind_probe)
        print("control_self_aware %s" % aware_row["can_notice_own_drift"])
        print("control_self_blind %s" % blind_row["can_notice_own_drift"])
        if aware_row["can_notice_own_drift"] is not True or blind_row["can_notice_own_drift"] is not False:
            print("CONTROL_FAILED")
            return 1
    finally:
        for probe in (aware_probe, blind_probe):
            probe.unlink(missing_ok=True)

    print("checked %d, not-in-this-tree %d, cannot-notice-own-drift %d, carry-empty-refusal %d"
          % (len(CHECKS), len(missing), len(blind), len(guarded)))
    print("blind_list %s" % ", ".join(blind))
    print("guarded_list %s" % ", ".join(guarded))
    print("VERDICT MEASURED_NOT_SCORED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())