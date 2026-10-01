"""ORD-0530 screen reach: bring the stack up at 5a4cdbd2 -- bring the stack back up on the same copy.

The line moved under the block (`frontend/src/app/v8PanelRegistry.tsx` is what changed, read from
`git diff --name-only`), so the grouping arms and the failure sentence that goes through the same
mount are replayed on the new bytes.  The library is the same copy, and it is only used after the
marker row this lane wrote is read back through the door.
"""
import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request

ROOT = "D:/moodle/_qoder_ai_ord0387_20260928"
WT = ROOT + "/wt"
DB = ROOT + "/ord0530_denominator_r3.db"
JOURNEY = "22222222-2222-4222-8222-222222222222"
MARKER = "ORD-0530 r3 分母 · 昨天的第三枚"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = "C:/Program Files/nodejs/node.exe"
VITE = ROOT + "/node_modules/vite/bin/vite.js"


def clean_env(extra=None):
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
              "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "OPENAI_API_KEY"):
        e.pop(k, None)
    e["CITYNEXUS_AI_ENABLED"] = "false"
    e.update(extra or {})
    return e


def free_pair():
    out = []
    for _ in range(2):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        out.append(s.getsockname()[1])
        s.close()
    return out


bp, fp = free_pair()
be_log = open(ROOT + "/ord0530_backend_r8.log", "w", encoding="utf-8", newline="\n")
be = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                       "--port", str(bp), "--log-level", "info"], cwd=WT + "/backend",
                      env=clean_env({"CITYNEXUS_DATABASE_URL": "sqlite:///" + DB}),
                      stdout=be_log, stderr=subprocess.STDOUT)


def get(url, timeout=15):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return None, repr(e).encode()


health = None
for _ in range(90):
    st, _b = get("http://127.0.0.1:%d/api/v1/health" % bp)
    if st == 200:
        health = st
        break
    time.sleep(1)

fe_log = open(ROOT + "/ord0530_vite_r8.log", "w", encoding="utf-8", newline="\n")
fe = subprocess.Popen([NODE, VITE, "--port", str(fp), "--strictPort", "--host", "127.0.0.1"],
                      cwd=WT + "/frontend", env=clean_env({"CITYNEXUS_BACKEND_PORT": str(bp)}),
                      stdout=fe_log, stderr=subprocess.STDOUT)
served = None
for _ in range(60):
    st, _b = get("http://127.0.0.1:%d/v8/footprints" % fp)
    if st == 200:
        served = st
        break
    time.sleep(1)

st, body = get("http://127.0.0.1:%d/api/v1/journeys/%s/checkins" % (bp, JOURNEY))
rows = json.loads(body.decode()) if st == 200 else []
mine = open(WT + "/frontend/index.html", "rb").read()
st2, entry = get("http://127.0.0.1:%d/index.html" % fp)
receipt = {"at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "backend_port": bp, "frontend_port": fp,
           "backend_pid": be.pid, "frontend_pid": fe.pid,
           "health": health, "frontend_status": served,
           "ownership": {"door_http_status": st, "rows": len(rows),
                         "marker_row_present": any(MARKER in (r.get("note") or "") for r in rows),
                         "instants": [r["stamped_at"] for r in rows]},
           "entry_bytes_equal_my_disk": st2 == 200 and entry == mine,
           "provenance_line": "private stack: frontend=:%d -> backend=:%d db=%s ai=disabled"
                              % (fp, bp, os.path.basename(DB))}
dst = ROOT + "/ord0530_reads_r5/stack_receipt_r8.json"
json.dump(receipt, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(receipt, ensure_ascii=False, indent=1))
