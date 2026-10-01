"""ORD-0500 -- the footprint doors read at the HTTP level, on the candidate and on the CE-1 mutant.

Every cell is the raw answer, not a sentence I wrote about it: `http_status`, `content_type`,
`body_bytes`, `reason_code`, `message`, `details`, and a scan for whether an identifier reached the
traveller-facing message.  That shape is the one this project asks for when a refusal is being
displayed as evidence (Q53 ①).

Two backends, one command shape:
  wt6     -- the bytes this lane delivers (journey leg named, door's own duplicate lookup intact)
  mutgen8 -- the same bytes with `existing = None` in `create_journey_checkin`, so a replayed tap is
             refused only by the `UNIQUE (journey_id, target_key)` index

The last step of the mutant run is the point of the counter-example: the delivered phone face is
served over the mutated backend and the real arm still paints the duplicate sentence, because a
status-and-sentence reading cannot tell the door's predicate from the index.  It is run, not argued.
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
BACKEND_PORT = 8143
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
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
        return "STOPPED"
    return "NOTHING_TO_STOP"


def boot(tree, db):
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(db + suffix):
            os.remove(db + suffix)
    src = sqlite3.connect("file:" + SHARED.replace("\\", "/") + "?mode=ro", uri=True)
    dst = sqlite3.connect(db)
    src.backup(dst)
    dst.close()
    src.close()
    log = os.path.join(LANE, "run", "gen8_doors_backend_%s.log" % tree)
    ps = ("$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:DEEPSEEK_API_KEY=''; "
          "$env:PYTHONPATH='%s'; $env:CITYNEXUS_DATABASE_URL='sqlite:///%s'; "
          "$env:CITYNEXUS_DEMO_MODE='true'; $env:CITYNEXUS_AI_ENABLED='false'; "
          "Start-Process -FilePath '%s' -ArgumentList '-m','uvicorn','app.main:app',"
          "'--host','127.0.0.1','--port','%d' -WorkingDirectory '%s' -WindowStyle Hidden "
          "-RedirectStandardOutput '%s' -RedirectStandardError '%s'"
          % (LANE + "/" + tree, db.replace("\\", "/"), PY, BACKEND_PORT,
             LANE + "/" + tree + "/backend", log, log + ".err"))
    with open(log + ".launcher", "ab") as sink:
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdout=sink,
                           stderr=sink, timeout=90)
        except subprocess.TimeoutExpired:
            return {"ready": False, "ABORT": "LAUNCHER_TIMEOUT_90S"}
    for _ in range(45):
        time.sleep(2)
        pid = listener(BACKEND_PORT)
        if pid:
            try:
                with op.open("http://127.0.0.1:%d/api/v1/demo/scene" % BACKEND_PORT,
                             timeout=10) as r:
                    if r.status == 200:
                        scene = json.loads(r.read().decode("utf-8"))
                        return {"ready": True, "pid": pid, "db": db,
                                "journey_id": scene.get("journey_id")}
            except Exception:
                continue
    return {"ready": False, "ABORT": "BACKEND_NEVER_ANSWERED"}


def call(method, path, body=None):
    """One door, recorded as the bytes it answered."""
    url = "http://127.0.0.1:%d%s" % (BACKEND_PORT, path)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"content-type": "application/json"})
    try:
        with op.open(req, timeout=30) as r:
            raw, status, ctype = r.read(), r.status, r.headers.get("content-type")
    except urllib.error.HTTPError as exc:
        raw, status, ctype = exc.read(), exc.code, exc.headers.get("content-type")
    except Exception as exc:
        return {"method": method, "path": path, "ABORT": type(exc).__name__}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        parsed = None
    error = (parsed or {}).get("error") if isinstance(parsed, dict) else None
    message = (error or {}).get("message")
    details = (error or {}).get("details")
    return {"method": method, "path": path, "http_status": status, "content_type": ctype,
            "body_bytes": len(raw), "reason_code": (error or {}).get("reason_code"),
            "message": message, "details": details,
            "uuid_in_message": bool(UUID_RE.search(message or "")),
            "uuid_in_details": bool(UUID_RE.search(json.dumps(details, ensure_ascii=False)))
            if details is not None else None,
            "details_is_null": details is None,
            "envelope_keys": sorted((error or {}).keys()) if isinstance(error, dict)
            else "NO_ERROR_OBJECT"}


def probes(journey_id, activities, place_id):
    other = str(uuid.uuid4())
    real = activities[0]["id"]
    real2 = activities[1]["id"] if len(activities) > 1 else real
    out = []
    out.append(dict(case="no_target_named", **call(
        "POST", "/api/v1/journeys/%s/checkins" % journey_id, {})))
    out.append(dict(case="both_targets_named", **call(
        "POST", "/api/v1/journeys/%s/checkins" % journey_id,
        {"activity_id": real, "place_id": place_id})))
    out.append(dict(case="activity_not_on_this_server", **call(
        "POST", "/api/v1/journeys/%s/checkins" % journey_id, {"activity_id": other})))
    out.append(dict(case="place_not_on_this_server", **call(
        "POST", "/api/v1/journeys/%s/checkins" % journey_id, {"place_id": other})))
    out.append(dict(case="write_door_unknown_journey", **call(
        "POST", "/api/v1/journeys/%s/checkins" % other, {"activity_id": real})))
    out.append(dict(case="read_door_unknown_journey", **call(
        "GET", "/api/v1/journeys/%s/checkins" % other)))
    out.append(dict(case="first_tap_on_a_real_stop", **call(
        "POST", "/api/v1/journeys/%s/checkins" % journey_id, {"activity_id": real})))
    out.append(dict(case="same_stop_tapped_again", **call(
        "POST", "/api/v1/journeys/%s/checkins" % journey_id, {"activity_id": real})))
    out.append(dict(case="second_stop_tapped", **call(
        "POST", "/api/v1/journeys/%s/checkins" % journey_id, {"activity_id": real2})))
    out.append(dict(case="read_footprints_back", **call(
        "GET", "/api/v1/journeys/%s/checkins" % journey_id)))
    return out


def rows(db):
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    try:
        cur = con.execute("SELECT id, target_key, stamped_at, source FROM journey_checkins "
                          "ORDER BY stamped_at")
        cols = [d[0] for d in cur.description]
        data = [dict(zip(cols, r)) for r in cur.fetchall()]
    except sqlite3.OperationalError as exc:
        con.close()
        return {"ABORT": type(exc).__name__}
    con.close()
    return {"count": len(data), "rows": data}


def serve(face_dir, port, tree):
    """The DELIVERED phone face, served over whatever backend this run booted."""
    log = os.path.join(LANE, "run", "gen8_doors_face_%d.log" % port)
    with open(log, "ab") as sink:
        subprocess.Popen([NODE, "node_modules/vite/bin/vite.js", "preview",
                          "--outDir", os.path.join(LANE, face_dir), "--host", "127.0.0.1",
                          "--port", str(port), "--strictPort"],
                         cwd=os.path.join(LANE, tree, "frontend"),
                         env=env_clean({"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)}),
                         creationflags=0x208, stdout=sink, stderr=sink)
    for _ in range(30):
        time.sleep(2)
        try:
            with op.open("http://127.0.0.1:%d/" % port, timeout=10) as r:
                html = r.read().decode("utf-8", "replace")
            m = re.search(r'src="/assets/(index-[\w\-]+\.js)', html)
            return {"port": port, "face_dir": face_dir, "entry_asset": m.group(1),
                    "listener_pid": listener(port)}
        except Exception:
            continue
    return {"port": port, "face_dir": face_dir, "ABORT": "FACE_NEVER_ANSWERED"}


def phone_arm(port, tag):
    out = os.path.join(LANE, "evidence", "checkin_%s_390x844_r2.json" % tag)
    if os.path.exists(out):
        os.remove(out)
    try:
        p = subprocess.run(
            [NODE, os.path.join(LANE, "tools", "checkin_phone_r2.cjs"),
             "http://127.0.0.1:%d" % port, out, tag, "390", "844"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env_clean(), timeout=420)
    except subprocess.TimeoutExpired:
        return {"ABORT": "ARM_TIMEOUT_420S"}
    text = p.stdout.decode("utf-8", "replace")
    if not os.path.exists(out):
        return {"exit": p.returncode, "line": text.strip()[-300:], "ABORT": "NO_EVIDENCE_FILE"}
    d = json.load(open(out, encoding="utf-8"))
    dup = [r for r in d.get("rows", []) if r["arm"].endswith("_4_after_tapping_the_same_stop_again")]
    st = (dup[0].get("state") or {}) if dup else {}
    return {"exit": p.returncode, "line": text.strip().splitlines()[-1] if text.strip() else "",
            "evidence": os.path.basename(out),
            "requests": [r["method"] + ":" + str(r["http_status"]) for r in d.get("requests", [])],
            "notice_count": st.get("notice_count"), "notices": st.get("notices"),
            "notice_owners": st.get("notice_owners"), "marks": st.get("marks_stamped_words"),
            "uuids_on_screen": st.get("uuids_on_screen"), "page_errors": d.get("page_errors"),
            "FATAL": d.get("FATAL")}


def main():
    out = {"tool": "gen8_doors_r1", "took_local": datetime.now().astimezone().isoformat(),
           "shared_db": (lambda st: {"bytes": st.st_size, "mtime_local": time.strftime(
               "%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))})(os.stat(SHARED)), "runs": []}
    trees = tuple(sys.argv[1:]) or ("wt19", "mutgen8")
    for tree in trees:
        db = os.path.join(LANE, "run", "gen8_doors_%s.db" % tree)
        run = {"tree": tree,
               "main_sha256": hashlib.sha256(open(os.path.join(
                   LANE, tree, "backend", "app", "main.py"), "rb").read()).hexdigest()}
        stop(listener(BACKEND_PORT))
        run["backend"] = boot(tree, db)
        if not run["backend"].get("ready"):
            run["ABORT"] = "BACKEND_NOT_READY"
            out["runs"].append(run)
            continue
        # the boot ran ensure_schema, so the footprint table exists by now
        con = sqlite3.connect(db)
        journey_id = con.execute("SELECT id FROM journeys").fetchone()[0]
        acts = [dict(id=r[0], title=r[1], status=r[2]) for r in con.execute(
            "SELECT a.id, a.title, a.status FROM activities a JOIN plan_versions p "
            "ON a.plan_version_id = p.id WHERE p.journey_id = ? AND p.id = "
            "(SELECT active_plan_version_id FROM journeys WHERE id = ?) ORDER BY a.start_at",
            (journey_id, journey_id))]
        place_id = con.execute(
            "SELECT place_id FROM activities WHERE place_id IS NOT NULL LIMIT 1").fetchone()
        con.close()
        run["staged"] = {"journey_id": journey_id, "stops": len(acts),
                         "stop_titles": [a["title"] for a in acts],
                         "store_before": rows(db)}
        run["probes"] = probes(journey_id, acts, (place_id[0] if place_id else str(uuid.uuid4())))
        run["store_after"] = rows(db)
        if tree == "mutgen8":
            # CE-1's screen half: the delivered phone face over the mutated door.  If the duplicate
            # sentence still paints with the door's own lookup removed, the arm has not proved the
            # predicate -- it has proved the index, and that difference is the false green.
            face = serve(os.path.join(LANE, "faces", "o0500_r2"), 4876, "wt19")
            run["mutant_screen"] = {"serve": face}
            if not face.get("ABORT"):
                run["mutant_screen"]["arm"] = phone_arm(4876, "O0500_R4_UNDER_MUTANT_CE1")
                run["mutant_screen"]["store_after_screen"] = rows(db)
            stop(listener(4876))
        run["shared_after"] = (lambda st: {"bytes": st.st_size, "mtime_local": time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))})(os.stat(SHARED))
        run["shared_untouched"] = (run["shared_after"]["bytes"] == out["shared_db"]["bytes"]
                                   and run["shared_after"]["mtime_local"]
                                   == out["shared_db"]["mtime_local"])
        out["runs"].append(run)
        dup = [p for p in run["probes"] if p["case"] == "same_stop_tapped_again"][0]
        print("%s first=%s dup=%s caught_by=%s rows=%s->%s" % (
            tree, [p for p in run["probes"] if p["case"] == "first_tap_on_a_real_stop"][0]["http_status"],
            dup["http_status"], "caught_by" in json.dumps(dup["details"] or {}),
            run["staged"]["store_before"].get("count"), run["store_after"].get("count")), flush=True)
        stop(listener(BACKEND_PORT))
    suffix = "_" + "-".join(trees) if trees != ("wt19", "mutgen8") else "_r1"
    path = os.path.join(LANE, "evidence", "gen8_doors%s.json" % suffix)
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False)[:4500])
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
