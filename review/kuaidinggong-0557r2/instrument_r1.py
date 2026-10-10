import subprocess, io, json
from pathlib import Path

WT = "D:/moodle/_qoder_kuaidinggong_0557/wt2"
TIP = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4"
PROD = "review/快钉工-0557-r2"
DICT = "review/快钉工-0557-dict-r2"
FILE = "frontend/src/features/inbox/JourneyInboxWorkbench.tsx"
LOCF = "frontend/src/i18n/LocaleContext.tsx"
NL = chr(10)
EVIDENCE = "D:/moodle/_kd0557r2_evidence_r1.txt"
GATES = "D:/moodle/_kd0557r2_gates_r1.txt"
EXT_CFG = "D:/moodle/_kd0557r2_tsconfig_two_files.json"
PAIRS = [("inbox.handled", "已处理", "Handled"), ("inbox.toConfirm", "待确认", "To confirm")]


def git(*a):
    p = subprocess.run(["git", "-C", WT] + list(a), capture_output=True)
    assert p.returncode == 0, "git failed " + str(list(a)) + " " + p.stderr.decode("utf-8", "replace")
    return p.stdout.decode("utf-8")


def blob(ref, path):
    return git("show", ref + ":" + path).split(NL)


def shell(cmd):
    p = subprocess.run(cmd, shell=True, cwd=WT, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def hits(lines, needle):
    return [(i + 1, l.strip()) for i, l in enumerate(lines) if needle in l]


def count_errs(text):
    return len([l for l in text.split(NL) if "error TS" in l])


def first_err(text):
    got = [l for l in text.split(NL) if "error TS" in l]
    return got[0].strip() if got else "none"


def write_ext_cfg():
    src = json.loads(io.open(WT + "/frontend/tsconfig.typecheck.json", encoding="utf-8").read())
    src["compilerOptions"]["types"] = []
    src["include"] = [str(Path(WT) / FILE), str(Path(WT) / LOCF)]
    io.open(EXT_CFG, "w", encoding="utf-8").write(json.dumps(src, indent=2) + NL)


def measure(state, expect_head, expect_key_lines, expect_read_lines):
    head = git("rev-parse", "HEAD").strip()
    assert head == expect_head, "STATE MISMATCH " + state + " head=" + head
    loc_now = io.open(WT + "/" + LOCF, encoding="utf-8").read().split(NL)
    fil_now = io.open(WT + "/" + FILE, encoding="utf-8").read().split(NL)
    got_keys = len([l for l in loc_now if '"inbox.handled"' in l or '"inbox.toConfirm"' in l])
    got_reads = len([l for l in fil_now if 't("inbox.handled")' in l or 't("inbox.toConfirm")' in l])
    assert (got_keys, got_reads) == (expect_key_lines, expect_read_lines), "face mismatch " + state
    rc, out, _ = shell("node frontend/node_modules/typescript/bin/tsc -p frontend/tsconfig.typecheck.json --noEmit")
    rc2, out2, _ = shell("node frontend/node_modules/typescript/bin/tsc -p " + EXT_CFG + " --noEmit")
    rc3, out3, err3 = shell("python frontend/scripts/i18n_detail2_parity_r1.py")
    xor = [l for l in err3.split(NL) if "PARITY BREAK" in l]
    return " ".join([state + " head40 " + head,
                     "dict_key_lines=" + str(got_keys), "readpoint_lines=" + str(got_reads),
                     "full_tsc[rc=" + str(rc) + " error_lines=" + str(count_errs(out)) + " first=" + first_err(out) + "]",
                     "scoped_tsc[rc=" + str(rc2) + " error_lines=" + str(count_errs(out2)) + " first=" + first_err(out2) + "]",
                     "parity[rc=" + str(rc3) + " " + out3.split(NL)[0].strip() + " xor=" + (xor[-1].strip() if xor else "no-break") + "]"])


prod_tip = git("rev-parse", PROD).strip()
dict_tip = git("rev-parse", DICT).strip()
remote = git("ls-remote", "origin", "refs/heads/" + PROD, "refs/heads/" + DICT).strip().replace(NL, " | ")
tip_file = blob(TIP, FILE)
tip_loc = blob(TIP, LOCF)
my_loc = blob(dict_tip, LOCF)

en_edge = [i for i, l in enumerate(my_loc) if l.startswith("const en: Dict")][0]
zh_edge = [i for i, l in enumerate(my_loc) if l.startswith("const zhCN: Dict")][0]

E = []
E.append("line_tip " + TIP)
E.append("product_branch_head " + prod_tip)
E.append("dict_branch_head " + dict_tip)
E.append("ls-remote_origin_readback " + remote)
E.append("keys_missing_in_tip_dictionary " + str([len(hits(tip_loc, '"' + k + '"')) for (k, z, e) in PAIRS]))
for (k, z, e) in PAIRS:
    E.append("tip_literal_lines {} {}".format(k, hits(tip_file, '"{}" : "{}"'.format(z, e))))
    en_h = [h for h in hits(my_loc, '"' + k + '"') if en_edge + 1 < h[0] < zh_edge + 1]
    zh_h = [h for h in hits(my_loc, '"' + k + '"') if h[0] > zh_edge + 1]
    ev = en_h[0][1].split(": ", 1)[1].strip(' ",') if en_h else "MISSING"
    zv = zh_h[0][1].split(": ", 1)[1].strip(' ",') if zh_h else "MISSING"
    E.append("dict_sides {} en={} zh={}".format(k, en_h, zh_h))
    E.append("screen_unchanged {} en_value_matches_tip_literal={} zh_value_matches_tip_literal={}".format(
        k, ev == e, zv == z))
E.append("files_touched_by_product_vs_tip " + str(git("diff", "--name-only", TIP, prod_tip).split()))
E.append("files_touched_by_dict_vs_tip " + str(git("diff", "--name-only", TIP, dict_tip).split()))
E.append("product_carries_dict_is_ancestor_rc " + str(subprocess.run(["git", "-C", WT, "merge-base", "--is-ancestor", dict_tip, prod_tip], capture_output=True).returncode))
E.append("numstat_product " + git("diff", "--numstat", TIP, prod_tip, "--", FILE).strip().replace(NL, " "))
E.append("numstat_dict " + git("diff", "--numstat", TIP, dict_tip, "--", LOCF).strip().replace(NL, " "))
E.append("call_sites_pass_translator " + str(hits(blob(prod_tip, FILE), "zh, t)")))
E.append("helper_signatures " + str(hits(blob(prod_tip, FILE), "(key: string) => string")))
E.append("gate_readings_see _kd0557r2_gates_r1.txt")

write_ext_cfg()
G = []
git("checkout", "-q", "--detach", TIP)
G.append(measure("negative_control_line_tip", TIP, 0, 0))
git("checkout", "-q", DICT)
G.append(measure("dict_branch", dict_tip, 4, 0))
git("checkout", "-q", PROD)
G.append(measure("product_branch_carries_dict", prod_tip, 4, 3))
with io.open(GATES, "w", encoding="utf-8") as fh:
    for i, ln in enumerate(G):
        fh.write(str(i + 1) + ". " + ln + NL)
with io.open(EVIDENCE, "w", encoding="utf-8") as fh:
    for i, ln in enumerate(E):
        fh.write(str(i + 1) + ". " + ln + NL)
for ln in G:
    print(ln)
print("---")
for ln in E:
    print(ln[:180])
