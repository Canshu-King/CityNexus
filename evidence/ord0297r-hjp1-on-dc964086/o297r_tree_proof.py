"""Prove the trees I ran came out of `git archive <40-hex tip>`, not out of a shared working tree.

Why this is its own file: the commander's condition was "用 git archive dc964086… 导出干净树跑，不在共享工作树
上跑".  A build receipt that merely says so is a claim; this walks the exported directories, re-hashes every
file the way git would, and compares against the blob recorded for that path AT the tip -- so the proof is
the mismatch count, not my sentence.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
REPO = r"D:\moodle\_qoder_integration_20260919"
TIP = "dc964086c9d412573ac19d70b24b30e6c3ee6168"
# the release dist is a BUILD OUTPUT, not a tree export, so it is deliberately not walked here:
# only the sources and the backend that were fed into that build are
PREV = "5c4608cede6cb7bd5f3ac7e704bfee379ca47abc"
# each exported tree is compared against the commit it was exported FROM, and prev_base is
# deliberately the previous hop -- comparing it to the tip would manufacture mismatches
TREES = {"base_backend": ("o297r/base_backend/backend", "backend", TIP),
         "prev_base": ("o297r/prev_base/backend", "backend", PREV),
         "landed_src": ("o297r/landed/frontend/src", "frontend/src", TIP),
         "landed_next_src": ("o297r/landed_next/frontend/src", "frontend/src", TIP)}


def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def blob_of_tip_path(tip, path):
    r = git("rev-parse", "%s:%s" % (tip, path))
    v = (r.stdout or "").strip()
    # `git rev-parse` ECHOES the argument when the object is missing, so only a 40-hex counts as found
    return v if len(v) == 40 and all(c in "0123456789abcdef" for c in v) else None


def sha1_blob_file(p):
    b = io.open(p, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest(), len(b)


out = {"tip": TIP, "tip_present_in_this_object_store": git("cat-file", "-e", TIP + "^{commit}").returncode,
       "repo_path_used_for_archive": REPO,
       "note": ("this repo directory is the integration lane's clone; the ARCHIVE is read from the commit "
                "object, so a dirty working tree here cannot change what was exported -- the check below is "
                "export-vs-commit, never export-vs-worktree"),
       "trees": {}}
total, bad, missing = 0, [], []
for name, (rel, prefix, tip) in TREES.items():
    root = os.path.join(LANE, rel)
    if not os.path.isdir(root):
        out["trees"][name] = {"absent": root}
        continue
    same = diff = 0
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            p = os.path.join(dirpath, fn)
            rp = os.path.relpath(p, root).replace("\\", "/")
            tip_path = prefix + "/" + rp
            want = blob_of_tip_path(tip, tip_path)
            if want is None:
                missing.append({"tree": name, "path": tip_path})
                continue
            # paths that exist on disk but not in the commit are things the RUN produced (__pycache__,
            # .pytest_cache, a stray log).  They are counted and classified, never folded into "mismatch",
            # because "the export has extra generated files" and "the export is not the tip" are different
            # statements and only the second one would invalidate a reading.
            got, _n = sha1_blob_file(p)
            total += 1
            if got == want:
                same += 1
            else:
                diff += 1
                bad.append({"tree": name, "path": tip_path, "exported_blob": got, "tip_blob": want})
    out["trees"][name] = {"root": rel, "exported_from_commit": tip,
                      "files_compared_against_that_commit": same + diff, "match": same,
                      "mismatch": diff}
def kind(path):
    if "__pycache__" in path or path.endswith(".pyc"):
        return "bytecode the running interpreter wrote (__pycache__ / .pyc)"
    if ".pytest_cache" in path:
        return "pytest cache"
    if path.endswith((".log", ".jsonl", ".sqlite3", ".sqlite3-wal", ".sqlite3-shm")):
        return "a run artifact (log / database)"
    return "other -- needs naming before anyone calls this a clean export"


by_kind = {}
for m in missing:
    by_kind[kind(m["path"])] = by_kind.get(kind(m["path"]), 0) + 1
unexplained = [m for m in missing if kind(m["path"]).startswith("other")]
out["summary"] = {"files_compared_total": total, "mismatches": len(bad),
                  "mismatch_detail": bad, "paths_not_in_the_commit": len(missing),
                  "paths_not_in_the_commit_by_kind": by_kind,
                  "unexplained_extra_paths": unexplained[:20],
                  "expected_mismatch": ("exactly one: landed_next's frontend/src/main.tsx, which carries the "
                                        "one-line generation marker this order's second generation is built "
                                        "from. Any other mismatch would mean I ran a tree that is not the tip."),
                  "stamped": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
# the named file the order turns on, checked on its own so a reader can re-run one command
P = "frontend/src/features/planning/PlanWithAiSheet.tsx"
out["named_file_spot_check"] = {
    "path": P, "tip_blob": blob_of_tip_path(TIP, P),
    "exported_blob": sha1_blob_file(os.path.join(LANE, "o297r/landed/frontend/src/features/planning/PlanWithAiSheet.tsx"))[0],
    "command": "git -C %s rev-parse %s:%s" % (REPO, TIP, P)}
out["commander_pre_image_at_this_tip"] = {
    "quoted_by_commander": "c22cf42506a4175db992bde387ed8d9c6f1ffb9d",
    "equals_tip_blob": blob_of_tip_path(TIP, P) == "c22cf42506a4175db992bde387ed8d9c6f1ffb9d",
    "meaning": ("if false, the pre-image the commander quoted is from a different hop than the tip I ran on "
                "-- that is a fact about the order's coordinates, not something to smooth over")}
io.open(os.path.join(LANE, "o297r_tree_proof.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1)[:2000])
assert total > 200, "only %d files compared -- the export is not what I think it is" % total
assert [b["path"] for b in bad] == ["frontend/src/main.tsx"], (
    "the only deviation allowed is the marker line in landed_next's main.tsx; got %s"
    % json.dumps(bad, ensure_ascii=False)[:300])
assert not unexplained, "extra files in the export that are neither bytecode nor run artifacts: %s" % json.dumps(
    unexplained[:5], ensure_ascii=False)
print(json.dumps({"mismatches_allowed_and_named": len(bad),
                  "extra_paths_by_kind": by_kind}, ensure_ascii=False, indent=1))
