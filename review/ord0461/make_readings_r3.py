"""ORD-0461 r3: assemble the readings for this generation.

Every line is parsed out of a file a command wrote or computed from git. Both sides of the suite
comparison are asserted to have produced a red list before anything is compared: a comparison against an
empty side is what once produced a fake 'no new reds' on this lane.
"""
import io
import re
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0461_wt/"
EV = "review/ord0461/"
WK = "D:/moodle/_qoder_rel_ord0461_wk/"
TIP = "d7c08d1293835adc7b2628f7100263066d610322"
SEP = chr(92)


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, (args, p.stderr[:200])
    return p.stdout


def ev(name):
    return io.open(WT + EV + name, encoding="utf-8", errors="replace").read()


def last(text, pattern):
    hits = [l.strip() for l in text.splitlines() if re.search(pattern, l)]
    assert hits, "nothing matched %r" % pattern
    return hits[-1]


def group(text, pattern):
    hits = [re.search(pattern, l) for l in text.splitlines()]
    hits = [h for h in hits if h]
    assert hits, "nothing matched %r" % pattern
    return hits[-1].group(1)


def reds(text):
    return sorted(l.split(" ")[0].replace("backend" + SEP + "tests" + SEP, "tests/")
                  for l in re.findall(r"^FAILED (\S+)", text, re.M))


head = git("rev-parse", "HEAD").strip()
product_head = group(ev("r3_commit_message.txt"), r"(3714b1d[0-9a-f]{33})")
rows = ["== ORD-0461 r3 readings, every line parsed out of a command result =="]
rows.append("branch_head=" + head)
rows.append("product_head=" + product_head)
rows.append("product_bytes_identical_between_them=%s" % (
    git("diff", "--numstat", product_head, head, "--", "backend", "contracts", "frontend").strip() == ""))
rows.append("cut_from=" + TIP)
rows.append("ancestry_holds=%s" % (TIP in git("merge-base", TIP, head).strip()))
rows.append("commits_on_branch=%d" % int(git("rev-list", "--count", TIP + ".." + head)))
rows.append("diff_against_tip=%s" % git("diff", "--shortstat", TIP, head).strip())
numstat = git("diff", "--numstat", TIP, head).splitlines()
prod = [l for l in numstat if not l.split("\t")[2].startswith("review/")]
rows.append("product_add=%d product_del=%d" % (sum(int(l.split("\t")[0]) for l in prod),
                                               sum(int(l.split("\t")[1]) for l in prod)))
rows.append("numstat:")
rows += ["  " + l for l in prod]
rows.append("main_py_line_ending_after_reland=%s" % (
    "CRLF" if sum(1 for l in io.open(WT + "backend/app/main.py", "rb").read().split(b"\n")
                  if l.endswith(b"\r")) == io.open(WT + "backend/app/main.py", "rb").read().count(b"\n")
    else "mixed"))
rows.append("")

rows.append("== the refusal, at this head ==")
rows.append("neighbour_selection=" + last(ev("r3_neighbours.txt"), r"\d+ passed"))
rows.append("parity=" + ev("r3_parity.txt").strip().splitlines()[-1])
collect_mine, collect_base = ev("r3_collect_mine.txt").strip(), ev("r3_collect_base.txt").strip()
rows.append("collect mine=" + collect_mine)
rows.append("collect base=" + collect_base)
rows.append("arm_delta=%s-%s=%d" % (group(collect_mine, r"(\d+) tests collected"),
                                    group(collect_base, r"(\d+) tests collected"),
                                    int(group(collect_mine, r"(\d+) tests collected"))
                                    - int(group(collect_base, r"(\d+) tests collected"))))
rows.append("")

rows.append("== the client was replayed, not re-taken whole ==")
gen_a = io.open(WK + "r3_gen_A.ts", encoding="utf-8").read()
gen_b = io.open(WK + "r3_gen_B.ts", encoding="utf-8").read()
import difflib
gen_added = [l[1:] for l in difflib.unified_diff(gen_a.splitlines(), gen_b.splitlines(), n=0)
             if l.startswith("+") and not l.startswith("+++")]
