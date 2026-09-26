"""Six attempts per side on the one node whose rate differs (cand 1/3 vs base 0/3).

A startup-path schema step could in principle shift a five-process race, so "unrelated" has to be
measured rather than asserted.  A node is only attributable to the commit if it is red on the
candidate and absent on the base across the repeats.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import time

VENV_PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
ROOT = pathlib.Path("D:/moodle")
OUT = ROOT / "_qoder_n2_ord0355_r2/review/ord0355-r2-readings"
TREE = {"cand": ROOT / "_qoder_n2_ord0355_r2", "base": ROOT / "_qoder_n2_ord0355_base7e7"}
NODE = "tests/test_qoder_anywhere_gates.py::test_g3_xproc_loser_readback_five_processes_one_operation"
FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+::\S+)", re.M)
ATTEMPTS = 6


def one(which: str, attempt: int) -> dict:
    backend = TREE[which] / "backend"
    db = backend / f"_g3_{which}_{attempt}.db"
    if db.exists():
        db.unlink()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        str(p) for p in (backend, backend.parent / "agent-mcp", backend.parent)
    )
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
        env.pop(name, None)
    started = time.time()
    proc = subprocess.run(
        [VENV_PY, "-m", "pytest", "-q", "-p", "no:randomly", NODE],
        cwd=str(backend), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    log = OUT / f"g3_{which}_a{attempt}.log"
    log.write_text(out, encoding="utf-8", newline="\n")
    return {
        "tree": which,
        "attempt": attempt,
        "exit_code": proc.returncode,
        "wall_seconds": round(time.time() - started, 2),
        "red": bool(FAILED.findall(out)) or proc.returncode != 0,
        "log_sha1": hashlib.sha1(log.read_bytes()).hexdigest(),
    }


def main() -> int:
    rows = []
    for attempt in range(1, ATTEMPTS + 1):
        for which in ("cand", "base"):
            row = one(which, attempt)
            rows.append(row)
            print(f"a{attempt} {which:4s} {'RED ' if row['red'] else 'GREEN'} {row['wall_seconds']}s", flush=True)
            (OUT / "g3_readings.json").write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
            )
    for which in ("cand", "base"):
        red = sum(1 for r in rows if r["tree"] == which and r["red"])
        total = sum(1 for r in rows if r["tree"] == which)
        print(f"{which}: {red} red / {total} attempts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
