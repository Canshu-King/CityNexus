"""ORD-0512 lane gate runner r1 -- one command per gate attempt, on this order's own stack.

Why a new file instead of `ord0477_run_gate_r2.py`: that runner's evidence directory and tree are
ORD-0477's, and mixing two orders' readings into one folder is how a lane ends up quoting yesterday's
number at today's bytes.  Same rules, own names:

- the database is named after the run id and starts with an underscore, because
  `app/db/session.py` refuses to reopen an existing file whenever CITYNEXUS_E2E_RUN_ID is set
  (fresh-or-no-run), so a second attempt needs a new name;
- `CITYNEXUS_E2E_AUTHORITATIVE=1` is set here rather than inherited, because the failure this guards
  against was measured on :4933 -- `reuseExistingServer` adopted a neighbour's uvicorn and green tests
  reported on it;
- nothing here opens `D:/moodle/_qoder_preview_20260920/_preview.db`, and no port the phone chain or
  the shared preview owns (:8000, :4781, :4782, :8693) is bound.

usage: python ord0512_run_gate_r1.py <run-id> [playwright args...]
env:   ORD0512_TREE=<export root>            (default ord0512cut_1c785a2d)
       ORD0512_PORTS=<front>,<back>          (default 5150,5151)
"""
import os
import pathlib
import shutil
import subprocess
import sys

EXP = pathlib.Path(os.environ.get("ORD0512_TREE") or r"D:/moodle/_qoder_b_ord0417_20260928/ord0512cut_1c785a2d")
FE = EXP / "frontend"
RUN_DIR = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run")
DB_DIR = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/db")
EVIDENCE = pathlib.Path(os.environ.get("ORD0512_EVIDENCE") or r"D:/moodle/_qoder_b_ord0417_20260928/evidence")
VENV_PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
_pair = (os.environ.get("ORD0512_PORTS") or "5150,5151").split(",")
FRONT_PORT, BACK_PORT = _pair[0].strip(), _pair[1].strip()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    run_id = sys.argv[1]
    extra = sys.argv[2:]
    DB_DIR.mkdir(exist_ok=True)
    db = DB_DIR / f"_e2e_{run_id}.db"
    for suffix in ("", "-wal", "-shm"):
        path = pathlib.Path(str(db) + suffix)
        if path.exists():
            path.unlink()
    env = dict(os.environ)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_ENABLED"):
        env.pop(key, None)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_PORT": FRONT_PORT,
            "CITYNEXUS_BACKEND_PORT": BACK_PORT,
            "CITYNEXUS_PYTHON": VENV_PY,
            "PYTHONPATH": str(EXP / "backend"),
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{db.as_posix()}",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_EVIDENCE_DIR": str(EVIDENCE / "ord0512" / "e2e"),
            # authoritative mode demands the word, not an absence: "unset" is not "off".
            "CITYNEXUS_AI_ENABLED": "false",
        }
    )
    out_dir = EVIDENCE / "ord0512" / "gate"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / f"{run_id}.log"
    npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    cmd = [npm, "run", "test:e2e", "--", *(extra or ["--reporter=line"])]
    header = f"RUN {' '.join(cmd)} cwd {FE} db {db} ports {FRONT_PORT}/{BACK_PORT} tree {EXP}"
    with open(log, "w", encoding="utf-8", errors="replace") as handle:
        handle.write(header + chr(10))
        proc = subprocess.run(cmd, cwd=FE, env=env, stdout=handle, stderr=subprocess.STDOUT)
    rc = proc.returncode
    # Snapshot this run's per-arm readings under its own run id. The suite writes them into one flat
    # directory, so a mutant run that starts ten minutes later overwrites the candidate's reading of the
    # same arm -- and a delivery that ships "the readings" from that directory ships whichever run
    # finished last. Each run keeps its own copy; nothing borrows another run's numbers.
    glass = EVIDENCE / "ord0512" / "e2e" / "ord0512-glass"
    snapshot = EVIDENCE / "ord0512" / "readings" / run_id
    if glass.exists():
        snapshot.mkdir(parents=True, exist_ok=True)
        for arm in glass.glob("reading_*.json"):
            shutil.copy2(arm, snapshot / arm.name)
    tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-60:]
    # the log holds box-drawing characters and Playwright titles; this console is GBK, and printing
    # them raised UnicodeEncodeError *after* a completed run.
    sys.stdout.buffer.write((chr(10).join(tail) + chr(10)).encode("utf-8", "replace"))
    print(f"GATE_RC={rc} RUN_ID={run_id} LOG={log}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
