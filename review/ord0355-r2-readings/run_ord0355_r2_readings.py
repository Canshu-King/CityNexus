"""Run the named ORD-0355 readings and derive every count from the log it came from.

Each run gets its own run_id, its own fresh `_*` database and its own log file.  The receipt
carries `collected`, the terminal summary line and the FAILED nodeids parsed back out of that
same log, so no number quoted in the ledger block is typed from memory.
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
RECEIPTS = ROOT / "_qoder_n2_ord0355_r2/review/ord0355-r2-readings"
TREE = {"cand": ROOT / "_qoder_n2_ord0355_r2", "base": ROOT / "_qoder_n2_ord0355_base7e7"}

MY_MODULE = "tests/test_qoder_ord0355_honest_stay_budget.py"
FLAPPERS = ["tests/test_qoder_anywhere_lock_duration.py", "tests/test_qoder_ord197_four_class_receipt.py"]

RUNS = [
    ("N2R2-A", "cand", ["--collect-only", "-q", MY_MODULE], "_n2r2_a.db"),
    ("N2R2-B", "cand", ["-q", "-p", "no:randomly", MY_MODULE], "_n2r2_b.db"),
    ("N2R2-C", "cand", ["--collect-only", "-q"], "_n2r2_c.db"),
    ("N2R2-D", "cand", ["-q", "-p", "no:randomly"], "_n2r2_d.db"),
    ("N2R2-E", "cand", ["-q", "-p", "no:randomly"], "_n2r2_e.db"),
    ("N2R2-F", "base", ["--collect-only", "-q"], "_n2r2_f.db"),
    ("N2R2-G", "base", ["-q", "-p", "no:randomly"], "_n2r2_g.db"),
    ("N2R2-H", "cand", ["-q", "-p", "no:randomly", *FLAPPERS], "_n2r2_h.db"),
    ("N2R2-I", "base", ["-q", "-p", "no:randomly", *FLAPPERS], "_n2r2_i.db"),
]

COLLECTED = re.compile(r"^(\d+) tests collected in [\d.]+s", re.M)
SUMMARY = re.compile(r"^(\d+) failed.*$", re.M)
FAILED = re.compile(r"^FAILED (\S+::\S+)", re.M)


def one(run_id: str, which: str, args: list[str], db_name: str) -> dict:
    backend = TREE[which] / "backend"
    database = backend / db_name
    if database.exists():
        database.unlink()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        str(p) for p in (backend, backend.parent / "agent-mcp", backend.parent)
    )
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
        env.pop(name, None)

    started = time.time()
    proc = subprocess.run(
        [VENV_PY, "-m", "pytest", *args],
        cwd=str(backend),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if not database.exists():
        # collect-only never opens the file; say so rather than pretend it did.
        pass
    log = RECEIPTS / f"{run_id}.log"
    log.write_text(out, encoding="utf-8", newline="\n")
    bytes_ = log.read_bytes()
    collected = COLLECTED.search(out)
    return {
        "run_id": run_id,
        "tree": which,
        "tree_dir": backend.as_posix(),
        "command": f"{VENV_PY} -m pytest {' '.join(args)}",
        "database": database.as_posix(),
        "database_existed_after_run": database.exists(),
        "exit_code": proc.returncode,
        "wall_seconds": round(time.time() - started, 2),
        "log": log.as_posix(),
        "log_bytes": len(bytes_),
        "log_sha1": hashlib.sha1(bytes_).hexdigest(),
        "collected": int(collected.group(1)) if collected else None,
        "summary_line": (SUMMARY.search(out).group(0).strip() if SUMMARY.search(out) else None),
        "tail_line": next(
            (line.strip("= ") for line in reversed(out.splitlines())
             if " passed" in line or "collected in" in line),
            None,
        ),
        "failed_nodeids": FAILED.findall(out),
    }


def main() -> int:
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    receipts = []
    for spec in RUNS:
        print(f"running {spec[0]} ({spec[1]}) ...", flush=True)
        rec = one(*spec)
        receipts.append(rec)
        print(
            f"  exit={rec['exit_code']} collected={rec['collected']} "
            f"n_failed={len(rec['failed_nodeids'])} sha1={rec['log_sha1'][:12]} "
            f"tail={rec['tail_line']}",
            flush=True,
        )
        (RECEIPTS / "readings.json").write_text(
            json.dumps(receipts, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
