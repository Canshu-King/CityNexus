"""ORD-0444 product round: the container over real HTTP, with 成员归属 exercised as a scope.

Same three ownership proofs as every prior stack receipt, taken in the same batch as the reads:
the listening pid is the child this script launched, that process' command line names the app, and
the rows the answers report are read back out of THIS script's own sqlite file -- whose name is
handed to the server from the same variable this script opens, so "the store I read" and "the store
the door wrote" cannot drift apart (they did, in an earlier round of this probe).
"""
import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BACKEND = r"D:/moodle/_qoder_newlane_ord0444_20260929/wt2/backend"
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
PREVIEW = r"D:/moodle/_qoder_preview_20260920/_preview.db"
PRIVATE = os.path.join(BACKEND, "ord0444prod_%s.db" % uuid.uuid4().hex[:8])
LOG = r"D:/moodle/_qoder_newlane_ord0444_20260929/scratch/uvicorn_prod.log"
PORT = 60181
BASE = "http://127.0.0.1:%d/api/v1" % PORT
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
out = {"port": PORT, "at": time.strftime("%H:%M:%S"), "steps": [], "ownership": {}}


def note(step, **kw):
    out["steps"].append(dict(step=step, **kw))
    print(json.dumps(kw, ensure_ascii=False)[:400])


def call(method, path, body=None, query=None):
    url = BASE + path + ("?" + urllib.parse.urlencode(query) if query else "")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("content-type", "application/json")
    try:
        with OP.open(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        out["steps"].append({"step": "instrument_exception", "path": path,
                             "type": type(e).__name__, "msg": str(e)[:200]})
        raise


def envelope(raw):
    j = json.loads(raw) if raw else {}
    return j.get("error", j)


def digest(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


shutil.copyfile(PREVIEW, PRIVATE)
out["ownership"]["private_db"] = os.path.basename(PRIVATE)
out["ownership"]["preview_sha1_before"] = digest(PREVIEW)

con = sqlite3.connect("file:%s?mode=ro" % PRIVATE.replace("\\", "/"), uri=True)
places = [r[0] for r in con.execute("SELECT id FROM places ORDER BY id LIMIT 2")]
travelers = [r[0] for r in con.execute("SELECT id FROM travelers ORDER BY id LIMIT 2")]
con.close()
note("ids_from_private_copy", places=places, travelers=travelers)
owner = travelers[0]
other = travelers[1] if len(travelers) > 1 else None

env = dict(os.environ)
env["CITYNEXUS_DATABASE_URL"] = "sqlite:///./" + os.path.basename(PRIVATE)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    env.pop(k, None)
out["ownership"]["url_given_to_server"] = env["CITYNEXUS_DATABASE_URL"]
out["ownership"]["same_file_on_both_sides"] = env["CITYNEXUS_DATABASE_URL"].endswith(
    os.path.basename(PRIVATE))
# a port somebody else holds is not mine to measure on
stale = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                       errors="replace").stdout
holding = sorted({l.split()[-1] for l in stale.splitlines()
                  if ":%d " % PORT in l and "LISTENING" in l.upper()})
if holding:
    for pid in holding:
        subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
    time.sleep(3)
    out["ownership"]["killed_stale_listener_pids"] = holding
logf = open(LOG, "wb")
child = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                          "--port", str(PORT)], cwd=BACKEND, env=env, stdout=logf,
                         stderr=subprocess.STDOUT)
out["ownership"]["launched_pid"] = child.pid
up = False
t0 = time.time()
refusals = 0
while time.time() - t0 < 180:
    try:
        st, _ = call("GET", "/health")
    except urllib.error.URLError:
        # refused while uvicorn boots -- a state of the wait, not a finding about the product
        refusals += 1
        st = None
    if st == 200:
        up = True
        break
    time.sleep(1)
note("server_up", up=up, seconds=round(time.time() - t0, 1), refused_while_booting=refusals)

# The stage carries one traveller, and a scope is only proven against a second pair of eyes.  That
# traveller is minted through the product's own door rather than written into the file, so the read
# below is a read of what the server would answer to a real caller.
if not other:
    st, raw = call("POST", "/travelers", {"display_name": "ORD-0444 第二位旅客",
                                          "timezone": "Asia/Shanghai"})
    made = json.loads(raw)
    other = str(made.get("id"))
    note("second_traveller_minted_through_the_door", status=st, id=other)
else:
    note("second_traveller_from_the_stage", id=other)

net = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                     errors="replace").stdout
listeners = sorted({l.split()[-1] for l in net.splitlines()
                    if ":%d " % PORT in l and "LISTENING" in l.upper()})
out["ownership"]["listening_pids"] = listeners
ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | ForEach-Object "
                     "{ \"$($_.ProcessId)|$($_.ParentProcessId)|$($_.CommandLine)\" }"
                     % (listeners[0] if listeners else "0")],
                    capture_output=True, text=True, errors="replace").stdout.strip()
parts = ps.split("|")
out["ownership"]["server_pid"] = parts[0] if parts else None
out["ownership"]["server_parent_pid"] = parts[1] if len(parts) > 1 else None
out["ownership"]["server_command_line"] = (parts[2] if len(parts) > 2 else "")[:200]
out["ownership"]["pid_matches_child"] = (
    listeners == [str(child.pid)]
    or (out["ownership"]["server_parent_pid"] == str(child.pid)
        and "uvicorn" in out["ownership"]["server_command_line"]))
