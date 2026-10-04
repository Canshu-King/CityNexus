"""ORD-0545 slice six -- run the two new screen arms and the slice-five regression on my own stack.

What this proves and what it does not:
  * the lane backend listens on a port of mine over a COPY of the commander's canary, which is hashed
    before and after so "I never wrote to the source" is a measurement, not a claim;
  * the slice-six spec (4 arms) and the slice-five spec (4 arms, one criterion re-cast) each get their
    own collected/passed/failed counts read out of the runner's own stdout;
  * it does not run the product suite, does not touch the commander's ports, and tears its child down in
    a finally block -- a hard-killed run is what left a mutation in a published file once before.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
FRONTEND = ROOT / "frontend"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
READOUTS = ROOT / "review/ord0545/readouts"
SOURCE_CANARY = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db")
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SFX = RUN_STAMP[-7:-1]
TAG = "s6" + SFX
BASE_TIP = os.environ.get("CITYNEXUS_ORD0545_BASE_TIP", "")
BACKEND_PORT = int(os.environ.get("CITYNEXUS_S6_BACKEND_PORT", "4931"))
FRONTEND_PORT = int(os.environ.get("CITYNEXUS_S6_FRONTEND_PORT", "4936"))
STORE = DATA / f"_ord0545s6_{SFX}.db"
BACKEND_LOG = DATA / f"uvicorn_{BACKEND_PORT}_{SFX}.log"
RECEIPT = READOUTS / f"slice6_glass_{RUN_STAMP}.json"
LOCK = DATA / f"slice6_glass_{SFX}.lock"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
FORBIDDEN = (8000, 4781, 4782, 4783, 4785, 4786, 4787, 8693, 4789, 4799, 4820)

S6_CONFIG = "playwright.ord0545s6-copy-cells.config.ts"
S5_CONFIG = "playwright.ord0545s5-refusal-glass2.config.ts"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def listeners(port: int) -> list[str]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace").stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if len(ln.split()) >= 5 and ln.split()[0].upper() == "TCP"
                   and ln.split()[3].upper() == "LISTENING" and ln.split()[1].endswith(f":{port}")})


def command_line(pid: str) -> str:
    probe = ("Get-CimInstance Win32_Process -Filter 'ProcessId=" + pid + "' "
             "| ForEach-Object { $_.CommandLine }")
    return subprocess.run(["powershell.exe", "-NoProfile", "-Command", probe],
                          capture_output=True, text=True, errors="replace").stdout.strip()


def children_of(pid: int) -> list[str]:
    """The DB URL travels in the environment, not in the command line, so attribution has to be by
    process family: the listener is either my child or a child of my child."""
    probe = ("Get-CimInstance Win32_Process -Filter 'ParentProcessId=" + str(pid) + "' "
             "| ForEach-Object { $_.ProcessId }")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", probe],
                         capture_output=True, text=True, errors="replace").stdout
    return [x for x in out.split() if x.isdigit()]


def http(method: str, url: str, body: dict | None = None, timeout: int = 20):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"content-type": "application/json",
                                          "user-agent": "CityNexus-ORD-0545-s6-lane"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return r.status, json.loads(raw)
    except ValueError:
        return r.status, raw


def row_count(db: pathlib.Path, sql: str):
    """Read-only open of a file I own (or the commander's canary, never written)."""
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        return conn.execute(sql).fetchone()[0]
    finally:
        conn.close()


def gate(name: str, config: str, grep: str, port_key: str) -> dict:
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_ORD0545_TAG": TAG,
        "CITYNEXUS_ORD0545_BASE_TIP": BASE_TIP,
        "CITYNEXUS_ORD0545_BACKEND_PORT": str(BACKEND_PORT),
        port_key: str(FRONTEND_PORT),
        "DEEPSEEK_API_KEY": "",
        "PYTHONIOENCODING": "utf-8",
    })
    cmd = ["node", "node_modules/@playwright/test/cli.js", "test", "-c", config, "-g", grep]
    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=FRONTEND, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=480, env=env)
        out, rc = (proc.stdout or "") + (proc.stderr or ""), proc.returncode
    except subprocess.TimeoutExpired:
        out, rc = "TIMEOUT after 480s", -9
    (DATA / f"slice6_{name}_{SFX}.txt").write_text(out, encoding="utf-8", newline="\n")
    num = lambda pat: (int(re.search(pat, out).group(1)) if re.search(pat, out) else 0)
    return {
        "label": name, "config": config, "grep": grep, "rc": rc,
        "wall_seconds": round(time.time() - started, 1),
        "collected": num(r"Running (\d+) tests?"),
        "passed": num(r"(\d+) passed"), "failed": num(r"(\d+) failed"),
        "first_failure_lines": [l.strip()[:160] for l in out.splitlines() if re.match(r"\s*\d+\) ", l)][:3],
    }


