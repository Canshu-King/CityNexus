"""ORD-0477 lane gate runner r1 -- one command per gate attempt, on this order's own stack.

Why this exists and is not a copy of the ORD-0417 runner: `app/db/session.py` refuses to reopen an
existing database whenever CITYNEXUS_E2E_RUN_ID is set, so a second attempt on the same file dies
before a single product assertion runs.  This runner names the database after the run id and removes
any stale file for that *own* name first.  It never opens D:/moodle/_qoder_preview_20260920/_preview.db
and never rebinds :8000, :4781, :4782 or :8693 (the phone chain and the shared preview).

Ports: :4910 frontend, :4911 backend by default; ORD0477_PORTS=<front>,<back> overrides so a
candidate reading and a subtraction reading can never be mistaken for each other.

usage: python ord0477_run_gate_r1.py <run-id> [playwright args...]
"""
import os
import pathlib
import shutil
import subprocess
import sys

EXP = pathlib.Path(os.environ.get("ORD0477_TREE") or r"D:/moodle/_qoder_b_ord0417_20260928/ord0477")
FE = EXP / "frontend"
RUN_DIR = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run")
DB_DIR = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/db")
EVIDENCE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence")
VENV_PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
_pair = (os.environ.get("ORD0477_PORTS") or "4910,4911").split(",")
FRONT_PORT, BACK_PORT = _pair[0].strip(), _pair[1].strip()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    run_id = sys.argv[1]
    extra = sys.argv[2:]
    DB_DIR.mkdir(exist_ok=True)
    db = DB_DIR / f"e2e_{run_id}.db"
    for suffix in ("", "-wal", "-shm"):
        p = pathlib.Path(str(db) + suffix)
        if p.exists():
            p.unlink()
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    env.update(
        {
            "CITYNEXUS_E2E_PORT": FRONT_PORT,
            "CITYNEXUS_BACKEND_PORT": BACK_PORT,
            "CITYNEXUS_PYTHON": VENV_PY,
            "PYTHONPATH": str(EXP / "backend"),
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{db.as_posix()}",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_EVIDENCE_DIR": str(EVIDENCE / "ord0477" / "e2e"),
        }
    )
    out_dir = EVIDENCE / "ord0477" / "gate"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / f"{run_id}.log"
    npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    cmd = [npm, "run", "test:e2e", "--", *(extra or ["--reporter=line"])]
    header = f"RUN {' '.join(cmd)} cwd {FE} db {db} ports {FRONT_PORT}/{BACK_PORT} tree {EXP}"
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        fh.write(header + chr(10))
        p = subprocess.run(cmd, cwd=FE, env=env, stdout=fh, stderr=subprocess.STDOUT)
    rc = p.returncode
    tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-45:]
    # the log holds box-drawing characters and Playwright titles; this console is GBK, and printing them
    # raised UnicodeEncodeError *after* a completed run, replacing a real exit code with a traceback.
    sys.stdout.buffer.write((chr(10).join(tail) + chr(10)).encode("utf-8", "replace"))
    print(f"GATE_RC={rc} RUN_ID={run_id} LOG={log} DB={db} PORTS={FRONT_PORT}/{BACK_PORT}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
