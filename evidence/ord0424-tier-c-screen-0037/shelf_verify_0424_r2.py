# -*- coding: utf-8 -*-
"""Read the ORD-0424 shelf directory back from commander/control and write the r2 receipt.

The earlier r2 publish script pushed correctly but verified against a tree it had not re-fetched, so it
reported the two new paths as missing. This script does only the read-back: enumerate the slug with
`git ls-tree`, then hash each local file the same way git does and compare.
"""
import hashlib
import io
import json
import os
import subprocess

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0424"
REPO = "D:/moodle/CityNexus"
SLUG = "evidence/ord0424-tier-c-screen-0037"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")


def git(*a):
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900, env=ENV)
    if r.returncode != 0:
        raise SystemExit("git failed: %s :: %s" % (a[:2], (r.stderr or "")[-200:]))
    return (r.stdout or "").strip()


def main():
    ref = "refs/remotes/verify/cc4"
    git("fetch", "-q", "origin", "+refs/heads/commander/control:" + ref)
    tip = git("rev-parse", ref)
    rows = []
    for line in git("ls-tree", "-r", ref, SLUG + "/").splitlines():
        mode, typ, blob, path = line.split(None, 3)
        if typ != "blob":
            continue
        name = path.rsplit("/", 1)[-1]
        localp = os.path.join(WORK, name)
        if os.path.exists(localp):
            raw = io.open(localp, "rb").read()
            want = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
            rows.append({"path": path, "server_blob_ls_tree": blob, "local_bytes": len(raw),
                         "byte_equal": want == blob})
        else:
            rows.append({"path": path, "server_blob_ls_tree": blob, "local_bytes": None,
                         "byte_equal": None,
                         "note": "on the shelf, not in this run's work dir"})
    doc = {"slug": SLUG, "branch": "commander/control", "control_tip_after": tip, "files": rows,
           "shelf_count": len(rows),
           "all_local_byte_equal": all(r["byte_equal"] for r in rows if r["byte_equal"] is not None),
           "new_this_run": [SLUG + "/" + n for n in ("legacy_403_proof_r2.py", "legacy_403_proof_r2.json")],
           "method": "git ls-tree -r on the re-fetched commander/control tip; local hash uses the git blob "
                     "header, not a bare file sha1"}
    io.open(os.path.join(WORK, "publish_0424_receipt_r2.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": tip, "shelf_count": len(rows),
                      "all_local_byte_equal": doc["all_local_byte_equal"],
                      "r2_present": sorted(r["server_blob_ls_tree"] for r in rows
                                           if r["path"].endswith("_r2.py") or
                                           r["path"].endswith("legacy_403_proof_r2.json"))},
                     ensure_ascii=False))
    return 0 if doc["all_local_byte_equal"] else 5


raise SystemExit(main())
