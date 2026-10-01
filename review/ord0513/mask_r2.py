"""ORD-0513 · the vocabulary-channel counterexample, run honestly.

The previous cut of this measurement reported the masked phase green while `vite build` had actually
exited 1: the running preview server holds `dist/` open on Windows, so the rebuild never landed and
the browser was served the unmasked bundle.  A green taken off bytes that were never shipped is the
false green this order is not allowed to deliver.

So this file does three things the earlier one did not:
  stops the static server before every build,
  asserts the build exited 0,
  asserts the entry the server answers with CHANGED between the two generations, and aborts rather
  than reporting a number it did not ship.

argv: python ord0513_mask_r2.py
"""
import io
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
WT = r"D:/moodle/_qoder_newlane_ord0444_20260929/wt2"
BACKEND = os.path.join(WT, "backend")
FRONTEND = os.path.join(WT, "frontend")
SC = r"D:/moodle/_qoder_newlane_ord0444_20260929/scratch"
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
NPM = r"C:/Program Files/nodejs/npm.cmd"
ARM = os.path.join(SC, "ord0513_arm_r1.cjs")
COPY = "frontend/src/features/collections/collectionCopy.ts"
PREVIEW_DB = r"D:/moodle/_qoder_preview_20260920/_preview.db"
BASE_REV = "0c061d9eb74b21f0b0b297a068778479b08658b4"
OUT = os.path.join(SC, "ord0513_mask_r2_%s.json" % BASE_REV[:8])
ENV = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)


def sh(cwd, *a, timeout=1200):
    r = subprocess.run(list(a), cwd=cwd, env=ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


out = {"started": time.strftime("%m-%d %H:%M:%S"), "head": sh(WT, "git", "rev-parse", "HEAD")[1].strip()}
preview_stat0 = os.stat(PREVIEW_DB)
copy_now = io.open(os.path.join(WT, COPY), "rb").read()
db = os.path.join(BACKEND, "ord0513_mask_%d.db" % (int(time.time()) % 100000))
shutil.copyfile(PREVIEW_DB, db)
PORT = free_port()
env = dict(ENV, CITYNEXUS_DATABASE_URL="sqlite:///./" + os.path.basename(db),
           CITYNEXUS_DEMO_MODE="true")
log = io.open(os.path.join(SC, "uvicorn_0513_mask.log"), "wb")
kid = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(PORT)], cwd=BACKEND, env=env, stdout=log,
                       stderr=subprocess.STDOUT)
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=data, method=method)
    if data:
        req.add_header("content-type", "application/json")
    try:
        with OP.open(req, timeout=25) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"head": raw[:120].decode("utf-8", "replace")}


for _ in range(200):
    try:
        with OP.open("http://127.0.0.1:%d/api/v1/health" % PORT, timeout=6) as r:
            if r.status == 200:
                break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("backend never came up")

with sqlite3.connect("file:%s?mode=ro" % PREVIEW_DB.replace("\\", "/"), uri=True) as s:
    jid, owner = s.execute("SELECT id, traveler_id FROM journeys LIMIT 1").fetchone()
made = http("POST", "/api/v1/collections", {"name": "ORD-0513 反例架", "owner_traveler_id": owner})
out["shelf"] = {"created": made[0], "listed": len(http("GET", "/api/v1/collections?traveler_id=%s"
                                                       % owner)[1] or [])}
print("shelf:", out["shelf"])

pchild = None


def start_preview():
    global pchild
    port = free_port()
    handle = io.open(os.path.join(SC, "vite_preview_0513_mask.log"), "wb")
    pchild = subprocess.Popen(["node", os.path.join(FRONTEND, "node_modules", "vite", "bin",
                                                    "vite.js"), "preview", "--host", "127.0.0.1",
                               "--port", str(port), "--strictPort"], cwd=FRONTEND,
                              env=dict(ENV, CITYNEXUS_BACKEND_PORT=str(PORT)), stdout=handle,
                              stderr=subprocess.STDOUT)
    for _ in range(150):
        try:
            with OP.open("http://127.0.0.1:%d/index.html" % port, timeout=8) as r:
                if r.status == 200:
                    html = r.read().decode("utf-8", "replace")
                    entry = re.findall(r"/assets/(index-[A-Za-z0-9_\-]+\.js)", html)[:1]
                    if entry:
                        return port, entry[0]
        except Exception:
            time.sleep(1)
    raise SystemExit("the static server never answered with a named entry")


def stop_preview():
    global pchild
    if pchild:
        subprocess.run(["taskkill", "/PID", str(pchild.pid), "/T", "/F"], capture_output=True)
        time.sleep(3)
        pchild = None


def arms(port, tag):
    rows = []
    for shape in ("390x844", "1280x900"):
        for locale in ("zh-CN", "en"):
            wr = subprocess.run(["node", ARM, "http://127.0.0.1:%d" % port, locale, jid, shape, tag],
                                cwd=FRONTEND,
                                env=dict(ENV, NODE_PATH=os.path.join(FRONTEND, "node_modules")),
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=600)
            payload = {}
            for line in wr.stdout.splitlines():
                if line.strip().startswith("{"):
                    payload = json.loads(line)
            rows.append({"shape": shape, "locale": locale, "exit": wr.returncode,
                         "failures": payload.get("failures"), "checks": payload.get("checks"),
                         "console_errors": payload.get("console_errors")})
    # merge, do not replace: an earlier cut wrote the entry name here and arms() then overwrote the
    # whole dict, so the artifact could not show which bytes each row was taken against.
    gen = out["generations"].setdefault(tag, {})
    gen["rows"] = rows
    gen["all_green"] = all(r["exit"] == 0 for r in rows)
    print("%-10s %s" % (tag, " ".join("%s/%s:%d" % (r["shape"], r["locale"], r["exit"])
                                      for r in rows)))
    return rows


