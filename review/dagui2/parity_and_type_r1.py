import hashlib, io, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = os.path.join(ROOT, "frontend")
SRC_REL = "frontend/src/features/simulation/SimulationPanel.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
SRC = os.path.join(FE, "src", "features", "simulation", "SimulationPanel.tsx")
DICT = os.path.join(FE, "src", "i18n", "LocaleContext.tsx")
BASE = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4"
KEY = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
log = []


def load(t):
    i, j, k = t.index("const en: Dict"), t.index("const zhCN: Dict"), t.index("const dictionaries")
    out = []
    for chunk in (t[i:j], t[j:k]):
        d = {}
        for line in chunk.split("\n"):
            s = line.strip()
            if s.startswith("//") or s.startswith("*"):
                continue
            m = KEY.match(line)
            if m:
                d[m.group(1)] = m.group(2)
        out.append(d)
    return out


def show(ref, path):
    return subprocess.check_output(["git", "show", "%s:%s" % (ref, path)],
                                   text=True, encoding="utf-8", cwd=ROOT)


be, bz = load(show(BASE, DICT_REL))
ne, nz = load(io.open(DICT, encoding="utf-8").read())
log.append("base en=%d zh=%d diff=%s" % (len(be), len(bz), sorted(set(be) ^ set(bz))))
log.append("now  en=%d zh=%d diff=%s" % (len(ne), len(nz), sorted(set(ne) ^ set(nz))))
log.append("added en=%d zh=%d" % (len(set(ne) - set(be)), len(set(nz) - set(bz))))
log.append("existing_text_rewritten en=%d zh=%d"
           % (len([k for k in be if be[k] != ne.get(k)]),
              len([k for k in bz if bz[k] != nz.get(k)])))
mine = ("simulation.closeStage", "simulation.onStage", "simulation.sceneWindow")
log.append("my_keys_on_both_sides=%d of 3" % len([k for k in mine if k in ne and k in nz]))

# type-layer control: a module-level string assigned to a number must be TS2322
blob = io.open(SRC, "rb").read()
before = hashlib.sha1(blob).hexdigest()
text = io.open(SRC, encoding="utf-8", newline="").read()
anchor = 'import { cityNexusApi } from "../../api/citynexus";'
assert text.count(anchor) == 1
io.open(SRC, "w", encoding="utf-8", newline="").write(
    text.replace(anchor, anchor + '\nconst __bad_type_r1: number = "x";', 1)
)
p = subprocess.run(["node_modules\\.bin\\tsc", "-p", "tsconfig.check.json", "--noEmit"],
                   cwd=FE, capture_output=True, text=True, encoding="utf-8",
                   errors="replace", shell=True)
raw = (p.stdout or "") + (p.stderr or "")
errs = [l for l in raw.split("\n") if "error TS" in l]
log.append("NEG2c tsc_rc=%d error_lines=%d first=%s" % (p.returncode, len(errs),
                                                        errs[0][:120] if errs else raw[:120]))
io.open(SRC, "wb").write(blob)
after = hashlib.sha1(io.open(SRC, "rb").read()).hexdigest()
log.append("restored_same_bytes=%d" % int(after == before))
ok = p.returncode != 0 and len(errs) >= 1 and after == before
log.append("verdict=%s" % ("PROVEN" if ok else "CHECK"))
io.open(os.path.join(ROOT, "review", "dagui2", "parity_and_type_r1.txt"), "w",
        encoding="utf-8").write("\n".join(log) + "\n")
sys.stdout.write("\n".join(log) + "\n")
sys.exit(0 if ok else 6)
