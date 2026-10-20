"""Bring THIS lane's phone stack up and prove it up by asking it, not by looking for a listener.

Why a third generation: r1 hardcoded a tree that no longer exists, and r2 -- which is published on the
hand ref and must not be rewritten -- declares BACKEND_NEVER_ANSWERED from `netstat` while the very same
run's uvicorn log said "Uvicorn running".  On this box netstat sometimes answers with a statistics notice
instead of the table, so a listener lookup is not a readiness test.  Here readiness is the HTTP probe
itself, and the probe's own exception text is carried into the receipt: an instrument that drops the
reason it failed is worse than a silent one.

The static leg is started the same way: vite preview binds to 127.0.0.1 and takes its backend port from
the environment inside the cmd it runs in, because `VAR=x cmd` through bash on this box sets positional
parameters instead of the environment, which silently proxies to the default port and reads as a 500.

Ports are mine (backend 8145, static 4894); 4783/4787/4799 belong to the commander and are never touched.
The shared preview DB is opened read-only and copied with sqlite's backup(), then re-stat'ed so the
receipt can prove the shared file was never written.

argv: python building_stack_up_r3.py --tree TREE --db FILE --backend-port N --static-port N --tag TAG --out FILE
"""
import argparse
import json
import os
import socket
import sqlite3
import subprocess
import time
import urllib.request

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
NODE = r"C:/Program Files/nodejs/node.exe"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def listener(port):
    """Best-effort: returns the pid, or None when netstat answers with something unparsable.
    Readiness never depends on this -- it is only the pre-flight that refuses to sit on someone else's
    port, and when it cannot read, the caller falls through to the real test."""
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "tcp"], stdout=subprocess.PIPE,
                             timeout=30).stdout
    except Exception:
        return "UNKNOWN"
    for line in out.decode("gbk", errors="replace").splitlines():
        q = line.split()
        if len(q) >= 5 and q[0].upper() == "TCP" and q[1].endswith(":%d" % port) \
                and q[3].upper() == "LISTENING":
            return q[4]
    return None


def port_open_locally(port):
    s = socket.socket()
    s.settimeout(1.0)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def fresh_store(db):
    for suffix in ("", "-wal", "-shm"):
        p = db + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                time.sleep(1)
                os.remove(p)
    before = os.stat(SHARED)
    src = sqlite3.connect("file:" + SHARED.replace("\\", "/") + "?mode=ro", uri=True)
    dst = sqlite3.connect(db)
    src.backup(dst)
    dst.close()
    src.close()
    after = os.stat(SHARED)
    return {"shared_bytes_before": before.st_size, "shared_mtime_before": before.st_mtime,
            "shared_bytes_after": after.st_size, "shared_mtime_after": after.st_mtime,
            "shared_untouched": (before.st_size == after.st_size and before.st_mtime == after.st_mtime),
            "private_store_bytes": os.path.getsize(db)}


def start(ps, log):
    open(log, "ab").close()
    with open(log + ".launcher", "ab") as sink:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdout=sink, stderr=sink,
                       timeout=120)


