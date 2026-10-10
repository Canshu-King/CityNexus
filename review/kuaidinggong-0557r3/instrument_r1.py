import subprocess, io, json
from pathlib import Path

WT = "D:/moodle/_qoder_kuaidinggong_0557/wt2"
ROOT = "D:/moodle/"
BASE = "26136afacf9e0c951bf4911f4d219161e07c4746"
PROD = "review/快钉工-0557-r3"
DICT = "review/快钉工-0557-dict-r3"
F = "frontend/src/features/inbox/JourneyInboxWorkbench.tsx"
D = "frontend/src/i18n/LocaleContext.tsx"
KEY = "inbox.recorded"
LIT_ZH = "已记录"
LIT_EN = "Recorded"
DEAD = "moneyLabel"
NL = chr(10)
EV = "_kd0557r3_evidence_r1.txt"
GT = "_kd0557r3_gates_r1.txt"
CFG = "_kd0557r3_tsconfig_two_files.json"


def git(*a):
    p = subprocess.run(["git", "-C", WT] + list(a), capture_output=True)
    assert p.returncode == 0, str(list(a)) + p.stderr.decode("utf-8", "replace")
    return p.stdout.decode("utf-8").strip()


def rc_anc(h, tip):
    return subprocess.run(["git", "-C", WT, "merge-base", "--is-ancestor", h, tip], capture_output=True).returncode


def blob(ref, path):
    return git("show", ref + ":" + path).split(NL)


def at(lines, needle):
    return [(i + 1, l.strip()) for i, l in enumerate(lines) if needle in l]


def shell(cmd):
    p = subprocess.run(cmd, shell=True, cwd=WT, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def errs(text):
    return [l for l in text.split(NL) if "error TS" in l]


def write_cfg():
    src = json.loads(io.open(WT + "/frontend/tsconfig.typecheck.json", encoding="utf-8").read())
    src["compilerOptions"]["types"] = []
    src["include"] = [str(Path(WT) / F), str(Path(WT) / D)]
    io.open(ROOT + CFG, "w", encoding="utf-8", newline=chr(10)).write(json.dumps(src, indent=2) + NL)


def measure(state, expect_head, expect_keys, expect_reads):
    head = git("rev-parse", "HEAD").strip()
    assert head == expect_head, "STATE MISMATCH " + state
    loc = io.open(WT + "/" + D, encoding="utf-8").read().split(NL)
    fil = io.open(WT + "/" + F, encoding="utf-8").read().split(NL)
    gk = len([l for l in loc if '"' + KEY + '"' in l])
    gr = len([l for l in fil if 't("' + KEY + '")' in l])
    assert (gk, gr) == (expect_keys, expect_reads), "face mismatch " + state
    rc1, o1, _ = shell("node frontend/node_modules/typescript/bin/tsc -p frontend/tsconfig.typecheck.json --noEmit")
    rc2, o2, _ = shell("node frontend/node_modules/typescript/bin/tsc -p " + ROOT + CFG + " --noEmit")
    rc3, o3, e3 = shell("python frontend/scripts/i18n_detail2_parity_r1.py")
    xor = [l for l in e3.split(NL) if "PARITY BREAK" in l]
    return " ".join([state + " head40 " + head, "key_lines=" + str(gk), "readpoint_lines=" + str(gr),
                     "full_tsc[rc=" + str(rc1) + " error_lines=" + str(len(errs(o1))) + " first=" + (errs(o1)[0] if errs(o1) else "none") + "]",
                     "scoped_tsc[rc=" + str(rc2) + " error_lines=" + str(len(errs(o2))) + "]",
                     "parity[rc=" + str(rc3) + " " + o3.split(NL)[0].strip() + " xor=" + (xor[-1].strip() if xor else "no-break") + "]"])


write_cfg()
prod_head = git("rev-parse", PROD)
dict_head = git("rev-parse", DICT)
base_loc = blob(BASE, D)
base_fil = blob(BASE, F)
dict_loc = blob(dict_head, D)
en_edge = [i for i, l in enumerate(dict_loc) if l.startswith("const en: Dict")][0]
zh_edge = [i for i, l in enumerate(dict_loc) if l.startswith("const zhCN: Dict")][0]
en_h = [h for h in at(dict_loc, '"' + KEY + '"') if en_edge + 1 < h[0] < zh_edge + 1]
zh_h = [h for h in dict_loc]
zh_h = [h for h in at(dict_loc, '"' + KEY + '"') if h[0] > zh_edge + 1]

scan = subprocess.run("grep -rn --include=*.ts --include=*.tsx " + DEAD + " frontend/src frontend/e2e",
                      shell=True, cwd=WT, capture_output=True)
scan_lines = [l for l in scan.stdout.decode("utf-8", "replace").split(NL) if l.strip()]
defs = [l for l in scan_lines if "function " + DEAD in l]
calls = [l for l in scan_lines if "function " + DEAD not in l]

E = ["base_tip " + BASE, "product_head " + prod_head, "dict_head " + dict_head,
     "ls-remote_now " + git("ls-remote", "origin", "refs/heads/" + PROD, "refs/heads/" + DICT).replace(NL, " | "),
     "key_already_in_base_dictionary " + str(len(at(base_loc, '"' + KEY + '"'))),
     "base_literal_line " + str(at(base_fil, '"{}" : "{}"'.format(LIT_ZH, LIT_EN))),
     "dict_sides {} en={} zh={}".format(KEY, en_h, zh_h),
     "ev_values " + str([h[1].split(": ", 1)[1].strip(' ",') for h in en_h + zh_h]),
     "numstat_product " + git("diff", "--numstat", BASE, prod_head, "--", F).strip().replace(NL, " "),
     "numstat_dict " + git("diff", "--numstat", BASE, dict_head, "--", D).strip().replace(NL, " "),
     "files_product_vs_base " + str(git("diff", "--name-only", BASE, prod_head).split()),
     "files_dict_vs_base " + str(git("diff", "--name-only", BASE, dict_head).split()),
     "product_carries_dict_rc " + str(rc_anc(dict_head, prod_head)),
     "moneyLabel_scan_hits " + str(len(scan_lines)),
     "moneyLabel_definitions " + str(defs),
     "moneyLabel_call_sites " + str(len(calls)),
     "gate_readings_see " + GT]

G = []
git("checkout", "-q", "--detach", BASE)
G.append(measure("negative_control_base", BASE, 0, 0))
git("checkout", "-q", DICT)
G.append(measure("dict_branch", dict_head, 2, 0))
git("checkout", "-q", PROD)
G.append(measure("product_branch", prod_head, 2, 1))

with io.open(ROOT + GT, "w", encoding="utf-8", newline=chr(10)) as fh:
    for i, ln in enumerate(G):
        fh.write(str(i + 1) + ". " + ln + NL)
with io.open(ROOT + EV, "w", encoding="utf-8", newline=chr(10)) as fh:
    for i, ln in enumerate(E):
        fh.write(str(i + 1) + ". " + ln + NL)
for ln in G:
    print(ln)
print("---")
for ln in E:
    print(ln[:190])
