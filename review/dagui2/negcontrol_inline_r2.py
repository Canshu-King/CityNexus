import hashlib, io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = os.path.join(ROOT, "frontend")
SRC = os.path.join(FE, "src", "features", "simulation", "SimulationPanel.tsx")
log = []

blob = io.open(SRC, "rb").read()
before = hashlib.sha1(blob).hexdigest()
text = io.open(SRC, encoding="utf-8", newline="").read()
anchor = u'{t("simulation.closeStage")}'
assert text.count(anchor) == 1
io.open(SRC, "w", encoding="utf-8", newline="").write(
    text.replace(anchor, u'(() => { const __bad_r1: number = %s; return __bad_r1; })()' % anchor, 1)
)
p = subprocess.run(["node_modules\\.bin\\tsc", "-p", "tsconfig.check.json", "--noEmit"],
                   cwd=FE, capture_output=True, text=True, encoding="utf-8",
                   errors="replace", shell=True)
errs = [l for l in (p.stdout + p.stderr).split("\n") if "error TS" in l]
log.append("NEG2b string assigned to a number tsc_rc=%d error_lines=%d first=%s"
           % (p.returncode, len(errs), errs[0][:110] if errs else ""))
io.open(SRC, "wb").write(blob)
after = hashlib.sha1(io.open(SRC, "rb").read()).hexdigest()
log.append("restored_same_bytes=%d" % int(after == before))
ok = p.returncode != 0 and len(errs) >= 1 and after == before
log.append("verdict=%s" % ("PROVEN" if ok else "CHECK"))
io.open(os.path.join(ROOT, "review", "dagui2", "negcontrol_inline_r2.txt"), "w",
        encoding="utf-8").write("\n".join(log) + "\n")
sys.stdout.write("\n".join(log) + "\n")
sys.exit(0 if ok else 6)
