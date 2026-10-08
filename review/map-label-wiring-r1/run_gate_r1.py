#!/usr/bin/env python3
"""ORD-0415 lane runner -- start this run's own stack and run the named map-label gates.

Why a runner instead of a bare `npx playwright test`
----------------------------------------------------
Authoritative mode (`CITYNEXUS_E2E_AUTHORITATIVE=1`) is the only mode whose numbers mean anything on
this machine: it refuses a borrowed :8000, refuses a system Python that cannot import the app, and
refuses to reopen a database it did not create (see `docs/E2E_ACCEPTANCE_POLICY.md` and
`frontend/playwrightEnv.ts`). That mode needs six variables to agree with each other plus two live AI
keys absent, and the run is only attributable if the provenance is written down while it runs. This
script does both, and prints which product bytes it measured -- the "before" and "after" readings this
order asks for are two runs of the same gate, and the only honest way to tell them apart is to record
the blob of every file the wiring touches.

    python review/map-label-wiring-r1/run_gate_r1.py --tag before --spec e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts
    python review/map-label-wiring-r1/run_gate_r1.py --tag after  --spec e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts

Ports are chosen and proven free before the servers start; the database path is absolute because a
relative `sqlite:///` resolves against the backend's cwd and would write into a shared tree.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
LANE = ROOT / "review" / "map-label-wiring-r1"
# Raw artefacts go OUTSIDE the worktree: a canonical gate run must leave the checkout holding only the
# files this order changed (`git status --porcelain` is part of the receipt). The numbers themselves are
# summarised into review/map-label-wiring-r1/readings/ by report_readings_r1.py, which does get committed.
ARTEFACTS = ROOT.parent / "evidence"
# The interpreter that can import this app (ortools + fastapi), proven by the suite that runs on it.
VENV_PYTHON = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")
WATCHED = [
    "frontend/src/lib/mapLabelRules.ts",
    "frontend/src/lib/mapStopLabels.ts",
    "frontend/src/components/v8/MapPanel.tsx",
    "frontend/src/components/JourneyMap.tsx",
    "frontend/e2e/_mapLabelRules.ts",
    "frontend/e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts",
    "review/map-label-wiring-r1/stop_rename_fixture_r1.py",
]


def sh(*args: str) -> str:
    return subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8").stdout.strip()


def port_free(port: int) -> bool:
    """Ask the OS twice, differently: a bind proves nothing is holding the port, and netstat proves
    there is no LISTENING socket I am about to confuse with a neighbour's (TIME_WAIT rows name PID 0
    and would be a false red)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        return False
    finally:
        probe.close()
    netstat = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    listening = [
        line for line in netstat.splitlines()
        if f":{port} " in line and "LISTENING" in line and "127.0.0.1" in line
    ]
    return not listening


def pick_ports(count: int, base: int) -> list[int]:
    chosen: list[int] = []
    port = base
    while len(chosen) < count:
        if port_free(port):
            chosen.append(port)
        port += 1
    return chosen


def provenance(tag: str, run_id: str, ports: list[int], db: Path) -> dict:
    head = sh("git", "rev-parse", "HEAD")
    blobs = {}
    worktree = {}
    for path in WATCHED:
        out = subprocess.run(["git", "rev-parse", f"HEAD:{path}"], cwd=str(ROOT), capture_output=True, text=True)
        blobs[path] = out.stdout.strip() if out.returncode == 0 else "absent-at-HEAD"
        # The bytes the run actually served, not the bytes HEAD claims: the before-run deliberately
        # checks three of these files back out to the base line, and a reading that could not tell the
        # two apart would be worthless.
        target = ROOT / path
        worktree[path] = (
            subprocess.run(["git", "hash-object", path], cwd=str(ROOT), capture_output=True, text=True).stdout.strip()
            if target.exists()
            else "absent-on-disk"
        )
    dirty = [line.split()[1] for line in sh("git", "status", "--porcelain").splitlines() if line.strip()]
    return {
        "tag": tag,
        "run_id": run_id,
        "head": head,
        "head_subject": sh("git", "log", "-1", "--format=%h %ad %s", "--date=iso", head),
        "watched_blobs": blobs,
        "watched_worktree_blobs": worktree,
        "dirty_files": dirty,
        "frontend_port": ports[0],
        "backend_port": ports[1],
        "database": str(db),
        "python": str(VENV_PYTHON),
        "python_version": subprocess.run([str(VENV_PYTHON), "--version"], capture_output=True, text=True).stdout.strip(),
        "node_version": subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip(),
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True, help="what this run measured, e.g. before / after")
    parser.add_argument("--spec", action="append", required=True, help="e2e spec path, repeatable")
    parser.add_argument("--grep", default="", help="optional Playwright --grep title filter")
    parser.add_argument("--workers", default="1")
    args = parser.parse_args(argv)

    if not VENV_PYTHON.exists():
        print(json.dumps({"ok": False, "reason": f"no interpreter at {VENV_PYTHON}"}), file=sys.stderr)
        return 3
    run_id = f"ord0415{time.strftime('%H%M%S')}"
    db = BACKEND / f"_{run_id}.db"
    if db.exists():
        db.unlink()
    frontend_port, backend_port = pick_ports(2, 4780)

    env = dict(os.environ)
    # An authoritative run must not carry a live AI key: the refusal is in playwrightEnv.ts, so popping
    # them here is a courtesy to the reader, not the guard itself.
    for key in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "OPENAI_API_KEY"):
        env.pop(key, None)
    evidence = ARTEFACTS / args.tag
    evidence.mkdir(parents=True, exist_ok=True)
    env.update({
        "CITYNEXUS_E2E_AUTHORITATIVE": "1",
        "CITYNEXUS_E2E_PORT": str(frontend_port),
        "CITYNEXUS_BACKEND_PORT": str(backend_port),
        "CITYNEXUS_PYTHON": str(VENV_PYTHON),
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{db.as_posix()}",
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_EVIDENCE_DIR": str(evidence),
        # The runner writes its own report; the specs write into CITYNEXUS_EVIDENCE_DIR.
        "PYTHONIOENCODING": "utf-8",
    })

    record = provenance(args.tag, run_id, [frontend_port, backend_port], db)
    (evidence / f"provenance_{run_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=1), flush=True)

    command = ["node", "node_modules/@playwright/test/cli.js", "test", f"--workers={args.workers}"]
    command += args.spec
    if args.grep:
        command += ["--grep", args.grep]
    started = time.time()
    process = subprocess.run(command, cwd=str(FRONTEND), env=env)
    elapsed = round(time.time() - started, 1)
    summary = {
        "tag": args.tag,
        "run_id": run_id,
        "head": record["head"],
        "command": " ".join(command),
        "exit_code": process.returncode,
        "elapsed_seconds": elapsed,
        "evidence_dir": str(evidence),
        "database_after_run": str(db),
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
    }
    (evidence / f"run_summary_{run_id}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1), flush=True)
    return process.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
