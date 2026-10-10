"""ORD-0538: build four generations, and let the hit test decide each one.

Four cases, four answers, all measured on rendered text:
  base       -- the tip without this round's wiring: the empty cells carry no action at all, so the
                "every empty cell offers a way forward" arm must go red here.
  candidate  -- my bytes: five cells, five actions, each answering a point at its own centre in both
                language arms, and the one write-action going 0 rows -> 1 row read back.
  sever      -- `issueLinkGrant`'s onClick replaced by a no-op: the grants arm must go red.
  grow-en    -- the English label of that same control lengthened by a sentence: the *centre hit*
                must go red.  This is the case NO_GROWTH cannot see (it only guards the Chinese arm
                from gaining words), and it is the reason the roadmap asks for a hit test here.

Two stores run side by side so all five cells are reachable: one where every trip is in the bin
(=> the "no trip listed" and "pick a trip first" cells), one with a trip that has no members, no
invitations and no recorded action (=> the roster, invitation and action cells).
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
import urllib.request
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
WT = r"D:/moodle/_qoder_newlane_ord0444_20260929/wt2"
BACKEND = os.path.join(WT, "backend")
FRONTEND = os.path.join(WT, "frontend")
SC = r"D:/moodle/_qoder_newlane_ord0444_20260929/scratch"
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
NPM = r"C:/Program Files/nodejs/npm.cmd"
ARM = os.path.join(SC, "ord0538_arm_r4.cjs")
PREVIEW_DB = r"D:/moodle/_qoder_preview_20260920/_preview.db"
OUT = os.path.join(SC, "ord0538_arms_514b397f.json")
BASE_REV = "514b397f96f3b5165b24865f4a544ab6f8020084"
PANEL = "frontend/src/features/access/AccessPanel.tsx"
COPY = "frontend/src/features/access/accessCopy.ts"
REG = "frontend/src/app/v8PanelRegistry.tsx"
CSS = "frontend/src/features/access/access.css"
CHANGED = [PANEL, COPY, REG]
# `--only candidate` runs a subset and writes a separate file, so a diagnostic pass can never
# overwrite the four-generation evidence the block cites.
ONLY = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")]
# `grow` is the case the roadmap names -- an English sentence added on the side NO_GROWTH cannot see
# -- and its answer is whatever the hit test measures, not a colour fixed in advance.  `pin` is the
# counterexample for the hit test itself: every action of this screen pinned into the fixed bar's
# band, which is exactly the failure the test exists to catch.
KINDS = [("base", "red"), ("candidate", "green"), ("sever", "red"), ("grow", "measured"),
         ("pin", "red")]

if ONLY:
    KINDS = [k for k in KINDS if k[0] in ONLY[0].split(",")]
    OUT = os.path.join(SC, "ord0538_diag_%s.json" % ONLY[0].replace(",", "-"))
ENV = dict(os.environ)
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(_k, None)
out = {"base_revision": BASE_REV,
       "candidate_head": subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"],
                                        capture_output=True, text=True).stdout.strip(),
       "generated_at": time.strftime("%H:%M:%S"), "runs": []}


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def listeners(port):
    net = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         errors="replace").stdout
    return sorted({l.split()[-1] for l in net.splitlines()
                   if ":%d " % port in l and "LISTENING" in l.upper()})


def ancestry(pid):
    """`python.exe` in that venv is a launcher: it re-execs the real interpreter as its child, so the
    process holding my socket is never the one `Popen` handed back.  Ownership is therefore the parent
    chain, and it is measured rather than assumed -- a listener whose chain does not run through my
    child is some other lane's backend, and every reading in this file would belong to it."""
    ps = 'Get-CimInstance Win32_Process | ForEach-Object { "$($_.ProcessId) $($_.ParentProcessId)" }'
    txt = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                         text=True, errors="replace").stdout
    par = {}
    for line in txt.splitlines():
        bits = line.split()
        if len(bits) == 2 and bits[0].isdigit() and bits[1].isdigit():
            par[int(bits[0])] = int(bits[1])
    chain, cur = [], int(pid)
    for _ in range(14):
        chain.append(cur)
        cur = par.get(cur, 0)
        if cur == 0 or cur in chain:
            break
    return chain


