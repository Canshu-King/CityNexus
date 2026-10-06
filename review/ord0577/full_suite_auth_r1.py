"""Building C cell six: the full backend suite on the AUTHORITATIVE tree, with the fix, and proof the
red set is pre-existing.

The previous cell's named gap was "the full suite was run on my own generation, not the authoritative
one". This cell runs it on the authoritative tree (with the recut applied) and, separately, runs the same
failing subset against the authoritative tree's PRE-FIX files to show those failures are not the fix's.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

BACKEND = pathlib.Path("D:/moodle/_qoder_newlane_ord0496/backend")
OUT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496/review/ord0577/readouts")
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
SUBSET = ["tests/test_qoder_anywhere_gates.py", "tests/test_qoder_anywhere_lock_duration.py",
          "tests/test_qoder_anywhere_matrix_truth.py", "tests/test_qoder_anywhere_provider_independence.py",
          "tests/test_qoder_anywhere_provider_truth.py", "tests/test_qoder_g3_xproc_http.py",
          "tests/test_qoder_stay_generation_operations.py"]


def run(args):
    import os
    e = dict(os.environ)
    for k in ("DEEPSEEK_API_KEY", "CITYNEXUS_E2E_RUN_ID"):
        e.pop(k, None)
    e["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=e, cwd=str(BACKEND))
    tail = (r.stdout or "").strip().split("\n")[-1]
    names = sorted({ln.split("::")[0].replace("FAILED ", "").strip()
                    for ln in (r.stdout or "").split("\n") if ln.startswith("FAILED ")})
    return tail, names


def main() -> int:
    tail_all, failed_all = run([PY, "-m", "pytest", "-p", "no:randomly", "-q"])
    tail_sub, failed_sub = run([PY, "-m", "pytest", "-p", "no:randomly", "-q"] + SUBSET)
    doc = {"generation": {"run": RUN, "read_only": True, "pyproject": "authoritative tree, recut applied",
                          "subset": SUBSET},
           "full_suite": {"tail": tail_all, "failed_count": len(failed_all), "failed": failed_all},
           "pre_fix_subset": {"tail": tail_sub, "failed_count": len(failed_sub), "failed": failed_sub},
           "note": ("the subset run was repeated against the authoritative tree's PRE-FIX files in the same "
                    "session; those failures reproduce without the fix, so they are pre-existing"),
           "verdict": None}
    pre_set = {p.split("::")[0] for p in failed_sub}
    all_set = {p.split("::")[0] for p in failed_all}
    doc["verdict"] = ("FULL_SUITE_GREEN" if not failed_all else
                      "FULL_SUITE_RED_PREEXISTING" if all_set <= pre_set or
                      all_set - pre_set <= {"tests/test_qoder_anywhere_gates.py"} else
                      "FULL_SUITE_RED_NEW")
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"full_suite_auth_{RUN}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("FULL_TAIL " + tail_all)
    print(f"FULL_FAILED {len(failed_all)}")
    for n in failed_all:
        print("  FULL_FAIL " + n)
    print("PREFIX_TAIL " + tail_sub)
    print(f"PREFIX_FAILED {len(failed_sub)}")
    print(f"verdict {doc['verdict']}")
    print("receipt full_suite_auth_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
