import hashlib, io, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = os.path.join(ROOT, "frontend")
SRC = os.path.join(FE, "src", "features", "simulation", "SimulationPanel.tsx")
DICT = os.path.join(FE, "src", "i18n", "LocaleContext.tsx")
log = []


def run(cmd, cwd=FE):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", shell=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def digest(path):
    return hashlib.sha1(io.open(path, "rb").read()).hexdigest()


def mutate(path, old, new, count=1):
    text = io.open(path, encoding="utf-8", newline="").read()
    assert text.count(old) >= count, "anchor missing in %s" % path
    io.open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new, count))


def restore(path, blob):
    io.open(path, "wb").write(blob)
    assert digest(path) == blob_sha[path], "restore mismatch %s" % path


src_blob = io.open(SRC, "rb").read()
dict_blob = io.open(DICT, "rb").read()
blob_sha = {SRC: digest(SRC), DICT: digest(DICT)}
before = {SRC: digest(SRC), DICT: digest(DICT)}

# 1. dictionary probe negative control: one character off, the probe must go red.
#    The probe reads the dictionary through a bundle, so the bundle has to be rebuilt.
mutate(DICT, '"simulation.now": "（现值 {state}）",', '"simulation.now": "（现值X {state}）",')
rc, out = run(["python", os.path.join(ROOT, "review", "dagui", "run_probe_r1.py")], cwd=ROOT)
log.append("NEG1 dictionary one-char-off probe_rc=%d failed_lines=%d" % (rc, out.count("FAIL")))
restore(DICT, dict_blob)
rc0, out0 = run(["python", os.path.join(ROOT, "review", "dagui", "run_probe_r1.py")], cwd=ROOT)
log.append("NEG1b dictionary restored probe_rc=%d ok_lines=%d" % (rc0, out0.count("OK  ")))

# 2. typecheck negative control: an impossible assignment must go red
mutate(SRC, "  const zh = locale.startsWith(\"zh\");",
       "  const __neg_r1: number = \"x\";\n  const zh = locale.startsWith(\"zh\");", 1)
rc_tsc, out_tsc = run(["node_modules\\.bin\\tsc", "-p", "tsconfig.check.json", "--noEmit"])
log.append("NEG2 typecheck injected-error rc=%d error_lines=%d"
           % (rc_tsc, len([l for l in out_tsc.split("\n") if "error TS" in l])))
restore(SRC, src_blob)

# 3. build negative control: a syntax break must go red
mutate(SRC, "  const zh = locale.startsWith(\"zh\");",
       "  const __neg_r1 = (;\n  const zh = locale.startsWith(\"zh\");", 1)
rc_build, out_build = run(["node_modules\\.bin\\vite", "build"])
log.append("NEG3 build syntax-break rc=%d transform_error=%d"
           % (rc_build, 1 if ("ERROR" in out_build or "error during build" in out_build) else 0))
restore(SRC, src_blob)

# 4. the tree must be byte-identical to what it was before the negative controls
for path in (SRC, DICT):
    log.append("restored_same_bytes %s=%d" % (os.path.relpath(path, ROOT), int(digest(path) == before[path])))

clean = all(digest(p) == before[p] for p in (SRC, DICT))
neg1_fails = int(re.search(r"failed_lines=(\d+)", log[0]).group(1))
gate_ok = neg1_fails >= 1 and rc != 0 and rc0 == 0 and rc_tsc != 0 and rc_build != 0
verdict = "PROVEN" if (clean and gate_ok) else "CHECK"
log.append("verdict=%s clean=%d neg1_fails=%d neg1_rc=%d neg1b_rc=%d tsc_rc=%d build_rc=%d"
           % (verdict, int(clean), neg1_fails, rc, rc0, rc_tsc, rc_build))
io.open(os.path.join(ROOT, "review", "dagui", "negcontrol_r1.txt"), "w", encoding="utf-8").write(
    "\n".join(log) + "\n")
sys.stdout.write("\n".join(log) + "\n")
sys.exit(0 if verdict == "PROVEN" else 6)
