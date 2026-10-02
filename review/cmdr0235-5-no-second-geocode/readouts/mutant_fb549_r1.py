"""Mutant pair for CMDR 02:35 (5): the bounded-fallback gate.

The whole ruling lives in one statement, so both mutants replace that statement and nothing else:

  M1 -> `anchor_grounded_by_leg = False`  the gate can never close the door (pre-ruling behaviour)
  M2 -> `anchor_grounded_by_leg = True`   the door is welded shut (over-tightened)

Each run prints the exact FAILED node id set plus pytest's own summary line, so a kill is a
measured red, not an inference. The product file is restored from the bytes captured before the
mutation and re-hashed after.
"""

import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(os.environ.get("MUT_ROOT", r"D:/moodle/_qoder_seed_ord0489/wt_fb549"))
PROD = ROOT / "backend" / "app" / "integrations" / "discovery" / "real_city.py"
BACKEND = ROOT / "backend"

STATEMENT = (
    "                anchor_grounded_by_leg = any(\n"
    "                    reading.get(\"attempted\")\n"
    "                    and reading.get(\"answered\")\n"
    "                    and str((anchor or {}).get(\"source\") or \"\").startswith(f\"{reading.get('leg')}_\")\n"
    "                    for reading in anchor_leg_readings\n"
    "                )\n"
)
M1 = "                anchor_grounded_by_leg = False  # MUTANT M1\n"
M2 = "                anchor_grounded_by_leg = True  # MUTANT M2\n"

ARMS = {
    "answered_anchor": "tests/test_qoder_city_failure_reasons.py::test_an_answered_anchor_costs_the_fallback_door_nothing",
    "failed_leg": "tests/test_qoder_city_failure_reasons.py::test_a_failed_anchor_leg_still_closes_the_second_ask",
    "journey_state": "tests/test_qoder_city_failure_reasons.py::test_when_no_leg_was_asked_the_fallback_door_is_still_asked",
    "default_fence": "tests/test_qoder_city_failure_reasons.py::test_the_default_resolver_was_not_swapped_and_the_replay_fallback_still_answers",
}
EXPECTED = {
    "M1": {"answered_anchor", "failed_leg"},
    "M2": {"journey_state", "default_fence"},
}


def run(arms: list[str]) -> tuple[set[str], str, int]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--no-header"] + arms,
        cwd=BACKEND, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    failed = {name for name, nodeid in ARMS.items() if f"FAILED {nodeid}" in proc.stdout}
    summary = [line for line in proc.stdout.splitlines() if " passed" in line or " failed" in line]
    return failed, (summary[-1].strip() if summary else "(no summary line)"), proc.returncode


def main() -> int:
    original = PROD.read_bytes()
    text = original.decode("utf-8")
    print(f"statement occurrences in product file: {text.count(STATEMENT)}")
    if text.count(STATEMENT) != 1:
        return 9
    import ast
    ast.parse(text)

    readings: dict[str, set[str]] = {}
    for label, replacement in (("M1", M1), ("M2", M2)):
        PROD.write_bytes(text.replace(STATEMENT, replacement, 1).encode("utf-8"))
        mutated = PROD.read_bytes().decode("utf-8")
        assert "anchor_grounded_by_leg = any(" not in mutated, label
        ast.parse(mutated)
        print(f"\n=== {label} ===")
        failed, summary, rc = run(list(ARMS.values()))
        readings[label] = failed
        print(f"  rc={rc}  summary: {summary}")
        for name in ARMS:
            if name in failed:
                print(f"  RED    {name}  {ARMS[name]}")
            else:
                print(f"  green  {name}")
        PROD.write_bytes(original)
        restored = PROD.read_bytes()
        same = restored == original
        print(f"  restore: sha256[:16] {hashlib.sha256(restored).hexdigest()[:16]} "
              f"vs original {hashlib.sha256(original).hexdigest()[:16]} -> byte-identical={same}")
        if not same:
            return 8

    all_ok = True
    print("\n=== verdict ===")
    for label, expected in EXPECTED.items():
        got = readings[label]
        ok = got == expected
        all_ok = all_ok and ok
        print(f"  {label}: want {sorted(expected)}  got {sorted(got)}  "
              f"-> {'KILLED' if ok else 'MISMATCH'}")
        if ok and got:
            print(f"     survivors under {label}: {sorted(set(ARMS) - got)}")
    status = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--stat", "--", "backend/app/integrations/discovery/real_city.py"],
        capture_output=True, text=True,
    )
    print("\ngit diff --stat for the product file after both restores (should show only my gate edit):")
    print("  " + status.stdout.strip().replace("\n", "\n  "))
    return 0 if all_ok else 8


if __name__ == "__main__":
    raise SystemExit(main())
