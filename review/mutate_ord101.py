"""Kill evidence for ORD-0101: four sabotages, each owned by a named gate.

Run:  python review/mutate_ord101.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord101/kill-evidence.json

The order's shape is "add a name, change no sentence", so the mutants attack both halves:
collapse the two conditions into one name (K1), stop forwarding the name at all (K2),
**reword the message** instead - which the pre-existing gate in
`test_qoder_city_catalogue.py`'s sibling file quotes and must therefore catch (K3), and
finally emit the key unconditionally, which is the version that would look like rigour and
teach nothing (K4). Files are restored from raw bytes and verified by SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
SERVICES = TREE / "backend" / "app" / "services.py"
MAIN = TREE / "backend" / "app" / "main.py"
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord101\kill-evidence.json")

NEW_FILE = "tests/test_qoder_catalog_reason_code.py"
OLD_FILE = "tests/test_qoder_beijing_catalogue.py"

MUTANTS = [
    {
        "name": "K1 one name for two different conditions",
        "file": SERVICES,
        "test": NEW_FILE,
        "old": "            reason_code=CATALOG_EMPTY if not places else CATALOG_INSUFFICIENT,",
        "new": "            reason_code=CATALOG_INSUFFICIENT,",
        "gate": "test_an_empty_catalog_says_so_instead_of_borrowing_the_other_refusal",
    },
    {
        "name": "K2 the name is computed but never forwarded to the envelope",
        "file": MAIN,
        "test": NEW_FILE,
        "old": '        reason = getattr(exc, "reason_code", None)\n        if reason:',
        "new": "        reason = None\n        if reason:",
        "gate": "test_an_empty_catalog_says_so_instead_of_borrowing_the_other_refusal",
    },
    {
        "name": "K3 the message is reworded instead of the refusal being named",
        "file": SERVICES,
        "test": OLD_FILE,
        "old": '            "No feasible plan candidates satisfy the journey constraints" + detail,\n',
        "new": '            "catalog shortfall, see reason_code",\n',
        "gate": "test_a_city_with_nothing_in_the_catalogue_is_still_refused_by_name",
    },
    {
        "name": "K4 every error grows the key, named or not",
        "file": MAIN,
        "test": NEW_FILE,
        "old": "    if reason_code:\n        body[\"reason_code\"] = reason_code\n",
        "new": '    body["reason_code"] = reason_code or "UNSPECIFIED"\n',
        "gate": "test_a_refusal_that_is_not_about_the_catalog_grows_no_name",
    },
]


def run_gate(test_file: str, gate: str) -> tuple[int, str]:
    completed = subprocess.run(
        [str(PYTHON), "-m", "pytest", test_file, "-q", "--no-header", "-k", gate,
         "-p", "no:cacheprovider"],
        cwd=TREE / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode, completed.stdout + completed.stderr


def main() -> int:
    originals = {path: path.read_bytes() for path in (SERVICES, MAIN)}
    digests = {path: hashlib.sha256(raw).hexdigest() for path, raw in originals.items()}
    results = []
    try:
        for mutant in MUTANTS:
            path = mutant["file"]
            text = originals[path].decode("utf-8")
            hits = text.count(mutant["old"])
            if hits != 1:
                results.append(
                    {"mutant": mutant["name"], "verdict": "NOT-MEASURED", "anchor_hits": hits}
                )
                continue
            path.write_bytes(text.replace(mutant["old"], mutant["new"]).encode("utf-8"))
            code, output = run_gate(mutant["test"], mutant["gate"])
            summary = [l for l in output.splitlines() if " passed" in l or " failed" in l]
            results.append(
                {
                    "mutant": mutant["name"],
                    "owner_gate": f'{mutant["test"]}::{mutant["gate"]}',
                    "killed": code != 0,
                    "summary": summary[-1] if summary else output[-200:],
                }
            )
            path.write_bytes(originals[path])
    finally:
        for path, raw in originals.items():
            path.write_bytes(raw)

    payload = {
        "restored": all(
            hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in digests.items()
        ),
        "cases": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["restored"] and all(item.get("killed") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
