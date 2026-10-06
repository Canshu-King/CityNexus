"""ORD-0513 · measure the same three refusals on two generations, then prove the arm can fail.

Four phases, one file:
  base        -- the tip's `main.py`: what the doors say today.
  candidate   -- this round's `main.py`: the two sentences that carried identifiers, rewritten.
                 The reason codes and the `error.details` keys are compared by name against base, so
                 "I only changed the words" is a measurement rather than a claim.
  screen      -- the glass, both language arms, both shapes: 收藏到… pressed twice on one stop, which
                 is the product's own way to meet the 409.  Assertions read `innerText`.
  masked      -- the counterexample: `alreadyHere` taken out of the feature's copy table.  If the
                 screen arm still passed with the vocabulary channel cut, it was never reading words.

Nothing writes to `D:/moodle/_qoder_preview_20260920/_preview.db`: it is copied per phase and every
row lands in a private file under `backend/`.
"""
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
WT = r"D:/moodle/_qoder_newlane_ord0444_20260929/wt2"
BACKEND = os.path.join(WT, "backend")
FRONTEND = os.path.join(WT, "frontend")
SC = r"D:/moodle/_qoder_newlane_ord0444_20260929/scratch"
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
NPM = r"C:/Program Files/nodejs/npm.cmd"
BASE_REV = "0c061d9eb74b21f0b0b297a068778479b08658b4"
MAIN = "backend/app/main.py"
COPY = "frontend/src/features/collections/collectionCopy.ts"
OUT = os.path.join(SC, "ord0513_runs_%s.json" % BASE_REV[:8])
ENV = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)


def sh(cwd, *a, timeout=1200):
    r = subprocess.run(list(a), cwd=cwd, env=ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def git_show(rev, path):
    return subprocess.run(["git", "-C", WT, "show", "%s:%s" % (rev, path)],
                          capture_output=True).stdout


out = {"base_revision": BASE_REV,
       "head": sh(WT, "git", "rev-parse", "HEAD")[1].strip(),
       "started": time.strftime("%m-%d %H:%M:%S"), "phases": {}}
main_now = io.open(os.path.join(WT, MAIN), "rb").read()
copy_now = io.open(os.path.join(WT, COPY), "rb").read()
out["candidate_main_is_tip_bytes"] = main_now == git_show(BASE_REV, MAIN)
print("candidate main differs from tip:", not out["candidate_main_is_tip_bytes"])


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def dump(where):
    out["dumped_after"] = where
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("  [partial json after %s: %d B]" % (where, os.path.getsize(OUT)))



# ------------------------------------------------------------------ phase 1 and 2: the doors
for tag, blob in (("base", git_show(BASE_REV, MAIN)), ("candidate", main_now)):
    io.open(os.path.join(WT, MAIN), "wb").write(blob)
    rc, txt = sh(BACKEND, PY, "-u", os.path.join(SC, "ord0513_doors_r1.py"), tag, timeout=900)
    read = {}
    path = os.path.join(SC, "ord0513_doors_%s.json" % tag)
    if os.path.exists(path):
        read = json.loads(io.open(path, encoding="utf-8").read())
    out["phases"][tag] = {"exit": rc, "stdout_tail": txt[-400:], "refusals": read.get("refusals"),
                          "preview_store_untouched": read.get("preview_store_untouched"),
                          "head": read.get("head")}
    print("%-10s doors exit=%s refusals=%s" % (tag, rc, len(read.get("refusals") or [])))
    dump(tag)

io.open(os.path.join(WT, MAIN), "wb").write(main_now)

# ------------------------------------------------- compare the two generations, by name
def by_code(refusals):
    d = {}
    for r in refusals or []:
        d.setdefault(str(r["reason_code"]), []).append(r)
    return d


b, c = by_code(out["phases"]["base"]["refusals"]), by_code(out["phases"]["candidate"]["refusals"])
cmp_rows = []
for code in sorted(set(b) | set(c)):
    rb = (b.get(code) or [{}])[0]
    rc = (c.get(code) or [{}])[0]
    cmp_rows.append({
        "reason_code": code,
        "in_base": code in b, "in_candidate": code in c,
        "http_status_base": rb.get("http_status"), "http_status_candidate": rc.get("http_status"),
        "details_keys_base": rb.get("details_keys"), "details_keys_candidate": rc.get("details_keys"),
        "details_shape_same": rb.get("details_keys") == rc.get("details_keys"),
        "code_field_same": rb.get("code") == rc.get("code"),
        "message_changed": rb.get("message") != rc.get("message"),
        "uuid_in_message_base": rb.get("message_has_uuid"),
        "uuid_in_message_candidate": rc.get("message_has_uuid"),
        "message_base": rb.get("message"), "message_candidate": rc.get("message"),
    })
out["door_comparison"] = cmp_rows
for row in cmp_rows:
    print("  %-30s status %s->%s details_same=%s uuid_in_msg %s->%s" % (
        row["reason_code"], row["http_status_base"], row["http_status_candidate"],
        row["details_shape_same"], row["uuid_in_message_base"], row["uuid_in_message_candidate"]))

# --------------------------------------------------------- the stack the glass runs on
PORT = free_port()
src = r"D:/moodle/_qoder_preview_20260920/_preview.db"
db_path = os.path.join(BACKEND, "ord0513_screen_%d.db" % (int(time.time()) % 100000))
env = dict(ENV, CITYNEXUS_DATABASE_URL="sqlite:///./" + os.path.basename(db_path),
           CITYNEXUS_DEMO_MODE="true")
shutil.copyfile(src, db_path)
out["screen_store"] = {"private_copy": os.path.basename(db_path),
                       "copied_from_bytes": os.path.getsize(src)}
log = io.open(os.path.join(SC, "uvicorn_0513_screen.log"), "wb")
kid = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(PORT)], cwd=BACKEND, env=env, stdout=log,
                       stderr=subprocess.STDOUT)
