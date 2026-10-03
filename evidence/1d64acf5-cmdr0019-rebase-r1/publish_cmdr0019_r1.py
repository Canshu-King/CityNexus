# -*- coding: utf-8 -*-
"""Put the CMDR 00:19 rebase hand on the shelf under one new slug, reading every path back.

Same mechanic as rounds one and two: only paths that are absent get written, the ruler code keeps its own
name so nothing published earlier is rewritten, and after the push the branch is re-fetched and each file
re-hashed with the git blob header so the byte-equality claim is computed against the server's listing
rather than against what the writer remembered.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
MIR = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\cmdr_git_mirror_r1.py"
REPO = "D:/moodle/CityNexus"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
SLUG = "evidence/1d64acf5-cmdr0019-rebase-r1"
VERIFY_REF = "refs/remotes/verify/cmdr0019r1"
MSG = ("S4-ast-taint CMDR 00:19 item 1: both ruled cells rebased onto the tip read back by ls-remote (b7bb40ee90619c0febc667394279bd3c8a1d835d) and re-measured on that generation - eight states with both arm generations over one injection set for the single-source cell, six for the ORD-0476 door, plus the landing read-back of both refs. One earlier probe run read PRE at the wrong ancestor commit; its output was discarded and the run repeated, which is recorded rather than hidden. 0 product bytes.")
NEW = ["g4_shape_probe_r3.py", "g4_shape_probe_r3.json", "g4_shape_artifact_r3.py",
       "g4_single_source_shape_r3.json", "ord0476_gate_probe_r4.py", "ord0476_gate_probe_r4.json",
       "cmdr0019_landing_prediction_r1.py", "cmdr0019_landing_prediction_r1.json",
       "publish_cmdr0019_r1.py"]


def git(*a):
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900, env=ENV)
    return r.returncode, (r.stdout or "").strip()


def server_blob(path):
    rc, out = git("ls-tree", VERIFY_REF, path)
    parts = out.split()
    return parts[2] if rc == 0 and len(parts) >= 3 and parts[1] == "blob" else None


def put(name):
    remote = SLUG + "/" + name
    raw = io.open(os.path.join(WORK, name), "rb").read()
    want = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    git("fetch", "-q", "origin", "+refs/heads/commander/control:" + VERIFY_REF)
    if server_blob(remote) is not None:
        return {"path": remote, "bytes": len(raw), "byte_equal": False,
                "refused": "already on the shelf - this slug adds new names only"}
    rec = None
    for _attempt in (1, 2, 3):
        r = subprocess.run([sys.executable, MIR, "--file", os.path.join(WORK, name),
                            "--repo-path", remote, "--branch", "commander/control",
                            "--allow-identical", "--message", MSG],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=1800, env=ENV, cwd=os.path.dirname(MIR))
        out = (r.stdout or "") + (r.stderr or "")
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                rec = json.loads(line)
        if r.returncode == 0 and rec and rec.get("byte_equal"):
            break
        time.sleep(3)
    git("fetch", "-q", "origin", "+refs/heads/commander/control:" + VERIFY_REF)
    got = server_blob(remote)
    return {"path": remote, "bytes": len(raw), "server_blob_ls_tree": got, "byte_equal": got == want}


def main():
    rows = [put(n) for n in NEW]
    git("fetch", "-q", "origin", "+refs/heads/commander/control:" + VERIFY_REF)
    tip = git("rev-parse", VERIFY_REF)[1]
    shelf = []
    for line in git("ls-tree", "-r", VERIFY_REF, SLUG + "/")[1].splitlines():
        _mode, typ, blob, path = line.split(None, 3)
        if typ != "blob":
            continue
        name = path.rsplit("/", 1)[-1]
        lp = os.path.join(WORK, name)
        equal = None
        if os.path.exists(lp):
            raw = io.open(lp, "rb").read()
            equal = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest() == blob
        shelf.append({"path": path, "server_blob_ls_tree": blob, "byte_equal": equal})
    doc = {"slug": SLUG, "branch": "commander/control", "control_tip_after": tip,
           "published_this_run": rows, "files": shelf, "shelf_count": len(shelf),
           "all_local_byte_equal": all(s["byte_equal"] for s in shelf if s["byte_equal"] is not None),
           "method": "push only absent paths, re-fetch, then enumerate the slug with ls-tree and hash each "
                     "local file with the git blob header"}
    io.open(os.path.join(WORK, "publish_cmdr0019_receipt_r1.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": tip, "shelf_count": len(shelf),
                      "new_equal": [r["byte_equal"] for r in rows],
                      "all_local_byte_equal": doc["all_local_byte_equal"]}, ensure_ascii=False))
    return 0 if (all(r["byte_equal"] for r in rows) and doc["all_local_byte_equal"]) else 5


raise SystemExit(main())
