"""Try, on this generation, the one CSS rule that was measured useless on the previous one.

At 390x844 the census on tip 514b397f answers 5 of 6 stop controls reachable by centre hit: index 1
(Riverside Museum) sits with its centre on the fixed bottom nav's 「地图」 button after the browser's
own `scrollIntoViewIfNeeded`, on the base bundle and on my candidate alike.  Desktop 1280x800 is 6 of
6.  An earlier generation measured `scroll-margin-bottom` on `.trip-stop` as changing nothing, so the
rule was taken out rather than shipped as decoration -- but the rows grew since then (ORD-0510's
collect entry and ORD-0530's day grouping), so the measurement belongs again, now.

This script only answers one question: with the rule present, does the census reach 6 of 6?  It boots
this lane's backend on its own port with a fresh private store, serves the rebuilt face, runs the
arm, and prints the census.  Keeping or dropping the rule is then decided from that number.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
DB = os.path.join(LANE, "run", "phone_scrolltest.db")
BACKEND_PORT = 8147
FACE_PORT = 4883
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def env_clean(extra=None):
    e = {k: v for k, v in os.environ.items()
         if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY")}
    if extra:
        e.update(extra)
    return e


def listener(port):
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], stdout=subprocess.PIPE,
                         timeout=30).stdout
    for line in out.decode("gbk", errors="replace").splitlines():
        q = line.split()
        if len(q) >= 5 and q[0].upper() == "TCP" and q[1].endswith(":%d" % port) \
                and q[3].upper() == "LISTENING":
            return q[4]
    return None


def stop(pid):
    if pid and str(pid).isdigit():
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)


stop(listener(BACKEND_PORT))
stop(listener(FACE_PORT))
for suffix in ("", "-wal", "-shm"):
    if os.path.exists(DB + suffix):
        os.remove(DB + suffix)
src = sqlite3.connect("file:" + SHARED.replace("\\", "/") + "?mode=ro", uri=True)
dst = sqlite3.connect(DB)
src.backup(dst)
dst.close()
src.close()

log = os.path.join(LANE, "run", "scrolltest_backend.log")
ps = ("$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:DEEPSEEK_API_KEY=''; "
      "$env:PYTHONPATH='%s'; $env:CITYNEXUS_DATABASE_URL='sqlite:///%s'; "
      "$env:CITYNEXUS_DEMO_MODE='true'; $env:CITYNEXUS_AI_ENABLED='false'; "
      "Start-Process -FilePath '%s' -ArgumentList '-m','uvicorn','app.main:app',"
      "'--host','127.0.0.1','--port','%d' -WorkingDirectory '%s' -WindowStyle Hidden "
      "-RedirectStandardOutput '%s' -RedirectStandardError '%s.out'"
      % (LANE + "/wt19", DB.replace("\\", "/"), PY, BACKEND_PORT,
         LANE + "/wt19/backend", log, log))
with open(log + ".launcher", "ab") as sink:
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdout=sink, stderr=sink,
                   timeout=90)
for _ in range(45):
    time.sleep(2)
    try:
        with op.open("http://127.0.0.1:%d/api/v1/demo/scene" % BACKEND_PORT, timeout=10) as r:
            if r.status == 200:
                break
    except Exception:
        continue
else:
    raise SystemExit("ABORT_BACKEND")

face = os.path.join(LANE, "faces", "o0500_r4_scrollfix")
if os.path.exists(face):
    shutil.rmtree(face)
p = subprocess.run([NODE, "node_modules/vite/bin/vite.js", "build", "--outDir", face,
                    "--emptyOutDir"], cwd=os.path.join(LANE, "wt19", "frontend"),
                   env=env_clean(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
open(os.path.join(LANE, "run", "scrolltest_build.txt"), "w", encoding="utf-8").write(
    p.stdout.decode("utf-8", "replace"))
entry = None
html = open(os.path.join(face, "index.html"), encoding="utf-8").read()
import re
m = re.search(r'src="/assets/(index-[\w\-]+\.js)', html)
entry = m.group(1) if m else None
print("build exit", p.returncode, "entry", entry)

logf = os.path.join(LANE, "run", "scrolltest_face.log")
with open(logf, "ab") as sink:
    subprocess.Popen([NODE, "node_modules/vite/bin/vite.js", "preview", "--outDir", face,
                      "--host", "127.0.0.1", "--port", str(FACE_PORT), "--strictPort"],
                     cwd=os.path.join(LANE, "wt19", "frontend"),
                     env=env_clean({"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)}),
                     creationflags=0x208, stdout=sink, stderr=sink)
for _ in range(30):
    time.sleep(2)
    try:
        with op.open("http://127.0.0.1:%d/" % FACE_PORT, timeout=10):
            break
    except Exception:
        continue

out = os.path.join(LANE, "evidence", "checkin_SCROLLTEST_phone_390x844_r2.json")
if os.path.exists(out):
    os.remove(out)
p2 = subprocess.run([NODE, os.path.join(LANE, "tools", "checkin_phone_r2.cjs"),
                     "http://127.0.0.1:%d" % FACE_PORT, out, "SCROLLTEST", "390", "844"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env_clean(), timeout=420)
print(p2.stdout.decode("utf-8", "replace").strip()[-300:])
d = json.load(open(out, encoding="utf-8"))
cen = [r for r in d["rows"] if r["arm"].endswith("_2_census_after_scroll")][0]["buttons"]
for b in cen:
    print("  idx %s %s box %dx%d centre_hit=%s hit=%s nav=%s" % (
        b["index"], b["stop"][:18], b["box"]["w"], b["box"]["h"], b["hit_self"],
        (b.get("hit_words") or "")[:8], b.get("overlaps_nav")))
print("PRESSABLE_WITH_RULE %d of %d" % (sum(1 for b in cen if b["hit_self"]), len(cen)))
stop(listener(FACE_PORT))
stop(listener(BACKEND_PORT))
