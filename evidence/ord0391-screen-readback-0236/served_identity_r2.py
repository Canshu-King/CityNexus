# -*- coding: utf-8 -*-
"""ORD-0391 r2 - whose bytes and whose store the walk read (replaces the r1 record; the r1 path stays on the shelf untouched).

Why a second copy: the r1 record asked the front door for a canned answer and then reported the
scenario header as null - my front door does not forward that header, so the field read like a failure
when it was really a property of the hop. This version asks the stub directly as well, and names which
link carries which proof. and whose store the walk actually read, while the stack is still up.

Four links, each measured rather than asserted:
 1. the front door serves the files on disk in my export (asset sha1 equality) and 404s a missing asset
    instead of falling back to index.html, so a 200 cannot hide a stale chunk;
 2. the only process listening on :7041 is my uvicorn, started against my own store copy;
 3. a row that exists only in my copy is visible through the chain 4541 -> 7042 -> 7041, so the API the
    page reached is my database and not another lane's;
 4. the stub stamps every overridden answer with the scenario in force, which is how each reading knows
    its arm landed.
The marker row is written to my copy only, and removed again at the end; `_preview.db` was opened
mode=ro to make the copy and is never written.
"""
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import urllib.error
import urllib.request

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
DIST = os.path.join(WT, "frontend", "dist")
DB = os.path.join(WT, "backend", "tierC_ord0391_lane.db")
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord0391"
JID = "22222222-2222-4222-8222-222222222222"
MARK_TITLE = "ORD0391-LANE-MARKER-1d64acf5"
ENV = dict(os.environ, NO_PROXY="*")
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)


def get(url, method="GET", body=None):
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def blob_sha1(path):
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(), len(raw)


def listeners(port):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=120).stdout or ""
    pids = sorted({l.split()[-1] for l in out.splitlines()
                   if (":%s " % port) in l and "LISTENING" in l.upper()})
    procs = []
    for pid in pids:
        ps = ("Get-CimInstance Win32_Process -Filter \"ProcessId=%s\" | "
              "Select-Object -ExpandProperty CommandLine" % pid)
        cmd = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", env=ENV,
                             timeout=180).stdout or ""
        procs.append({"pid": pid, "command_line": cmd.strip().replace("\n", " ")[:260]})
    return procs


def main():
    assets = []
    index = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", errors="replace").read()
    names = ["index.html"] + [m for m in
                              [index.split('assets/')[i + 1].split('"')[0]
                               for i in range(index.count("assets/"))] if "." in m][:4]
    for rel in dict.fromkeys(names):
        p = os.path.join(DIST, rel if rel == "index.html" else os.path.join("assets", rel))
        if not os.path.exists(p):
            continue
        disk, size = blob_sha1(p)
        served = hashlib.sha1(b"blob %d\x00" % size + get("http://127.0.0.1:4541/" +
                                                          ("" if rel == "index.html" else "assets/") +
                                                          rel)[1]).hexdigest()
        assets.append({"asset": rel, "disk_git_blob_sha1": disk, "served_git_blob_sha1": served,
                       "equal": disk == served, "bytes": size})
    missing = get("http://127.0.0.1:4541/assets/definitely-not-here-9f31.js")[0]
    fallback = get("http://127.0.0.1:4541/v8/hub")
    api_via_door = get("http://127.0.0.1:4541/api/v1/health")
    ports = {"4541": listeners(4541), "7041": listeners(7041), "7042": listeners(7042)}

    con = sqlite3.connect(DB)
    before = con.execute("select count(*) from journeys").fetchone()[0]
    cols = [r[1] for r in con.execute("PRAGMA table_info(journeys)").fetchall()]
    template = con.execute("select * from journeys where id = ?", (JID,)).fetchone()
    if template is None:
        raise SystemExit("ABORT: the store copy holds no journey row to copy a marker shape from")
    values = dict(zip(cols, template))
    values["id"] = "77777777-7777-4777-8777-777777777777"
    values["title"] = MARK_TITLE
    con.execute("insert into journeys (%s) values (%s)"
                % (", ".join(cols), ", ".join("?" * len(cols))),
                [values[c] for c in cols])
    con.commit()
    con.close()
    listed = get("http://127.0.0.1:4541/api/v1/journeys")
    seen = MARK_TITLE in (listed[1].decode("utf-8", "replace") if listed[0] == 200 else "")
    stub_echo = get("http://127.0.0.1:7042/__scenario", "POST", {"name": "not_found"})
    canned = get("http://127.0.0.1:4541/api/v1/journeys/" + JID)
    canned_direct = get("http://127.0.0.1:7042/api/v1/journeys/" + JID)
    get("http://127.0.0.1:7042/__scenario", "POST", {"name": "off"})
    con = sqlite3.connect(DB)
    con.execute("delete from journeys where id = ?", ("77777777-7777-4777-8777-777777777777",))
    con.commit()
    after = con.execute("select count(*) from journeys").fetchone()[0]
    con.close()
    out = {
        "front_door": "http://127.0.0.1:4541", "stub": "http://127.0.0.1:7042",
        "backend": "http://127.0.0.1:7041", "dist": DIST, "store_copy": DB,
        "assets_served_equal_disk": assets,
        "all_assets_equal": all(a["equal"] for a in assets),
        "missing_asset_status": missing, "route_fallback_status": fallback[0],
        "route_fallback_is_index_bytes": fallback[1] == io.open(os.path.join(DIST, "index.html"),
                                                                "rb").read(),
        "health_through_door": {"status": api_via_door[0],
                                "body": api_via_door[1][:120].decode("utf-8", "replace")},
        "listening_processes": ports,
        "marker_journey_written_to_my_copy_only": {"title": MARK_TITLE,
                                                   "journeys_before": before,
                                                   "journeys_after_cleanup": after,
                                                   "visible_through_chain_4541_7042_7041": seen,
                                                   "list_status": listed[0]},
        "stub_stamp_on_canned_answer": {"scenario_switch_status": stub_echo[0],
                                        "canned_status_through_front_door": canned[0],
                                        "scenario_header_through_front_door":
                                            canned[2].get("X-Cnx-Stub-Scenario"),
                                        "canned_status_direct": canned_direct[0],
                                        "scenario_header_direct":
                                            canned_direct[2].get("X-Cnx-Stub-Scenario"),
                                        "content_type": canned[2].get("Content-Type"),
                                        "note": "the scenario header is set by the stub and survives a "
                                                "direct call; my front door does not forward that header, "
                                                "so the arm landing on screen is proven by the status and "
                                                "media type the page itself observed, which is recorded "
                                                "per state in the walk files"},
        "shared_preview_db": "mode=ro for the copy; 0 writes to it in this run",
    }
    io.open(os.path.join(HERE, "served_identity_r2.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"all_assets_equal": out["all_assets_equal"],
                      "missing": missing, "marker_visible": seen,
                      "before_after": [before, after],
                      "canned": [canned[0], canned[2].get("X-Cnx-Stub-Scenario")]},
                     ensure_ascii=False))
    return 0 if (out["all_assets_equal"] and seen and canned[0] == 404 and missing == 404) else 5


raise SystemExit(main())
