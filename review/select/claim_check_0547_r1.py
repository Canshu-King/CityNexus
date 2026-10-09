"""Who is already sitting on ORD-0547's four entry points -- the right predicate.

The first revision compared each branch's blob against the tip's blob and reported
over a thousand "claimants" per file. That number was noise: any branch that merely
predates a change to the file differs from the tip without having touched it. The
commander's rule (CITYNEXUS_AGENT_CONTROL.md:1112) is about a branch's own diff, so
this asks the question that way: is there a commit reachable from some review branch,
not reachable from the authoritative tip, that changes one of these paths?
"""
import subprocess
import sys

REPO = r"D:/moodle/_qoder_select_1008"
TIP = "5a3d31efdd20a15ae5daaa26cdde13d73970a2a2"
PATHS = [
    "frontend/src/api/citynexus.ts",
    "frontend/src/features/simulation/simulationAdapter.ts",
    "frontend/src/demo/goldenScenario.ts",
    "frontend/src/features/simulation/SimulationPanel.tsx",
]


def git(*args, stdin=None):
    proc = subprocess.run(
        ["git", "-C", REPO] + list(args),
        input=stdin, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        # A failed walk must never be able to print "nothing claimed". The first
        # revision of this file did exactly that: the fatal went to stderr, stdout was
        # empty, zero commits came back, and the verdict line said "all four free".
        print("ABORT: git %s exited %d: %s" % (" ".join(args[:3]), proc.returncode, proc.stderr.strip()[:200]))
        sys.exit(3)
    return proc.stdout


refs = git("for-each-ref", "--format=%(refname)", "refs/remotes/origin/review/").split()
if not refs:
    print("ABORT: no review refs fetched -- this cannot answer 'free'")
    sys.exit(3)

print("review_branches_seen=%d" % len(refs))

# One walk over the review branch set only. `--all` was wrong (it also walks the frozen
# local baseline), and a bare directory path is not a revision -- git rejects it, and
# the rejection has to stop this file rather than read as an empty result.
out = git(
    "rev-list",
    "--glob=refs/remotes/origin/review/*",
    "--not", TIP,
    "--", *PATHS,
)
commits = [c for c in out.split() if c]
# Prove the glob reached branches at all, or "zero commits" means nothing.
sanity = git("rev-list", "--glob=refs/remotes/origin/review/*", "--count")
print("review_commits_reachable_by_glob=%s" % sanity.strip())

print("in_flight_commits_touching_those_paths=%d" % len(commits))
if not commits:
    print("VERDICT: all four faces are free across the whole review/* set")
    sys.exit(0)

# Attribute each in-flight commit to the review branches that actually contain it.
per_path = {p: [] for p in PATHS}
for sha in commits[:200]:
    files = git("show", "--pretty=", "--name-only", sha).split()
    holders = [
        r.replace("refs/remotes/", "").replace("origin/", "")
        for r in git(
            "for-each-ref", "--format=%(refname)", "--contains", sha, "refs/remotes/origin/review/"
        ).split()
    ]
    for f in files:
        if f in per_path:
            per_path[f].append((sha[:10], holders[:3], len(holders)))

for path in PATHS:
    rows = per_path[path]
    print("\n%s" % path)
    print("  in_flight_commits_touching_it=%d" % len(rows))
    for sha, holders, count in rows[:8]:
        print("   ", sha, "carried by", count, "review branch(es):", ", ".join(holders))
    if len(rows) > 8:
        print("    ... and %d more" % (len(rows) - 8))
