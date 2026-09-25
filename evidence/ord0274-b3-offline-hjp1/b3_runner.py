"""ORD-0290 arm runner: same one-shot discipline as ORD-0269-4, driven by a spec file.

Spec (o290_arms.json) gives, per arm: which built tree the returning client is installed on,
which tree is the "new generation", how the trip-writing POST is treated, and which commit is
being claimed.  Nothing here trusts B's worktree, and nothing here touches a shared DB: the
SQLite file is created inside the arm's own run dir and the whole dir is deleted at the end
with an assertion that it is gone.
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
PY = r"C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe"
TREE = os.path.join(LANE, "o269_tree_c79e2b4", "backend")
BE_PORT, OR_PORT = 8964, 8963

ARM = sys.argv[1]
spec_path = os.path.join(LANE, "o2b3_arms.json")
SPEC = json.load(open(spec_path, encoding="utf-8"))
assert ARM in SPEC, sorted(SPEC)
S = SPEC[ARM]
RUNDIR = os.path.join(LANE, "o2b3_run", ARM)
DB = os.path.join(RUNDIR, "one_shot.sqlite3")
rec = {"order": "ORD-0274-B3", "arm": ARM, "verifier": "1a986a24 HJ-P1",
       "claim_under_test": S.get("claim"), "installed_commit": S["installed_sha"],
       "next_commit": S["next_sha"], "root_installed": S["root_installed"], "root_next": S["root_next"],
       "arm_kind": S["kind"], "write_mode": S["mode"], "cells_this_arm_judges": S["cells"],
       "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "ports": {"backend": BE_PORT, "origin": OR_PORT}}
pids, handles = [], []


def open_log(p):
    fh = open(p, "wb")
    handles.append(fh)
    return fh


def listening(port):
    o = subprocess.run('netstat -ano | findstr ":%d "' % port, shell=True, capture_output=True,
                       text=True).stdout or ""
    return [ln.strip() for ln in o.splitlines() if "LISTENING" in ln.upper()]


def http(url, timeout=8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:                                    # noqa: BLE001
        return None, str(e)[:150].encode()


def kill(pid):
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)


def table_facts(label):
    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    names = [r[0] for r in con.execute("select name from sqlite_master where type='table' order by name")]
    facts = {}
    for t in names:
        try:
            cols = [r[1] for r in con.execute('PRAGMA table_info("%s")' % t) if r[5]]
            n = con.execute('select count(*) from "%s"' % t).fetchone()[0]
            keys = []
            if n:
                pk = ",".join('"%s"' % c for c in (cols or ["rowid"]))
                keys = [dict(r) for r in con.execute('select %s from "%s" order by 1 limit 20' % (pk, t))]
            facts[t] = {"pk_columns": cols, "rows": n, "keys": keys}
        except Exception as e:                                # noqa: BLE001
            facts[t] = {"rows": None, "keys": [], "read_error": str(e)[:90]}
    con.close()
    return {"measured_at": label, "tables_measured": len(names),
            "nonempty": sorted([t for t in facts if facts[t]["rows"]]),
            "counts": {t: facts[t]["rows"] for t in facts}, "detail": facts}


def dist_identity(d):
    html = open(os.path.join(d, "index.html"), encoding="utf-8").read()
    js = re.search(r"assets/(index-[\w-]+\.js)", html).group(1)
    return {"root": os.path.basename(os.path.dirname(os.path.dirname(d))) if False else d,
            "bundle": js,
            "shell_md5": hashlib.md5(open(os.path.join(d, "index.html"), "rb").read()).hexdigest(),
            "worker_sha256_16": hashlib.sha256(open(os.path.join(d, "v10-sw.js"), "rb").read()).hexdigest()[:16]}


import hashlib                                                 # noqa: E402
try:
    # a rundir left behind by a killed arm is not a place to write a new run's facts: clear it, or
    # stop here, because silently sharing it would mix two runs' DB and log lines into one receipt
    for _ in range(10):
        if not os.path.isdir(RUNDIR):
            break
        shutil.rmtree(RUNDIR, ignore_errors=True)
        time.sleep(0.5)
    assert not os.path.isdir(RUNDIR), "could not clear the arm rundir: " + RUNDIR
    os.makedirs(RUNDIR)
    open(os.path.join(RUNDIR, "current_root.txt"), "w", encoding="utf-8").write(S["root_installed"])
    open(os.path.join(RUNDIR, "mode.txt"), "w", encoding="utf-8").write("answer")
    open(os.path.join(RUNDIR, "asset_root.txt"), "w", encoding="utf-8").write(S["root_installed"])
    rec["identity_installed"] = dist_identity(S["root_installed"])
    rec["identity_next"] = dist_identity(S["root_next"])
    assert rec["identity_installed"]["bundle"] != rec["identity_next"]["bundle"], "the two gens are not separable"

    env = dict(os.environ)
    env.update({"CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
                "CITYNEXUS_DEMO_MODE": "false", "CITYNEXUS_AI_ENABLED": "false",
                "CITYNEXUS_AI_API_KEY": "", "DEEPSEEK_API_KEY": "", "CITYNEXUS_LIVE_VALHALLA_URL": "",
                "CITYNEXUS_GUARDIAN_AUTORUN": "false", "CITYNEXUS_REAL_CITY_ENABLED": "false",
                "CITYNEXUS_ENV": "development", "PYTHONIOENCODING": "utf-8"})
    assert DB.count("one_shot") == 1 and "citynexus.db" not in env["CITYNEXUS_DATABASE_URL"]
    be = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                           "--port", str(BE_PORT), "--log-level", "info"], cwd=TREE, env=env,
                          stdout=open_log(os.path.join(RUNDIR, "backend.log")), stderr=subprocess.STDOUT)
    pids.append(be.pid)
    paths = None
    for _ in range(60):
        time.sleep(1.0)
        st, body = http("http://127.0.0.1:%d/openapi.json" % BE_PORT, timeout=3)
        if st == 200:
            paths = len(json.loads(body).get("paths", {}))
            break
        if be.poll() is not None:
            break
    assert paths, "backend not up"
    orp = subprocess.Popen([PY, os.path.join(LANE, "o2b3_origin.py"), RUNDIR, str(OR_PORT), str(BE_PORT)],
                           stdout=open_log(os.path.join(RUNDIR, "origin.log")), stderr=subprocess.STDOUT, env=env)
    pids.append(orp.pid)
    time.sleep(3.0)
    st, body = http("http://127.0.0.1:%d/" % OR_PORT)
    served = (re.search(rb"assets/(index-[\w-]+\.js)", body or b"") or [None, None])[1]
    rec["surface"] = {"backend_pid": be.pid, "origin_pid": orp.pid, "openapi_paths": paths,
                      "root_status": st, "served_entry": served and served.decode()}
    assert st == 200 and served and served.decode() == rec["identity_installed"]["bundle"], rec["surface"]
    rec["db_before"] = table_facts("after boot, before any click")

    wenv = dict(env)
    wenv.update({"CNX_BASE": "http://127.0.0.1:%d" % OR_PORT, "CNX_RUN": ARM, "CNX_ARM": S["kind"],
                 "CNX_PROFILE": os.path.join(RUNDIR, "profile"), "CNX_ROOT_A": S["root_installed"],
                 "CNX_ROOT_B": S["root_next"], "CNX_POINTER": os.path.join(RUNDIR, "current_root.txt"),
                 "CNX_MODEFILE": os.path.join(RUNDIR, "mode.txt"),
                 "CNX_ASSET_POINTER": os.path.join(RUNDIR, "asset_root.txt"),
                 "CNX_WRITE_MODE": S["mode"], "CNX_INSTALL_MODE": S.get("install_mode", "two_navigations"),
                 "CNX_SHOTS": os.path.join(LANE, "shots")})
    t0 = time.time()
    with open(os.path.join(RUNDIR, "arm_stdout.json"), "wb") as wf:
        rc = subprocess.call(["node", os.path.join(LANE, "o2b3_arms.cjs")], env=wenv, stdout=wf,
                             stderr=subprocess.STDOUT, timeout=1200)
    rec["arm_exit"] = rc
    rec["arm_wall_s"] = round(time.time() - t0, 1)
    for p in pids:
        kill(p)
    for fh in handles:
        fh.close()
    time.sleep(2.0)
    rec["db_after"] = table_facts("after the walk, backend stopped")
    rx = re.compile(r'"(POST|PUT|PATCH) (/api/v1/[^"]*)" 2\d\d')
    rec["backend_write_log"] = [l.rstrip() for l in open(os.path.join(RUNDIR, "backend.log"),
                                                          encoding="utf-8", errors="replace") if rx.search(l)][-25:]
finally:
    for p in pids:
        kill(p)
    for fh in handles:
        try:
            fh.close()
        except Exception:                                     # noqa: BLE001
            pass
    time.sleep(1.5)
    for src, dst in [(os.path.join(RUNDIR, "requests.jsonl"), os.path.join(LANE, "o2b3_requests_%s.jsonl" % ARM)),
                     (os.path.join(RUNDIR, "arm_stdout.json"), os.path.join(LANE, "o2b3_stdout_%s.json" % ARM))]:
        if os.path.exists(src):
            shutil.copy(src, dst)
    for _ in range(6):
        if not os.path.isdir(RUNDIR):
            break
        shutil.rmtree(RUNDIR, ignore_errors=True)
        time.sleep(0.7)
    rec["isolation"] = {"rundir_deleted": not os.path.exists(RUNDIR),
                        "db_leftovers": [x for x in (DB, DB + "-wal", DB + "-shm") if os.path.exists(x)],
                        "profile_leftovers": os.path.exists(os.path.join(RUNDIR, "profile")),
                        "ports_final": {"backend": listening(BE_PORT), "origin": listening(OR_PORT)}}
    rec["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    json.dump(rec, open(os.path.join(LANE, "o2b3_run_%s.json" % ARM), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, default=str)
    brief = {k: rec.get(k) for k in ("arm", "claim_under_test", "installed_commit", "next_commit",
                                     "arm_kind", "write_mode", "arm_exit", "arm_wall_s", "surface",
                                     "identity_installed", "identity_next", "isolation",
                                     "backend_write_log")}
    for k in ("db_before", "db_after"):
        r = rec.get(k) or {}
        brief[k] = {"tables": r.get("tables_measured"), "nonempty": r.get("nonempty"),
                    "journeys": (r.get("counts") or {}).get("journeys"),
                    "travelers": (r.get("counts") or {}).get("travelers")}
    print(json.dumps(brief, ensure_ascii=False, indent=2, default=str))
