"""Kill + cross-isolation evidence for the named mobility hard-eligibility gap (ORD-0191 tail E).

Run:  D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_integration_20260919/review/mutate_ord191_gap.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord191/gap-kill-evidence.json

The arbitration's acceptance string was `HYDRATABLE` + `MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`, and the
commander measured that the string had no emitter in `app/` at all - it lived only as a literal inside
one door.  An emitter that prints a word is not the same thing as a rule, so three sabotages each
break a different half of the rule:

* GG1 fire regardless of the facts        -> the empty axis and the unresolved destination both
  start claiming a gap over material that does not exist
* GG2 never fire                          -> the named gap disappears from the answer and the job
* GG3 call any class hard-eligible          -> the gap disappears exactly where it is owed

Cross entries then say which doors must stay green under each, because a shared code path can hide
behind a passing count.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
MODULE = TREE / "backend" / "app" / "anywhere_capability.py"
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord191\gap-kill-evidence.json")
FILE = "tests/test_qoder_mobility_hard_gap.py"

G1 = "test_a_frozen_only_mobility_axis_names_the_gap_and_stays_hydratable"
G2 = "test_the_gap_survives_into_the_stored_job_not_only_the_response"
G3 = "test_an_axis_with_nothing_in_it_is_MISSING_and_claims_no_gap"
G4 = "test_a_live_captured_route_removes_the_gap_it_named"
G5 = "test_a_destination_that_never_resolved_claims_no_hard_gap"
# The fail-closed half needs its own door: the first version of G6 pointed at a gate that never
# reaches the eligibility test at all, so GG4 survived - an owner that cannot see the branch is not
# an owner. This door strips the two new keys from a real report for a destination that does have
# material, which is the only way the silence case is reachable.
G6 = "test_an_eligibility_question_nobody_answered_claims_no_gap"

CONDITION = """    hard_eligible = mobility.get("hard_eligible")
    if (
        resolution.resolved
        and place_count > 0
        and int(mobility.get("candidate_count") or 0) > 0
        and hard_eligible is False
    ):
        hard_gaps.append(GAP_MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE)
"""
CONDITION_ALWAYS = """    if True:  # GG1: the gap is printed whatever the facts say
        hard_gaps.append(GAP_MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE)
"""
CONDITION_NEVER = """    if False:  # GG2: no emitter, only the field
        hard_gaps.append(GAP_MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE)