def sh(cwd, *a, timeout=1200):
    r = subprocess.run(list(a), cwd=cwd, env=ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="strict", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def git_show(rev, path):
    return subprocess.run(["git", "-C", WT, "show", "%s:%s" % (rev, path)],
                          capture_output=True).stdout


# ------------------------------------------------------------------ two stores, two backends
DB_BINNED = os.path.join(BACKEND, "ord0538_a_%s.db" % uuid.uuid4().hex[:8])
DB_JOURNEY = os.path.join(BACKEND, "ord0538_b_%s.db" % uuid.uuid4().hex[:8])
shutil.copyfile(PREVIEW_DB, DB_BINNED)
shutil.copyfile(PREVIEW_DB, DB_JOURNEY)
PORT_A, PORT_B = free_port(), free_port()
now = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
# One trip per (generation, case, language, shape).  A shared trip is what made the previous pass's
# two counterexamples worthless: the candidate run's own write emptied the grants cell, so `sever`
# and `grow` went red on "the empty cell is not on screen" instead of on the thing they mutate.
JOURNEYS_B = {"%s|%s|%s|%s" % (kind, case, lang, shape): str(uuid.uuid4())
              for kind, _ in KINDS for case in ("no_anything", "roles_empty")
              for lang in ("zh", "en") for shape in ("390x844", "1280x900")}
# A journey made here has no members, no invitations and no recorded action by construction, so the
# three cells under test start empty without deleting anything: the member and grant tables do not
# even exist in this copy until `ensure_schema` adds them at startup.
with sqlite3.connect(DB_JOURNEY) as con:
    owner = con.execute("SELECT id FROM travelers ORDER BY id LIMIT 1").fetchone()[0]
    for tag, jid in JOURNEYS_B.items():
        con.execute(
            "INSERT INTO journeys (id, traveler_id, title, city_code, timezone, start_at, end_at,"
            " budget_currency, budget_amount_minor, planning_mode, status, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (jid, owner, "关系层空态 走查 " + tag, "CN-XIAMEN", "Asia/Shanghai",
             "2031-05-01T00:00:00+00:00", "2031-05-03T00:00:00+00:00", "CNY", 120000, "balanced",
             "PLANNED", now, now))
out["stores"] = {"journeys": JOURNEYS_B, "owner_traveller": owner}

env_a = dict(ENV, CITYNEXUS_DATABASE_URL="sqlite:///./" + os.path.basename(DB_BINNED),
             CITYNEXUS_DEMO_MODE="true")
env_b = dict(ENV, CITYNEXUS_DATABASE_URL="sqlite:///./" + os.path.basename(DB_JOURNEY),
             CITYNEXUS_DEMO_MODE="true")
logs = [open(os.path.join(SC, "uvicorn_0538_%s.log" % k), "wb") for k in ("a", "b")]
kids = [subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                          "--port", str(p)], cwd=BACKEND, env=e, stdout=g,
                         stderr=subprocess.STDOUT) for p, e, g in
        ((PORT_A, env_a, logs[0]), (PORT_B, env_b, logs[1]))]
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for p in (PORT_A, PORT_B):
    for _ in range(150):
        try:
            with OPENER.open("http://127.0.0.1:%d/api/v1/health" % p, timeout=6) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(1)
    else:
        raise SystemExit("backend :%d never came up" % p)
def http_json(port, method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data, method=method)
    if data:
        req.add_header("content-type", "application/json")
    try:
        with OPENER.open(req, timeout=25) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"head": raw[:120].decode("utf-8", "replace")}


import urllib.error
# store A: the trips go into the bin through the door that owns that column -- no direct write to a
# column this copy predates
listed = http_json(PORT_A, "GET", "/api/v1/journeys")[1] or []
binned = [http_json(PORT_A, "DELETE", "/api/v1/journeys/%s" % row["id"])[0] for row in listed]
out["stores"]["binned_through_the_door"] = {"requested": len(listed), "statuses": sorted(set(binned)),
                                            "list_now_returns": len(http_json(PORT_A, "GET",
                                                                               "/api/v1/journeys")[1] or [])}
print("store A binned:", out["stores"]["binned_through_the_door"])
with sqlite3.connect(DB_JOURNEY) as con:
    try:
        gone = con.execute("SELECT count(*) FROM journey_role_capabilities").fetchone()[0]
        con.execute("DELETE FROM journey_role_capabilities")
    except sqlite3.OperationalError:
        gone = -1
out["stores"]["role_capability_rows_removed"] = gone
out["backends"] = {"a": {"port": PORT_A, "pids": listeners(PORT_A), "pid": kids[0].pid},
                   "b": {"port": PORT_B, "pids": listeners(PORT_B), "pid": kids[1].pid}}
