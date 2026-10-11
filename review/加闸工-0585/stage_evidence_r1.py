# -*- coding: utf-8 -*-
"""Stage the ORD-0585 evidence set on top of the product commit, via plumbing only.

Each file is hashed with an explicit --path so no text/eol filter can rewrite it, the resulting blob is
read back and compared to what was hashed (a blob that is not in the store is not an artifact), and the
commit is refused if any file is missing or the evidence tree equals the product tree.
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
    ("readout_r1.txt", DST + "readout_r1.txt"),
    ("gates_r1.txt", DST + "gates_r1.txt"),
    ("typecheck_full_r1.txt", DST + "typecheck_full_r1.txt"),
    ("listfiles_r1.txt", DST + "listfiles_r1.txt"),
    ("vite_build_r1.txt", DST + "vite_build_r1.txt"),
    ("codes_gate_r1.txt", DST + "codes_gate_r1.txt"),
    ("codes_gate_selftest_r1.txt", DST + "codes_gate_selftest_r1.txt"),
    ("dict_key_arm_r1.txt", DST + "dict_key_arm_r1.txt"),
    ("dict_lang_check_tip_r1.txt", DST + "dict_lang_check_tip_r1.txt"),
    ("dict_lang_check_cand_r1.txt", DST + "dict_lang_check_cand_r1.txt"),
    ("inline_ruler_tip_replay_r1.txt", DST + "inline_ruler_tip_replay_r1.txt"),
    ("inline_ruler_cand_r1.txt", DST + "inline_ruler_cand_r1.txt"),
    ("copy_tiers_before_r1.txt", DST + "copy_tiers_before_r1.txt"),
    ("copy_tiers_after_r1.txt", DST + "copy_tiers_after_r1.txt"),
    ("byte_proof_r1.txt", DST + "byte_proof_r1.txt"),
    ("anchor_checks_r1.txt", DST + "anchor_checks_r1.txt"),
    ("probe_0585.ts.txt", DST + "probe_0585.ts.txt"),
    ("probe_base_out.json", DST + "probe_base_out.json"),
    ("probe_wt_out.json", DST + "probe_wt_out.json"),
    ("adapter_at_tip.ts.txt", DST + "adapter_at_tip.ts.txt"),
    ("simpanel_934_tipbase.txt", DST + "simpanel_934_tipbase.txt"),
    ("simpanel_934_cand.txt", DST + "simpanel_934_cand.txt"),
    ("patch_r1.py", DST + "patch_r1.py"),
    ("lang_check_replay_r1.py", DST + "lang_check_replay_r1.py"),
    ("inline_ruler_replay_r1.py", DST + "inline_ruler_replay_r1.py"),
    ("compare_proof_r1.py", DST + "compare_proof_r1.py"),
    ("stage_evidence_r1.py", DST + "stage_evidence_r1.py"),
    ("blobs_r1.txt", DST + "blobs_r1.txt"),
]


def git(args):
    p = subprocess.run(["git", "-C", REPO] + args, capture_output=True)
    if p.returncode:
        raise SystemExit("GIT_FAIL %s :: %s" % (args, p.stdout.decode("utf-8", "replace")[:300]))
    return p.stdout.decode("utf-8", "replace").strip()


pairs = []
for local, rel in FILES:
    path = SRC + local
    if not os.path.isfile(path):
        raise SystemExit("MISSING evidence file %s" % path)
    size = os.path.getsize(path)
    blob = git(["hash-object", "-w", "-t", "blob", "--path=" + rel, path])
    back = git(["cat-file", "-s", blob])
    if int(back) != size:
        raise SystemExit("BLOB_SIZE_MISMATCH %s file=%d blob=%s" % (rel, size, back))
    pairs.append((blob, rel, size))
    print("STAGED %8d B  %s" % (size, rel))

env = dict(os.environ, GIT_INDEX_FILE="D:/moodle/_jz_0585/idx_evidence")
if os.path.exists(env["GIT_INDEX_FILE"]):
    os.remove(env["GIT_INDEX_FILE"])


def git_env(args):
    p = subprocess.run(["git", "-C", REPO] + args, capture_output=True, env=env)
    if p.returncode:
        raise SystemExit("GIT_FAIL %s :: %s" % (args, p.stdout.decode("utf-8", "replace")[:300]))
    return p.stdout.decode("utf-8", "replace").strip()


git_env(["read-tree", PARENT])
for blob, rel, _ in pairs:
    git_env(["update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, rel)])
tree = git_env(["write-tree"])
if tree == git_env(["rev-parse", "%s^{tree}" % PARENT]):
    raise SystemExit("EMPTY_ARTIFACT: evidence tree identical to the product commit -- nothing was added")
msg = ("jiazagong 0585 r1 evidence: reading board, two-generation byte proof plus missing-key control, "
       "inline ruler and dictionary rulers on both generations, five gates")
commit = git_env(["commit-tree", tree, "-p", PARENT, "-m", msg])
git_env(["update-ref", "refs/heads/review/jiazagong-0585-r1", commit])
print("EVIDENCE_COMMIT %s" % commit)
print("FILES %d  TOTAL %d B" % (len(pairs), sum(s for _, _, s in pairs)))
diff = git_env(["diff", "--name-status", PARENT, commit])
print("DIFF_FROM_PRODUCT_COMMIT %d 行" % len(diff.splitlines()))
