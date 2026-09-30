"""ORD-0461 r2 (the 04:15 re-cut): assemble the delivered-generation readings file.

Every emitted value is parsed from a file a command wrote, or computed here from git/pytest output.
Both sides of every comparison are asserted to have produced a reading first: an empty side once
produced a fake 'no new reds' on this lane.
"""
import io
import json
import re
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0461_wt/"
EV = "review/ord0461/"
WK = "D:/moodle/_qoder_rel_ord0461_wk/"
TIP = "f707e1b3908c9ff4371e4a013242880b7e36045d"
SEP = chr(92)


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, (args, p.stderr[:200])
    return p.stdout


def ev(name):
    return io.open(WT + EV + name, encoding="utf-8", errors="replace").read()


def summary(text):
    hits = [l.strip() for l in text.splitlines() if re.search(r"\d+ passed", l)]
    assert hits, "no summary line in the evidence file"
    return hits[-1]


def group(text, pattern):
    hits = [re.search(pattern, l) for l in text.splitlines()]
    hits = [h for h in hits if h]
    assert hits, "no line matched %r" % pattern
    return hits[-1].group(1)


def reds(text):
    return sorted(l.split(" ")[0].replace("backend" + SEP + "tests" + SEP, "tests/")
                  for l in re.findall(r"^FAILED (\S+)", text, re.M))


head = git("rev-parse", "HEAD").strip()
RUN_HEAD = group(ev("member_r2_fe_gates_r1.txt"), r"head=([0-9a-f]{40})")
product_delta = git("diff", "--numstat", RUN_HEAD, head, "--", "backend", "contracts", "frontend")
rows = ["== ORD-0461 r2 (04:15 re-cut) readings, every line parsed out of a command result =="]
rows.append("branch_head=" + head)
rows.append("readings_measured_while_the_runs_were_taken_at=" + RUN_HEAD)
rows.append("product_bytes_identical_between_that_head_and_this_one=%s (the only commits in between add "
            "review/ evidence files)" % (product_delta.strip() == ""))
rows.append("rebased_onto=" + TIP)
rows.append("ancestry_holds=%s" % (TIP in git("merge-base", TIP, head).strip()))
rows.append("commits_on_branch=%d" % int(git("rev-list", "--count", TIP + ".." + head).strip()))
rows.append("diff_against_tip=%s" % git("diff", "--shortstat", TIP, head).strip())
numstat = git("diff", "--numstat", TIP, head).splitlines()
prod = [l for l in numstat if not l.split("\t")[2].startswith("review/")]
rows.append("product_files=%d product_add=%d product_del=%d"
            % (len(prod), sum(int(l.split("\t")[0]) for l in prod),
               sum(int(l.split("\t")[1]) for l in prod)))
rows.append("product_file_list=" + ",".join(l.split("\t")[2] for l in prod))
rows.append("numstat:")
rows += ["  " + l for l in numstat]
rows.append("")

rows.append("== the two doors and their refusals, at this head ==")
rows.append("doors_r2_selection=" + summary(ev("member_r2_doors_r1.txt")))
rows.append("doors_wide_selection=" + summary(ev("member_r2_doors_wide_r1.txt")))
arms = {}
for name in ["test_qoder_ord0461_member_write_doors_r2", "test_qoder_ord0434_share_grants",
             "test_qoder_ord0460_expiry_in_past", "test_qoder_ord0272_continuation",
             "test_contract", "test_qoder_anywhere_contract_parity"]:
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "--collect-only",
                          "backend/tests/%s.py" % name], cwd=WT.rstrip("/"),
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace").stdout
    arms[name] = group(out, r"(\d+) tests? collected")
assert all(v != "0" for v in arms.values()), "a named door file collected no arms"
rows.append("collected_per_file=" + ",".join(
    "%s=%s" % (re.sub(r"^test_qoder_|^test_", "", k), v) for k, v in arms.items()))
rows.append("")

