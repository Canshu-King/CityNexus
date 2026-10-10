import subprocess, io, os, sys

WT = "D:/moodle/_qoder_kuaidinggong_0557/wt"
TIP = "7ce836f9afafe9e763527cba828719b414b18db8"
PROD = "review/快钉工-0557-r1"
DICT = "review/快钉工-0557-dict-r1"
COMB = "tmp/kuaidinggong-0557-combined"
PANEL = "frontend/src/features/recovery/V14PreventivePanel.tsx"
LOCF = "frontend/src/i18n/LocaleContext.tsx"
KEYS = ["recovery.noDominantMode", "recovery.noneOnThisJourney"]
OLD = {"recovery.noDominantMode": "no dominant mode", "recovery.noneOnThisJourney": "none on this journey"}
EVIDENCE = "D:/moodle/_kd0557_evidence_r1.txt"
GATES = "D:/moodle/_kd0557_gates_r1.txt"


def git(*args):
    return subprocess.run(["git", "-C", WT] + list(args), capture_output=True, check=True).stdout.decode("utf-8")


def blob(ref, path):
    return git("show", ref + ":" + path).split("\n")


def find_lines(lines, needle):
    return [(n + 1, ln.strip()) for n, ln in enumerate(lines) if needle in ln]


def run_gates(state):
    """Run both gates against the currently checked-out tree; append readings."""
    p = subprocess.run(["python", "frontend/scripts/i18n_detail2_parity_r1.py"],
                       capture_output=True, cwd=WT)
    out = p.stdout.decode("utf-8", "replace").split("\n")
    err = p.stderr.decode("utf-8", "replace").split("\n")
    counts = out[0].strip() if out else ""
    xorline = [ln for ln in err if "PARITY BREAK" in ln]
    parity = "rc={} {} xor={}".format(p.returncode, counts, xorline[-1].strip() if xorline else "no-break-line")
    t = subprocess.run(["node", "frontend/node_modules/typescript/bin/tsc",
                        "-p", "frontend/tsconfig.typecheck.json", "--noEmit"],
                       capture_output=True, cwd=WT)
    tlines = [ln for ln in t.stdout.decode("utf-8", "replace").split("\n") if ln.strip()]
    tsc = "rc={} error_lines={} first={}".format(t.returncode, len(tlines), tlines[0] if tlines else "none")
    head = git("rev-parse", "HEAD").strip()
    line = "{} head40 {} parity[{}] tsc[{}]".format(state, head, parity, tsc)
    with io.open(GATES, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
    print(line)


if len(sys.argv) > 1 and sys.argv[1] == "--gates":
    run_gates(sys.argv[2])
    sys.exit(0)

prod_tip = git("rev-parse", PROD).strip()
dict_tip = git("rev-parse", DICT).strip()
comb_tip = git("rev-parse", COMB).strip()
remote = git("ls-remote", "origin", "refs/heads/" + PROD, "refs/heads/" + DICT).strip()

panel_old = blob(TIP, PANEL)
panel_new = blob(prod_tip, PANEL)
loc_new = blob(dict_tip, LOCF)
ns = git("diff", "--numstat", TIP, prod_tip, "--", PANEL).strip()
nd = git("diff", "--numstat", TIP, dict_tip, "--", LOCF).strip()

en_span = [n for (n, ln) in enumerate(loc_new) if ln.startswith("const en: Dict")][0]
zh_span = [n for (n, ln) in enumerate(loc_new) if ln.startswith("const zhCN: Dict")][0]

R = []
R.append("authoritative_tip40 " + TIP)
R.append("product_branch {} tip40 {}".format(PROD, prod_tip))
R.append("dict_branch {} tip40 {}".format(DICT, dict_tip))
R.append("local_only_merge_prediction_for_landing {} tip40 {}".format(COMB, comb_tip))
R.append("ls-remote_origin_readback " + remote.replace("\n", " | "))
R.append("product_file_numstat " + ns)
R.append("dict_file_numstat " + nd)
R.append("files_touched product_dict_each {}".format(
    [len(git("diff", "--name-only", TIP, prod_tip).split()), len(git("diff", "--name-only", TIP, dict_tip).split())]))
for key in KEYS:
    R.append("before_panel_line {} -> {}".format(OLD[key], find_lines(panel_old, OLD[key] + '"')))
    R.append("after_panel_line {} -> {}".format(key, find_lines(panel_new, 't("' + key + '")')))
    en_hits = [h for h in find_lines(loc_new, '"' + key + '"') if en_span + 1 < h[0] < zh_span + 1]
    zh_hits = [h for h in find_lines(loc_new, '"' + key + '"') if h[0] > zh_span + 1]
    R.append("en_side {} at {}".format(key, en_hits))
    R.append("zh_side {} at {}".format(key, zh_hits))
    ev = en_hits[0][1].split(": ", 1)[1].strip(' ",') if en_hits else "MISSING"
    zv = zh_hits[0][1].split(": ", 1)[1].strip(' ",') if zh_hits else "MISSING"
    on_tip = bool(find_lines(panel_old, OLD[key] + '"'))
    verdict = "SCREEN_TEXT_IDENTICAL" if (on_tip and ev == OLD[key] and zv == OLD[key]) else "SCREEN_TEXT_MOVED"
    R.append("equality {} tip_literal_present={} en_value_matches={} zh_value_matches={} verdict={}".format(
        key, on_tip, ev == OLD[key], zv == OLD[key], verdict))
R.append("dict_diff_deletes_existing_line " + nd.split("\t")[1])
R.append("panel_locale_conditionals " + str(len(find_lines(panel_new, "locale ==="))))
spec = blob(TIP, "frontend/e2e/predictive-real-city-v6.spec.ts")
R.append("e2e_lines_asserting_the_two_testids " + str(
    [h for h in find_lines(spec, "v14-preventive-evidence") + find_lines(spec, "v14-preventive-protected")]))
hits = []
for root, dirs, files in os.walk(WT + "/frontend/src"):
    dirs[:] = [d for d in dirs if d != "node_modules"]
    for fn in files:
        if fn.endswith((".ts", ".tsx")):
            txt = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
            if any(OLD[k] in txt for k in KEYS):
                hits.append(os.path.relpath(os.path.join(root, fn), WT).replace("\\", "/"))
R.append("files_under_src_holding_the_two_literals_in_this_checkout " + str(hits))
R.append("gate_readings_see D:/moodle/_kd0557_gates_r1.txt")

with io.open(EVIDENCE, "w", encoding="utf-8", newline="\n") as fh:
    for i, line in enumerate(R):
        fh.write("{}. {}\n".format(i + 1, line))
print("\n".join(R))
