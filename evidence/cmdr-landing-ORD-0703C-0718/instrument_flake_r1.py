"""ORD-0703 丙: measure the residual flake of the whole hydration file, and keep WHY.

The first six-round instrument filtered the output down to the summary lines and therefore could
not say what round four actually failed on -- an instrument that swallows its own verdict.  This
one writes the full `--tb=short` body of every non-green round to its own file and only then
prints the count, so a red is readable rather than just counted.

Nothing else may run at the same time: a flake measured against a competing pytest process is a
measurement of CPU contention, not of this harness.
"""

from __future__ import annotations

import hashlib
import subprocess
import time
from pathlib import Path

BACKEND = Path(r"D:/moodle/_cmdr_ord0705_wt_1022/backend")
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
HERE = Path(r"D:/moodle/_cmdr_fe_rev_1016")
OUT = HERE / "cmdr_ord0703c_flake_1022b.txt"
TARGET = "tests/test_qoder_catalog_hydration.py"
ROUNDS = 12


def main() -> int:
    rows: list[str] = []
    OUT.write_text("", encoding="utf-8")
    for index in range(1, ROUNDS + 1):
        started = time.time()
        proc = subprocess.run(
            [PY, "-X", "utf8", "-m", "pytest", TARGET, "-q", "--no-header"],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
        body = (proc.stdout or "") + (proc.stderr or "")
        summary = [
            line.rstrip()
            for line in body.splitlines()
            if line.startswith(("FAILED", "ERROR")) or " passed" in line or " failed" in line
        ]
        wall = time.time() - started
        stamp = time.strftime("%H:%M:%S")
        block = "round {0:02d}  rc={1}  wall={2:.1f}s  at {3}\n{4}\n".format(
            index, proc.returncode, wall, stamp, "\n".join(summary) or "(no summary line)"
        )
        if proc.returncode != 0:
            detail = HERE / "cmdr_ord0703c_flake_{0:02d}_1022b.txt".format(index)
            detail.write_text(body, encoding="utf-8")
            block += "  full output -> {0} ({1} bytes, sha1 {2})\n".format(
                detail.name, detail.stat().st_size,
                hashlib.sha1(detail.read_bytes()).hexdigest(),
            )
        with OUT.open("a", encoding="utf-8") as handle:
            handle.write(block)
    with OUT.open("a", encoding="utf-8") as handle:
        handle.write(
            "end sha1 {0}\n".format(hashlib.sha1(OUT.read_bytes()).hexdigest())
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