for k, kid in (("a", kids[0]), ("b", kids[1])):
    rec = out["backends"][k]
    rec["listener_ancestry"] = {p: ancestry(p) for p in rec["pids"]}
    rec["every_listener_descends_from_my_child"] = bool(rec["pids"]) and all(
        kid.pid in chain for chain in rec["listener_ancestry"].values())


# ------------------------------------------------------------------- previews (one per store)
PREF_A, PREF_B = free_port(), free_port()
plogs = [open(os.path.join(SC, "vite_preview_0538_%s.log" % k), "wb") for k in ("a", "b")]
pchildren = []
for port, backend, handle in ((PREF_A, PORT_A, plogs[0]), (PREF_B, PORT_B, plogs[1])):
    penv = dict(ENV, CITYNEXUS_BACKEND_PORT=str(backend))
    pchildren.append(subprocess.Popen(
        ["node", os.path.join(FRONTEND, "node_modules", "vite", "bin", "vite.js"), "preview",
         "--host", "127.0.0.1", "--port", str(port), "--strictPort"], cwd=FRONTEND, env=penv,
        stdout=handle, stderr=subprocess.STDOUT))


def wait_preview(port):
    for _ in range(120):
        try:
            with OPENER.open("http://127.0.0.1:%d/index.html" % port, timeout=8) as r:
                if r.status == 200:
                    return re.findall(r"/assets/(index-[A-Za-z0-9_\-]+\.js)",
                                      r.read().decode("utf-8"))[:1]
        except Exception:
            time.sleep(1)
    return []


# ------------------------------------------------------------------ the four generations
saved = {p: io.open(os.path.join(WT, p), "rb").read() for p in CHANGED + [CSS]}
EN_LABEL = '"access.emptyIssueGrant": "Issue a link-readable invitation",'


def apply_generation(kind):
    for p in CHANGED + [CSS]:
        io.open(os.path.join(WT, p), "wb").write(saved[p])
    if kind == "base":
        # The clearance fix is not what this order is about, so base keeps it: the base run must go
        # red for exactly one reason -- the empty cells carry no action at all.
        for p in CHANGED:
            io.open(os.path.join(WT, p), "wb").write(git_show(BASE_REV, p))
    elif kind == "pin":
        # Candidate's bytes, with every action of this screen pinned into the fixed bar's band.  If
        # the hit test still passed here it would be testing nothing.
        s = io.open(os.path.join(WT, CSS), encoding="utf-8").read()
        io.open(os.path.join(WT, CSS), "w", encoding="utf-8", newline="\n").write(
            s + "\n/* MUTATED (ORD-0538 counterexample): pinned into the nav band at every scroll */\n"
                ".cn-access .cn-access-row-action { position: fixed; bottom: 2px; left: 6px;"
                " z-index: 5; }\n")
    elif kind == "sever":
        s = io.open(os.path.join(WT, PANEL), encoding="utf-8").read()
        needle = 'emptyAction("access-empty-issue-link-grant", "access.emptyIssueGrant",\n                () => void issueLinkGrant())'
        assert s.count(needle) == 1, s.count(needle)
        s = s.replace(needle,
                      'emptyAction("access-empty-issue-link-grant", "access.emptyIssueGrant",\n'
                      '                () => { /* MUTATED: the write wiring taken out */ })', 1)
        io.open(os.path.join(WT, PANEL), "w", encoding="utf-8", newline="\n").write(s)
    elif kind == "grow":
        s = io.open(os.path.join(WT, COPY), encoding="utf-8").read()
        assert s.count(EN_LABEL) == 1
        s = s.replace(EN_LABEL, '"access.emptyIssueGrant":'
                                ' "Issue a link-readable invitation so that anybody holding the address'
                                ' can open this trip without being a member of it,",', 1)
        io.open(os.path.join(WT, COPY), "w", encoding="utf-8", newline="\n").write(s)


CASES = [("no_anything", PREF_B, "journey"), ("roles_empty", PREF_B, "journey"),
         ("roles_no_pick", PREF_B, "no trip picked"),
         ("roles_no_ref", PREF_B, "no reference stored"), ("reachability", PREF_A, "no trip at all")]
# The three wall probes read the shell, not this round's bytes: they run once against base and once
# against the candidate, and they are readings rather than arms -- nothing inside an unmounted panel
# can be tapped, so an assertion there could only ever be vacuous.
WALL_CASES = ("roles_no_pick", "roles_no_ref", "reachability")
ONLY_KINDS = {case: ("base", "candidate") for case in WALL_CASES}
# A red is only evidence if it names the thing the generation broke.  These are the phrases each
# mutation must produce, and the phrases it must not -- the last pass's sever went red on a cell that
# had simply been filled by the generation before it, which says nothing about a severed write.
MUST_RED = {"sever": "the invitation action wrote a row", "pin": "centre hit",
            "base": "carries an action"}
