"""ORD-0432 reverse arms: each witness must die on its own cause, and not on its siblings.

One throwaway export of `backend data contracts` (never the worktree, so `backend/` commits stay
the only product bytes), three mutations applied one at a time with a full restore between rounds:

  A  twin stops feeding the disruption codes            -> the MAJOR arm must go red
  B  MINOR joins the severity table ("any event")       -> the MINOR guard arm must go red
  C  worst-last instead of worst-first                   -> the unit arm must go red

Round 0 runs the same set unmutated: an arm whose tree was not green before the cut proves nothing.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

WT = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
MUT = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\mut")
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212\ORD0432_REVERSE_ARMS.json")

TARGETS = ["tests/test_dsh_twin_disruption_risk.py", "tests/test_wp06_twin_v2_gate.py"]
ENVELOPE = "app/intelligence/feasibility_envelope.py"
MAIN = "app/main.py"

ARMS = {
    "A_twin_drops_the_disruption_codes": (MAIN,
        "        extra_risk_reason_codes=disruption_risk_codes(unresolved_severities),\n", ""),
    "B_minor_counts_as_a_disruption": (ENVELOPE,
        '    "CRITICAL": ReasonCode.DISRUPTION_CRITICAL,\n',
        '    "CRITICAL": ReasonCode.DISRUPTION_CRITICAL,\n    "MINOR": ReasonCode.DISRUPTION_MAJOR,\n'),
    "C_ordering_dropped": (ENVELOPE,
        '    ordered = sorted(named, key=("CRITICAL", "MAJOR").index)\n',
        '    ordered = sorted(named, key=("CRITICAL", "MAJOR").index)[::-1]\n'),
}


def run_suite(label: str) -> dict:
    proc = subprocess.run(
        [str(PY), "-m", "pytest", *TARGETS, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=str(MUT / "backend"), text=True, encoding="utf-8", errors="replace",
        capture_output=True,
        env={"PATH": str(PY.parent) + ";C:\\Windows\\System32", "PYTHONPATH": ".",
             "SYSTEMROOT": "C:\\Windows",
             "CITYNEXUS_DATABASE_URL": "sqlite:///" + (MUT / f"_arm_{label}.db").as_posix(),
             "PYTHONDONTWRITEBYTECODE": "1"},
    )
    text = proc.stdout + proc.stderr
    red = sorted(set(re.findall(r"^FAILED (\S+)", text, re.M)))
    return {"exit": proc.returncode, "collected": (re.findall(r"(\d+) passed", text) or [None])[0],
            "red": red, "tail": text.strip().splitlines()[-1] if text.strip() else "",
            "traceback": "\n".join(text.splitlines()[-40:])}


def main() -> int:
    if MUT.exists():
        shutil.rmtree(MUT)
    for part in ("backend", "data", "contracts"):
        shutil.copytree(WT / part, MUT / part, ignore=shutil.ignore_patterns("__pycache__"))
    report: dict = {"export": str(MUT), "targets": TARGETS, "arms": {}}
    report["round0_unmutated"] = run_suite("round0")
    assert report["round0_unmutated"]["exit"] == 0, "the export was not green before any cut"

    for name, (rel, needle, repl) in ARMS.items():
        target = MUT / "backend" / rel
        pristine = target.read_text(encoding="utf-8")
        assert pristine.count(needle) == 1, f"{name}: anchor appears {pristine.count(needle)}x"
        target.write_text(pristine.replace(needle, repl), encoding="utf-8", newline="\n")
        report["arms"][name] = run_suite(name)
        target.write_text(pristine, encoding="utf-8", newline="\n")
        assert target.read_text(encoding="utf-8") == pristine, f"{name}: restore failed"

    red_sets = {k: set(v["red"]) for k, v in report["arms"].items()}
    report["red_lists_disjoint_pairs"] = {
        f"{a}|{b}": sorted(red_sets[a] & red_sets[b])
        for a in red_sets for b in red_sets if a < b
    }
    report["each_arm_reddens_at_least_one"] = {k: len(v) for k, v in red_sets.items()}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: {"exit": v["exit"], "red": v["red"]}
                      for k, v in list(report["arms"].items())}, ensure_ascii=False, indent=1))
    print("DISJOINT", json.dumps(report["red_lists_disjoint_pairs"]))
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
