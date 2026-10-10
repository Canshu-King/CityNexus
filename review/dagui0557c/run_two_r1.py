import io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = os.path.join(ROOT, "frontend")
KEEP = os.path.join(ROOT, "review", "dagui0557c", "probe_two_r1.jsx")
TMP = os.path.join(FE, "__probe_two_tmp_r1.jsx")
BUNDLE = os.path.join(ROOT, "review", "dagui0557c", "probe_two_bundle_r1.cjs")
ESBUILD = os.path.join(FE, "node_modules", ".bin", "esbuild.cmd")
DICT = os.path.join(FE, "src", "i18n", "LocaleContext.tsx")
BASE = io.open(os.path.join(ROOT, "review", "dagui0557c", "tip.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(ROOT, "review", "dagui0557c", "probe_two_r1.txt")

src = io.open(KEEP, encoding="utf-8").read()
io.open(TMP, "w", encoding="utf-8", newline="\n").write(
    src.replace("../../frontend/src/i18n/LocaleContext", "./src/i18n/LocaleContext")
)
mine = io.open(DICT, "rb").read()
base_blob = subprocess.check_output(
    ["git", "show", "%s:frontend/src/i18n/LocaleContext.tsx" % BASE], cwd=ROOT)
log = []


def probe(tag):
    b = subprocess.run([ESBUILD, "__probe_two_tmp_r1.jsx", "--bundle", "--platform=node",
                        "--format=cjs", "--outfile=" + BUNDLE, "--jsx=automatic"],
                       cwd=FE, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", shell=True)
    if b.returncode != 0:
        log.append("BUNDLE FAILED %s rc=%d %s" % (tag, b.returncode, b.stdout + b.stderr))
        raise SystemExit(2)
    q = subprocess.run(["node", BUNDLE], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    body = (q.stdout or "") + (q.stderr or "")
    log.append("$ esbuild + node probe_two_bundle_r1.cjs  [%s]" % tag)
    log.append("rc=%d ok=%d fail=%d" % (q.returncode, body.count("OK  "), body.count("FAIL")))
    log.append(body.rstrip())
    return q.returncode


rc_mine = probe("this branch: the two keys are in the dictionary")
io.open(DICT, "wb").write(base_blob)
rc_base = probe("control: the base generation %s, without them" % BASE[:10])
io.open(DICT, "wb").write(mine)
if os.path.exists(BUNDLE):
    os.remove(BUNDLE)
os.remove(TMP)
assert io.open(DICT, "rb").read() == mine, "dictionary not restored"
summary = "verdict=%s mine_rc=%d base_rc=%d restored=1" % (
    "PROVEN" if (rc_mine == 0 and rc_base != 0) else "CHECK", rc_mine, rc_base)
log.append(summary)
io.open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
sys.stdout.write("\n".join(log) + "\n")
sys.exit(0 if "PROVEN" in summary else 6)
