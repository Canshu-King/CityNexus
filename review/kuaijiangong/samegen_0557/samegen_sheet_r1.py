"""Sheet for the ORD-0557 simulationAdapter cell under the new 口径 (no new dictionary helper).

Reads only: tip exports, every call site of describeFailure, and which live lane branches already
touch the neighbour component file. Zero product bytes touched.
"""
import datetime
import io
import subprocess

REPO = r"D:\moodle\CityNexus"
T = "81856e9c49938b17ecf9c2e2045656faaf0c9a51"
LOC = "frontend/src/i18n/LocaleContext.tsx"
ADP = "frontend/src/features/simulation/simulationAdapter.ts"
PANEL = "frontend/src/features/simulation/SimulationPanel.tsx"
SPEC = "frontend/e2e/qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts"
OUT = r"D:\moodle\_qoder_kuaijiangong_samegen_sheet_r1.txt"


def git(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


lines = []
rc, out = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1")
lines.append("A0 tip re-read at run time %s" % out.strip())
lines.append("A1 tip used %s cat-file -t=%s" % (T, git("cat-file", "-t", T)[1].strip()))

rc, out = git("grep", "-n", "^export ", T, "--", LOC)
exports = out.splitlines()
lines.append("B1 dictionary exports on the tip: %d" % len(exports))
for e in exports:
    lines.append("B2 %s" % e.split(":", 2)[-1][:120])

rc, out = git("grep", "-c", "export function localeText", T, "--", LOC)
lines.append("C1 localeText present in the tip dictionary file: %s (rc=%d means zero hits)" % (
    out.strip() or "zero", rc))
rc, out = git("grep", "-rn", "localeText", T, "--", "frontend/src")
lines.append("C2 files in frontend/src importing or defining localeText at the tip: %d" % len(
    [x for x in out.splitlines() if x.strip()]))

rc, out = git("grep", "-n", "describeFailure", T, "--", "frontend")
sites = [x.split(":", 2)[-1] for x in out.splitlines() if x.strip()]
lines.append("D1 describeFailure sites at the tip: %d" % len(sites))
for s in sites:
    lines.append("D2 %s" % s[:150])

rc, out = git("show", "%s:%s" % (T, ADP))
body = out.splitlines()
lines.append("E1 is describeFailure a React component? starts with capital: %s | signature line: %s" % (
    body[144].split("(")[0].strip().endswith("describeFailure"), body[144].strip()[:120]))
lines.append("E2 hook or dictionary imports in that file: %d" % sum(
    1 for l in body[:12] if "useT" in l or "useLocale" in l or "i18n" in l))

# live lane branches touching the neighbour file
rc, out = git("for-each-ref", "--format=%(objectname)%09%(committerdate:unix)%09%(refname:short)",
              "refs/remotes/origin/review")
rows = []
for l in out.splitlines():
    parts = l.split("\t")
    if len(parts) == 3:
        rows.append(parts)
hits = []
skipped_batch = 0
for sha, stamp, name in rows:
    short = name.replace("origin/review/", "")
    if short.startswith("cmdr-batch"):
        skipped_batch += 1
        continue
    if git("cat-file", "-e", sha + "^{commit}")[0]:
        continue
    if git("merge-base", "--is-ancestor", T, sha)[0] == 0:
        continue
    mb = git("merge-base", T, sha)[1].strip()
    if not mb:
        continue
    _, o = git("diff", "--name-only", mb, sha, "--", PANEL)
    if o.strip():
        hits.append((datetime.datetime.fromtimestamp(int(stamp)).strftime("%m-%d %H:%M"), short))
hits.sort(reverse=True)
lines.append("F1 refs examined=%d driver snapshots skipped=%d live lane branches touching SimulationPanel.tsx=%d" % (
    len(rows), skipped_batch, len(hits)))
for d, n in hits[:12]:
    lines.append("F2 %s | %s" % (d, n))

io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("\n".join(lines))
