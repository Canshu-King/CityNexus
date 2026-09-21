"""Kill evidence for ORD-0191 ⑤ (the provider leg): five sabotages, each owned by a green door.

Run:  python D:/moodle/_qoder_integration_20260919/review/mutate_ord191_leg.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord191/kill-evidence.json

The leg is new, so the mutants are the ones that would make it *look* finished without being
truthful:

* **M6** un-wires the call - the commander's own requested mutant: if removing the resolver does
  not redden gate 1, gate 1 was never measuring the resolver.
* **M7** accepts whatever the search engine returns, so a near match (`遂昌县` for `云合`) becomes
  a canonical identity - the hashing mistake with better credentials.
* **M8** turns a transport failure into a structural `NO_MATCH` - the hard negative the arbiter
  named for this slice ("超时/传输/运行性失败不得变成 NO_MATCH").
* **M9** collapses a tie between two bounded areas, i.e. breaks a rule only when it is convenient.
* **M10** prefers the bare point over the area it marks, which would make an index marker the
  destination and lose the extent the discovery range is supposed to come from.

As in ORD-0167: the named gates are measured green in this same script *before* anything is
mounted, and files are restored from bytes and verified.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
CAPABILITY = TREE / "backend" / "app" / "anywhere_capability.py"
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord191\kill-evidence.json")

FILE = "tests/test_qoder_provider_identity_leg.py"

MUTANTS = [
    {
        "name": "M6 the resolver call is un-wired (gate 1 must fall back to red)",
        "gates": ["test_g2_a_provider_named_county_becomes_hydratable_not_dead"],
        "old": "    provider = _provider_resolution(raw)\n",
        "new": "    provider = None  # M6: the leg exists but is never consulted\n",
    },
    {
        "name": "M7 any provider answer counts as the name",
        "gates": ["test_g6_a_fuzzy_near_match_is_not_an_identity"],
        "old": '    return [place for place in places if _normalise(place.name or "") == wanted]\n',
        "new": "    return list(places)  # M7: a near match is treated as a resolution\n",
    },
    {
        "name": "M8 a transport failure becomes a structural NO_MATCH",
        "gates": ["test_g4_a_timeout_stays_a_named_runtime_failure_and_never_structural"],
        "old": '            method="provider_error",\n            state="RUNTIME_FAILURE",\n',
        "new": '            method="provider_error",\n            state="NO_MATCH",\n',
    },
    {
        "name": "M9 a tie between two bounded areas is collapsed anyway",
        "gates": ["test_g5_two_disagreeing_answers_must_not_pick_one"],
        "old": "    if len(bounded) == 1:\n",
        "new": "    if bounded:\n        bounded = bounded[:1]  # M9: the first bounded answer wins\n",
    },
    {
        "name": "M10 the point marker is preferred over the area it marks",
        "gates": ["test_g10_one_place_two_index_entries_collapses_under_a_named_version"],
        "old": '    is_relation = str(getattr(place, "external_id", "")).startswith("R:")\n    return is_relation and len(extent) == 4\n',
        "new": '    is_relation = str(getattr(place, "external_id", "")).startswith("R:")\n    return (not is_relation) or len(extent) != 4  # M10 inverted\n',
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


def main() -> int:
    original = CAPABILITY.read_bytes()
    text = original.decode("utf-8")
    for mutant in MUTANTS:
        hits = text.count(mutant["old"])
        mutant["anchor_hits"] = hits
        if hits != 1:
            print(f"FATAL: {mutant['name']} anchor hits = {hits}")
            return 1

    all_gates = sorted({gate for mutant in MUTANTS for gate in mutant["gates"]})
    code, out = _run(all_gates)
    print("baseline", code, out.strip().splitlines()[-1] if out.strip() else "")
    if code != 0:
        print("FATAL: a declared target is not green in this baseline; refusing to mount")
        return 1

    report = {"baseline_gates": all_gates, "mutants": []}
    for mutant in MUTANTS:
        patched = text.replace(mutant["old"], mutant["new"], 1)
        CAPABILITY.write_bytes(patched.encode("utf-8"))
        code, out = _run(mutant["gates"])
        CAPABILITY.write_bytes(original)
        restored = _sha(CAPABILITY.read_bytes()) == _sha(original)
        verdict = "KILLED" if code != 0 else "SURVIVED"
        report["mutants"].append(
            {
                "name": mutant["name"],
                "gates": mutant["gates"],
                "anchor_hits": mutant["anchor_hits"],
                "returncode": code,
                "verdict": verdict,
                "restored": restored,
                "first_failure": next(
                    (line.strip()[:160] for line in out.splitlines() if "AssertionError" in line), ""
                ),
            }
        )
        print(f"{verdict:9s} {mutant['name']} rc={code} restored={restored}")
        if not restored:
            print("FATAL: byte restore failed")
            return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    killed = sum(1 for item in report["mutants"] if item["verdict"] == "KILLED")
    print(f"{killed}/{len(MUTANTS)} killed; evidence -> {OUT}")
    return 0 if killed == len(MUTANTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
