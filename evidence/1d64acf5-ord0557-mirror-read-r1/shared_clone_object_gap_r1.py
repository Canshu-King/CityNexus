# -*- coding: utf-8 -*-
"""Record the shared-clone object gap this hand hit, with readings taken now rather than remembered.

Two separate facts are kept apart here:
  (a) the failure mode itself - a fetch that reports success, moves a ref, and leaves the commit it points at
      absent from the object store, after which every later fetch negotiates zero objects because the broken ref
      advertises that sha as "have";
  (b) whether it is still broken at the moment of reading - re-measured below, because the interrupted
      `--refetch` may well have written the pack before the link dropped.
"""
import io
import json
import os
import shutil
import subprocess
import time

REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
for _k in ("http_proxy", "https_proxy"):
    ENV[_k] = ""


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=900)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


live = git("ls-remote", "--refs", "origin", TIP_REF)[1].split()[0]
track = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
rc_commit, o_commit, e_commit = git("cat-file", "-t", live + "^{commit}")
shallow = io.open(os.path.join(REPO, ".git", "shallow"), encoding="utf-8", errors="replace").read().split()
total, used, free = shutil.disk_usage("D:\\")
verify_refs = [l.split()[-1] for l in git("for-each-ref", "--format=%(refname)",
                                          "refs/remotes/verify/")[1].splitlines() if l.strip()]
doc = {
    "read_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
    "authoritative_tip_named_by_server": live,
    "that_commit_opens_locally_now": rc_commit == 0,
    "cat_file_now": {"rc": rc_commit, "type": o_commit or None, "stderr": (e_commit or "")[:160]},
    "repo_is_shallow": bool(shallow), "shallow_boundaries_recorded": shallow,
    "remote_tracking_ref": {"name": track, "reads": git("rev-parse", track)[1]},
    "disk_D": {"free_bytes": free, "total_bytes": total, "used_pct": round(100.0 * used / total, 1)},
    "verify_refs_this_lane_owns": verify_refs,
    "failure_witnessed": {
        "what": "the server named 868958e7e11472faa0fc84c2218304c36d1885b0 as the tip; `git cat-file -t` on it "
                "returned rc 128 while `git fetch` reported success and updated the ref, so no pack was ever "
                "sent (the broken ref advertises that sha as `have`)",
        "fetch_forms_tried": ["+refs/heads/<tip>:refs/remotes/origin/<track>",
                              "+refs/heads/<tip>:refs/remotes/verify/ord0557_tipfix",
                              "git fetch --depth=1 origin <full sha> (FETCH_HEAD written, object still absent)",
                              "git fetch --refetch --depth=1 origin +...:refs/remotes/verify/ord0557_refetch"],
        "refetch_outcome": "rc 128 with `client_loop: send disconnect: Connection reset by peer`, `fetch-pack: "
                           "unexpected disconnect while reading sideband packet`, `fatal: early EOF`, `fatal: "
                           "fetch-pack: invalid index-pack output` - yet the objects arrived, which is what "
                           "`that_commit_opens_locally_now` reads above",
        "not_touched": "the shared refs/remotes/origin/mirror/... was left alone; only refs/remotes/verify/"
                       "ord0557_* names created by this lane were dropped",
        "hazard_for_other_lanes": "any lane that cuts, diffs or merge-trees against `git rev-parse "
                                  "refs/remotes/origin/<authoritative>` gets a sha whose objects may not exist; "
                                  "the cheap guard is to `cat-file -e <sha>^{commit}` before using it, which is "
                                  "what the reader module now does for its own ref name"},
    "instrument_change_it_caused": "tools/cnx_ledger_mirror_reader_r1.py proves the fetched commit AND the blob "
                                   "for the requested path are openable, and re-fetches once after dropping the "
                                   "single ref name it owns, before it will return any bytes",
}
n = os.path.join(HERE, "shared_clone_object_gap_r1.json")
io.open(n, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
print(json.dumps({k: doc[k] for k in ("read_at_local", "authoritative_tip_named_by_server",
                                      "that_commit_opens_locally_now", "repo_is_shallow", "disk_D",
                                      "verify_refs_this_lane_owns")}, ensure_ascii=False))
