# -*- coding: utf-8 -*-
"""Mutation control driver: one expected value at a time, so fail-fast cannot hide the rest."""

import pathlib
import subprocess
import sys

BACKEND = pathlib.Path("D:/moodle/_qoder_yanlugong_0559b/backend")
SRC = BACKEND / "tests" / "test_route_stub_验路工_0559b_r1.py"
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"

MUTATIONS = [
    ("available_modes word list", '"available_modes"] == AVAILABLE_MODES', '"available_modes"] == ["WALK"]'),
    ("choose_for_me flag", '"choose_for_me"] is True', '"choose_for_me"] is False'),
    ("transit duration_min", '"duration_min"] == 31', '"duration_min"] == 32'),
    ("fact key set", 'set(item) == FACT_KEYS', 'set(item) == (FACT_KEYS - {"crs"})'),
    ("modes ordering", "triples == sorted(triples)", "triples == sorted(triples, reverse=True)"),
    ("empty-trip modes list", 'body["modes"] == []', 'body["modes"] == [1]'),
    ("isolation: stored id list", '[item["id"] for item in mine.json()["modes"]] == [stored]',
     '[item["id"] for item in mine.json()["modes"]] == [stored, "nope"]'),
    ("404 envelope code", 'error["code"] == "NOT_FOUND"', 'error["code"] == "GONE"'),
]

original = SRC.read_text(encoding="utf-8")
results = []
try:
    for label, needle, replacement in MUTATIONS:
        assert original.count(needle) >= 1, needle
        mutated = original.replace(needle, replacement, 1)
        temp = BACKEND / "tests" / "_tmp_ylg_b_mut.py"
        temp.write_text(mutated, encoding="utf-8", newline="\n")
        proc = subprocess.run(
            [PY, "-m", "pytest", str(temp), "-p", "no:cacheprovider", "-q", "--tb=no"],
            cwd=str(BACKEND), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        out = proc.stdout.decode("utf-8", "replace")
        collected = [line for line in out.splitlines() if " passed" in line or " failed" in line
                     or "error" in line]
        if not collected:
            # a run that collected nothing proves nothing; refuse to read it as "the
            # assertion did not bite" (observed: a bare file name instead of a path, rc=4)
            raise SystemExit("CONTROL_INSTRUMENT_DEAD rc=%d :: %s :: %s" % (
                proc.returncode, label, out[-300:]))
        failed = [line.split("::")[-1].strip() for line in out.splitlines() if line.startswith("FAILED")]
        results.append((label, proc.returncode, len(failed), failed))
        temp.unlink()
finally:
    SRC.write_text(original, encoding="utf-8", newline="\n")

for label, rc, n_failed, names in results:
    print("MUT %-26s rc=%d failed=%d %s" % (label, rc, n_failed, "; ".join(names)[:120]))
red = sum(1 for _, _, n, _ in results if n >= 1)
print("CONTROLS %d of %d mutations turned the suite red" % (red, len(results)))
print("SOURCE_RESTORED", SRC.read_text(encoding="utf-8") == original)
