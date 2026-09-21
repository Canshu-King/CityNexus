"""Kill + cross-isolation evidence for the ORD-0197 behaviour receipt.

Run:  D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_integration_20260919/review/mutate_ord197_receipt.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord191/receipt-kill-evidence.json

The receipt claims two things that are easy to satisfy accidentally and hard to keep:

* the attempt history reaches the **stored job**, not only the response that rendered it - a job
  outlives its request, which is exactly where an outage becomes invisible;
* **every** attempt survives, not only the one that produced the conclusion.

Three sabotages, each representing the shortcut someone would take:

* N1 the audit helper returns nothing at all (the response still looks complete)
* N2 only the last attempt is kept  -> the two-mirror case silently loses the outage
* N3 an ambiguous answer takes element zero -> a winner is installed by code order
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
CAPABILITY = TREE / "backend" / "app" / "anywhere_capability.py"
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord191\receipt-kill-evidence.json")
FILE = "tests/test_qoder_ord197_four_class_receipt.py"

R1 = "test_r1_a_matched_answer_becomes_a_chaseable_identity_and_stays_split_in_columns"
R1B = "test_r1b_a_matched_answer_without_a_usable_id_or_position_refuses_instead_of_minting"
R2 = "test_r2_an_ambiguous_answer_holds_no_identity_and_replay_does_not_pick_one"
R3 = "test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage"
R4 = "test_r4_a_failed_source_is_named_retryable_and_never_becomes_no_match"
R5 = "test_r5_a_timeout_then_an_empty_answer_concludes_no_match_but_keeps_both_attempts"

AUDIT_HEAD = """    evidence: dict[str, Any] = {}
    observation = resolution.observation
    if isinstance(observation, dict) and observation.get("attempts"):
        evidence["provider_attempts"] = [dict(item) for item in observation["attempts"]]
"""
AUDIT_HEAD_EMPTY = """    evidence: dict[str, Any] = {}
    return evidence  # N1: the response keeps its evidence, the row keeps none
"""
AUDIT_HEAD_LAST_ONLY = """    evidence: dict[str, Any] = {}
    observation = resolution.observation
    if isinstance(observation, dict) and observation.get("attempts"):
        # N2: only the attempt that produced the conclusion is kept.
        evidence["provider_attempts"] = [dict(observation["attempts"][-1])]
"""
AMBIGUOUS_GATE = "    adopted, set_aside = _collapse_point_markers(usable)\n"
AMBIGUOUS_GATE_PICKS = (
    "    adopted = usable[:1]  # N3: element zero wins, whatever the provider refused to rank\n"
    "    set_aside: list[Any] = []\n"
)

MUTANTS = [
    {
        "name": "N1 the durable job keeps no provider audit at all",
        "edits": [(AUDIT_HEAD, AUDIT_HEAD_EMPTY)],
        "gates": [R1, R1B, R2, R3, R4, R5],
    },
    {
        "name": "N2 only the last attempt is kept",
        "edits": [(AUDIT_HEAD, AUDIT_HEAD_LAST_ONLY)],
        "gates": [R5],
    },
    {
        "name": "N3 an ambiguous answer is resolved by taking the first candidate",
        "edits": [(AMBIGUOUS_GATE, AMBIGUOUS_GATE_PICKS)],
        "gates": [R2],
    },
]

CROSS = [
    {
        "name": "X-R1 keeping one attempt instead of none must disturb only the two-mirror audit",
        "edits": [(AUDIT_HEAD, AUDIT_HEAD_LAST_ONLY)],
        "expect_red": [R5],
        "expect_green": [R1, R3, R4],
    },
    {
        "name": "X-R2 installing a winner must not disturb a single-area answer or the empties",
        "edits": [(AMBIGUOUS_GATE, AMBIGUOUS_GATE_PICKS)],
        "expect_red": [R2],
        "expect_green": [R1, R3, R5],
    },
    {
        "name": "X-R3 dropping the audit must not change any conclusion, only its traceability",
        "edits": [(AUDIT_HEAD, AUDIT_HEAD_EMPTY)],
        "expect_red": [R1, R5],
        "expect_green": [],
        "note": "declared with no expected-green doors on purpose: R1B/R2/R3/R4 also redden, so a "
        "claim of independence here would be false. What this entry does record is that the "
        "conclusions themselves (destination_state, canonical, attribution) are untouched by N1 - "
        "the readings that stayed identical are in the evidence JSON.",
    },
]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _run(gates: list[str]) -> tuple[int, str]:
    finished = subprocess.run(
        [str(PYTHON), "-m", "pytest", "-q", "--tb=line", "-p", "no:randomly",
         *[f"{FILE}::{gate}" for gate in gates]],
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


def main() -> int:
    original = CAPABILITY.read_bytes()
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
        CAPABILITY.write_bytes(patched.encode("utf-8"))
        gates = sorted(set(entry.get("gates", []) + entry.get("expect_red", []) + entry.get(
            "expect_green", []
        )))
        code, out = _run(gates)
        CAPABILITY.write_bytes(original)
        restored = _sha(CAPABILITY.read_bytes()) == _sha(original)
        failed = _failed(out)
        kind = "kill" if "gates" in entry else "cross"
        if kind == "kill":
            reddened = [gate for gate in entry["gates"] if gate in failed]
            verdict = "KILLED" if code != 0 and len(reddened) == len(entry["gates"]) else (
                "PARTIALLY_KILLED" if code != 0 else "SURVIVED"
            )
            detail = {"gates": entry["gates"], "reddened": reddened}
        else:
            missed = [gate for gate in entry["expect_red"] if gate not in failed]
            coupled = [gate for gate in entry["expect_green"] if gate in failed]
            verdict = "KILLED+ISOLATED" if not missed and not coupled else "NOT_ISOLATED"
            detail = {"expect_red": entry["expect_red"], "expect_green": entry["expect_green"],
                      "missed": missed, "coupled": coupled}
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
    killed = sum(
        1
        for item in report["mutants"]
        if item["verdict"] in {"KILLED", "KILLED+ISOLATED"}
    )
    total = len(report["mutants"])
    print(f"{killed}/{total} as declared; {problems} problem(s); evidence -> {OUT}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
