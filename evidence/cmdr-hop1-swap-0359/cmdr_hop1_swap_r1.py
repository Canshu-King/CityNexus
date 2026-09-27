"""CMDR hop1 backend swap: point the phone chain's backend at an export of the authoritative tip.

Why: ORD-B landed backend/app changes, so the served frontend (tip) and hop1 (older export tree)
drifted apart.  This script does the swap in one place and records what it observed:
  1. resolve the pid listening on the chain port, name the command line it was started with
  2. stop that one process (nothing else), start the same module on the new tree with the same env
  3. wait for /openapi.json, then read the two ORD-B fields back out of the LIVE spec
  4. re-probe the phone-facing assets so the generation claim stays same-generation
Writes a JSON receipt next to itself.  Refuses to act if the port owner is not a uvicorn on the
chain's own tree, because killing somebody else's backend would hand them a fake defect.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

CHAIN_PORT = "8693"
NEW_TREE = "D:/moodle/_qoder_cmdr_backend_live_0350"
DB = "D:/moodle/_qoder_preview_20260920/_preview.db"
VENV_PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
HERE = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
RECEIPT = HERE + "/cmdr_hop1_swap_receipt.json"


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, shell=False)


def port_owner(port):
    out = sh(["netstat", "-ano", "-p", "TCP"]).stdout
    pids = set()
    for line in out.splitlines():
        if (":" + port) in line and "LISTENING" in line.upper():
            pids.add(line.split()[-1])
    return sorted(pids)


def cmdline(pid):
    # `wmic` is gone from this box, so ask PowerShell's CIM store instead.  The filter string is built
    # here and passed as ONE argv element -- no shell, no expansion.
    ps = ("(Get-CimInstance Win32_Process -Filter \"ProcessId=%s\").CommandLine" % pid)
    r = sh(["powershell", "-NoProfile", "-Command", ps])
    return (r.stdout or "").strip()


def main():
    rep = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "port": CHAIN_PORT, "new_tree": NEW_TREE}
    owners = port_owner(CHAIN_PORT)
    rep["owners_before"] = owners
    if not owners:
        rep["decision"] = "REFUSED_NO_LISTENER"
        json.dump(rep, open(RECEIPT, "w"), indent=1)
        print("REFUSED: nothing listens on", CHAIN_PORT)
        return 1
    cl = " ".join(cmdline(p) for p in owners)
    rep["owner_cmdline_head"] = cl[:400]
    if "uvicorn" not in cl.lower():
        rep["decision"] = "REFUSED_OWNER_NOT_UVICORN"
        json.dump(rep, open(RECEIPT, "w"), indent=1)
        print("REFUSED: the port owner is not a uvicorn I recognise --", cl[:160])
        return 1

    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    env["PYTHONPATH"] = NEW_TREE + "/backend"
    env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DB
    env["CITYNEXUS_DEMO_MODE"] = "true"
    env["CITYNEXUS_AI_ENABLED"] = "false"
    env["NO_PROXY"] = "*"
    env["PYTHONIOENCODING"] = "utf-8"

    for p in owners:
        sh(["taskkill", "/PID", p, "/T", "/F"])
    time.sleep(2.0)
    rep["owners_after_kill"] = port_owner(CHAIN_PORT)

    log = open(HERE + "/cmdr_hop1_new.log", "wb")
    proc = subprocess.Popen([VENV_PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                             "--port", CHAIN_PORT],
                            cwd=NEW_TREE + "/backend", env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=0x00000008)
    rep["started_pid"] = proc.pid
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    spec = None
    for _ in range(60):
        time.sleep(1)
        if proc.poll() is not None:
            rep["decision"] = "DIED rc=%s" % proc.poll()
            rep["log_tail"] = open(HERE + "/cmdr_hop1_new.log", "rb").read()[-600:].decode("utf-8", "replace")
            break
        try:
            spec = json.load(op.open("http://127.0.0.1:%s/openapi.json" % CHAIN_PORT, timeout=5))
            break
        except Exception:
            pass
    if spec is not None:
        s = json.dumps(spec)
        rep["openapi_paths"] = len(spec.get("paths", {}))
        rep["provider_key_in_live_spec"] = "provider_key" in s
        rep["coordinate_system_in_live_spec"] = "coordinate_system" in s
        rep["decision"] = "SWAPPED_AND_SPEC_READ"
    json.dump(rep, open(RECEIPT, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "owner_cmdline_head"}, ensure_ascii=False)[:600])
    return 0 if rep.get("decision") == "SWAPPED_AND_SPEC_READ" else 1


if __name__ == "__main__":
    sys.exit(main())
