import io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEEP = os.path.join(ROOT, "review", "dagui", "probe_locale_r1.jsx")
TMP = os.path.join(ROOT, "frontend", "__probe_tmp_r1.jsx")
BUNDLE = os.path.join(ROOT, "review", "dagui", "probe_bundle_r1.cjs")
ESBUILD = os.path.join(ROOT, "frontend", "node_modules", ".bin", "esbuild.cmd")

src = io.open(KEEP, encoding="utf-8").read()
io.open(TMP, "w", encoding="utf-8", newline="\n").write(
    src.replace('../../frontend/src/i18n/LocaleContext', './src/i18n/LocaleContext')
)
cmds = [
    [ESBUILD, "__probe_tmp_r1.jsx", "--bundle", "--platform=node", "--format=cjs",
     "--outfile=" + BUNDLE, "--jsx=automatic"],
    ["node", BUNDLE],
]
log = []
rc_all = 0
for c in cmds:
    p = subprocess.run(c, cwd=os.path.join(ROOT, "frontend"), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", shell=True)
    log.append("$ " + " ".join(c))
    log.append("rc=%d" % p.returncode)
    log.append((p.stdout or "") + (p.stderr or ""))
    if p.returncode != 0:
        rc_all = p.returncode
    if c[0] == "node":
        os.remove(TMP)
io.open(os.path.join(ROOT, "review", "dagui", "probe_run_r1.txt"), "w", encoding="utf-8").write(
    "\n".join(log) + "\n")
sys.stdout.write(log[-1] if log[-1].strip() else log[-3])
sys.exit(rc_all)
