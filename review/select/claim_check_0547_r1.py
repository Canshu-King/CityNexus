"""Which review branches are already sitting on a given set of files.

The commander's standing rule for calling a face free (CITYNEXUS_AGENT_CONTROL.md:1112)
is that both the ledger and the whole review/* diff set must be empty on it. This does
the review/* half, and it asks the only question that means anything: relative to that
branch's own merge base with the tip, did it change the file?

An earlier revision of this file used `rev-list --not <tip> -- <paths>`. That counted
every commit a branch carries which the tip does not -- including whole generations the
mirror branch dropped when it was force-updated -- so it reported stale ancestry as an
active claim and inflated the numbers by an order of magnitude.

A branch whose merge base cannot be computed inside the shallow window is NOT counted
clean. It is counted unknown, and the caller has to say how many there were, because
"I found nobody" and "I could not look" are different sentences.
"""
import subprocess
import sys

REPO = r"D:/moodle/_qoder_select_1008"
TIP = "5a3d31efdd20a15ae5daaa26cdde13d73970a2a2"

DEFAULT_PATHS = [
    "frontend/src/api/citynexus.ts",
    "frontend/src/features/simulation/simulationAdapter.ts",
    "frontend/src/demo/goldenScenario.ts",
    "frontend/src/features/simulation/SimulationPanel.tsx",
]

PATHS = sys.argv[1:] or DEFAULT_PATHS


def run(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True)


def must(*args):
    proc = run(*args)
    if proc.returncode != 0:
        print("ABORT: git %s exited %d: %s" % (" ".join(args[:2]), proc.returncode, proc.stderr.strip()[:200]))
        sys.exit(3)
    return proc.stdout


refs = must("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/review").split()
if len(refs) < 100:
    print("ABORT: only %d review refs fetched -- cannot call anything free" % len(refs))
    sys.exit(3)

claimed = {p: [] for p in PATHS}
clean = {p: 0 for p in PATHS}
unknown = {p: 0 for p in PATHS}
unknown_branches = []

for ref in refs:
    base = run("merge-base", TIP, ref)
    if base.returncode != 0 or not base.stdout.strip():
        unknown_branches.append(ref)
        for path in PATHS:
            unknown[path] += 1
        continue
    files = run("diff", "--name-only", "--no-renames", base.stdout.strip(), ref, "--", *PATHS).stdout.split()
    for path in PATHS:
        if path in files:
            claimed[path].append(ref)
        else:
            clean[path] += 1

print("tip=%s" % TIP)
print("review_branches_scanned=%d  merge_base_uncomputable=%d" % (len(refs), len(unknown_branches)))
for path in PATHS:
    print("\n%s" % path)
    print("  claimed_by=%d  clean=%d  unknown_base=%d" % (len(claimed[path]), clean[path], unknown[path]))
    for ref in claimed[path][:10]:
        print("   ", ref)
    if len(claimed[path]) > 10:
        print("    ... and %d more" % (len(claimed[path]) - 10))

free = [p for p in PATHS if not claimed[p]]
print("\nfaces_with_no_claimant=%d" % len(free))
for path in free:
    print("   no claimant (but %d branches had no computable base): %s" % (unknown[path], path))
