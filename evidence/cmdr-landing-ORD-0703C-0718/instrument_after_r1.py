"""ORD-0703 丙: the reshaped hydration doors, twenty-four whole-file rounds, verdict kept.

Same rule the previous instrument learned the hard way: a red must arrive with its sentence, so
every non-green round is written out in full next to the count.  Nothing else may run meanwhile.
"""

from __future__ import annotations

import hashlib
import subprocess
import time
from pathlib import Path

BACKEND = Path(r"D:/moodle/_cmdr_ord0705_wt_1022/backend")
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
HERE = Path(r"D:/moodle/_cmdr_fe_rev_1016")
OUT = HERE / "cmdr_ord0703c_after_1022c.txt"
TARGET = "tests/test_qoder_catalog_hydration.py"
ROUNDS = 24


def main() -> int:
    OUT.write_text("", encoding="utf-8")
    greens = 0
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
        block = "round {0:02d}  rc={1}  wall={2:.1f}s  at {3}\n{4}\n".format(
            index,
            proc.returncode,
            wall,
            time.strftime("%H:%M:%S"),
            "\n".join(summary) or "(no summary line)",
        )
        if proc.returncode == 0:
            greens += 1
        else:
            detail = HERE / "cmdr_ord0703c_red_{0:02d}_1022c.txt".format(index)
            detail.write_text(body, encoding="utf-8")
            block += "  full output -> {0} ({1} bytes, sha1 {2})\n".format(
                detail.name,
                detail.stat().st_size,
                hashlib.sha1(detail.read_bytes()).hexdigest(),
            )
        with OUT.open("a", encoding="utf-8") as handle:
            handle.write(block)
    with OUT.open("a", encoding="utf-8") as handle:
        handle.write(
            "green {0} of {1} rounds; report sha1 {2}\n".format(
                greens, ROUNDS, hashlib.sha1(OUT.read_bytes()).hexdigest()
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
