"""Turn the working-tree copy of checkinCopy.ts into a named commit on top of the live tip, so a mutant
bundle can be built from git bytes instead of from a dirty tree.

Why a commit: `cmdr_build_bundle_r1.py` builds by `git archive <sha> frontend`, so a mutation that only
lives in a working tree would never reach the bundle -- and a bundle that silently ignored the mutation
would print a green screen and call the counter-arm a pass.

Local refs only (`refs/e766-mut/*`): 0 pushes, and no branch of anyone else is written. The printed sha is
the coordinate the receipts cite, and `git cat-file -e <sha>:<path>` retrieves the mutated blob.
"""
import json
import os
import subprocess
import sys
import time

WT = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"
TIP = "06ad00b0267c2bef08d4cdcbae2e5a206ded8666"
PATH = "frontend/src/features/checkin/checkinCopy.ts"
IDX_DIR = "D:/moodle/_qoder_e766b154_ord0528_20261001/run"
RECEIPT = ("%s/frontend/review/checkin-words-mutants-day25/receipts/"
           "mutant_commits_r1.json" % WT)


def git(*args):
    r = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    which = sys.argv[1]
    ref = "refs/e766-mut/day25-%s" % which
    _rc, out, err = git("hash-object", "-w", os.path.join(WT, PATH))
    blob = out
    if not blob:
        print("HASH_FAILED %s" % err[:160])
        return 2
    idx = os.path.join(IDX_DIR, "mut_%s_index" % which)
    if os.path.exists(idx):
        os.remove(idx)
    env = dict(os.environ, GIT_INDEX_FILE=idx.replace("\\", "/"))
    subprocess.run(["git", "-C", WT, "read-tree", TIP], env=env, check=True, capture_output=True)
    subprocess.run(["git", "-C", WT, "update-index", "--add", "--cacheinfo",
                    "100644,%s,%s" % (blob, PATH)], env=env, check=True, capture_output=True)
    tree = subprocess.run(["git", "-C", WT, "write-tree"], env=env, capture_output=True,
                          text=True).stdout.strip()
    os.remove(idx)
    rc, commit, err = git("commit-tree", tree, "-p", TIP, "-m",
                          "E766 counter-arm %s: checkinCopy.ts mutated in one place, never pushed"
                          % which)
    if rc != 0 or not commit:
        print("COMMIT_FAILED %s" % err[:160])
        return 3
    rc, _o, err = git("update-ref", ref, commit)
    if rc != 0:
        print("REF_FAILED %s" % err[:160])
        return 4
    verify = git("rev-parse", "%s:%s" % (commit, PATH))[1]
    body = {"events": []}
    if os.path.exists(RECEIPT):
        body = json.load(open(RECEIPT, encoding="utf-8"))
    body["events"].append({"mutant": which, "ref": ref, "commit": commit, "tree": tree,
                           "mutated_blob": blob, "blob_in_commit_equals_worktree_copy": verify == blob,
                           "tip_parent": TIP, "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    with open(RECEIPT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    print("MUT_COMMIT %s %s blob=%s verified=%s" % (which, commit, blob, verify == blob))
    return 0


if __name__ == "__main__":
    sys.exit(main())
