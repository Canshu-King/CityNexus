"""Landability probe: run the landing gate's OWN test against whatever the tip is right now.

The gate refused one of this lane's branches with "2 files did not merge to the lane's own bytes",
and refused a later one only because the line had been re-rooted under it.  Both are facts about
the moment of landing, so this probe re-derives them instead of quoting a reading:

    python review/a68b0631-landing-check/landability_probe_r1.py [branch] [tip-sha]

It exits 0 only when every gated file merges to this branch's own bytes AND the branch still
changes something.  Anything else exits non-zero and says which condition failed.

Two instrument rules learned the hard way, applied here:
  * the tip is fetched by REFSPEC, never by sha -- a sha fetch brings the commit without its
    ancestry, which makes the tip look parentless and makes `merge-tree` answer "refusing to merge
    unrelated histories" for a pair that is in fact related;
  * git's exit status is read without a pipe, because `rc=$?` after a pipeline reports the last
    command's status, not git's.
"""
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0447_wt/"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
DEFAULT_BRANCH = "refs/heads/review/a68b0631-ord0507-clock-attribution-r12"
# the files the landing gate named when it refused; a branch that touches these must merge to its
# own bytes.  Read from the branch itself so this list cannot drift away from the hand.
GATED = ["frontend/src/app/V8Experience.tsx",
         "frontend/src/features/simulation/SimulationPanel.tsx"]


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=WT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def blob(rev, path):
    return git("rev-parse", "%s:%s" % (rev, path)).stdout.strip()


def main():
    branch = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRANCH
    fetch = git("fetch", "origin", "+%s:%s" % (TIP_REF, "refs/tmp/landability_probe"), )
    tip = git("rev-parse", "refs/tmp/landability_probe").stdout.strip()
    if len(sys.argv) > 2:
        tip = sys.argv[2]
    print("branch = %s" % branch)
    print("tip    = %s (fetched by refspec; rc of the fetch is reported below)" % tip)
    print("fetch exit status = %d" % fetch.returncode)

    parents = git("log", "-1", "--format=%p", tip).stdout.strip()
    count = git("rev-list", "--count", tip).stdout.strip()
    print("tip parents = %r, rev-list --count = %s" % (parents, count))

    ff = git("merge-base", "--is-ancestor", tip, branch).returncode == 0
    print("branch is a descendant of the tip (landing would be a fast-forward): %s" % ff)

    mt = git("merge-tree", "--write-tree", "--name-only", tip, branch)
    print("merge-tree exit status = %d  (read without a pipe)" % mt.returncode)
    if mt.returncode != 0:
        print("merge-tree said: %s" % (mt.stderr or mt.stdout).strip()[:300])
        print("\nRESULT: NOT LANDABLE as a fast-forward.  Re-cut the branch at the tip and re-run.")
        return 2
    conflicts = [l for l in mt.stdout.splitlines() if l.startswith("CONFLICT")]
    print("conflicts = %d" % len(conflicts))
    merged_tree = mt.stdout.splitlines()[0].strip()
    print("merged tree = %s" % merged_tree)

    bad = []
    for p in GATED:
        mine, theirs, merged = blob(branch, p), blob(tip, p), blob(merged_tree, p)
        ok = mine == merged
        print("   %-24s branch=%s merged=%s  %s"
              % (p.split("/")[-1], mine[:12], merged[:12],
                 "the lane's own bytes" if ok else "DIFFERS FROM THE LANE'S OWN BYTES"))
        if not ok:
            bad.append(p)
    differs = [p for p in GATED if blob(tip, p) != blob(branch, p)]
    print("files this branch actually changes against the tip: %d" % len(differs))

    if bad:
        print("\nRESULT: the gate's condition FAILS for %s -- send the branch back to the lane."
              % bad)
        return 1
    if not differs:
        print("\nRESULT: the branch is byte-equal to the tip on the gated files, so landing it "
              "changes nothing there.  The gate would call that a no-op.")
        return 1
    print("\nRESULT: landable.  Every gated file merges to this branch's own bytes, and the branch "
          "still changes them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())