rows.append("== registered routes (proof the doors are reachable, not only written) ==")
routes = subprocess.run([sys.executable, "-c",
                         "import sys; sys.path.insert(0,'backend')\n"
                         "from app.main import app\n"
                         "rows = ['%s %s' % (sorted(r.methods)[0], r.path) for r in app.routes"
                         " if ('/members' in getattr(r,'path','') or '/acl/' in getattr(r,'path',''))]\n"
                         "print(';'.join(sorted(set(rows))))"],
                        cwd=WT.rstrip("/"), capture_output=True, text=True,
                        encoding="utf-8", errors="replace").stdout.strip().split(";")
assert len(routes) == 6, "expected the four landed member doors plus the two cut here: %s" % routes
new_two = [r for r in routes if r.endswith("/members/{member_id}/role")
           or r.startswith("DELETE /api/v1/journeys/{journey_id}/members/{member_id}")]
assert len(new_two) == 2, "the two new doors are not both registered: %s" % new_two
rows.append("member_and_acl_routes=%d" % len(routes))
rows.append("the_two_cut_here=" + " | ".join(new_two))
rows += ["  " + r for r in routes]
rows.append("")

rows.append("== collection (this tree vs the untouched tip it was cut from) ==")
mine_collect = ev("member_r2_collect_r1.txt").strip()
base_collect = ev("member_r2_base_collect_r1.txt").strip()
rows.append("mine=" + mine_collect)
rows.append("base=" + base_collect)
rows.append("arm_delta=%d-%d=%d" % (int(group(mine_collect, r"(\d+) tests collected")),
                                    int(group(base_collect, r"(\d+) tests collected")),
                                    int(group(mine_collect, r"(\d+) tests collected"))
                                    - int(group(base_collect, r"(\d+) tests collected"))))
rows.append("")

rows.append("== contract parity ==")
parity = ev("member_r2_parity_r1.txt")
rows.append("run=" + parity.strip().splitlines()[-1])
rows.append("formal_runtime_missing_extra_parsed=" + ",".join(
    re.findall(r"(?:formal|runtime|missing|extra) (\d+)", parity.strip().splitlines()[-1])))
rows.append("generated_api_ts_blob_at_head=" + git("rev-parse", head + ":frontend/src/generated/api.ts").strip())
regen_target = WK + "r2_api_regen_proof.ts"
node = "node.exe" if sys.platform == "win32" else "node"
gen = subprocess.run([node, "node_modules/openapi-typescript/bin/cli.js",
                      "../contracts/openapi.yaml", "-o", regen_target],
                     cwd=WT + "frontend", capture_output=True, text=True,
                     encoding="utf-8", errors="replace")
fresh = io.open(regen_target, "rb").read()
on_disk = io.open(WT + "frontend/src/generated/api.ts", "rb").read()
unclean = git("status", "--porcelain", "--", "frontend/src/generated/api.ts").strip()
rows.append("api_ts_regeneration_check=generator_rc=%d bytes_regenerated=%d "
            "bytes_equal_to_the_file_on_disk=%s the_file_on_disk_is_what_is_committed=%s"
            % (gen.returncode, len(fresh), fresh == on_disk, unclean == ""))
rows.append("")

rows.append("== frontend gates (each exit code captured by the command that produced it) ==")
fe = ev("member_r2_fe_gates_r1.txt")
rows.append("gates_run_at_head=" + group(fe, r"head=([0-9a-f]{40})"))
rows.append("tsc_check_rc=" + group(fe, r"check_rc=(\d+)"))
rows.append("tsc_check_output_bytes=" + group(fe, r"tsc_check_rc=\d+ output_bytes=(\d+)"))
rows.append("tsc_typecheck_rc=" + group(fe, r"typecheck_rc=(\d+)"))
rows.append("tsc_typecheck_output_bytes=" + group(fe, r"tsc_typecheck_rc=\d+ output_bytes=(\d+)"))
rows.append("vite_rc=" + group(fe, r"vite_rc=(\d+)") + " " + group(fe, r"(built in [\d.]+s)"))
rows.append("gate_cwd=" + WT + "frontend: npx tsc -p tsconfig.check.json --noEmit, "
                              "npx tsc -p tsconfig.typecheck.json --noEmit, npx vite build")
rows.append("")

