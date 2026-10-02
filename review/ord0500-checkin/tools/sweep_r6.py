"""ORD-0500 r6: walk each face in BOTH locales, one fresh private store per run.

Four runs: base face and candidate face, each at 390x844 in zh-CN and in en.  Why both locales: the
defect this order fixes is a sentence whose English form names a control that only exists on the
Chinese screen, and my r5 readings were taken in zh-CN only -- so the English half of my own screen
had never been looked at.

Lifted from gen9_stack_r1.py deliberately (same boot shape, same store discipline): the shared
preview DB is opened `mode=ro` and copied with sqlite's `backup()` per run, so nothing writes to it;
every subprocess is bounded and a failed step is recorded as ABORT_<name> instead of going quiet.
Face identity is proved twice per run -- the entry asset name read out of the served index.html, and
served bytes equal to disk bytes for both the html and the bundle; the third proof is named
NOT_AVAILABLE_BY_CMDR (vite preview writes no access log I control).
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
DB = os.path.join(LANE, "run", "phone_r6.db")
BACKEND_PORT = 8151
# the faces come from the build receipt of THIS generation, so a re-cut needs no editing here:
# (label, face dir, unused port) is read from evidence/build_faces_r6.json at start-up
def _runs_from_build():
    rec = json.load(open(os.path.join(LANE, "evidence", "build_faces_r6.json"), encoding="utf-8"))
    out = []
    for f in rec.get("faces", []):
        rel = os.path.relpath(f.get("out_dir", ""), LANE).replace(os.sep, "/")
        out.append((f.get("label"), rel, None))
    return out


RUNS = _runs_from_build()
LOCALES = [("zh", "zh-CN"), ("en", "en-US")]
W, H = 390, 844
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


def stop(mine):
    """Kill ONLY a process this run spawned.  An earlier version of this driver read `listener(port)`
    and taskkilled whatever answered there -- and because another lane already held the port, that
    killed THEIR preview (pid 41672 on 127.0.0.1:4892 at 16:43:10).  Never do that again: the pid is
    taken from the Popen handle, and a port that was stolen is left alone."""
    if not mine:
        return "NOTHING_TO_STOP"
    try:
        subprocess.run(["taskkill", "/PID", str(mine), "/T", "/F"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)
    except subprocess.TimeoutExpired:
        return "TASKKILL_TIMEOUT"
    return "STOPPED_OWN_PID_%s" % mine


def free_port(band):
    """A port nobody is listening on, from this lane's band.  A port that answers is NOT free just
    because my own spawn would fail on it -- strictPort then leaves another lane's bytes in place,
    and reading them as mine is the exact failure this run just hit."""
    for port in band:
        if listener(port) is None:
            return port
    return None


def shared_stat():
    st = os.stat(SHARED)
    return {"bytes": st.st_size,
            "mtime_local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))}


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
    counts["journey_checkins"] = (con.execute("SELECT COUNT(*) FROM journey_checkins").fetchone()[0]
                                  if "journey_checkins" in tables else "TABLE_ABSENT_UNTIL_BOOT")
    con.close()
    return counts


def checkin_rows():
    con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM journey_checkins").fetchone()[0]
    except sqlite3.OperationalError as exc:
        con.close()
        return {"ABORT": type(exc).__name__, "reason": str(exc)[:120]}
    con.close()
    return {"count": n}


def boot_backend(tree, port):
    """The port comes from a band this run verified unoccupied, which is what makes the listener pid
    mine -- and therefore the only process this run is allowed to stop."""
    global BACKEND_PORT
    BACKEND_PORT = port
    if listener(port) is not None:
        return {"ready": False, "ABORT": "PORT_TAKEN_BEFORE_LAUNCH"}
    log = os.path.join(LANE, "run", "r6_backend_%d.log" % port)
    open(log, "ab").close()
    ps = ("$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:DEEPSEEK_API_KEY=''; "
          "$env:PYTHONPATH='%s'; $env:CITYNEXUS_DATABASE_URL='sqlite:///%s'; "
          "$env:CITYNEXUS_DEMO_MODE='true'; $env:CITYNEXUS_AI_ENABLED='false'; "
          "Start-Process -FilePath '%s' -ArgumentList '-m','uvicorn','app.main:app',"
          "'--host','127.0.0.1','--port','%d' -WorkingDirectory '%s' -WindowStyle Hidden "
          "-RedirectStandardOutput '%s' -RedirectStandardError '%s'"
          % (LANE + "/" + tree, DB.replace("\\", "/"), PY, BACKEND_PORT,
             LANE + "/" + tree + "/backend", log, log + ".err"))
    with open(os.path.join(LANE, "run", "r6_launcher.log"), "ab") as sink:
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
                            "evidence_state": scene.get("evidence_state")}
        except Exception:
            continue
    return {"ready": False, "ABORT": "BACKEND_NEVER_ANSWERED", "pid": listener(BACKEND_PORT)}


def serve(face_dir, port, expect_entry):
    log = os.path.join(LANE, "run", "r6_face_%d.log" % port)
    proc = None
    with open(log, "ab") as sink:
        try:
            proc = subprocess.Popen([NODE, "node_modules/vite/bin/vite.js", "preview",
                                     "--outDir", os.path.join(LANE, face_dir), "--host", "127.0.0.1",
                                     "--port", str(port), "--strictPort"],
                                    cwd=os.path.join(LANE, "wt22", "frontend"),
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
        js_path = os.path.join(abs_face, "assets", m.group(1)) if m else None
        if js_path:
            try:
                with op.open("http://127.0.0.1:%d/assets/%s" % (port, m.group(1)), timeout=30) as r:
                    served_js = r.read()
            except Exception:
                served_js = None
        entry = {"port": port, "face_dir": face_dir, "my_pid": proc.pid,
                 "entry_asset": m.group(1) if m else None,
                 "entry_asset_expected_from_build": expect_entry,
                 "index_local_sha1_served": hashlib.sha1(html.encode("utf-8")).hexdigest(),
                 "index_local_sha1_disk": hashlib.sha1(disk).hexdigest(),
                 "index_bytes_equal_served_vs_disk":
                     hashlib.sha1(html.encode("utf-8")).hexdigest()
                     == hashlib.sha1(disk).hexdigest(),
                 "bundle_local_sha1_served": hashlib.sha1(served_js).hexdigest()
                 if served_js else "NOT_READ",
                 "bundle_local_sha1_disk": hashlib.sha1(open(js_path, "rb").read()).hexdigest()
                 if js_path and os.path.exists(js_path) else "NOT_READ",
                 "listener_pid": listener(port),
                 "i_own_this_port": listener(port) == str(proc.pid),
                 "access_log_proof": "NOT_AVAILABLE_BY_CMDR"}
        entry["bundle_bytes_equal_served_vs_disk"] = (
            entry["bundle_local_sha1_served"] == entry["bundle_local_sha1_disk"])
        entry["identity_ok"] = bool(
            entry["index_bytes_equal_served_vs_disk"]
            and entry["bundle_bytes_equal_served_vs_disk"]
            and entry["i_own_this_port"]
            and entry["entry_asset"] == expect_entry)
        if not entry["identity_ok"]:
            # someone else's bytes are on this port.  Do NOT run an arm against them and do NOT kill
            # them -- my own child is the only process this run is allowed to stop.
            entry["ABORT"] = "FACE_IDENTITY_MISMATCH"
        return entry
    return {"port": port, "face_dir": face_dir, "my_pid": proc.pid,
            "ABORT": "FACE_NEVER_ANSWERED"}


def arm(face_url, tag, locale):
    out = os.path.join(LANE, "evidence", "checkin_%s_%dx%d_r3.json" % (tag, W, H))
    cmd = [NODE, os.path.join(LANE, "tools", "checkin_phone_r3.cjs"), face_url, out, tag,
           str(W), str(H), locale]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=env_clean(), timeout=420)
    except subprocess.TimeoutExpired:
        return {"ABORT": "ARM_TIMEOUT_420S", "out": os.path.basename(out)}
    text = p.stdout.decode("utf-8", "replace")
    return {"exit": p.returncode, "line": text.strip().splitlines()[-1] if text.strip() else "",
            "evidence": os.path.basename(out),
            "bytes": os.path.getsize(out) if os.path.exists(out) else 0}


def pick(evidence):
    p = os.path.join(LANE, "evidence", evidence)
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    out = {"locale_in_receipt": d.get("locale"), "requests": [], "page_errors": d.get("page_errors"),
           "fresh_stop_basis": d.get("fresh_stop_basis")}
    out["requests"] = [r["method"] + ":" + str(r["http_status"]) for r in d.get("requests", [])]
    for row in d.get("rows", []):
        st = row.get("state") or {}
        arm_name = str(row.get("arm", ""))
        if arm_name.endswith("_1_arrived"):
            out["arrived"] = {k: st.get(k) for k in
                              ("control_labels_on_screen", "cjk_chars_on_screen",
                               "marks_zh_words", "marks_en_words", "marks_by_state",
                               "checkin_button_count", "rendered_chars")}
        if arm_name.endswith("_4_after_tapping_the_same_stop_again"):
            out["after_duplicate"] = {
                k: st.get(k) for k in ("notice_count", "notices", "notice_owners",
                                       "cjk_chars_on_screen", "cjk_runs_on_screen",
                                       "uuids_on_screen", "screaming_on_screen",
                                       "dotted_keys_on_screen", "marks_zh_words", "marks_en_words",
                                       "marks_by_state", "control_labels_on_screen")}
        if arm_name.endswith("_2_census_after_scroll"):
            b = row.get("buttons") or []
            out["census"] = {"controls": len(b),
                             "pressable_by_centre_hit": sum(1 for x in b if x.get("hit_self")),
                             "words": sorted({x.get("words") for x in b})}
    return out


BUILD = json.load(open(os.path.join(LANE, "evidence", "build_faces_r6.json"), encoding="utf-8"))
EXPECT = {f["label"]: (f.get("entry") or {}).get("entry_asset") for f in BUILD["faces"]}
FACE_BAND = [4931, 4932, 4933, 4934, 4935, 4936]
BACKEND_BAND = [8151, 8152, 8153, 8154]


def main():
    result = {"tool": "sweep_r6", "took_local": datetime.now().astimezone().isoformat(),
              "viewport": {"width": W, "height": H}, "shared_db": shared_stat(),
              "expected_entries": EXPECT, "runs": []}
    for label, face_dir, _old_port in RUNS:
        for shape, locale in LOCALES:
            tag = "%s_%s" % (label, shape)
            row = {"tag": tag, "face_dir": face_dir, "locale": locale,
                   "store_before": fresh_store()}
            bport = free_port(BACKEND_BAND)
            be = (boot_backend("wt22", bport) if bport
                  else {"ready": False, "ABORT": "NO_FREE_BACKEND_PORT"})
            row["backend"] = be
            fport = free_port(FACE_BAND)
            if be.get("ready") and fport:
                row["serve"] = serve(face_dir, fport, EXPECT.get(label))
                if not row["serve"].get("ABORT"):
                    row["arm"] = arm("http://127.0.0.1:%d" % fport, tag, locale)
                    row["readings"] = pick((row["arm"] or {}).get("evidence", ""))
                    row["store_after"] = checkin_rows()
                else:
                    row["arm"] = {"SKIPPED": row["serve"].get("ABORT")}
            else:
                row["serve"] = {"SKIPPED": ("BACKEND_ABSENT" if not be.get("ready")
                                            else "NO_FREE_FACE_PORT")}
                row["arm"] = {"SKIPPED": "FACE_ABSENT"}
            # only my own children are ever stopped: the face by its Popen pid, and the backend only
            # when the port was demonstrably free before I launched into it
            row["face_torn_down"] = stop((row.get("serve") or {}).get("my_pid"))
            row["backend_torn_down"] = stop(be.get("pid")) if be.get("ready") else "NOT_MINE_NO_STOP"
            row["shared_after"] = shared_stat()
            row["shared_untouched"] = (row["shared_after"] == result["shared_db"])
            result["runs"].append(row)
            print("%s exit=%s notices=%s cjk=%s marks=%s/%s labels=%s ident=%s" % (
                tag, (row.get("arm") or {}).get("exit"),
                (row.get("readings") or {}).get("after_duplicate", {}).get("notice_count"),
                (row.get("readings") or {}).get("after_duplicate", {}).get("cjk_chars_on_screen"),
                (row.get("readings") or {}).get("after_duplicate", {}).get("marks_zh_words"),
                (row.get("readings") or {}).get("after_duplicate", {}).get("marks_en_words"),
                (row.get("readings") or {}).get("after_duplicate", {}).get("control_labels_on_screen")
                or (row.get("readings") or {}).get("arrived", {}).get("control_labels_on_screen"),
                (row.get("serve") or {}).get("identity_ok")), flush=True)
    path = os.path.join(LANE, "evidence", "sweep_r6.json")
    json.dump(result, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
