"""ORD-0271-B: put either my real backend or one named junk origin behind :8411, and PROVE which one answers.

Why this exists as a checked script: :8411 is the whole attribution. vite's `/api` proxy target is fixed when
the face starts, so whatever listens there *is* the traveller's origin - and the first version of this switcher
learned that the hard way. It asked netstat once, saw no listener (netstat can answer with a short body),
reported the port free, started the junk origin, got `WinError 10013` because the real backend still owned the
port, and then a probe that accepted "any 200" cheerfully certified `ANSWERING` while the bytes came from the
backend. That is a false green that would have made every fifth-state reading a lie.

So every claim below is a separate measurement, and the run aborts if any one fails:

1. `listeners()` refuses to treat a suspicious netstat (non-zero exit, or fewer than 200 lines) as "empty".
   "I could not see" is never the same fact as "nobody is there".
2. The port must be observably free before a new origin starts, and after starting, the listener on :8411 must
   BE the pid this script spawned.
3. The probe must match the *named mode's* discriminating wire facts (status, Content-Type, byte count, first
   bytes) - the backend answers JSON, html answers 1,200 B of `<!doctype html>`, empty answers 0 B, nonjson
   answers 33 B of plain text. A probe that cannot tell those apart cannot certify one.
4. The instrument's own log must gain a fresh `answered` row for that probe, so "the origin answered" is a
   reading from the origin's side of the wire rather than my inference from a 200 in a browser.

Nothing here touches the user's ports or databases; `demo/reset` is never issued; processes are signalled only
after their command lines are read back and shown to be mine.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
PORT = 8411
JID = "22222222-2222-4222-8222-222222222222"
VENV_PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LAB_PY = sys.executable
# the canary tree and the canary store my face's ownership proof reads against - `repo/backend` with no env
# opens a CWD-relative empty database and answers 404 for the marker journey, which is not "my origin".
BACKEND_ROOT = BASE / "backend53" / "backend"
CANARY_DB = BASE / "db" / "canary_8411.db"
BACKEND_ENV = {"CITYNEXUS_DATABASE_URL": f"sqlite:///{CANARY_DB.as_posix()}", "CITYNEXUS_ENV": "dev",
               "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false",
               "CITYNEXUS_GUARDIAN_AUTORUN": "false", "DEEPSEEK_API_KEY": "", "CITYNEXUS_AI_API_KEY": "",
               "CITYNEXUS_ANYWHERE_RESOLVER": "off",
               "CITYNEXUS_PHOTON_BASE_URL": "http://127.0.0.1:9",
               "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
PROBE_PATH = f"/api/v1/journeys/{JID}/experience"
# what each mode must look like on the wire, or the switch is not proven
EXPECT = {
    "backend": {"status": 200, "content_type": "application/json", "min_bytes": 500, "head": '{"journey"'},
    "html": {"status": 200, "content_type": "text/html", "bytes": 1200, "head": "<!doctype html>"},
    "empty": {"status": 200, "content_type": "application/json", "bytes": 0, "head": ""},
    "nonjson": {"status": 200, "content_type": "text/plain", "bytes": 33, "head": "this sentence is not JSON"},
}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())


def ps(pid: int) -> str:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    return out.strip()


def listeners(port: int = PORT) -> list[int]:
    """PIDs listening on `port`. Refuses to read a broken netstat as an empty one."""
    r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0 or len(r.stdout.splitlines()) < 200:
        raise SystemExit(f"ABORT: netstat unusable (rc={r.returncode}, "
                         f"{len(r.stdout.splitlines())} lines); refusing to read that as 'port free'")
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", r.stdout)
                   if int(m.group(1)) == int(port)})   # int==str here would read every port as free


def mine(cl: str) -> bool:
    return (("app.main:app" in cl and f"--port {PORT}" in cl)
            or ("origin_answers_junk_200.py" in cl and str(BASE) in cl))


def free_port() -> dict:
    note = {"killed": [], "refused": [], "free": False, "netstat_observations": []}
    for _ in range(8):
        pids = listeners()
        note["netstat_observations"].append(pids)
        if not pids:
            note["free"] = True
            return note
        for pid in pids:
            cl = ps(pid)
            if not mine(cl):
                note["refused"].append({"pid": pid, "command_line": cl[:220]})
                print(f"REFUSE to signal :{PORT} pid {pid}, not mine: {cl[:180]}")
                return note
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
            note["killed"].append({"pid": pid, "command_line": cl[:200]})
        time.sleep(1.5)
    note["free"] = not listeners()
    return note


def probe() -> dict:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{PROBE_PATH}", timeout=8) as r:
            b = r.read()
            return {"status": r.status, "content_type": r.headers.get("Content-Type"),
                    "bytes": len(b), "head": b[:30].decode("utf-8", "replace"),
                    "sha256_16": hashlib.sha256(b).hexdigest()[:16]}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "content_type": (e.headers or {}).get("Content-Type"),
                "bytes": 0, "head": ""}
    except Exception as e:  # noqa: BLE001
        return {"status": None, "error": f"{type(e).__name__}: {e}"}


def matches(mode: str, p: dict) -> tuple[bool, list]:
    want, fails = EXPECT[mode], []
    if p.get("status") != want["status"]:
        fails.append(f"status {p.get('status')} != {want['status']}")
    if want["content_type"] not in (p.get("content_type") or ""):
        fails.append(f"content_type {p.get('content_type')!r} lacks {want['content_type']!r}")
    if "bytes" in want and p.get("bytes") != want["bytes"]:
        fails.append(f"bytes {p.get('bytes')} != {want['bytes']}")
    if "min_bytes" in want and (p.get("bytes") or 0) < want["min_bytes"]:
        fails.append(f"bytes {p.get('bytes')} < {want['min_bytes']}")
    if not (p.get("head") or "").startswith(want["head"]):
        fails.append(f"head {p.get('head')!r} does not start with {want['head']!r}")
    return (not fails), fails


def junk_answered_rows(mode: str) -> list[dict]:
    p = BASE / f"ord0263_junk_{mode}.log"
    if not p.is_file():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def descendants(root_pid: int, depth: int = 4) -> set:
    """`.venv\Scripts\python.exe` is a shim that re-execs the uv-managed interpreter as a child, so the
    process that ends up owning the port is a descendant of what I spawned, not the pid I hold."""
    out = {root_pid}
    frontier = {root_pid}
    for _ in range(depth):
        nxt = set()
        for p in frontier:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={p}').ProcessId"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
            nxt |= {int(x) for x in re.findall(r"\d+", r)}
        if not (nxt - out):
            break
        out |= nxt
        frontier = nxt - {0}
    return out


def start_and_certify(kind: str, mode: str) -> tuple[int, dict]:
    """kind is 'backend' or 'junk'; mode is '' for the backend, else html|empty|nonjson."""
    key = kind if kind == "backend" else mode
    label = kind + (mode or "")
    log = BASE / f"0271b_origin_{label}.log"
    fh = open(log, "a", encoding="utf-8")
    fh.write(f"\n=== {now()} kind={kind} mode={mode} ===\n")
    fh.flush()
    if kind == "backend":
        args = [VENV_PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)]
        cwd = str(BACKEND_ROOT)
    else:
        args = [LAB_PY, str(BASE / "tools" / "origin_answers_junk_200.py"), mode]
        cwd = str(BASE / "tools")
    env = dict(os.environ) | (BACKEND_ENV if kind == "backend" else {"PYTHONIOENCODING": "utf-8"})
    proc = subprocess.Popen(args, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, env=env)
    seen_before = len([r for r in junk_answered_rows(mode) if r.get("kind") == "answered"]) if mode else 0
    p, ok, fails, attempts = None, False, [], 0
    for _ in range(90 if kind == "backend" else 30):
        time.sleep(1)
        attempts += 1
        p = probe()
        ok, fails = matches(key, p)
        if ok:
            break
    holders = listeners()
    tree_pids = descendants(proc.pid)
    owns = bool(holders) and set(holders) <= tree_pids
    fresh_rows = []
    if mode:
        rows = [r for r in junk_answered_rows(mode) if r.get("kind") == "answered"][seen_before:]
        fresh_rows = rows[:3]
    rec = {"at": now(), "want": key, "expected_wire": EXPECT[key], "spawned_pid": proc.pid,
           "args": args, "cwd": cwd, "instrument_log": log.name,
           "probe": p, "probe_attempts": attempts,
           "probe_matches_mode": ok, "probe_mismatches": fails,
           "listeners_on_port_after_start": holders, "spawned_process_owns_port": owns,
           "spawned_process_tree": sorted(tree_pids),
           "listener_command_lines": [ps(p)[:200] for p in holders],
           "instrument_answered_rows_from_this_probe": fresh_rows,
           "alive": proc.poll() is None,
           "user_chain": {"ports_contacted": [], "db_files_opened": [], "demo_reset_issued": False}}
    out = BASE / f"ord0271b_origin_{label}.json"
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    verdict = ("CERTIFIED" if (ok and owns and rec["alive"] and (not mode or fresh_rows))
               else "NOT_CERTIFIED")
    print(json.dumps({"verdict": verdict, "want": key, "pid": proc.pid, "probe": p,
                      "owns_port": owns, "holders": holders, "mismatches": fails,
                      "instrument_rows": len(fresh_rows), "receipt": out.name},
                     ensure_ascii=False, indent=1))
    return (0 if verdict == "CERTIFIED" else 4), rec


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    kind = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    if kind not in ("backend", "junk"):
        print("usage: swap_origin_8411.py backend | swap_origin_8411.py junk html|empty|nonjson")
        return 2
    stopped = free_port()
    if not stopped["free"]:
        print(json.dumps({"verdict": "BLOCKED_PORT", "stop": stopped}, ensure_ascii=False, indent=1))
        return 3
    rc, _ = start_and_certify(kind, mode)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
