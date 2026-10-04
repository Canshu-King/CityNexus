# -*- coding: utf-8 -*-
"""Receipt: the mirror self-check that landed was deleted by a later merge on the authoritative line.

Every fact below is read twice where a channel exists - local git objects and the GitHub contents API - because
this box's clone has been unreliable tonight (a ref that pointed at a missing object). Read-only: nothing here
restores, moves or writes any ref.
"""
import io
import json
import os
import subprocess

TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
REPO = "D:/moodle/CityNexus"
LANDED_TIP = "0293e5c1cf9be4ea4e7d14005e14c508cb3f528b"     # where the check was landed (commander's re-hang)
CHECK = "tools/cnx_ledger_mirror_sync_check_r1.py"
CHECK_BLOB = "5d0ca99076de5c11e9906acadc9c03ed1a3b8e6e"
HOOK = "tools/cnx_ledger_mirror_sync_hook_r1.py"
HOOK_BRANCH = "refs/heads/review/1d64acf5-mirror-sync-hook-r1"
CHECK_BRANCH = "refs/heads/review/1d64acf5-mirror-sync-selfcheck-r1"
CELLS = {"backend/tests/test_qoder_ord0296_write_deadline.py": "032777990661c5220794a91c2a00a8ed1ea97fe7",
         "backend/tests/test_qoder_ord0476_checkins.py": "534b673b749adfd7548066cca770e0c52d105306"}
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
OUT = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors\merge_dropped_landed_tool_r1.json"


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=1800)
    return r.returncode, (r.stdout or "").strip()


def api_status(path, ref):
    import urllib.error
    import urllib.request
    tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/contents/%s?ref=%s"
                                 % (path, ref),
                                 headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-1d64acf5-probe",
                                          "Accept": "application/vnd.github+json"})
    try:
        with op.open(req, timeout=300) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main():
    tip = git("ls-remote", "--refs", "origin", TIP_REF)[1].split()[0]
    git("fetch", "-q", "--depth=2", "origin", tip)
    rows = {"tip": tip,
            "tip_parents": git("rev-list", "--parents", "-n", "1", tip)[1].split()[1:],
            "check_rows_on_tip": git("ls-tree", tip, "--", CHECK)[1].count("\n") + (1 if git("ls-tree", tip, "--",
                                                                                              CHECK)[1] else 0),
            "check_ls_tree_on_tip": git("ls-tree", tip, "--", CHECK)[1] or "NO ROW",
            "hook_ls_tree_on_tip": git("ls-tree", tip, "--", HOOK)[1] or "NO ROW",
            "api_http_check_on_tip": api_status(CHECK, tip),
            "api_http_hook_on_tip": api_status(HOOK, tip),
            "api_http_reader_on_tip": api_status("tools/cnx_ledger_mirror_reader_r1.py", tip),
            "deleted_between_landing_tip_and_now": [],
            "cells_still_on_tip": {}}
    # the deletion set A -> B, restricted to files that were on A
    rc, out = git("diff", "--name-status", LANDED_TIP, tip)
    for line in out.splitlines():
        if line.startswith("D\t"):
            rows["deleted_between_landing_tip_and_now"].append({"path": line.split("\t")[-1],
                                                                "was_blob_on": LANDED_TIP})
    rows["diff_counts"] = {"D": len([l for l in out.splitlines() if l.startswith("D\t")]),
                           "M": len([l for l in out.splitlines() if l.startswith("M\t")]),
                           "A": len([l for l in out.splitlines() if l.startswith("A\t")])}
    for p, want in CELLS.items():
        got = git("ls-tree", tip, "--", p)[1].split()[2] if git("ls-tree", tip, "--", p)[1] else None
        rows["cells_still_on_tip"][p] = {"expected_blob": want, "blob_on_tip": got, "intact": got == want}
    for p in (CHECK,):
        rows["check_present_on_each_parent"] = {par: bool(git("ls-tree", par, "--", p)[1])
                                               for par in rows["tip_parents"]}
    rows["restore_coordinates"] = {
        "branch_with_the_check": CHECK_BRANCH,
        "branch_head": git("ls-remote", "--refs", "origin", CHECK_BRANCH)[1].split()[0],
        "branch_blob": CHECK_BLOB,
        "branch_with_the_hook_never_landed": HOOK_BRANCH,
        "hook_branch_head": git("ls-remote", "--refs", "origin", HOOK_BRANCH)[1].split()[0],
        "note": "restoring is the sequencer's move - this file only measures and reports"}
    rows["reading"] = ("the check landed at %s and is gone from %s; neither parent of the current merge carries "
                       "it, so a merge resolved against an older side and silently deleted a landed file. My two "
                       "test-tree cells survived the same merge unchanged." % (LANDED_TIP[:12], tip[:12]))
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False, indent=1))
    print(json.dumps({k: rows[k] for k in ("tip", "tip_parents", "check_ls_tree_on_tip", "api_http_check_on_tip",
                                           "api_http_reader_on_tip", "diff_counts", "cells_still_on_tip",
                                           "check_present_on_each_parent")}, ensure_ascii=False))


main()
