# -*- coding: utf-8 -*-
"""ORD-0391 publish r2 - add the corrected identity pair as NEW paths and read the whole shelf back.

The r1 identity record asked the canned question through the front door, then wrote the missing scenario
header into a field that read like a failure. The correct statement needs both hops, so the corrected
script and its output go up under new names; the r1 paths are left exactly as published.
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
SLUG = os.environ.get("CNX_SLUG") or ("evidence/ord0479-0296-anchor-" + time.strftime("%H%M"))
VERIFY_REF = "refs/remotes/verify/anchors1"
MSG = ("S4-ast-taint CMDR 07:57 anchor item: the two rulers that named row numbers / a frozen file list "
       "now anchor on named symbols and a live scale - six mutation arms in both directions, before/after "
       "readings on the same tree shape, and the candidate diff. Evidence only; the product bytes behind the "
       "arms are untouched.")
NEW = ["anchor_mutation_arms_r1.json", "anchor_mutation_arms_r1.py", "land_candidate_r1.json",
       "before_three_files_r1.txt", "after_three_files_r1.txt", "anchor_diff_r1.patch"]


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
                "refused": "already on the shelf - r2 adds new names only"}
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
    io.open(os.path.join(WORK, "publish_anchors_receipt_r1.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": tip, "shelf_count": len(shelf),
                      "new_equal": [r["byte_equal"] for r in rows],
                      "all_local_byte_equal": doc["all_local_byte_equal"]}, ensure_ascii=False))
    return 0 if (all(r["byte_equal"] for r in rows) and doc["all_local_byte_equal"]) else 5


raise SystemExit(main())
