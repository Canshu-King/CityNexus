"""ORD-0411 / ORD-0402 tail: do the two arms still bite, or are they green because nothing fails?

Run it against an export of the candidate that has no repository above it:

    python review/ord0402-readouts/control_reds_r1.py <candidate-export-root> [<pytest-interpreter>]

(the root is where the copied mutant trees are built, so it must be writable and must NOT sit inside
a checkout - see EXPORT_SHAPE_NOTE_R1.txt for why that distinction is the whole point of this file).
Each mutant is one copied tree with one deliberate break; a mutant that comes back green means the
arm no longer measures what its name says.  The unmutated control has to be green, and the readout
records `git rev-parse --show-toplevel` inside it, so a green that came from a discovered repository
is visible as one.

The first version of this driver reported every arm as exit 1 with no output, including the control:
a hand-made environment with no TEMP in it, which the test process needs before it can build a
database.  The whole os.environ is passed through now with the dead proxy variables removed, and the
raw tails of both streams are kept, so a future instrument failure reads as one instead of a result.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

CAND = pathlib.Path(sys.argv[1]).resolve()
WORK = (
    pathlib.Path(sys.argv[2]).resolve()
    if len(sys.argv) > 2
    else CAND.parent / f"{CAND.name}_mutants"
)
PY = sys.argv[3] if len(sys.argv) > 3 else sys.executable

# Five copies of a whole tree get written under WORK, so two rules are enforced here rather than
# trusted to the caller.  The first one is not hypothetical: an earlier version of this file took a
# single directory as both the source tree and the destination parent, `copytree` then copied the
# source into itself, and the recursion filled the volume to 0 bytes free.
assert WORK != CAND and CAND not in WORK.parents, (
    f"refusing to build mutant trees inside the source tree ({CAND} -> {WORK}): copytree would "
    "recurse into its own output"
)
FREE_BYTES_MINIMUM = 2 * 1024**3
free = shutil.disk_usage(WORK.parent if WORK.parent.exists() else CAND.parent).free
assert free > FREE_BYTES_MINIMUM, (
    f"{free / 1024**3:.1f} GiB free on this volume, {FREE_BYTES_MINIMUM / 1024**3:.0f} GiB needed "
    "for the five copied trees - ABORTed before writing anything"
)

MODULE = "backend/tests/test_qoder_ord0402_recycle_bin.py"
ARM_BYTES = "test_the_existing_list_door_was_not_touched_down_to_its_bytes"
ARM_SEAM = "test_the_panels_one_constant_and_field_names_match_the_route_that_was_landed"


def environment(tree: pathlib.Path) -> dict[str, str]:
    env = dict(os.environ)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(name, None)
    env["PYTHONPATH"] = str(tree)
    return env


def run(tree: pathlib.Path, arm: str) -> dict[str, object]:
    out = subprocess.run(
        [PY, "-X", "utf8", "-m", "pytest", f"{MODULE}::{arm}", "-q", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(tree),
        env=environment(tree),
        check=False,
    )
    lines = out.stdout.splitlines()
    return {
        "exit_code": out.returncode,
        "verdict_line": next((line for line in reversed(lines) if " passed" in line or " failed" in line), ""),
        "assertion": next((line for line in reversed(lines) if line.startswith("E   ")), "")[:240],
        "stdout_tail": lines[-6:],
        "stderr_tail": out.stderr.splitlines()[-4:],
    }


def copy(name: str) -> pathlib.Path:
    tree = WORK / name
    if tree.exists():
        shutil.rmtree(tree)
    shutil.copytree(CAND, tree)
    return tree


def edit(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, (str(path), text.count(old))
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def main() -> None:
    results: dict[str, object] = {}

    tree = copy("mut_none")
    results["control_unmutated"] = {
        "tree": str(tree),
        "git_above": subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=str(tree),
            check=False,
        ).stderr.strip(),
        "bytes_arm": run(tree, ARM_BYTES),
        "seam_arm": run(tree, ARM_SEAM),
    }

    tree = copy("mut_one_word_in_the_door")
    edit(
        tree / "backend/app/main.py",
        "ORD-0383 slice 1 keeps this door to one rule",
        "ORD-0383 slice 1 keeps this door to two rules",
    )
    results["M1_one_word_in_the_door"] = {
        "break": "backend/app/main.py, inside list_journeys: one rule -> two rules",
        "bytes_arm": run(tree, ARM_BYTES),
    }

    tree = copy("mut_record_tampered")
    artifact = tree / "review/ord0402-readouts/LIST_DOOR_BASELINE_r2.json"
    record = json.loads(artifact.read_text(encoding="utf-8"))
    before = record["segment_lf"]
    record["segment_lf"] = before.replace("keeps this door to one rule", "keeps this door to one RULE")
    assert record["segment_lf"] != before, "M2 would be vacuous: the string is not in segment_lf"
    artifact.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    results["M2_baseline_record_tampered"] = {
        "break": "LIST_DOOR_BASELINE_r2.json: segment_lf edited (one rule -> one RULE), segment_sha256 left as it was",
        "bytes_arm": run(tree, ARM_BYTES),
    }

    tree = copy("mut_contract_drops_bin_state")
    edit(tree / "contracts/openapi.yaml", "          required: [deleted_at, bin_state]\n", "          required: [deleted_at]\n")
    edit(tree / "contracts/openapi.yaml", "            bin_state: {type: string, enum: [IN_RECYCLE_BIN]}\n", "")
    results["M3_contract_drops_bin_state"] = {
        "break": "contracts/openapi.yaml: RecycleBinJourney stops declaring bin_state",
        "seam_arm": run(tree, ARM_SEAM),
    }

    tree = copy("mut_generated_drifts")
    edit(tree / "frontend/src/generated/api.ts", '            bin_state: "IN_RECYCLE_BIN";\n', '            bin_state_local: "IN_RECYCLE_BIN";\n')
    results["M4_generated_client_drifts"] = {
        "break": "frontend/src/generated/api.ts: the component's field is renamed",
        "seam_arm": run(tree, ARM_SEAM),
    }

    out = WORK / "CONTROL_REDS.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    summary = {
        key: {
            arm: value[arm]["verdict_line"] or value[arm]["stdout_tail"][-1:]
            for arm in value
            if isinstance(value[arm], dict) and "exit_code" in value[arm]
        }
        for key, value in results.items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"readout: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
