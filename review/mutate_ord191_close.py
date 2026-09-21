"""Kill + cross-isolation evidence for the hydration job endings (ORD-0191 尾巴 A).

Run:  D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_integration_20260919/review/mutate_ord191_close.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord191/close-kill-evidence.json

What this family holds shut, measured on the tree at the SHA printed in the JSON:

* the final job ending used to name `ABANDON_REQUESTED` as a source for a `COMPLETED`/`UNAVAILABLE`
  write.  The transition table allows `ABANDON_REQUESTED -> {ABANDONED, FAILED}` and `mark` checks
  every *declared* source before it touches the store, so the pair raised on **every resolved job**:
  the worker died on its own bookkeeping and the traveller kept a spinner.  The Commander hit the
  UNAVAILABLE half live (贡山县), and it reproduces offline for a catalog city (Beijing).
* the worker's abandon endings ignored whether the write landed, so a request whose own durable move
  was refused by the store left the row open in `RUNNING` forever.

Four sabotages, each representing a shortcut somebody could take instead of the repair:

* K1 un-wire the repair: name both sources again at the final ending  -> the no-dead-worker doors
* K2 the wrong repair: widen the table and name both sources          -> an abandoned job completes
* K3 delete the legal two-step for a request that never landed        -> a job stays open
* K4 stop naming the abandoned outcome                                -> the ending says nothing

Cross-isolation entries then say which doors must stay green under each sabotage, because two node
ids prove two tests exist, not that two assertions are independent.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
MODULE = TREE / "backend" / "app" / "catalog_hydration_operations.py"
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord191\close-kill-evidence.json")
FILE = "tests/test_qoder_catalog_hydration.py"

G1 = "test_a_destination_the_catalog_resolves_closes_its_job_and_not_its_worker"
G2 = "test_a_destination_the_provider_resolves_reaches_the_terminal_write_too"
G3 = "test_an_abandon_from_another_process_resolves_the_terminal_write_as_abandoned"
G4 = "test_an_abandon_whose_own_write_never_landed_still_closes_the_job"
EXISTING = "test_abandon_reports_a_request_not_a_death"
QUEUED_CLOSE = "test_a_job_stopped_before_its_worker_starts_still_closes_itself"
WORKER_WAKES = "test_a_worker_that_wakes_on_an_abandoned_row_closes_it_instead_of_running_it"
RUNTIME_ENDING = "test_a_resolver_that_could_not_be_reached_does_not_make_a_destination_unavailable"
FINGERPRINT = "test_two_open_jobs_for_one_fingerprint_cannot_both_exist"
STRUCTURAL_ENDING = "test_a_hydration_cannot_invent_catalog_rows_it_did_not_fetch"

# --- anchors, each measured to hit exactly once in the file being sabotaged -----------------
FINAL_ENDING = """        _terminate(
            session,
            operation_id,
            COMPLETED if outcome != OUTCOME_NO_REGISTERED_SOURCE else UNAVAILABLE,
            phase="FINALIZING",
"""
FINAL_ENDING_UNWIRED = """        mark(
            session,
            operation_id,
            COMPLETED if outcome != OUTCOME_NO_REGISTERED_SOURCE else UNAVAILABLE,
            from_statuses=(RUNNING, ABANDON_REQUESTED),
            commit=False,
            phase="FINALIZING",
"""
TABLE_ROW = "    ABANDON_REQUESTED: frozenset({ABANDONED, FAILED}),\n"
TABLE_ROW_WIDENED = (
    "    ABANDON_REQUESTED: frozenset({ABANDONED, FAILED, COMPLETED, UNAVAILABLE}),\n"
)
TERMINATE_GUARD = """        to_status,
        from_statuses=(RUNNING,),
"""
TERMINATE_GUARD_WIDE = """        to_status,
        from_statuses=(RUNNING, ABANDON_REQUESTED),
"""
TWO_STEP = """    fresh = read_operation(session, operation_id)
    if fresh is not None and fresh.status == RUNNING:
"""
TWO_STEP_GONE = """    fresh = read_operation(session, operation_id)
    if False:  # K3: a request that never reached the row is simply not dealt with
"""
ABANDON_OUTCOME = '    fields.setdefault("outcome", OUTCOME_ABANDONED)\n'
ABANDON_OUTCOME_DROPPED = '    fields.setdefault("outcome", None)\n'

MUTANTS = [
    {
        "name": "K1 the final ending names both sources again (the shipped defect)",
        "edits": [(FINAL_ENDING, FINAL_ENDING_UNWIRED)],
        # Owned by the two doors that always reach the final ending.  `EXISTING` was declared here
        # first and stayed green under the mount: its abandon usually wins before FINALIZING, so the
        # mutated line is never executed and the flag branch closes the job.  A gate whose subject
        # depends on a thread interleaving cannot own a kill, so the declaration was wrong rather
        # than the mutant weak.
        "gates": [G1, G2],
    },
    {
        "name": "K2 widen the table instead of resolving the race",
        "edits": [(TABLE_ROW, TABLE_ROW_WIDENED), (TERMINATE_GUARD, TERMINATE_GUARD_WIDE)],
        "gates": [G3],
    },
    {
        "name": "K3 the legal two-step for an unrecorded abandon request is deleted",
        "edits": [(TWO_STEP, TWO_STEP_GONE)],
        "gates": [G4],
    },
    {
        "name": "K4 an abandoned job no longer names its own outcome",
        "edits": [(ABANDON_OUTCOME, ABANDON_OUTCOME_DROPPED)],
        "gates": [G3, G4],
    },
]

CROSS = [
    {
        "name": "X1 the dead-worker repair must not disturb the endings that were already legal",
        "edits": [(FINAL_ENDING, FINAL_ENDING_UNWIRED)],
        "expect_red": [G1, G2],
        "expect_green": [RUNTIME_ENDING, FINGERPRINT, STRUCTURAL_ENDING, QUEUED_CLOSE, WORKER_WAKES],
    },
    {
        "name": "X2 widening the table must redden only the abandoned-job verdict",
        "edits": [(TABLE_ROW, TABLE_ROW_WIDENED), (TERMINATE_GUARD, TERMINATE_GUARD_WIDE)],
        "expect_red": [G3],
        "expect_green": [G1, G4, EXISTING],
    },
    {
        "name": "X3 deleting the two-step must not disturb an abandon that did reach the row",
        "edits": [(TWO_STEP, TWO_STEP_GONE)],
        "expect_red": [G4],
        "expect_green": [G1, G2, G3, QUEUED_CLOSE, WORKER_WAKES],
    },
    {
        "name": "X4 the un-named outcome belongs to the abandon endings only",
        "edits": [(ABANDON_OUTCOME, ABANDON_OUTCOME_DROPPED)],
        "expect_red": [G3, G4],
        "expect_green": [G1, G2, STRUCTURAL_ENDING],
    },
]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _run(gates: list[str]) -> tuple[int, str]:
    command = [
        str(PYTHON), "-m", "pytest", "-q", "--tb=line", "-p", "no:randomly",
        *[f"{FILE}::{gate}" for gate in gates],
    ]
    finished = subprocess.run(
        command, cwd=str(TREE / "backend"), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return finished.returncode, (finished.stdout or "") + (finished.stderr or "")


def _failed_node_ids(text: str) -> set[str]:
    return {
        line.split("::")[-1].split(" ")[0].strip()
        for line in text.splitlines()
        if line.startswith("FAILED") and "::" in line
    }


def main() -> int:
    original = MODULE.read_bytes()
    text = original.decode("utf-8")
    for entry in MUTANTS + CROSS:
        for old, _new in entry["edits"]:
            hits = text.count(old)
            if hits != 1:
                print(f"FATAL: anchor hits = {hits} for {old[:60]!r} in {entry['name']}")
                return 1

    targets = sorted({gate for mutant in MUTANTS for gate in mutant["gates"]})
    code, out = _run(targets)
    print("kill baseline", code, out.strip().splitlines()[-1] if out.strip() else "")
    if code != 0:
        print("FATAL: a declared target is not green in this baseline; refusing to mount")
        return 1
    all_gates = sorted(
        {gate for entry in MUTANTS + CROSS for gate in entry.get("gates", []) + entry.get(
            "expect_red", []
        ) + entry.get("expect_green", [])}
    )
    code, out = _run(all_gates)
    print("cross baseline", code, out.strip().splitlines()[-1] if out.strip() else "")
    if code != 0:
        print("FATAL: a declared cross target is not green in this baseline; refusing to mount")
        return 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(TREE), capture_output=True, text=True
        ).stdout.strip(),
        "module": str(MODULE),
        "interpreter": subprocess.run(
            [str(PYTHON), "-V"], capture_output=True, text=True
        ).stdout.strip(),
        "file": FILE,
        "kill_baseline_gates": targets,
        "cross_baseline_gates": all_gates,
        "mutants": [],
        "problems": [],
    }
    for entry in MUTANTS:
        patched = text
        for old, new in entry["edits"]:
            patched = patched.replace(old, new, 1)
        MODULE.write_bytes(patched.encode("utf-8"))
        code, out = _run(entry["gates"])
        MODULE.write_bytes(original)
        restored = _sha(MODULE.read_bytes()) == _sha(original)
        failed = _failed_node_ids(out)
        reddened = [gate for gate in entry["gates"] if gate in failed]
        verdict = "KILLED" if code != 0 and len(reddened) == len(entry["gates"]) else (
            "PARTIALLY_KILLED" if code != 0 else "SURVIVED"
        )
        if verdict != "KILLED":
            report["problems"].append(f"{entry['name']}: {verdict}")
        report["mutants"].append(
            {
                "name": entry["name"],
                "kind": "kill",
                "gates": entry["gates"],
                "reddened": reddened,
                "verdict": verdict,
                "returncode": code,
                "restored": restored,
                "first_failure": next(
                    (line.strip()[:200] for line in out.splitlines() if "Error" in line), ""
                ),
            }
        )
        print(f"{verdict:16s} {entry['name']} rc={code} restored={restored}")
        if not restored:
            print("FATAL: byte restore failed")
            return 1

    for entry in CROSS:
        patched = text
        for old, new in entry["edits"]:
            patched = patched.replace(old, new, 1)
        MODULE.write_bytes(patched.encode("utf-8"))
        gates = sorted(set(entry["expect_red"] + entry["expect_green"]))
        code, out = _run(gates)
        MODULE.write_bytes(original)
        restored = _sha(MODULE.read_bytes()) == _sha(original)
        failed = _failed_node_ids(out)
        missed = [gate for gate in entry["expect_red"] if gate not in failed]
        coupled = [gate for gate in entry["expect_green"] if gate in failed]
        verdict = "KILLED+ISOLATED" if not missed and not coupled else "NOT_ISOLATED"
        if verdict != "KILLED+ISOLATED":
            report["problems"].append(f"{entry['name']}: missed={missed} coupled={coupled}")
        report["mutants"].append(
            {
                "name": entry["name"],
                "kind": "cross",
                "expect_red": entry["expect_red"],
                "expect_green": entry["expect_green"],
                "missed": missed,
                "coupled": coupled,
                "verdict": verdict,
                "returncode": code,
                "restored": restored,
            }
        )
        print(f"{verdict:16s} {entry['name']} coupled={coupled} missed={missed} restored={restored}")
        if not restored:
            print("FATAL: byte restore failed")
            return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    kills = [item for item in report["mutants"] if item["kind"] == "kill"]
    crosses = [item for item in report["mutants"] if item["kind"] == "cross"]
    killed = sum(1 for item in kills if item["verdict"] == "KILLED")
    isolated = sum(1 for item in crosses if item["verdict"] == "KILLED+ISOLATED")
    print(
        f"{killed}/{len(kills)} killed; {isolated}/{len(crosses)} cross-isolated; "
        f"{len(report['problems'])} problem(s); evidence -> {OUT}"
    )
    return 0 if killed == len(kills) and isolated == len(crosses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
