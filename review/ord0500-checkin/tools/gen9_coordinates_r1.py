"""The coordinate files the r3 blocks read: remote refs, predicted trees, and every citable blob.

Written as a tool rather than pasted into a block because every one of these strings has to be
re-derivable: `run/ls_remote_r9.txt` is what the remote actually serves for my refs and for the
authoritative branch, `run/merge_tree_r9.txt` is the read-only merge prediction of each candidate
against that tip, and `run/blobs_r9.txt` maps each shipped path to its blob id so the ledger gate can
`git cat-file -t` it.  Nothing here writes to the remote.
"""
import os
import subprocess

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = r"D:/moodle/CityNexus"
NL = chr(10)


def sh(args, cwd=REPO):
    return subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=240).stdout.decode("utf-8", "replace")


env_no_proxy = dict(os.environ)
env_no_proxy.pop("HTTP_PROXY", None)
env_no_proxy.pop("HTTPS_PROXY", None)
env_no_proxy["NO_PROXY"] = "api.github.com"


def sh_env(args):
    return subprocess.run(args, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=240, env=env_no_proxy).stdout.decode("utf-8", "replace")


tip = sh_env(["git", "ls-remote", "origin",
              "refs/heads/mirror/integration-frontend-apple-pass1"]).split()[0]
refs = sh_env(["git", "ls-remote", "origin", "refs/heads/review/newlane-ord0500*",
               "refs/heads/review/newlane-ord0485*"])
open(os.path.join(LANE, "run", "ls_remote_r9.txt"), "w", encoding="utf-8", newline=NL).write(refs)
cand = sh(["git", "-C", os.path.join(LANE, "wt22"), "rev-parse", "HEAD"]).strip()
dic = sh(["git", "-C", os.path.join(LANE, "wt15"), "rev-parse", "HEAD"]).strip()
lines = []
for branch in (cand, dic):
    out = sh(["git", "merge-tree", "--write-tree", tip, branch])
    lines.append("branch %s predicted_tree %s exit_marker see_block" % (branch, out.split(NL)[0]))
open(os.path.join(LANE, "run", "merge_tree_r9.txt"), "w", encoding="utf-8", newline=NL).write(
    NL.join(lines) + NL)

WANTED = [(cand, "review/ord0500-checkin/GEN9_READINGS.md"),
          (cand, "review/ord0500-checkin/receipts/gen9_checkin_sweep_r1.json"),
          (cand, "review/ord0500-checkin/receipts/gen9_doors_r1.json"),
          (cand, "review/ord0500-checkin/receipts/gen9_ce1_r1.json"),
          (cand, "review/ord0500-checkin/receipts/gen9_ce1_tree_proof_r1.json"),
          (cand, "review/ord0500-checkin/receipts/gen9_carrier_arms_r1.json"),
          (cand, "review/ord0500-checkin/receipts/gen9_builds_r1.json"),
          (cand, "review/ord0500-checkin/receipts/checkin_PRE_SLICE2_dcb90ccc_phone_390x844_r2.json"),
          (cand, "review/ord0500-checkin/receipts/checkin_SCROLLTEST_phone_390x844_r2.json"),
          (cand, "review/ord0500-checkin/receipts/exposure_tip_514b397f_r1.json"),
          (cand, "review/ord0500-checkin/receipts/exposure_r2_candidate_r1.json"),
          (cand, "review/ord0500-checkin/receipts/exposure_r4_candidate_r1.json"),
          (cand, "review/ord0500-checkin/receipts/gen9_landing_check_r1.json"),
          (cand, "frontend/e2e/qoder-ord0500-checkin-truth.spec.ts"),
          (cand, "frontend/playwright.ord0500-checkin.config.ts"),
          (cand, "backend/tests/test_qoder_ord0500_journey_refusal.py"),
          (cand, "frontend/src/features/checkin/checkinCopy.ts"),
          (cand, "frontend/src/features/checkin/checkins.ts"),
          (cand, "frontend/src/features/trip/TripItinerary.tsx"),
          (cand, "backend/app/main.py"),
          (dic, "review/ord0485-phone-walk/GEN6_READINGS.md"),
          (dic, "frontend/src/i18n/LocaleContext.tsx"),
          (dic, "review/ord0485-phone-walk/receipts/i18n_gap_TIP_0989713a_r1.json"),
          (dic, "review/ord0485-phone-walk/receipts/i18n_gap_O0485_R5_r1.json"),
          (dic, "review/ord0485-phone-walk/receipts/gen6_walk_r1.json"),
          (dic, "review/ord0485-phone-walk/receipts/gen6_builds_r1.json")]
rows = []
for commit, path in WANTED:
    sha = sh(["git", "rev-parse", "%s:%s" % (commit, path)]).strip()
    kind = sh(["git", "cat-file", "-t", sha]).strip()
    if kind != "blob":
        raise SystemExit("ABORT_NOT_A_BLOB %s -> %s %r" % (path, sha, kind))
    rows.append("%s %s" % (sha, path))
open(os.path.join(LANE, "run", "blobs_r9.txt"), "w", encoding="utf-8", newline=NL).write(
    NL.join(rows) + NL)
print("tip", tip)
print(NL.join(lines))
print("blobs written", len(rows), "each verified with git cat-file -t")
