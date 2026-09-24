"""ORD-0274 B-arm runner: one-shot backend + switchable two-generation origin + persistent profile.

Same isolation口径 I used on ORD-0269-4 (arbiter 5798800357): brand-new SQLite file nobody
else can see, my own named ports, nothing seeded, ports released by listener, and the whole
temp directory deleted and asserted gone.  The browser profile lives inside that directory
because "returning client" is exactly the state I am not allowed to leak anywhere else.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
PY = r"C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe"
TREE = os.path.join(LANE, "o269_tree_c79e2b4", "backend")
GEN_A = os.path.join(LANE, "o269_run", "dist_gen")            # index-Cpy_jhEg.js / worker e63d7421..
GEN_B = os.path.join(LANE, "o269_run", "dist_gen_c79e2b4")    # index-ChOTTCvB.js / worker 88a7d980..
BE_PORT, OR_PORT = 8942, 8941
RUN = sys.argv[1] if len(sys.argv) > 1 else "camp1"
SHA = "c79e2b4f4efe414dba22a071a7136ae10b5c84aa"

RUNDIR = os.path.join(LANE, "o274_run", RUN)
DB = os.path.join(RUNDIR, "one_shot.sqlite3")
PROFILE = os.path.join(RUNDIR, "profile")
POINTER = os.path.join(RUNDIR, "current_root.txt")
rec = {"order": "ORD-0274", "arm": "B", "run": RUN, "verifier": "1a986a24 HJ-P1",
       "source_sha": SHA, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
       "ports": {"backend": BE_PORT, "origin": OR_PORT}, "db": DB, "profile": PROFILE}
pids, handles = [], []


def open_log(p):
    fh = open(p, "wb")
    handles.append(fh)
    return fh


def listening(port):
    out = subprocess.run('netstat -ano | findstr ":%d "' % port, shell=True, capture_output=True,
                         text=True).stdout or ""
    return [ln.strip() for ln in out.splitlines() if "LISTENING" in ln.upper()]


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


def forbidden_move_audit(path):
    """'the instrument never cheated' has to be checkable by someone else.

    Comment lines are stripped first (this file's own header names the forbidden calls),
    and every remaining hit is printed - a bare 0 would be a claim, a listing is evidence.
    """
    rx = re.compile(r"\.unregister\s*\(|caches\s*\.\s*delete|caches\s*\.\s*clear|\.clear\s*\(\s*\)")
    code, hits = [], []
    for n, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        st = line.strip()
        if st.startswith(("//", "/*", "*")):
            continue
        code.append((n, st))
    for n, st in code:
        if rx.search(st):
            hits.append("%d: %s" % (n, st[:120]))
    return {"file": os.path.basename(path), "code_lines_scanned": len(code),
            "forbidden_calls_found": hits, "clean": not hits}


try:
    if os.path.isdir(RUNDIR):
        shutil.rmtree(RUNDIR)
    os.makedirs(RUNDIR)
    open(POINTER, "w", encoding="utf-8").write(GEN_A)

    env = dict(os.environ)
    env.update({"CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
                "CITYNEXUS_DEMO_MODE": "false", "CITYNEXUS_AI_ENABLED": "false",
                "CITYNEXUS_AI_API_KEY": "", "DEEPSEEK_API_KEY": "",
                "CITYNEXUS_LIVE_VALHALLA_URL": "", "CITYNEXUS_GUARDIAN_AUTORUN": "false",
                "CITYNEXUS_REAL_CITY_ENABLED": "false", "CITYNEXUS_ENV": "development",
                "PYTHONIOENCODING": "utf-8"})
    be = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                           "--port", str(BE_PORT), "--log-level", "warning"],
                          cwd=TREE, env=env, stdout=open_log(os.path.join(RUNDIR, "backend.log")),
                          stderr=subprocess.STDOUT)
    pids.append(be.pid)
    ready = None
    for _ in range(60):
        time.sleep(1.0)
        st, body = http("http://127.0.0.1:%d/openapi.json" % BE_PORT, timeout=3)
        if st == 200:
            ready = len(json.loads(body).get("paths", {}))
            break
        if be.poll() is not None:
            break
    assert ready, "backend did not come up"
    orp = subprocess.Popen([PY, os.path.join(LANE, "o274_origin.py"), LANE, RUNDIR,
                               str(OR_PORT), str(BE_PORT)],
                              stdout=open_log(os.path.join(RUNDIR, "origin.log")),
                              stderr=subprocess.STDOUT, env=env)
    pids.append(orp.pid)
    time.sleep(3.0)
    st, body = http("http://127.0.0.1:%d/" % OR_PORT)
    rec["surface"] = {"backend_openapi_paths": ready, "origin_root_status": st,
                      "served_entry": (lambda m: m.group(1).decode() if m else None)(re.search(rb"assets/(index-[\w-]+\.js)", body or b""))}
    assert st == 200 and b"index-Cpy_jhEg.js" in (body or b""), rec["surface"]

    wenv = dict(env)
    wenv.update({"CNX_BASE": "http://127.0.0.1:%d" % OR_PORT, "CNX_RUN": RUN, "CNX_PROFILE": PROFILE,
                 "CNX_GEN_A": GEN_A, "CNX_GEN_B": GEN_B, "CNX_POINTER": POINTER,
                 "CNX_SHOTS": os.path.join(LANE, "shots")})
    t0 = time.time()
    with open(os.path.join(RUNDIR, "campaign_stdout.json"), "wb") as wf:
        rc = subprocess.call(["node", os.path.join(LANE, "o274_arms.cjs")], env=wenv, stdout=wf,
                             stderr=subprocess.STDOUT, timeout=1500)
    rec["campaign"] = {"exit": rc, "wall_s": round(time.time() - t0, 1)}
    camp = os.path.join(LANE, "o274_campaign_%s.json" % RUN)
    rec["forbidden_move_audit"] = forbidden_move_audit(os.path.join(LANE, "o274_arms.cjs"))
finally:
    for p in pids:
        kill(p)
    for fh in handles:
        try:
            fh.close()
        except Exception:                                     # noqa: BLE001
            pass
    time.sleep(2.0)
    for src, dst in [(os.path.join(RUNDIR, "requests.jsonl"), os.path.join(LANE, "o274_requests_%s.jsonl" % RUN)),
                     (os.path.join(RUNDIR, "campaign_stdout.json"), os.path.join(LANE, "o274_stdout_%s.json" % RUN)),
                     (camp, camp)]:
        if os.path.exists(src) and src != dst:
            shutil.copy(src, dst)
    rec["kept"] = [os.path.basename(d) for _, d in
                   [(os.path.join(RUNDIR, "requests.jsonl"), os.path.join(LANE, "o274_requests_%s.jsonl" % RUN)),
                    (os.path.join(RUNDIR, "campaign_stdout.json"), os.path.join(LANE, "o274_stdout_%s.json" % RUN))]
                   if os.path.exists(d)]
    for _ in range(6):
        if not os.path.isdir(RUNDIR):
            break
        shutil.rmtree(RUNDIR, ignore_errors=True)
        time.sleep(0.7)
    rec["isolation"] = {"rundir_deleted": not os.path.exists(RUNDIR),
                        "db_leftovers": [p for p in (DB, DB + "-wal", DB + "-shm") if os.path.exists(p)],
                        "profile_leftovers": os.path.exists(PROFILE),
                        "ports_final": {"backend": listening(BE_PORT), "origin": listening(OR_PORT)}}
    rec["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with open(os.path.join(LANE, "o274_run_%s.json" % RUN), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=2, default=str)
    print(json.dumps({k: rec.get(k) for k in ("run", "surface", "campaign", "forbidden_move_audit",
                                              "isolation", "kept", "FAILED")}, ensure_ascii=False, indent=2))