# ---- generation 1: the shipped words
rc0, txt0 = sh(FRONTEND, NPM, "run", "build", timeout=900)
built_human = re.findall(r"/assets/(index-[A-Za-z0-9_\-]+\.js)",
                         io.open(os.path.join(FRONTEND, "dist", "index.html"),
                                 encoding="utf-8").read())[:1]
out["human_build"] = {"exit": rc0, "built_entry": built_human}
assert rc0 == 0, "the human-copy build did not succeed: " + txt0[-200:]
port, entry_human = start_preview()
assert entry_human == built_human[0] and entry_human, (
    "the server answered %s but the build wrote %s -- the human generation is not what I shipped"
    % (entry_human, built_human))
out["generations"] = {"human_copy": {"entry": entry_human}}
out["entry_human"] = entry_human
arms(port, "human_copy")
stop_preview()

# ---- generation 2: the vocabulary channel masked -- the machine token is what reaches the glass
ZH_LINE = '    zh: "这一枚已经在这个架子上。",'
EN_LINE = '    en: "This place is already on that shelf.",'
s = io.open(os.path.join(WT, COPY), encoding="utf-8").read()
assert s.count(ZH_LINE) == 1 and s.count(EN_LINE) == 1, (s.count(ZH_LINE), s.count(EN_LINE))
s = s.replace(ZH_LINE, '    zh: "PLACE_ALREADY_IN_COLLECTION",', 1)
s = s.replace(EN_LINE, '    en: "PLACE_ALREADY_IN_COLLECTION",', 1)
def restore_tree():
    """Put the tree back and rebuild, on EVERY exit path. An earlier cut of this file aborted after
    writing the mask and before restoring it, so the worktree was left holding `PLACE_ALREADY_IN_
    COLLECTION` in the copy table -- another run reading that file found "no such needle" and the
    dirty bytes would have ridden into the next diff."""
    io.open(os.path.join(WT, COPY), "wb").write(copy_now)
    rcb, txrb = sh(FRONTEND, NPM, "run", "build", timeout=900)
    out["restored_build"] = {"exit": rcb, "tail": txrb[-200:]}


import atexit
atexit.register(restore_tree)
io.open(os.path.join(WT, COPY), "w", encoding="utf-8", newline="\n").write(s)
rc, txt = sh(FRONTEND, NPM, "run", "build", timeout=900)
out["masked_build"] = {"exit": rc, "tail": txt[-500:]}
assert rc == 0, "the masked build did not succeed: " + txt[-300:]
built_masked = re.findall(r"/assets/(index-[A-Za-z0-9_\-]+\.js)",
                          io.open(os.path.join(FRONTEND, "dist", "index.html"),
                                  encoding="utf-8").read())[:1]
out["masked_build"]["built_entry"] = built_masked
port2, entry_masked = start_preview()
out["generations"]["masked_copy"] = {"entry": entry_masked}
out["entry_masked"] = entry_masked
assert entry_masked == built_masked[0], (
    "the server answered %s while the masked build wrote %s" % (entry_masked, built_masked))
assert entry_masked != entry_human, (
    "the server answered the SAME entry after a successful rebuild (%s) -- the counterexample would "
    "be measuring bytes it did not ship, so this run aborts instead of reporting" % entry_masked)
rows = arms(port2, "masked_copy")
stop_preview()

# every masked row must be red, and red on the machine-token check -- anything else says the arm is
# not reading the words it claims to read.
token_red = [c["check"] for r in rows for c in (r["checks"] or [])
             if c["held"] is False and "machine token" in c["check"]]
out["verdict"] = {
    "human_copy_green": out["generations"]["human_copy"]["all_green"],
    "masked_all_red": all(r["exit"] != 0 for r in rows),
    "masked_red_on_the_machine_token_check": len(token_red),
    "entries_differ": entry_masked != entry_human,
}
out["verdict"]["counterexample_holds"] = all([
    out["verdict"]["human_copy_green"], out["verdict"]["masked_all_red"],
    out["verdict"]["masked_red_on_the_machine_token_check"] >= 4,
    out["verdict"]["entries_differ"]])
io.open(os.path.join(WT, COPY), "wb").write(copy_now)
rc, txt = sh(FRONTEND, NPM, "run", "build", timeout=900)
out["restored_build"] = {"exit": rc}
subprocess.run(["taskkill", "/PID", str(kid.pid), "/T", "/F"], capture_output=True)
log.close()
time.sleep(5)
for p in (db,):
    for suffix in ("", "-wal", "-shm"):
        try:
            if os.path.exists(p + suffix):
                os.remove(p + suffix)
        except PermissionError:
            print("LEFTOVER_DB", p + suffix)
ps1 = os.stat(PREVIEW_DB)
out["preview_store_untouched"] = {"bytes_equal": preview_stat0.st_size == ps1.st_size,
                                  "mtime_ns_equal": preview_stat0.st_mtime_ns == ps1.st_mtime_ns,
                                  "bytes_before": preview_stat0.st_size, "bytes_after": ps1.st_size}
out["worktree_after"] = sh(WT, "git", "status", "--porcelain")[1].strip()
io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
print("verdict:", json.dumps(out["verdict"], ensure_ascii=False))
print("entries:", entry_human, "->", entry_masked, "| restored build exit", rc)
