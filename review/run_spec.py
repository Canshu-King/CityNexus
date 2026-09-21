"""Run one Playwright spec (or the whole suite) against an authoritative throwaway stack.

A fresh run id per attempt: backend/app/db/session.py refuses to reopen an existing e2e
database, so a reused id kills the run before any node speaks.
"""

import os
import subprocess
import sys
import time

# Redirecting this script's stdout to a file makes Python pick the console codepage (gbk here), and
# the tail print then dies on Playwright's box-drawing characters *after* a run that already passed --
# which reads as a failed run with no numbers.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = "D:/moodle/_qoder_integration_20260919"


def main() -> int:
    args = sys.argv[1:]
    listing = args and args[0] == "--list"
    if listing:
        args = args[1:]
    target = args[0] if args else "e2e/"
    port = int(args[1]) if len(args) > 1 else 4510
    extra = " ".join(args[2:])
    run_id = f"{'lst' if listing else 'run'}{int(time.time()) % 1000000:06d}"
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_E2E_PORT": str(port),
            "CITYNEXUS_BACKEND_PORT": str(port + 4000),
            "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{run_id}.db",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": f"{ROOT}/review/evidence",
        }
    )
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_AI_API_KEY", None)
    # Evidence written from inside a test can only quote the build it ran against if the run hands
    # it the sha: ORD-0087's screenshots carry HEAD + build + demo_mode.
    head = subprocess.run(
        "git rev-parse HEAD",
        cwd=ROOT,
        capture_output=True,
        text=True,
        shell=True,
    ).stdout.strip()
    env["CITYNEXUS_E2E_GIT_HEAD"] = head or "unknown"
    print(f"run_id={run_id} port={port}/{port + 4000} target={target}", flush=True)
    proc = subprocess.run(
        f'npx playwright test {target} --reporter=list{" --list" if listing else ""}{f" {extra}" if extra else ""}',
        cwd=f"{ROOT}/frontend",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    out = proc.stdout + proc.stderr
    log = f"{ROOT}/review/run-{run_id}.log"
    with open(log, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    if listing:
        counts = {}
        for line in out.splitlines():
            match = line.strip().split(" > ")[0]
            if match.endswith(".spec.ts"):
                counts[match] = counts.get(match, 0) + 1
        for spec in sorted(counts):
            print(f"{counts[spec]:4d}  {spec}", flush=True)
    quiet = [line for line in out.splitlines() if not line.startswith("[WebServer]")]
    print("\n".join(quiet[-90:]), flush=True)
    print(f"exit={proc.returncode} log={log}", flush=True)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
