"""ORD-0511: take the three refusal names back out and show the arms go red.

A named refusal is only a gate if removing the name is caught.  Each of the three `reason_code=` lines
added by this order is deleted on its own, the four cells run against that single change, and main.py is
restored and read back between every run.
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import subprocess
from pathlib import Path

WT = Path("D:/moodle/_qoder_n2b_ord0466_20260929/wt")
MAIN = WT / "backend" / "app" / "main.py"
OUT = Path("D:/moodle/_qoder_n2b_ord0511_20260930")
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"

with open(MAIN, encoding="utf-8", newline="") as handle:
    PRISTINE_TEXT = handle.read()
NL = "\r\n" if "\r\n" in PRISTINE_TEXT else "\n"
PRISTINE_SHA = hashlib.sha256(MAIN.read_bytes()).hexdigest()

TARGETS = ["STAY_OPTION_UNKNOWN", "STAY_ITINERARY_CONFLICT", "STAY_NOT_AUTHORITATIVE"]


def _child_env() -> dict[str, str]:
    """The parent environment with the provider key removed, not a hand-made one.

    A minimal dict kills Python on this box (the first take of this script produced runs with no pytest
    summary at all, which is a broken instrument, not a green arm).
    """
    import os

    env = dict(os.environ)
    for key in ("DEEPSEEK_API_KEY", "HTTP_PROXY", "HTTPS_PROXY"):
        env.pop(key, None)
    return env
lines = [f"main.py sha256 before = {PRISTINE_SHA}", f"newline = {NL!r}", ""]

for name in TARGETS:
    pattern = re.compile('[ \\t]*reason_code="' + name + '",\\r?\\n')
    hits = len(pattern.findall(PRISTINE_TEXT))
    mutated = pattern.sub("", PRISTINE_TEXT, count=1)
    assert mutated != PRISTINE_TEXT, f"no `reason_code=\"{name}\"` line found"
    ast.parse(mutated)
    with open(MAIN, "w", encoding="utf-8", newline="") as handle:
        handle.write(mutated)
    proc = subprocess.run(
        [PY, "-m", "pytest", "-q", "-p", "no:randomly", "tests/test_qoder_ord0511_stay_refusal_names.py"],
        cwd=WT / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_child_env(),
    )
    summary = [line for line in proc.stdout.splitlines() if "passed" in line or "failed" in line]
    reds = re.findall(r"FAILED \S+::(\S+)", proc.stdout)
    subprocess.run(["git", "checkout", "--", "backend/app/main.py"], cwd=WT, capture_output=True)
    restored = hashlib.sha256(MAIN.read_bytes()).hexdigest() == PRISTINE_SHA
    lines.append(
        f"### removed `reason_code=\"{name}\"` (present {hits}x in the file, removed 1)"
    )
    lines.append(f"    {summary[-1].strip() if summary else 'NO SUMMARY'}")
    lines.append(f"    red cells: {reds}")
    lines.append(f"    main.py restored byte-identical: {restored}")
    lines.append("")

(OUT / "reason_code_mutants_r1.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