MUST_NOT = {"sever": "is on screen", "pin": "carries an action"}
for kind, expect in KINDS:
    apply_generation(kind)
    built = sh(FRONTEND, NPM, "run", "build", timeout=900)
    entry = re.findall(r"/assets/(index-[A-Za-z0-9_\-]+\.js)",
                       io.open(os.path.join(FRONTEND, "dist", "index.html"),
                               encoding="utf-8").read())[:1]
    run = {"kind": kind, "expect": expect, "build_exit": built[0], "built_entry": entry,
           "cases": []}
    for case, preview, store in CASES:
        allowed = ONLY_KINDS.get(case)
        if allowed is not None and kind not in allowed:
            continue
        served = wait_preview(preview)
        for shape in ("390x844", "1280x900"):
            if case in WALL_CASES and shape != "390x844":
                continue  # what paints instead of the panel is a phone-shape finding
            for locale in ("zh-CN", "en"):
                journey = "" if case in WALL_CASES else (
                    JOURNEYS_B.get(
                        "%s|%s|%s|%s" % (kind, case, "zh" if locale == "zh-CN" else "en", shape),
                        ""))
                wr = subprocess.run(
                    ["node", ARM, "http://127.0.0.1:%d" % preview, case, locale, journey, owner,
                     shape],
                    cwd=FRONTEND, env=dict(ENV, NODE_PATH=os.path.join(FRONTEND, "node_modules")),
                    capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=600)
                payload = {}
                for line in wr.stdout.splitlines():
                    if line.strip().startswith("{"):
                        payload = json.loads(line)
                run["cases"].append({"case": case, "store": store, "locale": locale,
                                     "shape": shape,
                                     "preview_entry": served, "exit": wr.returncode,
                                     "checks": payload.get("checks"),
                                     "failures": payload.get("failures"),
                                     "cells": payload.get("cells"),
                                     "grant_rows_before": payload.get("grant_rows_before"),
                                     "grant_rows_after": payload.get("grant_rows_after"),
                                     "stderr_head": wr.stderr[-200:] if not payload else "",
                                     "wall": payload.get("wall"),
                                     "journey": journey})
    arm_cases = [c for c in run["cases"] if c["case"] not in WALL_CASES]
    ran_green = all(c["exit"] == 0 for c in arm_cases)
    run["all_cases_green"] = ran_green
    reds = sorted({f for c in arm_cases for f in (c["failures"] or [])})
    run["red_checks"] = reds
    run["hit_test_held"] = all("centre hit" not in f for f in reds)
    if expect == "measured":
        run["matches_expectation"] = "measured, no colour claimed in advance"
    elif expect == "green":
        run["matches_expectation"] = ran_green
    else:
        must, must_not = MUST_RED.get(kind), MUST_NOT.get(kind)
        run["matches_expectation"] = (not ran_green) and (
            must is None or any(must in f for f in reds)) and (
            must_not is None or not any(must_not in f for f in reds))
    out["runs"].append(run)
    print("%-9s expect=%-8s build=%s entry=%s cases=%s red=%d hit_held=%s -> %s" % (
        kind, expect, built[0], entry[:1],
        " ".join("%s/%s@%s:%d" % (c["case"], c["locale"], c["shape"], c["exit"])
                 for c in arm_cases),
        len(reds), run["hit_test_held"],
        "AS EXPECTED" if run["matches_expectation"] is True else run["matches_expectation"]))

for p in CHANGED + [CSS]:
    io.open(os.path.join(WT, p), "wb").write(saved[p])
out["restored_build"] = {"exit": sh(FRONTEND, NPM, "run", "build", timeout=900)[0],
                         "entry": re.findall(r"/assets/(index-[A-Za-z0-9_\-]+\.js)",
                                             io.open(os.path.join(FRONTEND, "dist", "index.html"),
                                                     encoding="utf-8").read())[:1]}
for pc in pchildren + kids:
    subprocess.run(["taskkill", "/PID", str(pc.pid), "/T", "/F"], capture_output=True)
for handle in plogs + logs:
    handle.close()
time.sleep(8)
for db in (DB_BINNED, DB_JOURNEY):
    for suffix in ("", "-wal", "-shm"):
        try:
            if os.path.exists(db + suffix):
                os.remove(db + suffix)
        except PermissionError:
            print("LEFTOVER_DB", db + suffix)
io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
