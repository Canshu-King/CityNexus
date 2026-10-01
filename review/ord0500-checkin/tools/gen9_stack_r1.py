"""ORD-0500 / ORD-0485 gen-4 driver -- one face at a time, each on its own fresh private store.

Why a fresh store per run: every arm taps stops, so a shared file would let the first run's stamps
decide the second run's first answer.  Each run re-copies the store from the shared preview DB with
sqlite's `backup()` on a read-only connection (the shared file is never opened for writing) and
re-stats it afterwards, bytes and mtime, in the receipt.

Every subprocess is bounded.  The previous version of this driver hung for two hours inside an
unbounded `subprocess.run` pipe read on the backend launcher, so here the launcher writes to a log
FILE and every call carries a timeout; a step that fails is recorded as ABORT_<name> and the sweep
moves on, instead of the whole run going quiet.

argv: node checkin_phone_r2.cjs <base> <out.json> <tag> <width> <height>
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
DB = os.path.join(LANE, "run", "phone_gen9.db")
BACKEND_PORT = 8141

# label, face dir, tree used as the backend, static port
FACES = [
    ("TIP_b604f50d", "faces/tip9", "wt23", 4869),
    ("O0500_R5", "faces/o0500_r5", "wt22", 4871),
    ("O0500_CLIENTBOOL_MUTANT", "faces/o0500_clientbool9", "wt22", 4872),
    
    # the generation my "手机上打不到卡" sentence was actually measured on: before ORD-0476
    # slice 2 shipped the per-stop control, so this face has no stop-checkin node at all.
    ("PRE_SLICE2_dcb90ccc", "export/frontend/dist", "export", 4873),
]
SHAPES = [("phone", 390, 844), ("desktop", 1280, 800)]
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def env_clean(extra=None):
    e = {k: v for k, v in os.environ.items()
         if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY")}
    if extra:
        e.update(extra)
    return e


def listener(port):
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "tcp"], stdout=subprocess.PIPE,
                             timeout=30).stdout
    except subprocess.TimeoutExpired:
        return "NETSTAT_TIMEOUT"
    for line in out.decode("gbk", errors="replace").splitlines():
        q = line.split()
        if len(q) >= 5 and q[0].upper() == "TCP" and q[1].endswith(":%d" % port) \
                and q[3].upper() == "LISTENING":
            return q[4]
    return None


def stop(pid):
    if not pid or not str(pid).isdigit():
        return "NOTHING_TO_STOP"
    try:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)
    except subprocess.TimeoutExpired:
        return "TASKKILL_TIMEOUT"
    return "STOPPED"


def shared_stat():
    st = os.stat(SHARED)
    return {"bytes": st.st_size, "mtime_local":
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))}


def fresh_store():
    for suffix in ("", "-wal", "-shm"):
        p = DB + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                time.sleep(1)
                os.remove(p)
    src = sqlite3.connect("file:" + SHARED.replace("\\", "/") + "?mode=ro", uri=True)
    dst = sqlite3.connect(DB)
    src.backup(dst)
    dst.close()
    src.close()
    con = sqlite3.connect(DB)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    counts = {"journeys": con.execute("SELECT COUNT(*) FROM journeys").fetchone()[0]}
    counts["journey_checkins"] = (
        con.execute("SELECT COUNT(*) FROM journey_checkins").fetchone()[0]
        if "journey_checkins" in tables else "TABLE_ABSENT_UNTIL_BOOT")
    con.close()
    return counts


def rows_and_keys():
    con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    try:
        rows = [dict(zip([d[0] for d in con.execute(
            "SELECT * FROM journey_checkins LIMIT 0").description], r))
            for r in con.execute("SELECT * FROM journey_checkins ORDER BY stamped_at")]
    except sqlite3.OperationalError as exc:
        con.close()
        return {"ABORT": type(exc).__name__, "reason": str(exc)[:120]}
    con.close()
    return {"count": len(rows), "rows": rows}


def boot_backend(tree):
    """Start this lane's uvicorn outside the shell's job, through Start-Process, bounded."""
    log = os.path.join(LANE, "run", "gen9_backend_%d.log" % BACKEND_PORT)
    open(log, "ab").close()
    ps = ("$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:DEEPSEEK_API_KEY=''; "
          "$env:PYTHONPATH='%s'; $env:CITYNEXUS_DATABASE_URL='sqlite:///%s'; "
          "$env:CITYNEXUS_DEMO_MODE='true'; $env:CITYNEXUS_AI_ENABLED='false'; "
          "Start-Process -FilePath '%s' -ArgumentList '-m','uvicorn','app.main:app',"
          "'--host','127.0.0.1','--port','%d' -WorkingDirectory '%s' -WindowStyle Hidden "
          "-RedirectStandardOutput '%s' -RedirectStandardError '%s'"
          % (LANE + "/" + tree, DB.replace("\\", "/"), PY, BACKEND_PORT,
             LANE + "/" + tree + "/backend", log, log + ".err"))
    with open(os.path.join(LANE, "run", "gen9_launcher.log"), "ab") as sink:
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdout=sink,
                           stderr=sink, timeout=90)
        except subprocess.TimeoutExpired:
            return {"ready": False, "ABORT": "LAUNCHER_TIMEOUT_90S"}
    for _ in range(45):
        time.sleep(2)
        pid = listener(BACKEND_PORT)
        if not pid:
            continue
        try:
            with op.open("http://127.0.0.1:%d/api/v1/demo/scene" % BACKEND_PORT, timeout=10) as r:
                if r.status == 200:
                    scene = json.loads(r.read().decode("utf-8"))
                    return {"ready": True, "pid": pid, "journey_id": scene.get("journey_id"),
                            "evidence_state": scene.get("evidence_state"),
                            "basis": scene.get("basis")}
        except Exception:
            continue
    return {"ready": False, "ABORT": "BACKEND_NEVER_ANSWERED", "pid": listener(BACKEND_PORT)}


def serve(face_dir, port, tree):
    log = os.path.join(LANE, "run", "gen9_face_%d.log" % port)
    with open(log, "ab") as sink:
        try:
            subprocess.Popen([NODE, "node_modules/vite/bin/vite.js", "preview",
                              "--outDir", os.path.join(LANE, face_dir), "--host", "127.0.0.1",
                              "--port", str(port), "--strictPort"],
                             cwd=os.path.join(LANE, tree, "frontend"),
                             env=env_clean({"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)}),
                             creationflags=0x208, stdout=sink, stderr=sink)
        except OSError as exc:
            return {"port": port, "ABORT": "SPAWN_" + type(exc).__name__}
    abs_face = os.path.join(LANE, face_dir)
    for _ in range(30):
        time.sleep(2)
        try:
            with op.open("http://127.0.0.1:%d/" % port, timeout=10) as r:
                html = r.read().decode("utf-8", "replace")
        except Exception:
            continue
        disk = open(os.path.join(abs_face, "index.html"), "rb").read()
        m = re.search(r'src="/assets/(index-[\w\-]+\.js)', html)
        served_js = None
        if m:
            js_path = os.path.join(abs_face, "assets", m.group(1))
            try:
                with op.open("http://127.0.0.1:%d/assets/%s" % (port, m.group(1)), timeout=30) as r:
                    served_js = r.read()
            except Exception:
                served_js = None
        entry = {"port": port, "face_dir": face_dir,
                 "entry_asset": m.group(1) if m else None,
                 "index_bytes_served": len(html.encode("utf-8")),
                 "index_bytes_on_disk": len(disk),
                 "index_local_sha1_served": hashlib.sha1(html.encode("utf-8")).hexdigest(),
                 "index_local_sha1_disk": hashlib.sha1(disk).hexdigest(),
                 "index_bytes_equal_served_vs_disk":
                     hashlib.sha1(html.encode("utf-8")).hexdigest()
                     == hashlib.sha1(disk).hexdigest(),
                 "bundle_local_sha1_served": hashlib.sha1(served_js).hexdigest()
                 if served_js else "NOT_READ",
                 "bundle_local_sha1_disk": hashlib.sha1(open(js_path, "rb").read()).hexdigest()
                 if js_path and os.path.exists(js_path) else "NOT_READ",
                 "listener_pid": listener(port)}
        entry["bundle_bytes_equal_served_vs_disk"] = (
            entry["bundle_local_sha1_served"] == entry["bundle_local_sha1_disk"])
        # third proof: does anything this server answered look like a request line in a log?
        entry["access_log_proof"] = "NOT_AVAILABLE_BY_CMDR"
        return entry
    return {"port": port, "face_dir": face_dir, "ABORT": "FACE_NEVER_ANSWERED"}


def arm(face_url, tag, width, height):
    out = os.path.join(LANE, "evidence", "checkin_%s_%dx%d_r2.json" % (tag, width, height))
    cmd = [NODE, os.path.join(LANE, "tools", "checkin_phone_r2.cjs"), face_url, out, tag,
           str(width), str(height)]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=env_clean(), timeout=420)
    except subprocess.TimeoutExpired:
        return {"ABORT": "ARM_TIMEOUT_420S", "out": os.path.basename(out)}
    text = p.stdout.decode("utf-8", "replace")
    return {"exit": p.returncode, "line": text.strip().splitlines()[-1] if text.strip() else "",
            "evidence": os.path.basename(out), "bytes": os.path.getsize(out)
            if os.path.exists(out) else 0}


def screen_rows(evidence_path):
    p = os.path.join(LANE, "evidence", evidence_path)
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    pick = {}
    for row in d.get("rows", []):
        st = row.get("state") or {}
        if row["arm"].endswith("_1_arrived"):
            pick["arrived"] = {"stops": st.get("stop_count"),
                               "controls": st.get("checkin_button_count"),
                               "marks": st.get("marks_stamped_words"),
                               "fresh_words": st.get("fresh_words"),
                               "visible_testids": st.get("visible_testid_count"),
                               "rendered_chars": st.get("rendered_chars")}
        if row["arm"].endswith("_4_after_tapping_the_same_stop_again"):
            pick["after_duplicate"] = {"notice_count": st.get("notice_count"),
                                       "notices": st.get("notices"),
                                       "notice_owners": st.get("notice_owners"),
                                       "marks": st.get("marks_stamped_words"),
                                       "uuids_on_screen": st.get("uuids_on_screen"),
                                       "screaming_on_screen": st.get("screaming_on_screen"),
                                       "dotted_keys_on_screen": st.get("dotted_keys_on_screen")}
        if row["arm"].endswith("_3_after_tapping_unstamped"):
            pick["after_first_tap"] = {"notice_count": st.get("notice_count"),
                                       "marks": st.get("marks_stamped_words"),
                                       "notice_owners": st.get("notice_owners")}
        if row["arm"].endswith("_5_after_tapping_a_second_stop"):
            pick["after_second"] = {"marks": st.get("marks_stamped_words"),
                                    "notice_count": st.get("notice_count")}
        if row["arm"].endswith("_2_census_after_scroll"):
            b = row.get("buttons") or []
            pick["census"] = {"controls": len(b),
                              "pressable_by_centre_hit": sum(1 for x in b if x.get("hit_self")),
                              "unpressable_indices": [x["index"] for x in b if not x.get("hit_self")],
                              "boxes": ["%dx%d" % (x["box"]["w"], x["box"]["h"]) for x in b if x.get("box")],
                              "words": [x.get("words") for x in b],
                              "stops": [x.get("stop") for x in b]}
        if row.get("ABORT"):
            pick[row["arm"].split("_", 1)[-1]] = row["ABORT"]
    pick["requests"] = [r["method"] + ":" + str(r["http_status"]) for r in d.get("requests", [])]
    pick["page_errors"] = d.get("page_errors")
    pick["FATAL"] = d.get("FATAL")
    return pick


def main():
    result = {"tool": "gen9_stack_r1", "took_local": datetime.now().astimezone().isoformat(),
              "shared_db": shared_stat(), "runs": []}
    for label, face_dir, backend_tree, port in FACES:
        for shape, w, h in SHAPES:
            if label in ("O0500_CLIENTBOOL_MUTANT", "PRE_SLICE2_dcb90ccc") \
                    and shape != "phone":
                continue
            tag = "%s_%s" % (label, shape)
            run = {"tag": tag, "face_dir": face_dir, "backend_tree": backend_tree,
                   "viewport": "%dx%d" % (w, h)}
            stop(listener(BACKEND_PORT))
            run["store_before"] = fresh_store()
            run["backend"] = boot_backend(backend_tree)
            if not run["backend"].get("ready"):
                run["ABORT"] = "BACKEND_NOT_READY"
                result["runs"].append(run)
                continue
            run["store_after_schema"] = rows_and_keys()
            serve_receipt = serve(face_dir, port, backend_tree)
            run["serve"] = serve_receipt
            if serve_receipt.get("ABORT"):
                run["ABORT"] = "FACE_NOT_UP"
                result["runs"].append(run)
                continue
            ev = "checkin_%s_%dx%d_r2.json" % (tag, w, h)
            run["arm"] = arm("http://127.0.0.1:%d" % port, tag, w, h)
            run["readings"] = screen_rows(ev)
            run["store_after_arm"] = rows_and_keys()
            run["shared_after"] = shared_stat()
            run["shared_untouched"] = (run["shared_after"]["bytes"] == result["shared_db"]["bytes"]
                                       and run["shared_after"]["mtime_local"]
                                       == result["shared_db"]["mtime_local"])
            result["runs"].append(run)
            print("%s marks=%s rows=%s notices=%s reqs=%s" % (
                tag, run["readings"].get("after_duplicate", {}).get("marks"),
                run["store_after_arm"].get("count"),
                run["readings"].get("after_duplicate", {}).get("notice_count"),
                ",".join(run["readings"].get("requests", []))), flush=True)
            stop(listener(BACKEND_PORT))
            stop(listener(port))
    path = os.path.join(LANE, "evidence", "gen9_checkin_sweep_r1.json")
    json.dump(result, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
