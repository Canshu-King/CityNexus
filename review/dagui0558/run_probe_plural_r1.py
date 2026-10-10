import io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = os.path.join(ROOT, "frontend")
KEEP = os.path.join(ROOT, "review", "dagui0558", "probe_plural_r1.ts")
TARGET = os.path.join(FE, "src", "features", "planning", "catalogueReadback.ts")
TMPJS = os.path.join(FE, "__probe_plural_tmp_r1.ts")
BUNDLE = os.path.join(ROOT, "review", "dagui0558", "probe_plural_bundle_r1.cjs")
ESBUILD = os.path.join(FE, "node_modules", ".bin", "esbuild.cmd")
TIP = io.open(os.path.join(ROOT, "tip_live_0558.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(ROOT, "review", "dagui0558", "probe_plural_r1.txt")
REL = "frontend/src/features/planning/catalogueReadback.ts"

src = io.open(KEEP, encoding="utf-8").read()
io.open(TMPJS, "w", encoding="utf-8", newline="\n").write(src)
mine = io.open(TARGET, "rb").read()
base = subprocess.check_output(["git", "show", "%s:%s" % (TIP, REL)], cwd=ROOT)
log = ["TIP=%s" % TIP]


def run_arm(tag):
    b = subprocess.run([ESBUILD, "__probe_plural_tmp_r1.ts", "--bundle", "--platform=node",
                        "--format=cjs", "--outfile=" + BUNDLE],
                       cwd=FE, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", shell=True)
    if b.returncode != 0:
        log.append("BUNDLE FAILED [%s] rc=%d %s" % (tag, b.returncode, b.stdout + b.stderr))
        raise SystemExit(2)
    q = subprocess.run(["node", BUNDLE], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    log.append("$ esbuild + node probe_plural_bundle_r1.cjs  [%s]" % tag)
    log.append("rc=%d" % q.returncode)
    log.append(((q.stdout or "") + (q.stderr or "")).rstrip())
    return (q.stdout or "") + (q.stderr or "")


after = run_arm("after: this branch")
io.open(TARGET, "wb").write(base)
before = run_arm("before: %s" % TIP[:10])
io.open(TARGET, "wb").write(mine)
if os.path.exists(BUNDLE):
    os.remove(BUNDLE)
os.remove(TMPJS)
assert io.open(TARGET, "rb").read() == mine, "file not restored"

Q = chr(34)
P1 = "en  count=1 text=" + Q + "Read back from the server: this city now has 1 place that can go into a trip." + Q
P2 = "en  count=2 text=" + Q + "Read back from the server: this city now has 2 places that can go into a trip." + Q
B1 = "en  count=1 text=" + Q + "Read back from the server: this city now has 1 places"
B2 = "en  count=2 text=" + Q + "Read back from the server: this city now has 2 places"
checks = [P1 in after, P2 in after, B1 in before, B2 in before]
zh_same = [l for l in after.split("\n") if l.startswith("zh ")] == [l for l in before.split("\n") if l.startswith("zh ")]
log.append("check_en_one_fixed=%d check_en_two_still_plural=%d check_before_was_wrong=%d zh_arms_identical=%d"
           % (int(checks[0]), int(checks[1]), int(checks[2]), int(zh_same)))
ok = all(checks) and zh_same
log.append("verdict=%s" % ("PROVEN" if ok else "CHECK"))
io.open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
sys.stdout.write("\n".join(log[-4:]) + "\n")
sys.exit(0 if ok else 6)
