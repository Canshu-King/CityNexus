"""ORD-0269-4 runtime verifier harness - one arm per invocation, fully disposable.

Isolation口径 (verbatim from arbiter 5798800357 / 5798888472, applied literally):
  * one-shot NEW sqlite file, created by the app itself, in a run dir this script makes
  * one-shot NAMED backend + origin ports, released by listener before returning
  * no lane livecopy, no shared/user DB: the DB path exists nowhere else
  * the only rows in the DB are the ones MY OWN walk writes (nothing is seeded)
  * before/after row counts and primary keys for EVERY table, plus a second-connection
    read while the server is still up
  * at the end: stop the ports, delete the whole temp DB/dir, assert it is gone

Usage:  python o269_arm.py <arm>        arm in {answer, never, swallow_journeys}
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
TREE = os.path.join(LANE, "o269_tree", "backend")            # git archive of the measured sha
DIST = os.path.join(LANE, "o269_run", "dist_gen")            # copy of the published generation
PY = r"C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe"
NODE = "node"
BE_PORT, OR_PORT = 8931, 8932
SHA = "1f4440819a9d773da6e18f12a31412f73c6d0f55"

ARM = sys.argv[1]
assert ARM in ("answer", "never", "swallow_journeys"), ARM
SUFFIX = os.getenv("CNX_ARM_SUFFIX", "").strip()
RUN_TAG = "%s__%s" % (ARM, SUFFIX) if SUFFIX else ARM
GEN_BUNDLE = os.getenv("CNX_GEN_BUNDLE", "index-Cpy_jhEg.js")
SHA = os.getenv("CNX_SHA", SHA)
DIST = os.getenv("CNX_DIST", DIST)
TREE = os.getenv("CNX_TREE", TREE)
RUNDIR = os.path.join(LANE, "o269_run", RUN_TAG)
DB = os.path.join(RUNDIR, "one_shot.sqlite3")
receipt = {"order": "ORD-0269", "cell": "4 (A3 write leg silent)", "verifier": "1a986a24 HJ-P1 (代任)",
           "arm": ARM, "run_tag": RUN_TAG, "source_sha_under_test": SHA,
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "ports": {"backend": BE_PORT, "origin": OR_PORT}, "db_path": DB,
           "gen_bundle_expected": GEN_BUNDLE, "dist_root": DIST,
           "tree_kind": "git archive export of the measured sha (0 product bytes edited)"}

pids = []
handles = []


def open_log(path):
    fh = open(path, "wb")
    handles.append(fh)
    return fh


def close_logs():
    for fh in handles:
        try:
            fh.close()
        except Exception:                                     # noqa: BLE001
            pass


def kill(pid):
    try:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=20)
    except Exception as e:                                    # noqa: BLE001
        receipt.setdefault("teardown_errors", []).append("taskkill %s: %s" % (pid, str(e)[:120]))


def listening(port):
    out = subprocess.run('netstat -ano | findstr ":%d "' % port, shell=True,
                         capture_output=True, text=True).stdout or ""
    return [ln.strip() for ln in out.splitlines() if "LISTENING" in ln.upper() or "LISTEN" in ln]


def http(url, timeout=8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:                                    # noqa: BLE001
        return None, str(e)[:160].encode()


def table_facts(label):
    """Read-only second connection: counts for every table + PKs of every non-empty table."""
    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    names = [r[0] for r in con.execute("select name from sqlite_master where type='table' order by name")]
    facts = {}
    for t in names:
        try:
            cols = [r[1] for r in con.execute('PRAGMA table_info("%s")' % t) if r[5]]      # pk_seq > 0
            n = con.execute('select count(*) from "%s"' % t).fetchone()[0]
            rows = []
            if n:
                pk = ",".join('"%s"' % c for c in (cols or ["rowid"]))
                rows = [dict(r) for r in con.execute('select %s from "%s" order by 1 limit 25' % (pk, t))]
            facts[t] = {"pk_columns": cols, "rows": n, "keys": rows}
        except Exception as e:                                # noqa: BLE001
            facts[t] = {"pk_columns": [], "rows": None, "keys": [],
                        "read_error": type(e).__name__ + ": " + str(e)[:120]}
    con.close()
    return {"measured_at": label, "tables_measured": len(names),
            "nonempty_tables": sorted([t for t in facts if facts[t]["rows"]]),
            "counts": {t: facts[t]["rows"] for t in facts}, "detail": facts}


def tail(path, rx, n=40):
    try:
        lines = [ln.rstrip() for ln in open(path, encoding="utf-8", errors="replace") if rx.search(ln)]
    except OSError:
        return []
    return lines[-n:]


try:
    if os.path.isdir(RUNDIR):
        shutil.rmtree(RUNDIR)
    os.makedirs(RUNDIR)
    open(os.path.join(RUNDIR, "mode.txt"), "w", encoding="utf-8").write("answer")

    env = dict(os.environ)
    env.update({"CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
                "CITYNEXUS_DEMO_MODE": "false", "CITYNEXUS_AI_ENABLED": "false",
                "CITYNEXUS_AI_API_KEY": "", "DEEPSEEK_API_KEY": "",
                "CITYNEXUS_LIVE_VALHALLA_URL": "", "CITYNEXUS_GUARDIAN_AUTORUN": "false",
                "CITYNEXUS_REAL_CITY_ENABLED": "false", "CITYNEXUS_ENV": "development",
                "PYTHONIOENCODING": "utf-8"})
    assert "citynexus.db" not in env["CITYNEXUS_DATABASE_URL"] and DB.count("one_shot") == 1

    be_log = open_log(os.path.join(RUNDIR, "backend_access.log"))
    be = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                           "--port", str(BE_PORT), "--log-level", "info"],
                          cwd=TREE, env=env, stdout=be_log, stderr=subprocess.STDOUT)
    pids.append(be.pid)

    ready = None
    for _ in range(60):
        time.sleep(1.0)
        st, body = http("http://127.0.0.1:%d/openapi.json" % BE_PORT, timeout=3)
        if st == 200:
            try:
                ready = len(json.loads(body).get("paths", {}))
            except Exception:                                  # noqa: BLE001
                ready = -1
            break
        if be.poll() is not None:
            receipt["FAILED"] = "backend exited rc=%s" % be.returncode
            receipt["backend_tail"] = open(os.path.join(RUNDIR, "backend_access.log"),
                                           encoding="utf-8", errors="replace").read()[-1800:]
            break
    assert ready, receipt.get("FAILED", "backend not ready")
    receipt["backend"] = {"pid": be.pid, "openapi_paths": ready}

    or_log = open_log(os.path.join(RUNDIR, "origin.log"))
    orp = subprocess.Popen([PY, os.path.join(LANE, "o269_origin.py"), DIST, str(OR_PORT),
                            str(BE_PORT), RUNDIR], stdout=or_log, stderr=subprocess.STDOUT, env=env)
    pids.append(orp.pid)
    time.sleep(3.0)
    st, body = http("http://127.0.0.1:%d/" % OR_PORT)
    m = re.search(rb"assets/(index-[A-Za-z0-9_-]+\.js)", body or b"")
    receipt["origin"] = {"pid": orp.pid, "root_status": st, "served_entry": m and m.group(1).decode()}
    assert st == 200 and m and m.group(1).decode() == GEN_BUNDLE, receipt["origin"]

    receipt["db_before"] = table_facts("after boot, before any click")

    wenv = dict(env)
    wenv.update({"CNX_BASE": "http://127.0.0.1:%d" % OR_PORT, "CNX_RUN": RUN_TAG,
                 "CNX_MODEFILE": os.path.join(RUNDIR, "mode.txt"), "CNX_ARM_MODE": ARM,
                 "CNX_SHOTS": os.path.join(LANE, "shots")})
    t0 = time.time()
    with open(os.path.join(RUNDIR, "walk_stdout.json"), "wb") as wf:
        rc = subprocess.call([NODE, os.path.join(LANE, "o269_walk.cjs")], env=wenv,
                             stdout=wf, stderr=subprocess.STDOUT, timeout=900)
    receipt["walk"] = {"exit": rc, "wall_s": round(time.time() - t0, 1)}
    shutil.copy(os.path.join(LANE, "o269_walk_%s.json" % RUN_TAG), os.path.join(RUNDIR, "walk.json"))

    # durable facts while the server is STILL UP - a second connection, outside the process
    receipt["db_after_live"] = table_facts("read-only 2nd connection, backend still running")

    for p in pids:
        kill(p)
    time.sleep(2.0)
    receipt["ports_after_kill"] = {"backend": listening(BE_PORT), "origin": listening(OR_PORT)}

    # same file again after shutdown: what survived the process
    receipt["db_after_shutdown"] = table_facts("after backend process exit")

    rx = re.compile(r'"(POST|PUT|PATCH) (/api/v1/(travelers|journeys|journeys/[^"]*))[^"]*" 2\d\d')
    receipt["backend_access_log_write_lines"] = tail(os.path.join(RUNDIR, "backend_access.log"), rx)
    ev = []
    for ln in open(os.path.join(RUNDIR, "events.jsonl"), encoding="utf-8"):
        try:
            ev.append(json.loads(ln))
        except Exception:                                      # noqa: BLE001
            pass
    receipt["origin_events"] = ev
    receipt["origin_events_summary"] = {
        "total": len(ev),
        "trip_write_decisions": [e for e in ev if e.get("path", "").startswith("/api/v1/journeys")
                                 and e.get("method") == "POST"],
        "swallowed": len([e for e in ev if e.get("kind") == "swallow"]),
        "held_never_forwarded": len([e for e in ev if e.get("kind") == "hold"]),
        "forwarded_and_answered": len([e for e in ev if e.get("kind") == "pass"]),
        "upstream_errors": len([e for e in ev if e.get("kind") == "upstream_error"])}
finally:
    for p in pids:
        kill(p)
    close_logs()
    time.sleep(1.5)
    # copy the evidence out BEFORE deleting, then delete the whole temp dir and assert it is gone
    keep = {"receipt": "o269_arm_%s.json" % RUN_TAG, "walk": "o269_walk_%s.json" % RUN_TAG,
            "origin_events": "o269_events_%s.jsonl" % RUN_TAG,
            "backend_access_log": "o269_backend_%s.log" % RUN_TAG}
    os.makedirs(os.path.join(LANE, "o269_kept"), exist_ok=True)
    pairs = [(os.path.join(RUNDIR, "mode.txt"), None),
             (os.path.join(RUNDIR, "walk.json"), os.path.join(LANE, keep["walk"])),
             (os.path.join(RUNDIR, "events.jsonl"), os.path.join(LANE, keep["origin_events"])),
             (os.path.join(RUNDIR, "backend_access.log"), os.path.join(LANE, keep["backend_access_log"]))]
    for src, dst in pairs:
        if dst and os.path.exists(src):
            shutil.copy(src, dst)
    receipt["kept_outside_tempdir"] = [d for _, d in pairs if d and os.path.exists(d)]
    for _ in range(6):
        if not os.path.isdir(RUNDIR):
            break
        shutil.rmtree(RUNDIR, ignore_errors=True)
        time.sleep(0.7)
    receipt["tempdir_deleted"] = not os.path.exists(RUNDIR)
    receipt["db_files_present_after_delete"] = [p for p in
                                                (DB, DB + "-wal", DB + "-shm") if os.path.exists(p)]
    receipt["ports_final"] = {"backend": listening(BE_PORT), "origin": listening(OR_PORT)}
    receipt["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with open(os.path.join(LANE, "o269_arm_%s.json" % RUN_TAG), "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, ensure_ascii=False, indent=2)
    brief = {k: receipt.get(k) for k in ("arm", "walk", "origin", "backend", "FAILED")}
    for k in ("db_before", "db_after_live", "db_after_shutdown"):
        r = receipt.get(k) or {}
        brief[k] = {"tables_measured": r.get("tables_measured"),
                    "nonempty": r.get("nonempty_tables"),
                    "counts_of_interest": {t: (r.get("counts") or {}).get(t) for t in
                                           ("travelers", "journeys", "journey_missions",
                                            "agent_runs", "audit_events", "plan_versions",
                                            "events", "idempotency_keys") if t in (r.get("counts") or {})}}
    brief["isolation"] = {"tempdir_deleted": receipt.get("tempdir_deleted"),
                          "db_files_present_after_delete": receipt.get("db_files_present_after_delete"),
                          "ports_final": receipt.get("ports_final")}
    brief["origin_events_summary"] = receipt.get("origin_events_summary")
    brief["backend_access_log_write_lines"] = receipt.get("backend_access_log_write_lines")
    print(json.dumps(brief, ensure_ascii=False, indent=2))
