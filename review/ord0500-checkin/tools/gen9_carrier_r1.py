"""ORD-0500 -- run the footprint-truth carrier against three served faces, and post the counts.

Three runs, all with the same spec file and the same fresh-store recipe, differing only in what is
being served:

  base      faces/tip9            + backend wt7  -- the tip as it stands.  The duplicate-sentence arm
                                                   is expected RED (one notice string, six owners).
  candidate faces/o0500_r5        + backend wt6  -- what this lane delivers.  Expected all GREEN.
  mutant    faces/o0500_clientbool9+ backend wt6  -- a throwaway bundle whose 已打卡 comes from the
                                                   plan's activity status, not the footprint read.
                                                   The marks-vs-rows arm is expected RED on a store
                                                   that holds zero rows: that is CE-2, run rather
                                                   than argued.

The counts come out of Playwright's own JSON report, not from a line I typed.
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
BACKEND_PORT = 8145
RUNS = [("base_tip", "faces/tip9", "wt23", "wt23", 4880),
        ("candidate_o0500", "faces/o0500_r5", "wt22", "wt22", 4881),
        ("mutant_clientbool_ce2", "faces/o0500_clientbool9", "wt22", "wt22", 4882)]
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


def boot(tree, db):
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(db + suffix):
            os.remove(db + suffix)
    src = sqlite3.connect("file:" + SHARED.replace("\\", "/") + "?mode=ro", uri=True)
    dst = sqlite3.connect(db)
    src.backup(dst)
    dst.close()
    src.close()
    log = os.path.join(LANE, "run", "gen9_carrier_backend_%s.log" % tree)
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
                        return {"ready": True, "pid": pid, "db": os.path.basename(db),
                                "journey_id": scene.get("journey_id")}
            except Exception:
                continue
    return {"ready": False, "ABORT": "BACKEND_NEVER_ANSWERED"}


def serve(face_dir, port, tree):
    log = os.path.join(LANE, "run", "gen9_carrier_face_%d.log" % port)
    with open(log, "ab") as sink:
        subprocess.Popen([NODE, "node_modules/vite/bin/vite.js", "preview",
                          "--outDir", os.path.join(LANE, face_dir), "--host", "127.0.0.1",
                          "--port", str(port), "--strictPort"],
                         cwd=os.path.join(LANE, "wt22", "frontend"),
                         env=env_clean({"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)}),
                         creationflags=0x208, stdout=sink, stderr=sink)
    for _ in range(30):
        time.sleep(2)
        try:
            with op.open("http://127.0.0.1:%d/" % port, timeout=10) as r:
                html = r.read().decode("utf-8", "replace")
            m = re.search(r'src="/assets/(index-[\w\-]+\.js)', html)
            disk = open(os.path.join(LANE, face_dir, "index.html"), "rb").read()
            return {"port": port, "face_dir": face_dir, "entry_asset": m.group(1) if m else None,
                    "index_bytes_equal_served_vs_disk": html.encode("utf-8") == disk,
                    "listener_pid": listener(port)}
        except Exception:
            continue
    return {"port": port, "face_dir": face_dir, "ABORT": "FACE_NEVER_ANSWERED"}


def rows(db):
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM journey_checkins").fetchone()[0]
    except sqlite3.OperationalError:
        n = "TABLE_ABSENT"
    con.close()
    return n


def main():
    out = {"tool": "gen9_carrier_r1", "took_local": datetime.now().astimezone().isoformat(),
           "spec_sha256": hashlib.sha256(open(os.path.join(
               LANE, "wt22/frontend/e2e/qoder-ord0500-checkin-truth.spec.ts"), "rb").read()).hexdigest(),
           "runs": []}
    for label, face_dir, be_tree, _gap, port in RUNS:
        db = os.path.join(LANE, "run", "gen9_carrier_%s.db" % label)
        run = {"label": label, "face_dir": face_dir, "backend_tree": be_tree}
        stop(listener(BACKEND_PORT))
        run["backend"] = boot(be_tree, db)
        if not run["backend"].get("ready"):
            run["ABORT"] = "BACKEND_NOT_READY"
            out["runs"].append(run)
            continue
        run["rows_before"] = rows(db)
        run["serve"] = serve(face_dir, port, be_tree)
        if run["serve"].get("ABORT"):
            run["ABORT"] = "FACE_NOT_UP"
            out["runs"].append(run)
            continue
        report = os.path.join(LANE, "run", "report_%s.json" % label)
        if os.path.exists(report):
            os.remove(report)
        p = subprocess.run(
            [NODE, "node_modules/@playwright/test/cli.js", "test",
             "--config", "playwright.ord0500-checkin.config.ts",
             "e2e/qoder-ord0500-checkin-truth.spec.ts"],
            cwd=os.path.join(LANE, "wt22", "frontend"),
            env=env_clean({"CITYNEXUS_ORD0500_BASE": "http://127.0.0.1:%d" % port,
                           "CITYNEXUS_ORD0500_REPORT": report}),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
        text = p.stdout.decode("utf-8", "replace")
        log = os.path.join(LANE, "run", "gen9_carrier_%s.txt" % label)
        open(log, "w", encoding="utf-8").write(text)
        run["exit"] = p.returncode
        run["log"] = os.path.relpath(log, LANE)
        verdict = [l for l in text.splitlines() if re.search(r"\d+ (passed|failed)", l)]
        run["verdict_line"] = verdict[-1].strip() if verdict else "NO_VERDICT_LINE"
        run["arm_lines"] = [l.strip()[:200] for l in text.splitlines()
                            if re.search(r"(✓|✘|x|–) .*ord0500-", l)]
        if os.path.exists(report):
            d = json.load(open(report, encoding="utf-8"))
            stats = d.get("stats", {})
            run["report_stats"] = {k: stats.get(k) for k in ("expected", "unexpected", "flaky", "skipped")}
            failures = []
            for suite in d.get("suites", []):
                for spec in suite.get("specs", []):
                    for t in spec.get("tests", []):
                        for r in t.get("results", []):
                            if r.get("status") != "expected":
                                msg = ""
                                for e in (r.get("error") or {}).get("message", "").splitlines():
                                    if "spec.ts ::" in e or "— " in e:
                                        msg = e.strip()
                                        break
                                failures.append({"title": spec.get("title"),
                                                 "status": r.get("status"),
                                                 "node_message": msg[:400]})
            run["failing_arms"] = failures
        run["rows_after"] = rows(db)
        out["runs"].append(run)
        print("%s %s rows=%s->%s" % (label, run.get("verdict_line"), run["rows_before"],
                                     run["rows_after"]), flush=True)
        stop(listener(port))
        stop(listener(BACKEND_PORT))
    path = os.path.join(LANE, "evidence", "gen9_carrier_r1.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False)[:4000])
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
