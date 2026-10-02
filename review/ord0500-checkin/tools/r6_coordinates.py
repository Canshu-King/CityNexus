"""ORD-0500 r6: the coordinates the block is allowed to quote, read from git and the server.

Three outputs, all re-derivable by the commander with the commands named in the block:
  run/r6_ls_remote.txt  -- what the server actually answers for the authoritative branch and for my
                           own review refs (r1..r6), read unproxied;
  run/r6_merge_tree.txt -- the read-only merge prediction of my candidate against the live tip, plus
                           the tip's sha on its own line so the block can say which tip it was judged
                           on at which minute;
  run/r6_blobs.txt      -- `<sha> <path>` for every artifact the block cites, each one verified with
                           `git cat-file -t` before it is written.
Nothing here writes to the remote and nothing writes a ref.
"""
import os
import re
import subprocess

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
WT = os.path.join(LANE, "wt22")
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
NL = chr(10)


def sh(args, cwd=REPO):
    env = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
    env["NO_PROXY"] = "*"
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=300, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def pick_sha(text, needle):
    """The sha comes from the line whose second field is the ref asked for -- a transport warning can
    be printed first, and reading the first token of the blob turned one run into `live_tip: ssh:`."""
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == needle and re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            return parts[0]
    return None


def main():
    rc, listed = sh(["git", "ls-remote", "origin", TIP_REF,
                     "refs/heads/review/newlane-ord0500*"])
    tip = pick_sha(listed, TIP_REF)
    if tip is None:
        raise SystemExit("ABORT_NO_LIVE_TIP " + listed[:200])
    open(os.path.join(LANE, "run", "r6_ls_remote.txt"), "w", encoding="utf-8", newline=NL).write(listed)

    rc, head = sh(["git", "rev-parse", "HEAD"], cwd=WT)
    head = head.strip()
    rc, merged = sh(["git", "merge-tree", "--write-tree", tip, head])
    if rc not in (0, 1):
        raise SystemExit("ABORT_MERGE_TREE rc=%s %s" % (rc, merged[:200]))
    predict = merged.splitlines()[0].strip()
    with open(os.path.join(LANE, "run", "r6_merge_tree.txt"), "w", encoding="utf-8", newline=NL) as f:
        f.write("live_tip %s%s" % (tip, NL))
        f.write("candidate %s%s" % (head, NL))
        f.write("branch %s predicted_tree %s exit_marker %s%s" % (head, predict, rc, NL))

    paths = ["review/ord0500-checkin/R6_READINGS.md",
             "review/ord0500-checkin/receipts/build_faces_r6.json",
             "review/ord0500-checkin/receipts/sweep_r6.json",
             "review/ord0500-checkin/receipts/checkin_copy_rows_r6.json",
             "review/ord0500-checkin/receipts/checkin_copy_rows_mutants_r6.json",
             "review/ord0500-checkin/receipts/pytest_r6.json",
             "review/ord0500-checkin/receipts/r6_exposure_base_dc9dc10f.json",
             "review/ord0500-checkin/receipts/r6_exposure_cand.json",
             "review/ord0500-checkin/receipts/checkin_O0500_R6_en_390x844_r3.json",
             "review/ord0500-checkin/receipts/checkin_TIP_dc9dc10f_en_390x844_r3.json",
             "review/ord0500-checkin/receipts/checkin_O0500_R6_zh_390x844_r3.json",
             "review/ord0500-checkin/receipts/checkin_TIP_dc9dc10f_zh_390x844_r3.json",
             "review/ord0500-checkin/tools/checkin_phone_r3.cjs",
             "review/ord0500-checkin/tools/checkin_copy_rows_r6.py",
             "review/ord0500-checkin/tools/sweep_r6.py",
             "review/ord0500-checkin/tools/build_faces_r6.py",
             "frontend/src/features/checkin/checkinCopy.ts",
             "frontend/src/features/trip/TripItinerary.tsx",
             "backend/app/main.py", "contracts/openapi.yaml",
             "frontend/src/features/checkin/checkins.ts",
             "frontend/src/features/checkin/footprint.css"]
    rows = []
    for p in paths:
        rc2, sha = sh(["git", "-C", WT, "rev-parse", "%s:%s" % (head, p)])
        sha = sha.strip()
        if rc2 != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise SystemExit("ABORT_NOT_IN_TREE %s (%s)" % (p, sha[:80]))
        rc3, kind = sh(["git", "-C", WT, "cat-file", "-t", sha])
        if kind.strip() != "blob":
            raise SystemExit("ABORT_NOT_A_BLOB %s %s" % (p, kind.strip()))
        rows.append("%s %s" % (sha, p))
    open(os.path.join(LANE, "run", "r6_blobs.txt"), "w", encoding="utf-8", newline=NL).write(
        NL.join(rows) + NL)
    print("tip", tip)
    print("candidate", head, "predicted_tree", predict, "merge_rc", rc)
    print("blobs", len([r for r in rows if not r.startswith("#")]),
          "each verified with git cat-file -t")


if __name__ == "__main__":
    main()
