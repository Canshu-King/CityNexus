"""Kill evidence for ORD-0167: five sabotages, each owned by a named gate that is green today.

Run:  python D:/moodle/_qoder_integration_20260919/review/mutate_ord167.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord167/kill-evidence.json

The arbiter asked for two reverse mutants on this order (policy rows 11 and 12) and the order's own
shape invites two more:

* **M1** writes `pending:<raw>` back into the identity column - the exact value the freeze sentence
  forbids, and the one a well-meaning "readability" fix would restore.
* **M2** joins the catalog on `destination_pending_key`.  Nothing looks wrong at the call site: the
  token is a string, the column is a string, and the join *works* - which is how a correlation
  id quietly becomes a place.
* **M3** stores the folded text and still claims it is what the user typed.  Enum-wise nothing is
  illegal; the database has just rewritten a witness statement.
* **M4** launders a broken source into a structural `NO_MATCH` - the R1 error in its purest form,
  invisible unless the job is asked which kind of failure it was.

Baseline first, always: every gate named as a target must be **green before the mutant is mounted**
(`e2526b3d` / ORD-0177).  A mutant mounted on an already-red gate is recorded as
`NOT_MEASURABLE_RED_BASE` and does not count as a kill.  Files are restored from raw bytes and
verified by SHA-256; nothing is committed from here.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
CAPABILITY = TREE / "backend" / "app" / "anywhere_capability.py"
HYDRATION = TREE / "backend" / "app" / "catalog_hydration_operations.py"
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord167\kill-evidence.json")

FILE = "tests/test_qoder_pending_destination_identity.py"

MUTANTS = [
    {
        "name": "M1 user text goes back into the identity column (`pending:<raw>`)",
        "file": CAPABILITY,
        "gates": ["test_g1_unresolved_text_never_reaches_the_identity_column"],
        "old": '        canonical_destination_id=None,\n        city_code=None,\n        method="unresolved",\n',
        "new": '        canonical_destination_id=f"{LEGACY_PENDING_PREFIX}{_normalise(raw)}",\n'
        '        city_code=None,\n        method="unresolved",\n',
    },
    {
        "name": "M2 the catalog is joined on the correlation token",
        "file": HYDRATION,
        "gates": ["test_g8_the_pending_key_cannot_buy_a_place_join"],
        "old": '        survey = _survey(session, resolution.canonical_destination_id)\n',
        "new": '        survey = _survey(\n'
        '            session, resolution.canonical_destination_id or row.destination_pending_key\n'
        '        )\n',
    },
    {
        "name": "M3 the folded text is filed as the traveller's exact words",
        "file": CAPABILITY,
        "gates": [
            "test_g6_the_stored_label_is_separate_from_the_normalised_resolver_query",
            "test_g7_punctuation_is_not_lost_when_the_input_is_stored",
        ],
        # The two identity helpers share this return shape, so the anchor starts above it.
        "old": '    has no work behind it - the same mistake, one column further along.\n    """\n\n    raw = str(query if query is not None else "")\n    return {\n        "pending_destination_label": raw,\n',
        "new": '    has no work behind it - the same mistake, one column further along.\n    """\n\n    raw = str(query if query is not None else "")\n    return {\n        "pending_destination_label": _normalise(raw),\n',
    },
    {
        "name": "M4 a broken source is laundered into a structural no-match",
        "file": CAPABILITY,
        "gates": [
            "test_g3_a_broken_source_is_a_runtime_failure_not_a_structural_no_match",
            "test_g3b_a_runtime_failure_ends_the_job_retryable_and_never_structural",
        ],
        "old": '            method="resolver_error",\n            state="RUNTIME_FAILURE",\n            reason_code=REASON_RESOLVER_UNAVAILABLE,\n            retryable=True,\n',
        "new": '            method="resolver_error",\n            state="NO_MATCH",\n            reason_code=REASON_NO_CANONICAL_IDENTITY,\n            retryable=False,\n',
    },
    {
        "name": "M5 a folded legacy label is certified as exact raw",
        "file": CAPABILITY,
        "gates": [
            "test_g10_legacy_pending_rows_migrate_in_place_without_losing_their_ids"
        ],
        "old": '        label, fidelity = survivor, PENDING_LABEL_LEGACY_NORMALIZED\n',
        "new": '        label, fidelity = survivor, PENDING_LABEL_EXACT_RAW\n',
    },
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _run(gates: list[str]) -> tuple[int, str]:
    command = [
        str(PYTHON),
        "-m",
        "pytest",
        "-q",
        "--tb=line",
        "-p",
        "no:randomly",
        *[f"{FILE}::{gate}" for gate in gates],
    ]
    finished = subprocess.run(
        command, cwd=str(TREE / "backend"), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return finished.returncode, (finished.stdout or "") + (finished.stderr or "")


def _assertions(text: str) -> list[str]:
    return [line.strip()[:200] for line in text.splitlines() if "Error" in line or line.startswith("FAILED")]


def main() -> int:
    originals = {}
    for mutant in MUTANTS:
        target = mutant["file"]
        originals.setdefault(target, target.read_bytes())
        text = target.read_text(encoding="utf-8")
        hits = text.count(mutant["old"])
        mutant["anchor_hits"] = hits
        if hits != 1:
            print(f"FATAL: {mutant['name']} anchor hits = {hits}")
            return 1

    report = {"baseline": {}, "mutants": []}
    all_gates = sorted({gate for mutant in MUTANTS for gate in mutant["gates"]})
    code, out = _run(all_gates)
    report["baseline"] = {
        "gates": all_gates,
        "returncode": code,
        "tail": out.strip().splitlines()[-1] if out.strip() else "",
    }
    print("baseline", code, report["baseline"]["tail"])
    if code != 0:
        print("FATAL: a declared mutant target is not green in this baseline; refusing to mount")
        print(_assertions(out))
        return 1

    for mutant in MUTANTS:
        target = mutant["file"]
        text = target.read_text(encoding="utf-8")
        target.write_bytes(
            text.replace(mutant["old"], mutant["new"], 1).encode("utf-8")
        )
        code, out = _run(mutant["gates"])
        target.write_bytes(originals[target])
        restored = _sha(target) == _sha_bytes(originals[target])
        verdict = "KILLED" if code != 0 else "SURVIVED"
        report["mutants"].append(
            {
                "name": mutant["name"],
                "file": str(target.relative_to(TREE)),
                "gates": mutant["gates"],
                "anchor_hits": mutant["anchor_hits"],
                "returncode": code,
                "verdict": verdict,
                "assertions": _assertions(out)[:4],
                "restored": restored,
            }
        )
        print(f"{verdict:9s} {mutant['name']} rc={code} restored={restored}")
        if not restored:
            print("FATAL: byte restore failed")
            return 1

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    killed = sum(1 for item in report["mutants"] if item["verdict"] == "KILLED")
    print(f"{killed}/{len(MUTANTS)} killed; evidence -> {OUT}")
    return 0 if killed == len(MUTANTS) else 1


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


if __name__ == "__main__":
    raise SystemExit(main())
