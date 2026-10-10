import hashlib, io, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = os.path.join(ROOT, "frontend")
SRC = os.path.join(FE, "src", "features", "simulation", "SimulationPanel.tsx")
DICT = os.path.join(FE, "src", "i18n", "LocaleContext.tsx")
log = []


def run(cmd, cwd=FE):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", shell=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def digest(p):
    return hashlib.sha1(io.open(p, "rb").read()).hexdigest()


def mutate(path, old, new):
    text = io.open(path, encoding="utf-8", newline="").read()
    assert text.count(old) == 1, "anchor not unique in %s" % path
    io.open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new, 1))


src_blob = io.open(SRC, "rb").read()
dict_blob = io.open(DICT, "rb").read()
before = {SRC: digest(SRC), DICT: digest(DICT)}

mutate(DICT, u'"simulation.onStage": "台上行程",', u'"simulation.onStage": "台上行程X",')
rc1, out1 = run(["python", os.path.join(ROOT, "review", "dagui2", "run_probe_inline_r1.py")], cwd=ROOT)
log.append("NEG1 dictionary one-char-off probe_rc=%d failed_lines=%d" % (rc1, out1.count("FAIL")))
io.open(DICT, "wb").write(dict_blob)
rc2, out2 = run(["python", os.path.join(ROOT, "review", "dagui2", "run_probe_inline_r1.py")], cwd=ROOT)
log.append("NEG1b restored probe_rc=%d ok_lines=%d" % (rc2, out2.count("OK  ")))

mutate(SRC, u'{t("simulation.closeStage")}', u'{t("simulation.closeStage") + 1}')
rc3, out3 = run(["node_modules\\.bin\\tsc", "-p", "tsconfig.check.json", "--noEmit"])
log.append("NEG2 typecheck bad-operand rc=%d error_lines=%d"
           % (rc3, len([l for l in out3.split("\n") if "error TS" in l])))
io.open(SRC, "wb").write(src_blob)

mutate(SRC, u'{t("simulation.onStage")}', u'{t("simulation.onStage"}')
rc4, out4 = run(["node_modules\\.bin\\vite", "build"])
log.append("NEG3 build syntax-break rc=%d" % rc4)
io.open(SRC, "wb").write(src_blob)

for p in (SRC, DICT):
    log.append("restored_same_bytes %s=%d" % (os.path.relpath(p, ROOT), int(digest(p) == before[p])))
clean = all(digest(p) == before[p] for p in (SRC, DICT))
ok = rc1 != 0 and out1.count("FAIL") >= 1 and rc2 == 0 and rc3 != 0 and rc4 != 0 and clean
log.append("verdict=%s clean=%d neg1_rc=%d neg1b_rc=%d tsc_rc=%d build_rc=%d"
           % ("PROVEN" if ok else "CHECK", int(clean), rc1, rc2, rc3, rc4))
io.open(os.path.join(ROOT, "review", "dagui2", "negcontrol_inline_r1.txt"), "w",
        encoding="utf-8").write("\n".join(log) + "\n")
sys.stdout.write("\n".join(log) + "\n")
sys.exit(0 if ok else 6)