"""
# GG4: read "the axis never answered the question" as "it answered: not eligible", owned by the
# door that takes the eligibility answer out of a report that really does hold material.
CONDITION_FROM_SILENCE = """        and hard_eligible is False
"""
CONDITION_FROM_SILENCE_BROKEN = """        and hard_eligible is not True
"""
ELIGIBLE = '                "hard_eligible": LIVE_PROVIDER_CAPTURE in classes,\n'
ELIGIBLE_BLIND = '                "hard_eligible": bool(classes),\n'

MUTANTS = [
    {
        "name": "GG1 the gap fires regardless of the facts",
        "edits": [(CONDITION, CONDITION_ALWAYS)],
        "gates": [G3, G5],
    },
    {
        "name": "GG2 the gap is never emitted",
        "edits": [(CONDITION, CONDITION_NEVER)],
        "gates": [G1, G2],
    },
    {
        "name": "GG3 any evidence class counts as hard-eligible",
        "edits": [(ELIGIBLE, ELIGIBLE_BLIND)],
        "gates": [G1, G2, G4],
    },
    {
        "name": "GG4 an unanswered eligibility question is read as a negative",
        "edits": [(CONDITION_FROM_SILENCE, CONDITION_FROM_SILENCE_BROKEN)],
        "gates": [G6],
    },
]

CROSS = [
    {
        "name": "X-G1 treating frozen as eligible must not invent gaps where nothing is held",
        "edits": [(ELIGIBLE, ELIGIBLE_BLIND)],
        "expect_red": [G1, G2, G4],
        "expect_green": [G3, G5],
    },
    {
        "name": "X-G2 never emitting must not change any other field of the answer",
        "edits": [(CONDITION, CONDITION_NEVER)],
        # G4 is in expect_red, not expect_green: it asserts the gap is present *before* the captured
        # route is added, so removing the emitter reddens it too.  My first declaration listed it as
        # independent and the measurement said otherwise - a mis-assigned expectation, not a weak
        # mutant.  What stays genuinely green under this sabotage is the pair of doors that claim
        # nothing: the empty axis and the unresolved destination.
        "expect_red": [G1, G2, G4],
        "expect_green": [G3, G5],
    },
    {
        "name": "X-G3 always emitting must not disturb the eligibility reading itself",
        "edits": [(CONDITION, CONDITION_ALWAYS)],
        # Same correction as above: G4's after-state is "no gap", so printing the gap regardless of
        # the facts is exactly what it catches.
        "expect_red": [G3, G4, G5],
        "expect_green": [G1, G2],
    },
]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _run(gates: list[str]) -> tuple[int, str]:
    finished = subprocess.run(
        [str(PYTHON), "-m", "pytest", "-q", "--tb=line", "-p", "no:randomly",
         *[gate if "::" in gate else f"{FILE}::{gate}" for gate in gates]],
        cwd=str(TREE / "backend"), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return finished.returncode, (finished.stdout or "") + (finished.stderr or "")


def _failed(text: str) -> set[str]:
    return {
        line.split("::")[-1].split(" ")[0].strip()
        for line in text.splitlines()
        if line.startswith("FAILED") and "::" in line
    }


def _reddened(gates: list[str], failed: set[str]) -> list[str]:
    """Which declared gates actually went red, for names that may be file-qualified."""

    return [gate for gate in gates if gate.split("::")[-1] in failed]


def main() -> int:
    original = MODULE.read_bytes()
    text = original.decode("utf-8")
    for entry in MUTANTS + CROSS:
        for old, _new in entry["edits"]:
            hits = text.count(old)
            entry["anchor_hits"] = hits
            if hits != 1:
                print(f"FATAL: anchor hits = {hits} for {old[:60]!r}")
                return 1

    all_gates = sorted(
        {
            gate
            for entry in MUTANTS + CROSS
            for gate in entry.get("gates", []) + entry.get("expect_red", []) + entry.get(
                "expect_green", []
            )
        }
    )
    code, out = _run(all_gates)
    print("baseline", code, out.strip().splitlines()[-1] if out.strip() else "")
    if code != 0:
        print("FATAL: a declared door is not green in this baseline; refusing to mount")
        return 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(TREE), capture_output=True, text=True
        ).stdout.strip(),
        "module": str(MODULE),
        "file": FILE,
        "interpreter": subprocess.run(
            [str(PYTHON), "-V"], capture_output=True, text=True
        ).stdout.strip(),
        "baseline_gates": all_gates,
        "mutants": [],
    }
    problems = 0
    for entry in MUTANTS + CROSS:
        patched = text
        for old, new in entry["edits"]:
            patched = patched.replace(old, new, 1)
        MODULE.write_bytes(patched.encode("utf-8"))
        gates = sorted(
            set(entry.get("gates", []) + entry.get("expect_red", []) + entry.get("expect_green", []))
        )
        code, out = _run(gates)
        MODULE.write_bytes(original)
        restored = _sha(MODULE.read_bytes()) == _sha(original)
        failed = _failed(out)
        kind = "kill" if "gates" in entry else "cross"
        if kind == "kill":
            reddened = _reddened(entry["gates"], failed)
            verdict = "KILLED" if code != 0 and len(reddened) == len(entry["gates"]) else (
                "PARTIALLY_KILLED" if code != 0 else "SURVIVED"
            )
            detail = {"gates": entry["gates"], "reddened": reddened}
        else:
            missed = [gate for gate in entry["expect_red"] if gate.split("::")[-1] not in failed]
            coupled = [gate for gate in entry["expect_green"] if gate.split("::")[-1] in failed]
            verdict = "KILLED+ISOLATED" if not missed and not coupled else "NOT_ISOLATED"
            detail = {
                "expect_red": entry["expect_red"],
                "expect_green": entry["expect_green"],
                "missed": missed,
                "coupled": coupled,
            }
        if verdict not in {"KILLED", "KILLED+ISOLATED"}:
            problems += 1
        report["mutants"].append(
            {"name": entry["name"], "kind": kind, "verdict": verdict, "returncode": code,
             "anchor_hits": entry["anchor_hits"], "restored": restored, "failed": sorted(failed),
             **detail}
        )
        print(f"{verdict:16s} {entry['name']} rc={code} restored={restored}")
        if not restored:
            print("FATAL: byte restore failed")
            return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    done = sum(
        1 for item in report["mutants"] if item["verdict"] in {"KILLED", "KILLED+ISOLATED"}
    )
    print(
        f"{done}/{len(report['mutants'])} as declared; {problems} problem(s); evidence -> {OUT}"
    )
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
