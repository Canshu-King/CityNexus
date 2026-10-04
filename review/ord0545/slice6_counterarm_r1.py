"""ORD-0545 slice six -- the two single-variable counter-arms.

A fix that cannot be broken is not a fix. Each mutation changes ONE cell of the shipped panel and must
turn red exactly the arms that watch that cell, while the sibling pair stays green and the file comes
back byte-identical:

  M1_channel_cell_paints_the_server_token -- the main channel slot goes back to printing the machine
     token. Arms A (zh, en) must go red; arms B must stay green.
  M2_no_status_cell_repeats_the_sentence -- the no-status technical line goes back to repeating the
     refusal sentence. Arms B must go red; arms A must stay green.

The stack is this lane's own: a copy of the commander's canary, a port of mine, and the attribution
round-trip re-run every time so a foreign listener can never be mistaken for mine.
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
PANEL = FRONTEND / "src/features/poiimport/PoiImportPanel.tsx"
SOURCE_CANARY = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db")
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SFX = RUN_STAMP[-7:-1]
TAG = "s6ca" + SFX
BASE_TIP = os.environ.get("CITYNEXUS_ORD0545_BASE_TIP", "")
BACKEND_PORT = int(os.environ.get("CITYNEXUS_S6_BACKEND_PORT", "4933"))
FRONTEND_PORT = int(os.environ.get("CITYNEXUS_S6_FRONTEND_PORT", "4938"))
STORE = DATA / f"_ord0545s6ca_{SFX}.db"
BACKEND_LOG = DATA / f"uvicorn_{BACKEND_PORT}_{SFX}.log"
RECEIPT = READOUTS / f"slice6_counterarms_{RUN_STAMP}.json"
LOCK = DATA / f"slice6_counterarm_{SFX}.lock"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
CONFIG = "playwright.ord0545s6-copy-cells.config.ts"
A_GREP, B_GREP = "Azh|Aen", "Bzh|Ben"

MUTATIONS = [
    ("M1_channel_cell_paints_the_server_token",
     '<b data-testid="poi-import-channel-name">{poiImportCopy(locale, CHANNEL_NAME[parsed?.source_channel ?? "LOCAL_TEXT_PARSER"])}</b>',
     '<b data-testid="poi-import-channel-name">{parsed?.source_channel ?? "LOCAL_TEXT_PARSER"}</b>',
     A_GREP, B_GREP),
    ("M2_no_status_cell_repeats_the_sentence",
     '<small data-testid="poi-import-error-detail">{poiImportCopy(locale, "noStatusMeasured")}</small>',
     '<small data-testid="poi-import-error-detail">{poiImportCopy(locale, "errNoResponse")}</small>',
     B_GREP, A_GREP),
]


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def listeners(port: int) -> list[str]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace").stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if len(ln.split()) >= 5 and ln.split()[0].upper() == "TCP"
                   and ln.split()[3].upper() == "LISTENING" and ln.split()[1].endswith(f":{port}")})


def children_of(pid: int) -> list[str]:
    probe = ("Get-CimInstance Win32_Process -Filter 'ParentProcessId=" + str(pid) + "' "
             "| ForEach-Object { $_.ProcessId }")
    return [x for x in subprocess.run(["powershell.exe", "-NoProfile", "-Command", probe],
                                      capture_output=True, text=True, errors="replace").stdout.split()
            if x.isdigit()]


def http(method: str, url: str, body: dict | None = None, timeout: int = 20):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"content-type": "application/json",
                                          "user-agent": "CityNexus-ORD-0545-s6-counterarm"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return r.status, json.loads(raw)
    except ValueError:
        return r.status, raw


def row_count(db: pathlib.Path, sql: str):
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        return conn.execute(sql).fetchone()[0]
    finally:
        conn.close()


def attribute(child) -> dict:
    marker = "ORD-0545-s6ca-" + SFX
    status, body = http("POST", f"http://127.0.0.1:{BACKEND_PORT}/api/v1/travelers",
                        {"display_name": marker, "locale": "zh-CN", "timezone": "Asia/Shanghai"})
    mine = row_count(STORE, "SELECT COUNT(*) FROM travelers WHERE display_name = '" + marker + "'")
    source = row_count(SOURCE_CANARY, "SELECT COUNT(*) FROM travelers WHERE display_name = '" + marker + "'")
    pids = listeners(BACKEND_PORT)
    return {"post_travelers_status": status, "marker_in_my_store_copy": mine,
            "marker_in_the_commanders_canary": source,
            "listener_pids": pids, "listener_is_my_child_or_its_child": bool(pids) and set(pids) <= {str(child.pid), *children_of(child.pid)},
            "the_listener_writes_only_my_copy": status == 201 and mine == 1 and source == 0}


def gate(label: str, grep: str) -> dict:
    env = dict(os.environ)
    env.update({"CITYNEXUS_ORD0545_TAG": TAG + "_" + re.sub(r"^M\d_", "", label)[:6].lower(),
                "CITYNEXUS_ORD0545_BASE_TIP": BASE_TIP,
                "CITYNEXUS_ORD0545_BACKEND_PORT": str(BACKEND_PORT),
                "CITYNEXUS_ORD0545S6_PORT": str(FRONTEND_PORT),
                "DEEPSEEK_API_KEY": "", "PYTHONIOENCODING": "utf-8"})
    cmd = ["node", "node_modules/@playwright/test/cli.js", "test", "-c", CONFIG, "-g", grep]
    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=FRONTEND, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=480, env=env)
        out, rc = (proc.stdout or "") + (proc.stderr or ""), proc.returncode
    except subprocess.TimeoutExpired:
        out, rc = "TIMEOUT after 480s", -9
    (DATA / f"slice6ca_{label}_{SFX}.txt").write_text(out, encoding="utf-8", newline="\n")
    num = lambda pat: (int(re.search(pat, out).group(1)) if re.search(pat, out) else 0)
    return {"label": label, "grep": grep, "rc": rc, "wall_seconds": round(time.time() - started, 1),
            "collected": num(r"Running (\d+) tests?"), "passed": num(r"(\d+) passed"),
            "failed": num(r"(\d+) failed"),
            "failed_names": sorted(set(re.findall(r"[AB][a-z]{2} [^\n]*", out)))[:2]}


def main() -> int:
    if LOCK.exists():
        holder = "".join(ch for ch in LOCK.read_text(encoding="utf-8") if ch.isdigit())
        alive = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                f"Get-Process -Id {holder} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.Id }}"],
                               capture_output=True, text=True).stdout.strip() if holder.isdigit() else ""
        if alive:
            raise SystemExit("ABORT another counter-arm run holds the lock (live pid " + alive + ")")
        print("lock left by a dead pid; taking it over", flush=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8", newline="\n")
    if not re.fullmatch(r"[0-9a-f]{40}", BASE_TIP or ""):
        raise SystemExit("ABORT CITYNEXUS_ORD0545_BASE_TIP must be the 40-hex tip measured on")
    if listeners(BACKEND_PORT) or listeners(FRONTEND_PORT):
        raise SystemExit("ABORT my ports are held: " + str(listeners(BACKEND_PORT) + listeners(FRONTEND_PORT)))

    original = PANEL.read_bytes()
    pristine = hashlib.sha256(original).hexdigest()
    source_before = sha(SOURCE_CANARY)
    rows: dict = {"generation": {"base_tip": BASE_TIP, "recorded_at": RUN_STAMP,
                                 "panel_sha_before": pristine,
                                 "panel_blob_at_tip": subprocess.run(
                                     ["git", "-C", str(ROOT), "rev-parse", BASE_TIP + ":" + "frontend/src/features/poiimport/PoiImportPanel.tsx"],
                                     capture_output=True, text=True).stdout.strip(),
                                 "canary_source_sha256_before": source_before,
                                 "this_lane_ports": [BACKEND_PORT, FRONTEND_PORT]},
                  "rows": []}

    def emit():
        READOUTS.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{STORE.as_posix()}"
    env["CITYNEXUS_DEMO_MODE"] = "true"
    STORE.write_bytes(SOURCE_CANARY.read_bytes())
    log = BACKEND_LOG.open("w", encoding="utf-8", errors="replace")
    child = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                              "--port", str(BACKEND_PORT), "--log-level", "warning"],
                             cwd=ROOT / "backend", env=env, stdout=log, stderr=subprocess.STDOUT)
    bits: list[bool] = []
    aborted = ""
    try:
        ready = False
        for _ in range(90):
            try:
                ready = http("GET", f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")[0] == 200
                if ready:
                    break
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            time.sleep(1)
        if not ready:
            raise SystemExit("ABORT the lane backend never answered; see " + str(BACKEND_LOG))
        rows["generation"]["attribution_before_arms"] = attribute(child)
        emit()
        if not rows["generation"]["attribution_before_arms"]["the_listener_writes_only_my_copy"]:
            raise SystemExit("ABORT attribution failed before any mutation")

        control = [gate("control_A", A_GREP), gate("control_B", B_GREP)]
        rows["rows"].append({"row": "control_shipped_source", "arms": control})
        bits.append(all(c["rc"] == 0 and c["collected"] == 2 and c["passed"] == 2 for c in control))
        emit()
        if not bits[-1]:
            aborted = "control red on the shipped source -- the batch can claim nothing"

        for name, needle, replacement, red_grep, green_grep in MUTATIONS:
            if aborted:
                break
            text = original.decode("utf-8")
            if text.count(needle) != 1:
                rows["rows"].append({"row": name, "skipped": f"anchor appears {text.count(needle)} times"})
                bits.append(False)
                aborted = name + ": anchor moved"
                emit()
                break
            PANEL.write_text(text.replace(needle, replacement, 1), encoding="utf-8", newline="\n")
            landed = hashlib.sha256(PANEL.read_bytes()).hexdigest() != pristine
            red = gate(name + "_red", red_grep)
            PANEL.write_bytes(original)
            restored = hashlib.sha256(PANEL.read_bytes()).hexdigest() == pristine
            sib = gate(name + "_sibling", green_grep)
            bites = (landed and red["rc"] != 0 and red["failed"] >= 1 and red["collected"] == 2
                     and sib["rc"] == 0 and sib["collected"] == 2 and sib["passed"] == 2 and restored)
            bits.append(bites)
            rows["rows"].append({"row": name, "mutation_landed": landed,
                                 "mutated_arms": red, "sibling_arms": sib,
                                 "panel_restored_byte_identical": restored, "bites": bites})
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
        rows["teardown"] = {"backend_exit": child.returncode,
                            "my_ports_listening_after": {str(p): listeners(p) for p in (BACKEND_PORT, FRONTEND_PORT)},
                            "panel_byte_identical_at_exit": hashlib.sha256(PANEL.read_bytes()).hexdigest() == pristine,
                            "canary_source_sha256_after": sha(SOURCE_CANARY),
                            "canary_source_untouched": sha(SOURCE_CANARY) == source_before}
        emit()
        LOCK.unlink(missing_ok=True)
        STORE.unlink(missing_ok=True)
        BACKEND_LOG.unlink(missing_ok=True)

    rows["verdict"] = ("KILL_OK two single-variable mutations each turn red exactly their own arms, "
                       "the sibling pair stays green, the panel returns byte-identical"
                       if all(bits) and rows["teardown"]["panel_byte_identical_at_exit"]
                       and rows["teardown"]["canary_source_untouched"] and not aborted
                       else "NOT_OK see the rows")
    emit()
    print(json.dumps({"receipt": str(RECEIPT), "verdict": rows["verdict"],
                      "teardown": rows["teardown"]}, ensure_ascii=False), flush=True)
    return 0 if rows["verdict"].startswith("KILL_OK") else 1


if __name__ == "__main__":
    sys.exit(main())