def main() -> int:
    if LOCK.exists():
        holder = "".join(ch for ch in LOCK.read_text(encoding="utf-8") if ch.isdigit())
        alive = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                f"Get-Process -Id {holder} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.Id }}"],
                               capture_output=True, text=True).stdout.strip() if holder.isdigit() else ""
        if alive:
            raise SystemExit("ABORT another slice-six run holds the lock (live pid " + alive + ")")
        print("lock left by a dead pid; taking it over", flush=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8", newline="\n")
    if not BASE_TIP or not re.fullmatch(r"[0-9a-f]{40}", BASE_TIP):
        raise SystemExit("ABORT CITYNEXUS_ORD0545_BASE_TIP must be the 40-hex tip measured on")
    if not SOURCE_CANARY.is_file():
        raise SystemExit("ABORT the commander's canary copy is missing: " + str(SOURCE_CANARY))
    held = {p: listeners(p) for p in (BACKEND_PORT, FRONTEND_PORT) if listeners(p)}
    if held:
        raise SystemExit("ABORT my ports are already held: " + json.dumps(held))
    forbidden_held = {p: listeners(p) for p in FORBIDDEN if listeners(p)}

    source_sha_before = sha(SOURCE_CANARY)
    STORE.write_bytes(SOURCE_CANARY.read_bytes())
    rows: dict[str, object] = {
        "generation": {"base_tip": BASE_TIP, "recorded_at": RUN_STAMP, "tag": TAG,
                       "this_lane_ports": [BACKEND_PORT, FRONTEND_PORT],
                       "store_copy": str(STORE), "store_copy_sha256": sha(STORE),
                       "canary_source": str(SOURCE_CANARY), "canary_source_sha256_before": source_sha_before,
                       "forbidden_ports_held_by_others": forbidden_held},
        "runs": [],
    }

    def emit() -> None:
        READOUTS.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{STORE.as_posix()}"
    env["CITYNEXUS_DEMO_MODE"] = "true"
    log = BACKEND_LOG.open("w", encoding="utf-8", errors="replace")
    child = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                              "--port", str(BACKEND_PORT), "--log-level", "warning"],
                             cwd=ROOT / "backend", env=env, stdout=log, stderr=subprocess.STDOUT)
    ready = None
    try:
        for _ in range(90):
            try:
                status, payload = http("GET", f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")
                if status == 200:
                    ready = payload
                    break
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            time.sleep(1)
        if ready is None:
            raise SystemExit("ABORT the lane backend never answered; see " + str(BACKEND_LOG))
        pids = listeners(BACKEND_PORT)
        family = {str(child.pid), *children_of(child.pid)}
        rows["generation"]["backend_listener"] = {
            "pids": pids, "my_child_pid": str(child.pid),
            "listener_is_my_child_or_its_child": bool(pids) and set(pids) <= family,
            "command_line": {p: command_line(p)[:120] for p in pids},
        }
        print("backend up:", json.dumps(rows["generation"]["backend_listener"], ensure_ascii=False), flush=True)

        # attribution, both directions: a marker the listener writes must land in MY copy and be absent
        # from the commander's canary -- the DB URL travels in the environment, so nothing in a command
        # line could prove this.
        marker = "ORD-0545-s6-" + SFX
        m_status, m_body = http("POST", f"http://127.0.0.1:{BACKEND_PORT}/api/v1/travelers",
                                {"display_name": marker, "locale": "zh-CN", "timezone": "Asia/Shanghai"})
        mine_after = row_count(STORE, "SELECT COUNT(*) FROM travelers WHERE display_name = '" + marker + "'")
        source_after = row_count(SOURCE_CANARY, "SELECT COUNT(*) FROM travelers WHERE display_name = '" + marker + "'")
        rows["generation"]["attribution"] = {
            "post_travelers_status": m_status,
            "marker_in_my_store_copy": mine_after,
            "marker_in_the_commanders_canary": source_after,
            "the_listener_writes_only_my_copy": m_status == 201 and mine_after == 1 and source_after == 0,
        }
        print("attribution:", json.dumps(rows["generation"]["attribution"]), flush=True)
        emit()
        if not rows["generation"]["attribution"]["the_listener_writes_only_my_copy"]:
            raise SystemExit("ABORT attribution failed -- the answer on my port is not serving my store copy")
        # there is no traveller-delete door on this line (measured: the only DELETE route under that
        # prefix is /travelers/{id}/traveler-twin/learned), so the marker is left where it can do no
        # harm -- inside MY copy of the store, which this tool unlinks in its teardown.
        rows["generation"]["marker_lives_only_in_my_copy"] = mine_after == 1 and source_after == 0

        for name, config, grep, port_key in (
            ("s6_all_four", S6_CONFIG, "Azh|Aen|Bzh|Ben", "CITYNEXUS_ORD0545S6_PORT"),
            ("s5_all_four", S5_CONFIG, "Uzh|Wen|Nzh|Ren", "CITYNEXUS_ORD0545S5_PORT"),
        ):
            r = gate(name, config, grep, port_key)
            rows["runs"].append(r)
            print(json.dumps(r, ensure_ascii=False), flush=True)
            emit()
    finally:
        child.terminate()
        for _ in range(30):
            if child.poll() is not None:
                break
            time.sleep(1)
        if child.poll() is None:
            child.kill()
        log.close()
        rows["teardown"] = {
            "backend_pid_exit": child.returncode,
            "my_ports_listening_after": {str(p): listeners(p) for p in (BACKEND_PORT, FRONTEND_PORT)},
            "canary_source_sha256_after": sha(SOURCE_CANARY),
            "canary_source_untouched": sha(SOURCE_CANARY) == source_sha_before,
        }
        emit()
        LOCK.unlink(missing_ok=True)
        STORE.unlink(missing_ok=True)
        BACKEND_LOG.unlink(missing_ok=True)

    bits = [r for r in rows["runs"]]
    attributed = bool(rows["generation"].get("backend_listener", {}).get("listener_is_my_child_or_its_child"))
    own_copy = bool(rows["generation"].get("attribution", {}).get("the_listener_writes_only_my_copy"))
    verdict = ("GLASS_OK four slice-six arms and four slice-five arms green on the retaken source, "
               "listener attributed to this lane's own store copy"
               if all(r["rc"] == 0 and r["collected"] == 4 and r["passed"] == 4 for r in bits)
               and rows["teardown"]["canary_source_untouched"] and attributed and own_copy
               else "NOT_GREEN see the rows")
    rows["verdict"] = verdict
    emit()
    print(json.dumps({"receipt": str(RECEIPT), "verdict": verdict,
                      "teardown": rows["teardown"]}, ensure_ascii=False), flush=True)
    return 0 if verdict.startswith("GLASS_OK") else 1


if __name__ == "__main__":
    sys.exit(main())