def probe(url, tries=45, pause=2.0):
    last = None
    for _ in range(tries):
        try:
            with opener.open(url, timeout=10) as r:
                return {"ready": True, "http_status": r.status, "bytes": len(r.read()),
                        "url": url, "tries": tries}
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, str(e)[:160])
            time.sleep(pause)
    return {"ready": False, "url": url, "last_probe_error": last}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--backend-port", type=int, required=True)
    ap.add_argument("--static-port", type=int, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tree = os.path.abspath(a.tree)
    if not os.path.isdir(os.path.join(tree, "backend")):
        raise SystemExit("ABORT_TREE_INCOMPLETE -- no backend/ under " + tree)
    doc = {"tree": tree, "started": time.strftime("%F %T"), "backend_port": a.backend_port,
           "static_port": a.static_port}

    for port, label in ((a.backend_port, "backend"), (a.static_port, "static")):
        doc["%s_port_pid" % label] = listener(port)
        doc["%s_already_up" % label] = port_open_locally(port)

    if not doc["backend_already_up"]:
        doc["store"] = fresh_store(a.db)
        if not doc["store"]["shared_untouched"]:
            raise SystemExit("ABORT_SHARED_DB_MOVED -- the read-only open did not stay read-only")
        blog = os.path.join(LANE, "run", "walk_backend_%s.log" % a.tag)
        ps = ("$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:DEEPSEEK_API_KEY=''; $env:NO_PROXY='*'; "
              "$env:PYTHONPATH='%s'; $env:CITYNEXUS_DATABASE_URL='sqlite:///%s'; "
              "$env:CITYNEXUS_DEMO_MODE='true'; $env:CITYNEXUS_AI_ENABLED='false'; "
              "Start-Process -FilePath '%s' -ArgumentList '-m','uvicorn','app.main:app','--host',"
              "'127.0.0.1','--port','%d' -WorkingDirectory '%s' -WindowStyle Hidden "
              "-RedirectStandardOutput '%s' -RedirectStandardError '%s'"
              % (tree, a.db.replace("\\", "/"), PY, a.backend_port, os.path.join(tree, "backend"),
                 blog, blog + ".err"))
        start(ps, blog)
        doc["backend_probe"] = probe("http://127.0.0.1:%d/api/v1/demo/scene" % a.backend_port)
        if not doc["backend_probe"]["ready"]:
            doc["backend_err_tail"] = open(blog + ".err", encoding="utf-8",
                                           errors="replace").read()[-700:]
            json.dump(doc, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print(json.dumps(doc, indent=1, ensure_ascii=False))
            raise SystemExit("ABORT_BACKEND_NOT_READY -- " + str(doc["backend_probe"]["last_probe_error"]))
    else:
        doc["backend_probe"] = probe("http://127.0.0.1:%d/api/v1/demo/scene" % a.backend_port, tries=3)
        doc["backend_note"] = ("this leg was already answering on my own port before the run; nothing "
                               "was started twice")
        if not doc["backend_probe"]["ready"]:
            json.dump(doc, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            raise SystemExit("ABORT_PORT_OCCUPIED_BUT_NOT_ANSWERING backend %d -- "
                             "%s" % (a.backend_port, doc["backend_probe"]["last_probe_error"]))

    if not doc["static_already_up"]:
        slog = os.path.join(LANE, "run", "walk_static_%s.log" % a.tag)
        front = os.path.join(tree, "frontend")
        # A batch file, not an inline command: PowerShell cannot bind an -ArgumentList string that
        # carries both `&&` and quoted absolute paths with spaces (PositionalParameterNotFound), and
        # that failure looks exactly like "vite would not start".
        batch = os.path.join(LANE, "run", "start_static_%s.cmd" % a.tag)
        with open(batch, "w", encoding="ascii", newline="\r\n") as fh:
            fh.write("@echo off\r\n")
            fh.write("set HTTP_PROXY=\r\nset HTTPS_PROXY=\r\nset NO_PROXY=\r\n")
            fh.write("set CITYNEXUS_BACKEND_PORT=%d\r\n" % a.backend_port)
            fh.write('cd /d "%s"\r\n' % front)
            fh.write('"C:\\Program Files\\nodejs\\node.exe" node_modules\\vite\\bin\\vite.js '
                     'preview --host 127.0.0.1 --outDir dist --port %d --strictPort > "%s" 2>&1\r\n'
                     % (a.static_port, slog))
        ps2 = ("Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','%s' -WindowStyle Hidden"
               % batch.replace("\\", "\\\\"))
        start(ps2, slog)
        doc["static_probe"] = probe("http://127.0.0.1:%d/v8/hub" % a.static_port, tries=30)
    else:
        doc["static_probe"] = probe("http://127.0.0.1:%d/v8/hub" % a.static_port, tries=3)
        doc["static_note"] = ("this leg was already answering on my own port before the run; nothing "
                              "was started twice")
    json.dump(doc, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(doc, indent=1, ensure_ascii=False))
    if not doc["static_probe"]["ready"]:
        raise SystemExit("ABORT_STATIC_NOT_READY -- " + str(doc["static_probe"]["last_probe_error"]))


if __name__ == "__main__":
    main()
