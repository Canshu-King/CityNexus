"""CMDR lan static port restore r1 -- bring 127.0.0.1:4783 back with the same generation it lost.

Root cause this repairs: the listener was serving `_build_day33/frontend/dist`, and that export tree no
longer exists on disk (a commander-side `_build_*` sweep), so every request died before writing a response.
The deaf process is a commander-owned instrument (`_cmdr_lan_static_api_r1.py`), not a human-owned service;
the api behind it (:4787) is healthy and is left running.

Everything it does is named and read back: kill the one PID it verified owns the port, relaunch on the same
port with a dist rebuilt from the recorded sha, then probe five paths and compare served bytes to disk bytes.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = 4783
API = 4787
LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
DIST = os.path.join(LIVE, "_build_0413e55", "frontend", "dist")
ENTRY = "index-BcQ9VAso.js"
SHA = "0413e55634e9c6953ea88a4b01a17b8afd7ac88a"
SCRIPT = os.path.join(LIVE, "_cmdr_lan_static_api_r1.py")
LOG = os.path.join(LIVE, "_lan_4783_log_restored_r1.json")
DETACHED = 0x00000008 | 0x00000200

if not os.path.exists(os.path.join(DIST, "index.html")):
    sys.exit("ABORT: dist has no index.html -- " + DIST)


def listeners(port):
    txt = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    out = []
    for line in txt.splitlines():
        up = line.upper()
        if (":" + str(port) + " ") in line and "LISTENING" in up:
            out.append(line.split()[-1])
    return out


def owner(pid):
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(pid) +
          "' | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                       text=True, timeout=120).stdout.strip()
    try:
        return json.loads(r)
    except Exception:
        return {}


before = listeners(PORT)
owners = []
for pid in before:
    o = owner(pid)
    owners.append({"pid": pid, "name": o.get("Name"), "cmdline": (o.get("CommandLine") or "")[:200]})

# refuse to touch anything that is not our own static proxy
foreign = [o for o in owners if "_cmdr_lan_static_api_r1.py" not in (o["cmdline"] or "")]
if foreign:
    print(json.dumps({"verdict": "REFUSED_FOREIGN_OWNER", "listeners": owners}, ensure_ascii=False, indent=1))
    sys.exit(2)

killed = []
for o in owners:
    r = subprocess.run(["taskkill", "/PID", str(o["pid"]), "/T", "/F"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    killed.append({"pid": o["pid"], "rc": r.returncode, "out": (r.stdout or r.stderr).strip()[:120]})
for _ in range(20):
    if not listeners(PORT):
        break
    time.sleep(0.5)
freed = not listeners(PORT)

env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    env.pop(k, None)
logf = open(LOG, "ab")
child = subprocess.Popen([sys.executable, SCRIPT, "--dist", DIST, "--port", str(PORT),
                          "--api", str(API), "--log", LOG],
                         cwd=LIVE, env=env, stdout=logf, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, creationflags=DETACHED, close_fds=True)

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def fetch(path):
    t0 = time.time()
    try:
        with opener.open(urllib.request.Request("http://127.0.0.1:" + str(PORT) + path,
                                                headers={"User-Agent": "cnx-cmdr-restore-r1"}),
                         timeout=10) as f:
            return f.status, len(f.read()), round((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        return e.code, len(e.read()), round((time.time() - t0) * 1000)
    except Exception as e:
        return None, type(e).__name__, round((time.time() - t0) * 1000)


probes = {}
ready_after_s = None
for i in range(60):
    st, size, ms = fetch("/index.html")
    if st == 200:
        ready_after_s = i
        break
    time.sleep(1.0)

paths = ["/", "/v8/hub", "/index.html", "/favicon.svg", "/assets/" + ENTRY]
for pth in paths:
    probes[pth] = fetch(pth)

disk = open(os.path.join(DIST, "assets", ENTRY), "rb").read()
st_last, size_last, ms_last = probes["/assets/" + ENTRY]
entry_equal = (st_last == 200 and size_last == len(disk))

receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "port": PORT, "api": API,
           "dist": DIST, "rebuilt_from_sha": SHA, "listeners_before": owners, "killed": killed,
           "port_freed": freed, "child_pid": child.pid, "ready_after_s": ready_after_s,
           "owner_after": owner(listeners(PORT)[0]) if listeners(PORT) else None,
           "probes": {k: list(v) for k, v in probes.items()},
           "entry_asset": ENTRY, "entry_disk_bytes": len(disk),
           "entry_served_bytes": size_last if st_last == 200 else None,
           "entry_bytes_match_disk": entry_equal,
           "log": LOG}
print(json.dumps(receipt, ensure_ascii=False, indent=1))
ok = (freed and entry_equal and sum(1 for v in probes.values() if v[0] == 200) == len(paths))
sys.exit(0 if ok else 1)
