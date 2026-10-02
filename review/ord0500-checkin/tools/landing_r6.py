"""ORD-0500 r6: does the pushed ref still land byte-for-byte on the tip the sequencer reads now?

Ancestry proves nothing here; bytes do.  For every path in the candidate's write-set the tool compares
the candidate's own blob against the blob the read-only merge predicts on the live tip, and names any
file that differs with both ids -- that difference is exactly what the landing gate would stop on.
`git cat-file -e` answers through its exit code, so the "does the tip carry this path at all" probe
goes through git_blob_probe's returncode, never through empty stdout.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
REFS = ["refs/heads/review/newlane-ord0500-phone-checkin-entry-r11",
        "refs/heads/review/newlane-ord0500-phone-checkin-entry-r10",
        "refs/heads/review/newlane-ord0500-phone-checkin-entry-r9",
        "refs/heads/review/newlane-ord0500-phone-checkin-entry-r8",
        "refs/heads/review/newlane-ord0500-phone-checkin-entry-r7",
        "refs/heads/review/newlane-ord0500-phone-checkin-entry-r6",
        "refs/heads/review/newlane-ord0500-phone-checkin-entry-r5",
        "refs/heads/review/newlane-ord0485-phone-walkthrough-r5"]


def git(*args):
    env = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
    env["NO_PROXY"] = "*"
    p = subprocess.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=300, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def pick(text, needle):
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == needle and re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            return parts[0]
    return None


def blob_at(rev, path):
    rc, out = git("cat-file", "-e", "%s:%s" % (rev, path))
    if rc != 0:
        return "ABSENT_AT_TIP"
    return git("rev-parse", "%s:%s" % (rev, path))[1]


def main():
    rc, listed = git("ls-remote", "origin", TIP_REF, *REFS)
    tip = pick(listed, TIP_REF)
    if tip is None:
        raise SystemExit("ABORT_NO_LIVE_TIP " + listed[:200])
    out = {"tool": "landing_r6", "took_local": datetime.now().astimezone().isoformat(),
           "live_tip": tip, "refs": []}
    for ref in REFS:
        sha = pick(listed, ref)
        if sha is None:
            out["refs"].append({"ref": ref, "ABSENT": "NOT_ON_REMOTE"})
            continue
        rc2, merged = git("merge-tree", "--write-tree", tip, sha)
        predict = merged.splitlines()[0].strip() if merged else ""
        # the write-set is what THIS ref changed from its own fork point -- not every path where the
        # ref and the tip differ.  An earlier version diffed tip..sha and so counted the tip's own
        # newer files as my changes: it reported 449 of 515 paths "needing another recut" for a
        # candidate that touches six of them.
        base = git("merge-base", tip, sha)[1].strip()
        if not re.fullmatch(r"[0-9a-f]{40}", base):
            out["refs"].append({"ref": ref, "commit": sha, "ABSENT": "NO_MERGE_BASE",
                                "merge_base_answer": base[:80]})
            continue
        rc3, files = git("diff", "--name-only", base, sha)
        paths = [p for p in files.splitlines() if p.strip()]
        differs, identical = [], 0
        for p in paths:
            rc_mine, mine = git("rev-parse", "--verify", "--quiet", "%s:%s" % (sha, p))
            rc_in, inmerge = git("rev-parse", "--verify", "--quiet", "%s:%s" % (predict, p))
            if rc_mine != 0 or rc_in != 0 or mine.strip() != inmerge.strip():
                differs.append({"path": p,
                                "candidate_blob": mine.strip() or "ABSENT_IN_CANDIDATE",
                                "merge_blob": inmerge.strip() or "ABSENT_IN_PREDICTION",
                                "live_tip_blob": blob_at(tip, p)})
            else:
                identical += 1
        out["refs"].append({"ref": ref, "commit": sha, "fork_point": base,
                            "predicted_tree": predict,
                            "merge_tree_exit": rc2, "write_set_files": len(paths),
                            "files_landing_byte_identical": identical,
                            "files_needing_another_recut": differs})
    path = os.path.join(LANE, "evidence", "landing_r6.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False)[:2600])
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