import sqlite3
import urllib.error
import urllib.request
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}) )
for _ in range(200):
    try:
        with OP.open("http://127.0.0.1:%d/api/v1/health" % PORT, timeout=6) as r:
            if r.status == 200:
                break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("screen backend never came up")

with sqlite3.connect("file:%s?mode=ro" % src.replace("\\", "/"), uri=True) as s0:
    jid = s0.execute("SELECT id FROM journeys LIMIT 1").fetchone()[0]
def call(method, path, body=None):
    """One call against my own private backend -- the same door the traveller's device uses."""
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


out["screen_journey_is_the_stores_own"] = bool(jid)

# The collect face asks for shelves by the journey's own traveller (`TripItinerary.tsx:536` reads
# `data.journey.traveler_id`), so the walk needs a shelf owned by that id -- made through the door,
# not inserted, because "the door answered 201 and the read lists it" is the fact the screen needs.
with sqlite3.connect(db_path) as con:
    journey_owner = con.execute("SELECT traveler_id FROM journeys WHERE id=?", (jid,)).fetchone()[0]
    shelves_for_owner = con.execute("SELECT count(*) FROM collection_folders WHERE owner_traveler_id=?",
                                    (journey_owner,)).fetchone()[0]
made = call("POST", "/api/v1/collections",
            {"name": "ORD-0513 走查架", "owner_traveler_id": journey_owner})
listed = call("GET", "/api/v1/collections?traveler_id=%s" % journey_owner)
out["shelf_for_the_walk"] = {
    "journey_owner_is_the_folders_owner": shelves_for_owner,
    "created_through_the_door": made[0],
    "read_lists_rows": len(listed[1] or []) if isinstance(listed[1], list) else None,
    "http_status_of_read": listed[0],
}
print("shelf for the walk:", out["shelf_for_the_walk"])

PREF = free_port()
plog = io.open(os.path.join(SC, "vite_preview_0513.log"), "wb")
pchild = subprocess.Popen(["node", os.path.join(FRONTEND, "node_modules", "vite", "bin", "vite.js"),
                           "preview", "--host", "127.0.0.1", "--port", str(PREF), "--strictPort"],
                          cwd=FRONTEND, env=dict(ENV, CITYNEXUS_BACKEND_PORT=str(PORT)),
                          stdout=plog, stderr=subprocess.STDOUT)


def wait_preview(port):
    for _ in range(150):
        try:
            with OP.open("http://127.0.0.1:%d/index.html" % port, timeout=8) as r:
                if r.status == 200:
                    return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(1)
    return ""