# Bolted to the door, not to my diligence: an answer from a process this script did not launch is
# not evidence about this tree.  An earlier round of this probe read a leftover server's database
# and called its own file "missing table" -- with this abort in place that cannot be reported.
if not (up and out["ownership"]["pid_matches_child"] and out["ownership"]["same_file_on_both_sides"]):
    print("ABORT_NOT_OWNED", json.dumps(out["ownership"], ensure_ascii=False)[:400])
    raise SystemExit(2)
try:
    st, raw = call("POST", "/collections", {"name": "周末收藏", "owner_traveler_id": owner})
    shelf = json.loads(raw)
    note("create_shelf", status=st, id=shelf.get("id"), name=shelf.get("name"),
         owner_on_answer=shelf.get("owner_traveler_id"), owner_sent=owner,
         matches=shelf.get("owner_traveler_id") == owner, item_count=shelf.get("item_count"))
    fid = shelf["id"]

    st, raw = call("POST", "/collections", {"name": "无人认领", "owner_traveler_id":
                                            "ord0444-no-such-traveller"})
    e = envelope(raw)
    note("counter_owner_unknown", status=st, code=e.get("code"), reason_code=e.get("reason_code"),
         details=e.get("details"), is_500=(st == 500))

    st, raw = call("GET", "/collections")
    e = envelope(raw)
    note("counter_unscoped_read", status=st, is_500=(st == 500), reason=e.get("reason_code"),
         body_head=(json.loads(raw) if raw and st == 200 else "not a shelf list"))

    st, raw = call("POST", "/collections/%s/items" % fid,
                   {"place_id": places[0], "note": "值得慢走一会"})
    added = json.loads(raw)
    note("add_place", status=st, place_name=added.get("name"), note_on_answer=added.get("note"))

    st, raw = call("GET", "/collections", query={"traveler_id": owner})
    mine = json.loads(raw)
    hit = [s for s in mine if s["id"] == fid][0]
    note("read_as_owner", status=st, shelves=len(mine), item_count=hit["item_count"],
         item_name=hit["items"][0]["name"], owner_of_every_shelf=sorted(
             {s["owner_traveler_id"] for s in mine}), tally_agrees=all(
             s["item_count"] == len(s["items"]) for s in mine))

    if other:
        st, raw = call("GET", "/collections", query={"traveler_id": other})
        theirs = json.loads(raw)
        note("read_as_other_traveller", status=st, shelves=len(theirs),
             my_shelf_visible=any(s["id"] == fid for s in theirs),
             ids=[s["id"] for s in theirs][:4])

    con = sqlite3.connect("file:%s?mode=ro" % PRIVATE.replace("\\", "/"), uri=True)
    fr = con.execute("SELECT count(*) FROM collection_folders WHERE id=?", (fid,)).fetchone()[0]
    ir = con.execute("SELECT count(*) FROM collection_items WHERE folder_id=?", (fid,)).fetchone()[0]
    owner_col = con.execute("SELECT owner_traveler_id FROM collection_folders WHERE id=?",
                            (fid,)).fetchone()
    con.close()
    note("store_named", db=os.path.basename(PRIVATE), folder_rows=fr, item_rows=ir,
         answered_item_count=hit["item_count"], agrees=ir == hit["item_count"],
         owner_column_holds=owner_col)

    for label, path, body in [
        ("no_such_shelf", "/collections/ord0444-missing-shelf/items", {"place_id": places[0]}),
        ("no_such_place", "/collections/%s/items" % fid, {"place_id": "ord0444-missing-place"}),
        ("duplicate_add", "/collections/%s/items" % fid, {"place_id": places[0]}),
    ]:
        st, raw = call("POST", path, body)
        e = envelope(raw)
        note("counter_" + label, status=st, code=e.get("code"), reason_code=e.get("reason_code"),
             details=e.get("details"), is_500=(st == 500))

    with OP.open("http://127.0.0.1:%d/openapi.json" % PORT, timeout=30) as r:
        spec = json.loads(r.read())
    paths = spec["paths"]
    comps = spec.get("components") or {}
    schemas = comps.get("schemas") or {}
    create_schema = schemas.get("CollectionFolderCreate") or {}
    note("served_spec", top_level_keys=sorted(spec.keys()),
         collections_paths=sorted(p for p in paths if "collections" in p),
         list_params=[(q.get("name"), q.get("in"), q.get("required")) for q in
                      paths["/api/v1/collections"]["get"].get("parameters", [])],
         list_responses=sorted(paths["/api/v1/collections"]["get"].get("responses", {})),
         create_responses=sorted(paths["/api/v1/collections"]["post"].get("responses", {})),
         create_required=create_schema.get("required"),
         create_schema_present=bool(create_schema),
         schema_key_names=sorted(schemas.keys())[:3] if schemas else "no components/schemas served")
finally:
    out["ownership"]["private_sha1_after"] = digest(PRIVATE)
    out["ownership"]["preview_sha1_after"] = digest(PREVIEW)
    out["ownership"]["preview_untouched"] = (out["ownership"]["preview_sha1_before"]
                                             == out["ownership"]["preview_sha1_after"])
    json.dump(out, open(r"D:/moodle/_qoder_newlane_ord0444_20260929/scratch/stack_prod.json",
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for pid in listeners[:1] + [str(child.pid)]:
        subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
    logf.close()
    time.sleep(3)
    for suffix in ("", "-wal", "-shm"):
        p = PRIVATE + suffix
        if os.path.exists(p):
            os.remove(p)
print("WROTE stack_prod.json; preview_untouched =", out["ownership"]["preview_untouched"])
print("leftover db files:", [f for f in os.listdir(BACKEND) if f.endswith(".db")])
