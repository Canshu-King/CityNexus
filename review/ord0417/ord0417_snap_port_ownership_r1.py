"""ORD-0417 snap stack: prove the two ports I am about to measure are MINE, in one batch.

A 200 on a port I chose is not identity -- another lane's backend can answer there (this lane hit
that at 05:16, when an ownership check pointed at a directory that was not the snap, and again with a
:4831 backend of an older generation under a current-tip bundle that produced `markers_before=0`).
Three proofs, taken together:
  P1 listener -> pid, straight off netstat;
  P2 that pid's command line names my port and my dist path;
  P3 content: the journey ids on :4861 are the ids in MY sqlite copy, and the bytes on :4862 hash the
     same as the index.html in MY dist.
"""
import hashlib
import json
import os
import sqlite3
import subprocess
import urllib.request
import sys

BACK = 4861
FRONT = 4862
MY_DB = r"D:/moodle/_qoder_b_ord0417_20260928/db/ord0417_snap0619.db"
MY_DIST = r"D:/moodle/_qoder_b_ord0417_20260928/snap0619/frontend/dist/index.html"
PREVIEW = r"D:/moodle/_qoder_preview_20260920/_preview.db"
WHEN = sys.argv[1] if len(sys.argv) > 1 else "before"


def get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read()


netstat = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
pids = {}
for line in netstat.splitlines():
    parts = line.split()
    if len(parts) == 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{BACK}"):
        pids["backend"] = parts[4]
    if len(parts) == 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{FRONT}"):
        pids["front"] = parts[4]

ps = (
    "Get-CimInstance Win32_Process -Filter 'Name=\"python.exe\"' | ForEach-Object "
    '{ "pid=$($_.ProcessId)`tpid=$($_.ParentProcessId)`t$($_.CommandLine)" }'
)
procs = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
cl, ppid = {}, {}
for line in procs.splitlines():
    if not line.startswith("pid="):
        continue
    fields = line.split("\t")
    if len(fields) < 3:
        continue
    pid = fields[0][len("pid="):]
    ppid[pid] = fields[1][len("ppid="):]
    cl[pid] = "\t".join(fields[2:])

db = sqlite3.connect(f"file:{MY_DB}?mode=ro", uri=True)
mine_ids = sorted(r[0] for r in db.execute("select id from journeys"))
# P4: the shared preview file must never move.  `before` counts rows in MY copy; `after` counts them
# again, and the difference is the proof that the API I measured answered from my file -- a different
# lane's backend on the same port could echo the same 1 journey and still not be mine.
mine_rows = {
    t: db.execute(f"select count(*) from {t}").fetchone()[0]
    for t in ("journeys", "activities", "places")
}
db.close()
preview = os.stat(PREVIEW)

st, body = get(f"http://127.0.0.1:{BACK}/api/v1/journeys")
payload = json.loads(body)
items = payload if isinstance(payload, list) else payload.get("items") or payload.get("journeys") or []
api_ids = sorted(j["id"] for j in items if isinstance(j, dict) and "id" in j)

stf, html = get(f"http://127.0.0.1:{FRONT}/")
disk = open(MY_DIST, "rb").read()

out = {
    "P1_listener_pids": pids,
    "P2_cmdlines": {
        "backend_port_named": f"--port {BACK}" in cl.get(pids.get("backend", ""), ""),
        "backend_reexec_parent_seen": bool(cl.get(ppid.get(pids.get("backend", ""), ""), "")),
        "front_dist_named": "snap0619/frontend/dist" in cl.get(pids.get("front", ""), ""),
        "front_api_named": f"--api {BACK}" in cl.get(pids.get("front", ""), ""),
    },
    "when": WHEN,
    "P4_write_isolation": {
        "my_copy_rows": mine_rows,
        "preview_db_mtime_epoch_s": int(preview.st_mtime),
        "preview_db_size_B": preview.st_size,
    },
    "P3_content": {
        "my_sqlite_journeys": len(mine_ids),
        "backend_http": st,
        "backend_journeys": len(api_ids),
        "ids_equal": mine_ids == api_ids,
        "front_http": stf,
        "served_index_sha1": hashlib.sha1(html).hexdigest(),
        "disk_index_sha1": hashlib.sha1(disk).hexdigest(),
        "bytes_equal": hashlib.sha1(html).hexdigest() == hashlib.sha1(disk).hexdigest(),
        "bundle_entry_in_served_index": b"assets/index-" in html,
    },
}
print(json.dumps(out, indent=1))
