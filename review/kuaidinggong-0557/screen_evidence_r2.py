import subprocess, io, os

WT = "D:/moodle/_qoder_kuaidinggong_0557/wt"
OLDTIP = "7ce836f9afafe9e763527cba828719b414b18db8"
NEWTIP = "f6e936c8e85e3d349f132a2034487962583e6333"
PROD = "review/快钉工-0557-r1"
DICT = "review/快钉工-0557-dict-r1"
PANEL = "frontend/src/features/recovery/V14PreventivePanel.tsx"
LOCF = "frontend/src/i18n/LocaleContext.tsx"
PAIRS = [("recovery.noDominantMode", "no dominant mode"), ("recovery.noneOnThisJourney", "none on this journey")]
EVIDENCE = "D:/moodle/_kd0557_evidence_r2.txt"
GATES = "D:/moodle/_kd0557_gates_r2.txt"


def git(*a):
    return subprocess.run(["git", "-C", WT] + list(a), capture_output=True).stdout.decode("utf-8")


def blob(ref, path):
    return git("show", ref + ":" + path).split("\n")


def at(lines, needle):
    return [(n + 1, ln.strip()) for n, ln in enumerate(lines) if needle in ln]


def rc_true(ref, anc):
    return subprocess.run(["git", "-C", WT, "merge-base", "--is-ancestor", anc, ref]).returncode


def gate(cmd, cwd=WT):
    p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace").split("\n"), p.stderr.decode("utf-8", "replace").split("\n")


def readings(state):
    rc, out, err = gate("node frontend/node_modules/typescript/bin/tsc -p frontend/tsconfig.typecheck.json --noEmit")
    errs = [ln for ln in out if "error TS" in ln]
    full = "rc={} error_lines={} first={}".format(rc, len(errs), errs[0] if errs else "none")
    rc2, out2, err2 = gate("node frontend/node_modules/typescript/bin/tsc -p review/kuaidinggong-0557/tsconfig.two_files.json --noEmit")
    scoped = "rc={} error_lines={}".format(rc2, len([ln for ln in out2 if "error TS" in ln]))
    rc3, out3, err3 = gate("python frontend/scripts/i18n_detail2_parity_r1.py")
    counts = out3[0].strip() if out3 else ""
    xor = [ln for ln in err3 if "PARITY BREAK" in ln]
    parity = "rc={} {} xor={}".format(rc3, counts, xor[-1].strip() if xor else "no-break")
    return "{} head40 {} full_tsc[{}] scoped_tsc[{}] parity[{}]".format(state, git("rev-parse", "HEAD").strip(), full, scoped, parity)


G = []
git("checkout", "-q", "--detach", NEWTIP)
G.append(readings("negative_control_at_line_tip"))
git("checkout", "-q", DICT)
G.append(readings("dict_branch"))
git("checkout", "-q", PROD)
G.append(readings("product_branch_carries_dict"))
with io.open(GATES, "w", encoding="utf-8", newline="\n") as fh:
    for i, ln in enumerate(G):
        fh.write("{}. {}\n".format(i + 1, ln))

panel_line_tip = blob(NEWTIP, PANEL)
panel_my = blob(git("rev-parse", PROD).strip(), PANEL)
loc_my = blob(git("rev-parse", DICT).strip(), LOCF)
loc_after_merge = blob(git("rev-parse", PROD).strip(), LOCF)

R = []
R.append("line_tip_now " + NEWTIP)
R.append("my_first_base_tip " + OLDTIP)
R.append("commits_the_line_moved_since_my_base " + git("rev-list", "--count", OLDTIP + ".." + NEWTIP).strip())
R.append("line_changed_this_panel_file " + str(len([p for p in git("diff", "--name-only", OLDTIP, NEWTIP).split("\n") if p == PANEL])))
R.append("read_points_still_on_those_lines_at_the_new_tip " + str(at(panel_my, 't("recovery.')))
R.append("panel_literals_still_there_on_the_line " + str(at(panel_line_tip, '"no dominant mode"') + at(panel_line_tip, '"none on this journey"')))
R.append("product_branch_head " + git("rev-parse", PROD).strip())
R.append("dict_branch_head " + git("rev-parse", DICT).strip())
R.append("product_carries_dict_tip_is_ancestor_rc " + str(rc_true(PROD, git("rev-parse", DICT).strip())))
R.append("product_carries_line_tip_is_ancestor_rc " + str(rc_true(PROD, NEWTIP)))
R.append("dict_carries_line_tip_is_ancestor_rc " + str(rc_true(DICT, NEWTIP)))
en_span = [n for (n, ln) in enumerate(loc_my) if ln.startswith("const en: Dict")][0]
zh_span = [n for (n, ln) in enumerate(loc_my) if ln.startswith("const zhCN: Dict")][0]
for key, lit in PAIRS:
    en_hits = [h for h in at(loc_my, '"' + key + '"') if en_span + 1 < h[0] < zh_span + 1]
    zh_hits = [h for h in at(loc_my, '"' + key + '"') if h[0] > zh_span + 1]
    same = [h for h in at(loc_after_merge, '"' + key + '"')]
    R.append("keys_on_dict_branch {} en={} zh={} occurrences_after_merge_into_product={}".format(
        key, en_hits, zh_hits, len(same)))
    R.append("value_still_the_screen_word {} {}".format(key, all(lit in ln for ln in [e[1] for e in en_hits] + [z[1] for z in zh_hits])))
R.append("files_touched_by_product_branch_vs_line " + str(git("diff", "--name-only", NEWTIP, PROD).split()))
R.append("files_touched_by_dict_branch_vs_line " + str(git("diff", "--name-only", NEWTIP, DICT).split()))
R.append("gate_readings_see review/kuaidinggong-0557/gates_readout_r2.txt")

with io.open(EVIDENCE, "w", encoding="utf-8", newline="\n") as fh:
    for i, ln in enumerate(R):
        fh.write("{}. {}\n".format(i + 1, ln))
print("\n".join(G))
print("\n".join(R))