def run_arms(tag, shapes):
    html = wait_preview(PREF)
    rows_meta = {"served_entry": re.findall(r"/assets/(index-[A-Za-z0-9_\-]+\.js)", html)[:1]}
    rows = []
    for shape in shapes:
        for locale in ("zh-CN", "en"):
            wr = subprocess.run(
                ["node", os.path.join(SC, "ord0513_arm_r1.cjs"),
                 "http://127.0.0.1:%d" % PREF, locale, jid, shape, tag],
                cwd=FRONTEND, env=dict(ENV, NODE_PATH=os.path.join(FRONTEND, "node_modules")),
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            payload = {}
            for line in wr.stdout.splitlines():
                if line.strip().startswith("{"):
                    payload = json.loads(line)
            rows.append({"shape": shape, "locale": locale, "exit": wr.returncode,
                         "checks": payload.get("checks"), "failures": payload.get("failures"),
                         "posts": payload.get("posts"),
                         "stderr_tail": wr.stderr[-200:]})
    out["phases"][tag] = {"rows": rows, "served_entry": rows_meta["served_entry"],
                          "all_green": all(r["exit"] == 0 for r in rows)}
    print("%-10s arms: %s" % (tag, " ".join("%s/%s:%d" % (r["shape"], r["locale"], r["exit"])
                                            for r in rows)))
    dump(tag)
    return rows


# Build first. This file used to walk whatever `dist/` the previous generation had left behind, and
# under a rebased tree that is a reading of bytes that no longer exist -- the served entry is now
# required to equal the entry this round's build just wrote, or the phase aborts.
rcb, txtb = sh(FRONTEND, NPM, "run", "build", timeout=900)
built_entry = re.findall(r"/assets/(index-[A-Za-z0-9_\-]+\.js)",
                         io.open(os.path.join(FRONTEND, "dist", "index.html"),
                                 encoding="utf-8").read())[:1]
out["screen_build"] = {"exit": rcb, "built_entry": built_entry}
print("screen build:", out["screen_build"])
assert rcb == 0, "the frontend build for the walk did not succeed"
served_html = wait_preview(PREF)
out["preview_ready"] = {"answered": bool(served_html),
                        "entry_from_served_html": re.findall(
                            r"/assets/(index-[A-Za-z0-9_\-]+\.js)", served_html)[:1]}
print("preview ready:", out["preview_ready"])
assert out["preview_ready"]["entry_from_served_html"] == built_entry, (
    "the static server is answering %s while this round's build wrote %s -- refusing to report "
    "screen readings taken against bytes I did not ship" % (
        out["preview_ready"]["entry_from_served_html"], built_entry))
run_arms("screen_tip_copy", ["390x844", "1280x900"])

# ------------------------------------------------ phase 4: mask the vocabulary channel
# Masking here means: the human arms are gone and the machine token is what reaches the glass.
# Swapping the two strings keeps every key, type and render path intact -- an earlier cut deleted
# `alreadyHere` from the table, the panel unmounted, and the arm went red for a reason that had
# nothing to do with words. A mutation that reddens the wrong check proves nothing.
s = io.open(os.path.join(WT, COPY), encoding="utf-8").read()
ZH_LINE = '    zh: "这一枚已经在这个架子上。",'
EN_LINE = '    en: "This place is already on that shelf.",'
TOKEN = '    zh: "PLACE_ALREADY_IN_COLLECTION",'
assert s.count(ZH_LINE) == 1, ("zh needle", s.count(ZH_LINE))
assert s.count(EN_LINE) == 1, ("en needle", s.count(EN_LINE))
s = s.replace(ZH_LINE, TOKEN, 1)
s = s.replace(EN_LINE, TOKEN.replace("zh:", "en"), 1)
io.open(os.path.join(WT, COPY), "w", encoding="utf-8", newline="\n").write(s)
rc, txt = sh(FRONTEND, NPM, "run", "build", timeout=900)
out["masked_build"] = {"exit": rc, "tail": txt[-200:]}
run_arms("masked_copy", ["390x844", "1280x900"])
io.open(os.path.join(WT, COPY), "wb").write(copy_now)
rc, txt = sh(FRONTEND, NPM, "run", "build", timeout=900)
out["restored_build"] = {"exit": rc, "tail": txt[-200:]}

subprocess.run(["taskkill", "/PID", str(pchild.pid), "/T", "/F"], capture_output=True)
subprocess.run(["taskkill", "/PID", str(kid.pid), "/T", "/F"], capture_output=True)
plog.close()
log.close()
time.sleep(6)
for p in (db_path,):
    for suffix in ("", "-wal", "-shm"):
        try:
            if os.path.exists(p + suffix):
                os.remove(p + suffix)
        except PermissionError:
            print("LEFTOVER_DB", p + suffix)
out["finished"] = time.strftime("%m-%d %H:%M:%S")
io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
print("worktree clean check:", sh(WT, "git", "status", "--porcelain")[1].strip()[:120])
