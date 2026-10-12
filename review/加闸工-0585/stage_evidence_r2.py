# -*- coding: utf-8 -*-
"""Stage the ORD-0585 r2 evidence set on top of the merge commit (plumbing only).

Each file is hashed with an explicit --path so no text/eol filter can rewrite it; the blob size is read
back and compared to the file, and the commit is refused if the tree is unchanged.
"""
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = "D:/moodle/CityNexus"
SRC = "D:/moodle/_jz_0585/"
DST = "review/加闸工-0585/"
PARENT = sys.argv[1]

FILES = [
    "readout_r2.txt", "gates_r2.txt", "keyset_r2.txt", "numstat_r2.txt", "tip_retryHint_r2.txt",
    "adapter_at_tip_r2.ts.txt", "byte_proof_r2.txt", "call_sites_r2.txt", "anchor_checks_r2.txt",
    "typecheck_full_r2.txt", "listfiles_r2.txt", "vite_build_r2.txt", "codes_gate_r2.txt",
    "codes_gate_selftest_r2.txt", "dict_key_arm_r2.txt", "dict_lang_check_tip_r2.txt",
    "dict_lang_check_cand_r2.txt", "inline_ruler_tip_r2.txt", "inline_ruler_cand_r2.txt",
    "copy_tiers_before_r2.txt", "copy_tiers_after_r2.txt", "probe_base2_out.json", "probe_wt2_out.json",
    "simpanel_934_tip2.txt", "simpanel_934_cand2.txt", "compare_proof_r2.py", "probe_0585.ts.txt",
    "stage_evidence_r2.py", "stage_evidence_r1.py",
]


def git(args, env=None):
    p = subprocess.run(["git", "-C", REPO] + args, capture_output=True, env=env)
    if p.returncode:
        raise SystemExit("GIT_FAIL %s :: %s" % (args, p.stdout.decode("utf-8", "replace")[:300]))
    return p.stdout.decode("utf-8", "replace").strip()


pairs = []
for name in FILES:
    path = SRC + name
    if not os.path.isfile(path):
        raise SystemExit("MISSING evidence file %s" % path)
    size = os.path.getsize(path)
    blob = git(["hash-object", "-w", "-t", "blob", "--path=" + DST + name, path])
    if int(git(["cat-file", "-s", blob])) != size:
        raise SystemExit("BLOB_SIZE_MISMATCH %s" % name)
    pairs.append((blob, DST + name, size))
    print("STAGED %8d B  %s" % (size, DST + name))

env = dict(os.environ, GIT_INDEX_FILE="D:/moodle/_jz_0585/idx_evidence_r2")
if os.path.exists(env["GIT_INDEX_FILE"]):
    os.remove(env["GIT_INDEX_FILE"])
git(["read-tree", PARENT], env)
for blob, rel, _ in pairs:
    git(["update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, rel)], env)
tree = git(["write-tree"], env)
if tree == git(["rev-parse", "%s^{tree}" % PARENT], env):
    raise SystemExit("EMPTY_ARTIFACT: 证据树与父提交相同，什么都没加")
msg = ("jiazagong 0585 r2 evidence: merged-generation re-reads -- both rulers on the new tip and on "
       "the merge, two-generation byte proof, keyset no-loss check")
commit = git(["commit-tree", tree, "-p", PARENT, "-m", msg], env)
git(["update-ref", "refs/heads/review/jiazagong-0585-r1", commit], env)
print("EVIDENCE_R2_COMMIT %s" % commit)
print("FILES %d  TOTAL %d B" % (len(pairs), sum(s for _, _, s in pairs)))
print("相对合并代新增 %d 行 diff" % len(git(["diff", "--name-status", PARENT, commit]).splitlines()))