tip_client = git("show", "%s:frontend/src/generated/api.ts" % TIP)
now_client = git("show", "%s:frontend/src/generated/api.ts" % head)
carried = [l[1:] for l in difflib.unified_diff(tip_client.splitlines(), now_client.splitlines(), n=0)
           if l.startswith("+") and not l.startswith("+++")]
rows.append("client_generation_delta_lines=%d lines_the_branch_adds_to_the_tip_client=%d same_content=%s"
            % (len(gen_added), len(carried),
               [x.strip() for x in gen_added] == [x.strip() for x in carried]))
rows.append("and_the_branch_removes_from_the_tip_client=%d (a wholesale regeneration would have moved "
            "far more lines than this order's own)"
            % len([l for l in difflib.unified_diff(tip_client.splitlines(), now_client.splitlines(), n=0)
                   if l.startswith("-") and not l.startswith("---")]))
rows.append("")

rows.append("== frontend gates, build entry and store ownership ==")
rows.append("tsc_check=" + last(ev("r3_tsc_check.txt"), r"tsc_check_rc=\d+"))
rows.append("tsc_typecheck=" + last(ev("r3_tsc_typecheck.txt"), r"tsc_typecheck_rc=\d+"))
rows.append("vite=" + last(ev("r3_vite_build.txt"), r"vite_rc=\d+"))
rows.append("build=" + last(ev("r3_vite_build.txt"), r"built in [\d.]+s"))
rows.append("entry_and_store=" + ev("r3_entry_and_store.txt").strip().replace("\n", " || "))
rows.append("")

rows.append("== whole backend suite: two runs here, two untouched worktrees of the tip ==")
mine_runs = [(n, ev(n)) for n in ("r3_suite_mine_1.txt", "r3_suite_mine_2.txt")]
base_runs = [(n, ev(n)) for n in ("r3_suite_base_1.txt", "r3_suite_base_2.txt")]
for name, text in mine_runs + base_runs:
    assert reds(text), "%s produced no red list -- an empty side fakes a clean comparison" % name
    rows.append("%s summary=%s reds=%d" % (name, last(text, r"\d+ (passed|failed)"), len(reds(text))))
mine_sets = [set(reds(t)) for _, t in mine_runs]
base_sets = [set(reds(t)) for _, t in base_runs]
mine_union, mine_core = set().union(*mine_sets), set(mine_sets[0]) & set(mine_sets[1])
base_union, base_core = set().union(*base_sets), base_sets[0] & base_sets[1]
rows.append("red_counts mine=%s base=%s" % ([len(s) for s in mine_sets], [len(s) for s in base_sets]))
rows.append("new_reds_on_my_tree_vs_base_union=" + (",".join(sorted(mine_union - base_union)) or "NONE"))
rows.append("my_core_is_inside_base_union=%s" % (mine_core <= base_union))
rows.append("mine_flip=%s" % (",".join(sorted(mine_union - mine_core)) or "NONE"))
rows.append("base_flip=%s" % (",".join(sorted(base_union - base_core)) or "NONE"))
rows.append("shared_reds:")
rows += ["  " + x for x in sorted(mine_union & base_union)]
rows.append("")

rows.append("== the mutation proof ==")
rows += ["  " + l for l in ev("r3_mutation.txt").splitlines() if l.strip()]
rows.append("")
rows.append("== control for the one arm that flipped red only inside my second full run ==")
rows.append("ord197 arm alone on this tree: " + last(ev("r3_ord197_alone_mine.txt"), r"\d+ passed|\d+ failed"))
rows.append("the same arm alone at the untouched tip: " + last(ev("r3_ord197_alone_base.txt"), r"\d+ passed|\d+ failed"))
rows.append("it is not in my stable core either, so no claim is made in either direction for it")

io.open(WT + EV + "READINGS_r3.txt", "w", encoding="utf-8", newline="\n").write("\n".join(rows) + "\n")
sys.stdout.write("\n".join(rows) + "\n")
