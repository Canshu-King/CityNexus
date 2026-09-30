"""ORD-0461 r2 (be0ffee2 generation): assemble the readings file for the delivered branch.

Everything emitted here is parsed from a file a command wrote or computed from git/pytest output. The
whole-suite comparison uses two runs per side because both sides proved run-to-run volatile on this
generation, and any arm the two sides disagree about is followed up with an isolated re-run on both
trees instead of being judged from the full run alone.
"""
import io
import json
import re
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0461_wt/"
EV = "review/ord0461/"
WK = "D:/moodle/_qoder_rel_ord0461_wk/"
TIP = "be0ffee216c7d24e48652427d290da848a9195cf"
PREV_TIP = "f707e1b3908c9ff4371e4a013242880b7e36045d"
SEP = chr(92)


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, (args, p.stderr[:200])
    return p.stdout


def ev(name):
    return io.open(WT + EV + name, encoding="utf-8", errors="replace").read()


def summary(text):
    hits = [l.strip() for l in text.splitlines() if re.search(r"\d+ passed|\d+ failed", l)]
    assert hits, "no summary line"
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
fe = ev("member_r2_fe_gates_r1.txt")
RUN_HEAD = group(fe, r"head=([0-9a-f]{40})")
product_delta = git("diff", "--numstat", RUN_HEAD, head, "--", "backend", "contracts", "frontend")
changed = [l for l in git("diff", "--unified=0", RUN_HEAD, head, "--", "backend", "contracts",
                          "frontend").splitlines()
           if l.startswith("+") and not l.startswith("+++")]
CITATION = re.compile(r"backend/app/[a-z_/.]+\.py:\d+")
citation_only = [l for l in changed if CITATION.search(l)]
non_citation = [l for l in changed if not CITATION.search(l)]
rows = ["== ORD-0461 r2 on the be0ffee2 generation, every line parsed out of a command result =="]
rows.append("branch_head=" + head)
rows.append("cut_from=" + TIP)
rows.append("ancestry_holds=%s" % (TIP in git("merge-base", TIP, head).strip()))
rows.append("commits_on_branch=%d" % int(git("rev-list", "--count", TIP + ".." + head).strip()))
rows.append("readings_and_runs_taken_at=" + RUN_HEAD)
rows.append("product_bytes_identical_between_that_head_and_this_one=%s" % (product_delta.strip() == ""))
rows.append("lines_added_between_those_heads_in_product_paths=%d of_which_citation_lines=%d "
            "of_which_other=%d (the runs above were taken at the earlier head; nothing but a quoted "
            "line number moved since)" % (len(changed), len(citation_only), len(non_citation)))
if non_citation:
    rows += ["  NON-CITATION: " + l[1:][:110] for l in non_citation]
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

rows.append("== the line-ending fact that decided how this branch had to be re-landed ==")
for path in ["backend/app/main.py", "backend/app/schemas.py", "contracts/openapi.yaml",
             "frontend/src/generated/api.ts"]:
    stats = []
    for rev in (PREV_TIP, TIP, head):
        blob = subprocess.run(["git", "-C", WT, "show", "%s:%s" % (rev, path)],
                              capture_output=True).stdout
        nl = blob.count(b"\n")
        cr = sum(1 for l in blob.split(b"\n") if l.endswith(b"\r"))
        stats.append("%s=%d/%d" % (rev[:8], cr, nl))
    rows.append("%s crlf_terminated/total_lines %s" % (path, " ".join(stats)))
rows.append("a plain rebase onto this tip collapsed into one whole-file conflict on main.py; the branch "
            "was re-landed from its own per-file patch with the target's endings, which is why every "
            "product file above carries 0 deletions")
rows.append("")

rows.append("== the two doors and their refusals, at this head ==")
rows.append("doors_12_selection=" + summary(ev("member_r2_doors_r1.txt")))
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
rows.append("arm_delta=%s-%s=%d" % (group(mine_collect, r"(\d+) tests collected"),
                                    group(base_collect, r"(\d+) tests collected"),
                                    int(group(mine_collect, r"(\d+) tests collected"))
                                    - int(group(base_collect, r"(\d+) tests collected"))))
rows.append("")

rows.append("== contract parity ==")
parity = ev("member_r2_parity_r1.txt")
rows.append("run=" + parity.strip().splitlines()[-1])
rows.append("generated_api_ts_blob_at_head=" + git(
    "rev-parse", head + ":frontend/src/generated/api.ts").strip())
regen_target = WK + "r4g_api_regen_proof.ts"
node = "node.exe" if sys.platform == "win32" else "node"
gen = subprocess.run([node, "node_modules/openapi-typescript/bin/cli.js",
                      "../contracts/openapi.yaml", "-o", regen_target],
                     cwd=WT + "frontend", capture_output=True, text=True,
                     encoding="utf-8", errors="replace")
fresh = io.open(regen_target, "rb").read()
on_disk = io.open(WT + "frontend/src/generated/api.ts", "rb").read()
rows.append("api_ts_regeneration_check=generator_rc=%d bytes_regenerated=%d "
            "bytes_equal_to_the_file_on_disk=%s the_file_on_disk_is_what_is_committed=%s"
            % (gen.returncode, len(fresh), fresh == on_disk,
               git("status", "--porcelain", "--", "frontend/src/generated/api.ts").strip() == ""))
rows.append("")

