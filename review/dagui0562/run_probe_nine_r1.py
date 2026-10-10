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

src = io.open(KEEP, encoding="utf-8").read()
io.open(TMP, "w", encoding="utf-8", newline="\n").write(
    src.replace("../../frontend/src/i18n/LocaleContext", "./src/i18n/LocaleContext")
)
log = ["$ " + " ".join([ESBUILD, TMP, "--bundle", "--platform=node", "--format=cjs",
                        "--outfile=" + BUNDLE, "--jsx=automatic"]), ""]
p = subprocess.run([ESBUILD, "__probe_nine_tmp_r1.jsx", "--bundle", "--platform=node",
                    "--format=cjs", "--outfile=" + BUNDLE, "--jsx=automatic"],
                   cwd=FE, capture_output=True, text=True, encoding="utf-8",
                   errors="replace", shell=True)
log[1] = "rc=%d" % p.returncode
log.append((p.stdout or "") + (p.stderr or ""))
os.remove(TMP)
if p.returncode != 0:
    io.open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
    sys.stdout.write("\n".join(log) + "\n")
    sys.exit(2)

mine = io.open(DICT, "rb").read()
tip_blob = subprocess.check_output(
    ["git", "show", "%s:frontend/src/i18n/LocaleContext.tsx" % TIP], cwd=ROOT)


def run_probe(tag):
    q = subprocess.run(["node", BUNDLE], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    body = (q.stdout or "") + (q.stderr or "")
    log.append("$ node probe_nine_bundle_r1.cjs   [%s]" % tag)
    log.append("rc=%d ok=%d fail=%d" % (q.returncode, body.count("OK  "), body.count("FAIL")))
    log.append(body)
    return q.returncode


rc_mine = run_probe("this branch: nine keys present")
io.open(DICT, "wb").write(tip_blob)
rc_tip = run_probe("control: the authoritative tip's dictionary")
io.open(DICT, "wb").write(mine)

align = subprocess.run(["python", "scripts/i18n_detail2_parity_r1.py"], cwd=FE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
log.append("$ python scripts/i18n_detail2_parity_r1.py   [this branch]")
log.append("rc=%d" % align.returncode)
log.append((align.stdout or "") + (align.stderr or ""))
io.open(DICT, "wb").write(tip_blob)
base = subprocess.run(["python", "scripts/i18n_detail2_parity_r1.py"], cwd=FE,
                      capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
io.open(DICT, "wb").write(mine)
log.append("$ python scripts/i18n_detail2_parity_r1.py   [the authoritative tip's dictionary]")
log.append("rc=%d" % base.returncode)
log.append((base.stdout or "") + (base.stderr or ""))

assert io.open(DICT, "rb").read() == mine, "dictionary not restored"
os.remove(BUNDLE)
io.open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
sys.stdout.write("\n".join([l for l in log if l and l[0] not in " ="][:4]) + "\n")
sys.stdout.write("mine_rc=%d tip_rc=%d align_mine=%s align_tip=%s\n"
                 % (rc_mine, rc_tip, align.returncode, base.returncode))
