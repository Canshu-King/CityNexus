import io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = os.path.join(ROOT, "frontend")
KEEP = os.path.join(ROOT, "review", "dagui0562", "probe_nine_r1.jsx")
TMP = os.path.join(FE, "__probe_nine_tmp_r1.jsx")
BUNDLE = os.path.join(ROOT, "review", "dagui0562", "probe_nine_bundle_r1.cjs")
ESBUILD = os.path.join(FE, "node_modules", ".bin", "esbuild.cmd")
DICT = os.path.join(FE, "src", "i18n", "LocaleContext.tsx")
TIP = io.open(os.path.join(ROOT, "review", "dagui0562", "tip.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(ROOT, "review", "dagui0562", "probe_nine_r1.txt")
ALIGN = os.path.join(ROOT, "review", "dagui0562", "align_r1.txt")

src = io.open(KEEP, encoding="utf-8").read()
io.open(TMP, "w", encoding="utf-8", newline="\n").write(
    src.replace("../../frontend/src/i18n/LocaleContext", "./src/i18n/LocaleContext")
)
log = []
alog = []
mine = io.open(DICT, "rb").read()
tip_blob = subprocess.check_output(
    ["git", "show", "%s:frontend/src/i18n/LocaleContext.tsx" % TIP], cwd=ROOT)


def bundle():
    p = subprocess.run([ESBUILD, "__probe_nine_tmp_r1.jsx", "--bundle", "--platform=node",
                        "--format=cjs", "--outfile=" + BUNDLE, "--jsx=automatic"],
                       cwd=FE, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", shell=True)
    if p.returncode != 0:
        log.append("BUNDLE FAILED rc=%d %s" % (p.returncode, (p.stdout or "") + (p.stderr or "")))
        raise SystemExit(2)


def probe(tag):
    bundle()
    q = subprocess.run(["node", BUNDLE], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    body = (q.stdout or "") + (q.stderr or "")
    log.append("$ esbuild + node probe_nine_bundle_r1.cjs   [%s]" % tag)
    log.append("rc=%d ok=%d fail=%d" % (q.returncode, body.count("OK  "), body.count("FAIL")))
    log.append(body)
    return q.returncode


def align(tag):
    r = subprocess.run(["python", "scripts/i18n_detail2_parity_r1.py"], cwd=FE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
    alog.append("$ python scripts/i18n_detail2_parity_r1.py   [%s]" % tag)
    alog.append("rc=%d" % r.returncode)
    alog.append((r.stdout or "") + (r.stderr or ""))


rc_mine = probe("this branch: the nine keys are in the dictionary")
align("this branch")
io.open(DICT, "wb").write(tip_blob)
rc_tip = probe("control: the authoritative tip's dictionary, without them")
align("the authoritative tip's dictionary")
io.open(DICT, "wb").write(mine)
if os.path.exists(BUNDLE):
    os.remove(BUNDLE)
os.remove(TMP)

assert io.open(DICT, "rb").read() == mine, "dictionary not restored"
summary = "verdict=%s mine_rc=%d mine_ok_lines=%d tip_rc=%d tip_fail_lines=%d restored=1" % (
    "PROVEN" if (rc_mine == 0 and rc_tip != 0) else "CHECK", rc_mine,
    log[2].count("OK  "), rc_tip, log[5].count("FAIL"))
log.append(summary)
io.open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
io.open(ALIGN, "w", encoding="utf-8").write("\n".join(alog) + "\n")
sys.stdout.write(summary + "\n")
sys.exit(0 if "PROVEN" in summary else 6)