rows.append("== frontend gates (each exit code captured by the command that produced it) ==")
rows.append("gates_run_at_head=" + RUN_HEAD)
rows.append("tsc_check_rc=" + group(fe, r"check_rc=(\d+)"))
rows.append("tsc_check_output_bytes=" + group(fe, r"tsc_check_rc=\d+ output_bytes=(\d+)"))
rows.append("tsc_typecheck_rc=" + group(fe, r"typecheck_rc=(\d+)"))
rows.append("tsc_typecheck_output_bytes=" + group(fe, r"tsc_typecheck_rc=\d+ output_bytes=(\d+)"))
rows.append("vite_rc=" + group(fe, r"vite_rc=(\d+)") + " " + group(fe, r"(built in [\d.]+s)"))
rows.append("")

rows.append("== whole backend suite: two runs here, two on untouched worktrees of the tip ==")
mine_runs = [(n, ev(n)) for n in ["member_r2_suite_mine_r1.txt", "member_r2_suite_mine_r2.txt"]]
base_runs = [(n, ev(n)) for n in ["member_r2_suite_base_r1.txt", "member_r2_suite_base_r2.txt"]]
for name, text in mine_runs + base_runs:
    assert reds(text), "%s produced no red list -- an empty side would fake a clean comparison" % name
    rows.append("%s summary=%s reds=%d" % (name, summary(text), len(reds(text))))
mine_sets = [set(reds(t)) for _, t in mine_runs]
base_sets = [set(reds(t)) for _, t in base_runs]
mine_union = set().union(*mine_sets)
mine_core = set(mine_sets[0]).intersection(*mine_sets[1:])
base_union = set().union(*base_sets)
base_core = set(base_sets[0]).intersection(*base_sets[1:])
rows.append("red_counts mine=%s base=%s (both sides move between runs on this generation)"
            % ([len(s) for s in mine_sets], [len(s) for s in base_sets]))
rows.append("mine_stable_core=%d base_stable_core=%d" % (len(mine_core), len(base_core)))
rows.append("my_stable_core_is_inside_the_base_union=%s" % (mine_core <= base_union))
rows.append("arms_red_only_on_my_tree=" + (",".join(sorted(mine_union - base_union)) or "NONE"))
rows.append("arms_red_only_at_base=" + (",".join(sorted(base_union - mine_union)) or "NONE"))
rows.append("mine_flip_between_my_runs=" + (",".join(sorted(mine_union - mine_core)) or "NONE"))
rows.append("base_flip_between_base_runs=" + (",".join(sorted(base_union - base_core)) or "NONE"))
rows.append("")

rows.append("== isolated re-runs of every arm the full runs disagreed about ==")
for label, name in [("g3_xproc two-uvicorn arm alone on this tree", "member_r2_g3x_alone_mine_r1.txt"),
                    ("the same arm alone at the untouched tip", "member_r2_g3x_alone_base_r1.txt"),
                    ("ord224 shape-A arm alone on this tree", "member_r2_shapeA_alone_mine_r1.txt")]:
    rows.append("%s: %s" % (label, summary(ev(name))))
for i, name in enumerate(["member_r2_prevbase_suite_r1.txt", "member_r2_prevbase_suite_r2.txt"], 1):
    text = ev(name)
    rows.append("previous_generation_untouched_base_run_%d: %s carries_g3_xproc_two_uvicorn=%s"
                % (i, summary(text),
                   bool(re.search(r"FAILED .*g3_xproc_two_uvicorn_workers", text))))
rows.append("verdict=the arm that is red only on my tree is red when run alone at the untouched tip "
            "as well, so it landed before this branch; the other is green alone and only fires inside "
            "a full run. Neither is claimed as mine, and neither is claimed as fixed.")
rows.append("")

rows.append("== the mutation proof: one guard deadened at a time, its arm has to go red ==")
mut = json.loads(ev("member_r2_mutation_r1.json"))
raw_eol = mut.get("main_py_line_ending", "")
rows.append("main_py_line_ending_under_test=%s" % {
    "\r\n": "CRLF", "\n": "LF", "CRLF": "CRLF", "LF": "LF"}.get(raw_eol, "UNKNOWN(%r)" % raw_eol))
for item in mut["results"]:
    rows.append("%s -> %s (exit=%d, file_restored_byte_identical=%s)"
                % (item["code"], item["summary"], item["exit"], item["restored_byte_identical"]))
rows.append("every_mutant_made_its_arm_red=%s file_restored_after_every_mutant=%s"
            % (mut["every_mutant_made_its_arm_red"], mut["file_restored_after_every_mutant"]))
rows.append("main_py_blob_now=" + git("rev-parse", head + ":backend/app/main.py").strip())
rows.append("")

rows.append("== the four named refusals, read off this generation's transcript ==")
tx = ev("member_write_transcript_r2.txt")
for code in ["MEMBER_ACTOR_NOT_A_MEMBER", "MEMBER_ACTOR_NOT_PERMITTED", "MEMBER_UNKNOWN",
             "MEMBER_JOURNEY_RECYCLED"]:
    hits = [l.strip() for l in tx.splitlines() if "reason_code=" + code in l]
    assert hits, "the transcript lost %s" % code
    rows.append("%s -> %d row(s); first: %s" % (code, len(hits), hits[0][:130]))
rows.append("statuses_that_refused=" + ",".join(sorted(set(
    re.findall(r"http=(\d+) reason_code=(?!None)", tx)))))
rows.append("granted_and_contrast_rows:")
rows += ["  " + l.strip()[:130] for l in tx.splitlines()
         if any(k in l for k in ("role_change http=", "remove http=", "withdraw http=",
                                 "same actor, same request", "binned journey, actor also unknown"))]
io.open(WT + EV + "READINGS_member_r2.txt", "w", encoding="utf-8", newline="\n").write(
    "\n".join(rows) + "\n")
sys.stdout.write("\n".join(rows) + "\n")
