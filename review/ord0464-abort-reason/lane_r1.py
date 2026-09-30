"""ORD-0464 lane: this tree's backend on :8713 + this tree's built bundle on :4192.

Both legs refuse rather than adopt a stranger's listener: the scene journey has to be readable from
*this* lane's sqlite copy, and the front has to serve the bundle gate.py just built from the 0464
worktree.  A leftover listener would make the screen readings describe somebody else's product.
"""
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request

WK = r"D:/moodle/_qoder_q_ord0369_wk"
TREE = r"D:/moodle/_qoder_q_ord0464"
EXPORT = os.path.join(WK, "build", "frontend")
DIST = os.path.join(WK, "dist_cand")
MY_DB = os.path.join(WK, "q0386.db")
BACKEND_PORT = 8713
FRONT_PORT = 4192
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SCENE_JID = "9c6c3d73-8b8e-4f71-beaf-32bc87aba035"


def listeners(port):
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True).stdout.decode(
        "gbk", errors="replace"
    )
    return [
        ln.split()[-1]
        for ln in out.splitlines()
        if f":{port} " in ln.replace("\t", " ") and "LISTENING" in ln
    ]


def env(extra=None):
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        e.pop(k, None)
    e["NO_PROXY"] = "*"
    e["PYTHONIOENCODING"] = "utf-8"
    e.update(extra or {})
    return e


def wait_http(url, seconds=45):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(1.0)
    raise SystemExit(f"REFUSE: {url} never answered")


def main():
    for port in (BACKEND_PORT, FRONT_PORT):
        if listeners(port):
            print(f"REFUSE: :{port} is already held by pids {listeners(port)} -- not starting a second")
            sys.exit(2)
    if not os.path.exists(os.path.join(DIST, "index.html")):
        print(f"REFUSE: no built bundle at {DIST}; run gate.py build first")
        sys.exit(2)

    be_log = open(os.path.join(WK, "o0464_backend.log"), "ab")
    be = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=os.path.join(TREE, "backend"),
        env=env({"CITYNEXUS_DATABASE_URL": f"sqlite:///{MY_DB}", "CITYNEXUS_DEMO_MODE": "true"}),
        stdout=be_log,
        stderr=subprocess.STDOUT,
    )
    fe_log = open(os.path.join(WK, "o0464_front.log"), "ab")
    fe = subprocess.Popen(
        [
            "node",
            os.path.join(EXPORT, "node_modules/vite/bin/vite.js"),
            "preview",
            "--outDir",
            DIST,
            "--host",
            "127.0.0.1",
            "--port",
            str(FRONT_PORT),
            "--strictPort",
        ],
        cwd=EXPORT,
        # vite's preview proxy reads this name and defaults to :8000 (`127ce7b05329eaa837701cdb93bdbc2e5d64e10f:frontend/vite.config.ts:143`); without it
        # the front answers its own 500 (text/plain, no error envelope) and the gate would be reading a
        # neighbour's absence instead of this tree's product.
        env=env({"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)}),
        stdout=fe_log,
        stderr=subprocess.STDOUT,
    )
    print("backend pid", be.pid, "front pid", fe.pid)

    scene = wait_http(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/demo/scene")
    jid = str(scene.get("journey_id") or "")
    con = sqlite3.connect(MY_DB)
    mine = con.execute("select count(*) from journeys where id=?", (jid,)).fetchone()[0]
    versions = con.execute(
        "select count(*) from plan_versions where journey_id=?", (jid,)
    ).fetchone()[0]
    deleted = con.execute(
        "select count(*) from journeys where id=? and deleted_at is not null", (jid,)
    ).fetchone()[0]
    con.close()
    print(f"scene journey {jid}: in MY copy={mine} versions={versions} already_binned={deleted}")
    if jid != SCENE_JID or mine != 1 or versions < 3:
        print("REFUSE: the listener is not answering from this lane's copy")
        sys.exit(3)

    served = urllib.request.urlopen(f"http://127.0.0.1:{FRONT_PORT}/", timeout=20).read()
    disk = open(os.path.join(DIST, "index.html"), "rb").read()
    asset = [ln for ln in disk.decode("utf-8", "replace").replace(">", ">\n").splitlines()
             if "assets/index-" in ln]
    print("served index == disk index:", served == disk, "| asset:", (asset[0].strip() if asset else "?")[:120])
    if served != disk:
        print("REFUSE: :4192 is not serving the bundle this tree built")
        sys.exit(4)

    # A stale dist_cand would pass both checks above: index.html and the served bytes agree with each
    # other even when the bundle belongs to an older lane head.  So read the entry asset the served
    # index actually points at and require this order's own feature in it.
    import re

    href = re.search(r"(?:src|href)=\"(/assets/index-[^\"]+\.js)\"", disk.decode("utf-8", "replace"))
    if not href:
        print("REFUSE: the served index names no entry bundle")
        sys.exit(5)
    bundle = urllib.request.urlopen(f"http://127.0.0.1:{FRONT_PORT}{href.group(1)}", timeout=30).read()
    for sentinel in (b"journey-abort", b"ITINERARY_NOT_USEFUL"):
        hits = bundle.count(sentinel)
        print(f"served bundle {href.group(1)}: {sentinel.decode()} hits={hits}")
        if hits == 0:
            print(f"REFUSE: the served bundle has no {sentinel.decode()} -- that is not this tree's front")
            sys.exit(5)
    print("lane up")


main()
