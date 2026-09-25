"""Run this lane's owner gates on ports this lane can prove are its own.

Why this exists (measured 2026-09-25 08:4x, not theorised): three of this lane's four gates came back
RED on a re-parent round with `Error: http://127.0.0.1:9013/api/v1/health is already used` and
`Process from config.webServer was not able to start. Exit code: 3`.  Nothing about the candidate was
wrong -- ASUS `ArmourySocketServer.exe` was listening on 9012 and 9013 and `ArmouryHtmlDebugServer.exe`
on 9014, i.e. on the backend side (`frontend_port + 4000`) of the band this batch had picked.  A
vendor HTTP server on a lane's port produces exactly the shape of a product red.

So the batch refuses to start unless, for every port pair it is about to use, it can see nobody
listening AND get nothing back over HTTP.  It names the owning process when it does find one, because
"the port was busy" without a name is how a shared box gets blamed twice.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
SPECS = [
    "e2e/qoder-continuation-owner.spec.ts",
    "e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts",
    "e2e/qoder-continuation-resume-carries-identity.spec.ts",
    "e2e/qoder-sheet-legs-carry-idempotency-key.spec.ts",
]

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def sh(cmd: str) -> str:
    return subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace"
    ).stdout


def listener_pid(port: int) -> str:
    m = re.search(rf"127\.0\.0\.1:{port}\s+\S+\s+LISTENING\s+(\d+)", sh("netstat -ano -p tcp"))
    return m.group(1) if m else ""


def process_name(pid: str) -> str:
    if not pid:
        return ""
    out = sh(f'tasklist /FI "PID eq {pid}" /FO CSV /NH')
    parts = [p.strip('"') for p in out.strip().split(",")] if out.strip() else []
    return parts[0] if parts and parts[0] else "?"


def http_answers(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}"       # an error page is still somebody answering
    except Exception:
        return ""


def probe(port: int) -> dict:
    """Occupied if a socket listens OR anything answers.  A 200 here is not 'ready', it is 'not mine'."""
    pid = listener_pid(port)
    url = f"http://127.0.0.1:{port}/" if port < 9000 else f"http://127.0.0.1:{port}/api/v1/health"
    answer = http_answers(url)
    return {
        "port": port,
        "listening_pid": pid,
        "listening_process": process_name(pid),
        "http_probe": answer or "no answer",
        "occupied": bool(pid) or bool(answer),
    }


def main() -> int:
    argv = sys.argv[1:]
    tag = argv[0] if argv else "round"
    base = int(argv[1]) if len(argv) > 1 else 4940
    out_dir = ROOT / "_scratch_0298"
    out_dir.mkdir(exist_ok=True)

    pairs = [(base + i, base + i + 4000) for i in range(len(SPECS))]
    probes = {}
    for front, back in pairs:
        for port in (front, back):
            probes[str(port)] = probe(port)
    dirty = sorted(p["port"] for p in probes.values() if p["occupied"])
    for port, p in sorted(probes.items(), key=lambda kv: int(kv[0])):
        print(f"  port {port}: pid={p['listening_pid'] or '-'} proc={p['listening_process'] or '-'} "
              f"{p['http_probe']} occupied={p['occupied']}")
    if dirty:
        print(f"ABORT_PORT_OCCUPIED {dirty} -- refusing to grade gates on someone else's socket; "
              "pick a band where every probe is silent")
        return 6

    env_probes = {"base": base, "pairs": [list(p) for p in pairs], "ports": probes,
                  "all_silent": not dirty}
    manifest = {"tag": tag, "preflight": env_probes, "runs": []}
    for index, spec in enumerate(SPECS):
        port = base + index
        started = time.time()
        import os
        env = dict(os.environ)
        env["CNX_LANE_ROOT"] = str(ROOT)
        proc = subprocess.run(
            [PYTHON, str(ROOT / "review/run_spec.py"), spec, str(port)],
            cwd=str(ROOT), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        out = proc.stdout + proc.stderr
        run_id = next((l.split("run_id=", 1)[1].split()[0] for l in out.splitlines() if l.startswith("run_id=")), "")
        log = ROOT / f"review/run-{run_id}.log"
        tally = [l.strip() for l in out.splitlines() if re.match(r"^\s*\d+ (passed|failed)", l)]
        record = {
            "spec": spec, "port": port, "backend_port": port + 4000, "exit": proc.returncode,
            "run_id": run_id, "log": log.name if log.exists() else "", "seconds": round(time.time() - started),
            "tally": tally, "post_run_probe": probe(port + 4000),
        }
        manifest["runs"].append(record)
        print(f"[{spec}] exit={record['exit']} run={run_id} {record['seconds']}s {tally} "
              f"backend_after={record['post_run_probe']['http_probe']}", flush=True)
        (out_dir / f"batch-{tag}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    ok = all(r["exit"] == 0 for r in manifest["runs"])
    print(f"manifest={out_dir / f'batch-{tag}.json'} all_exit_0={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
