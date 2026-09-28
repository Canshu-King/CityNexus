"""ORD-0417 lane gate runner r1 -- one command per gate attempt, with the run-id rule obeyed.

Why this exists: `app/db/session.py:41` refuses to reopen an existing database whenever
CITYNEXUS_E2E_RUN_ID is set, so a second attempt on the same file dies before a single product
assertion runs -- a red that says nothing about the product.  The order's own instruction is to issue a
new run id, so this runner names the database after the run id and deletes any stale file for that
name before starting.  Nothing here touches another lane's database, and nothing touches
D:/moodle/_qoder_preview_20260920/_preview.db (that one is opened read-only by the bundle stack).

Ports are this lane's own: :4834 frontend, :4835 backend.  :8000 is never started here, and :4781 /
:4782 / :8693 (the phone chain and the shared preview) are never rebound.

usage: python ord0417_run_gate_r1.py <run-id> [playwright args...]
"""
import os
import pathlib
import shutil
import subprocess
import sys

EXP = pathlib.Path(os.environ.get("ORD0417_TREE") or r"D:/moodle/_qoder_b_ord0417_20260928/exp2")
FE = EXP / "frontend"
DB_DIR = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/db")
EVIDENCE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence")
VENV_PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
# The baseline tree runs on its own pair of ports so a tip reading and a candidate reading can never
# be mistaken for each other, and neither borrows :8000, :4781, :4782 or :8693.
_is_baseline = "exp_tip" in str(EXP)
FRONT_PORT = "4836" if _is_baseline else "4834"
BACK_PORT = "4837" if _is_baseline else "4835"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    run_id = sys.argv[1]
    extra = sys.argv[2:]
    db = DB_DIR / f"e2e_{run_id}.db"
    for suffix in ("", "-wal", "-shm"):
        p = pathlib.Path(str(db) + suffix)
        if p.exists():
            p.unlink()
    DB_DIR.mkdir(exist_ok=True)
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    env.update({
        "CITYNEXUS_E2E_PORT": FRONT_PORT,
        "CITYNEXUS_BACKEND_PORT": BACK_PORT,
        "CITYNEXUS_PYTHON": VENV_PY,
        "PYTHONPATH": str(EXP / "backend"),
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{db.as_posix()}",
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_EVIDENCE_DIR": str(EVIDENCE / "e2e"),
    })
    out_dir = EVIDENCE / "gate"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / f"{run_id}.log"
    npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    cmd = [npm, "run", "test:e2e", "--", *(extra or ["--reporter=line"])]
    print("RUN", " ".join(cmd), "cwd", FE, "db", db)
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        p = subprocess.run(cmd, cwd=FE, env=env, stdout=fh, stderr=subprocess.STDOUT)
    rc = p.returncode
    tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
    print("\n".join(tail))
    print(f"GATE_RC={rc} RUN_ID={run_id} LOG={log} DB={db}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