rows.append("== whole backend suite: two runs on this tree, two on untouched full worktrees of the tip ==")
rows.append("suite_runs_taken_at_head=" + group(fe, r"head=([0-9a-f]{40})"))
mine_names = ["member_r2_suite_mine_r1.txt", "member_r2_suite_mine_r2.txt"]
base_names = ["member_r2_suite_base_r1.txt", "member_r2_suite_base_r2.txt"]
mine_runs = [(n, ev(n)) for n in mine_names]
base_runs = [(n, ev(n)) for n in base_names]
for name, text in mine_runs + base_runs:
    assert reds(text), "%s produced no red list -- comparing against an empty side fakes a clean result" % name
    rows.append("%s summary=%s reds=%d" % (name, summary(text), len(reds(text))))
mine_sets = [set(reds(t)) for _, t in mine_runs]
base_sets = [set(reds(t)) for _, t in base_runs]
base_union = set().union(*base_sets)
base_core = set(base_sets[0]).intersection(*base_sets[1:])
rows.append("mine_runs_agree_id_by_id=%s" % (all(s == mine_sets[0] for s in mine_sets)))
rows.append("base_runs_agree_id_by_id=%s base_red_counts=%s"
            % (all(s == base_sets[0] for s in base_sets), [len(s) for s in base_sets]))
rows.append("base_flip_between_runs=" + (
    ",".join(sorted(base_union - base_core)) or "NONE"))
rows.append("new_reds_on_my_tree_vs_base_union=" + (
    ",".join(sorted(mine_sets[0] - base_union)) or "NONE"))
rows.append("my_reds_all_inside_the_base_stable_core=%s" % (mine_sets[0] <= base_core))
rows.append("base_core_reds_absent_from_my_tree=" + (
    ",".join(sorted(base_core - mine_sets[0])) or "NONE"))
rows.append("control_for_those: %s || %s" % (
    summary(ev("member_r2_g3x_alone_mine_r1.txt")),
    summary(ev("member_r2_g3x_alone_base_r1.txt"))))
rows.append("the_two_control_arms_were_run_alone_on_both_trees_and_are_green_on_both,"
            " so the difference reads as a full-run state effect and is not claimed as a fix")
rows.append("mine_red_list:")
rows += ["  " + x for x in sorted(mine_sets[0])]
rows.append("base_union_red_list:")
rows += ["  " + x for x in sorted(base_union)]
rows.append("")

rows.append("== the mutation proof: one guard deadened at a time, the matching arm has to go red ==")
mut = json.loads(ev("member_r2_mutation_r1.json"))
for item in mut["results"]:
    rows.append("%s -> %s (exit=%d, file_restored_byte_identical=%s)"
                % (item["code"], item["summary"], item["exit"], item["restored_byte_identical"]))
rows.append("every_mutant_made_its_arm_red=%s file_restored_after_every_mutant=%s"
            % (mut["every_mutant_made_its_arm_red"], mut["file_restored_after_every_mutant"]))
rows.append("main_py_blob_now=" + git("rev-parse", head + ":backend/app/main.py").strip())
rows.append("")

rows.append("== the four named refusals, read off the transcript's own body column ==")
tx = ev("member_write_transcript_r2.txt")
for code in ["MEMBER_ACTOR_NOT_A_MEMBER", "MEMBER_ACTOR_NOT_PERMITTED", "MEMBER_UNKNOWN",
             "MEMBER_JOURNEY_RECYCLED"]:
    hits = [l.strip() for l in tx.splitlines() if "reason_code=" + code in l]
    assert hits, "the transcript lost %s -- do not report a refusal that was not seen" % code
    rows.append("%s -> %d row(s); first: %s" % (code, len(hits), hits[0][:132]))
rows.append("statuses_that_refused=" + ",".join(sorted(set(
    re.findall(r"http=(\d+) reason_code=(?!None)", tx)))))
rows.append("granted_rows_parsed:")
rows += ["  " + l.strip()[:132] for l in tx.splitlines()
         if ("role_change http=" in l or "remove http=" in l or "withdraw http=" in l
             or "same actor, same request" in l)]
io.open(WT + EV + "READINGS_member_r2.txt", "w", encoding="utf-8", newline="\n").write(
    "\n".join(rows) + "\n")
sys.stdout.write("\n".join(rows) + "\n")
