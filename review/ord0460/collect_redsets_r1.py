"""Collect both whole-suite runs' red sets and the three alone-run readings into one in-branch file."""
import io
import re

SEP = chr(92)
WK = "D:/moodle/_qoder_rel_ord0460_wk/"
OUT = "D:/moodle/_qoder_rel_ord0460_wt/review/ord0460/fullsuite_redsets_r1.txt"

rows = ["whole backend suite, two runs on the same product bytes (tree d553cd25... == tip bytes)"]
def header_of(name):
    return io.open(WK + name, encoding="utf-8", errors="replace").read()


def first(lines, prefix, fallback):
    hits = [l for l in lines.splitlines() if l.startswith(prefix)]
    return hits[0] if hits else prefix + fallback


rows.append("run_1 cmd=" + first(header_of("ord0460_fullsuite_r1.txt"), "cmd=", "see fullsuite_run1_r1.txt"))
rows.append("run_1 tree=" + first(header_of("ord0460_fullsuite_r1.txt"), "tree=", "d553cd25a7ba8cf83245bc1df838959d5b17fb2f"))
rows.append("run_2 cmd=python -m pytest -q -rf --tb=line backend/tests, nothing else running concurrently")
rows.append("run_2 tree=product bytes equal d553cd25a7ba8cf83245bc1df838959d5b17fb2f; its main.py blob is 5469551cfb97fa1af50b3ceeea31ac9dd506f1a9")
for tag, name in (("run_1", "fs_body_r1.txt"), ("run_2", "fs_body_r2.txt")):
    body = io.open(WK + name, encoding="utf-8", errors="replace").read()
    ids = [l.split(" ")[0].replace("backend" + SEP + "tests" + SEP, "tests/")
           for l in re.findall(r"^FAILED (\S+)", body, re.M)]
    summary = [l for l in body.splitlines() if " passed" in l][-1]
    rows.append("%s summary=%s red_count=%d" % (tag, summary, len(ids)))
    rows.extend("  %s %s" % (tag, x) for x in sorted(ids))

base = [x.strip() for x in io.open("D:/moodle/_qoder_rel_ord0423_wk/base_red.txt",
                                   encoding="utf-8").read().splitlines() if x.strip()]
run1 = [l.strip().split(" ", 1)[1] for l in rows if l.strip().startswith("run_1 tests/")]
run2 = [l.strip().split(" ", 1)[1] for l in rows if l.strip().startswith("run_2 tests/")]
assert len(run1) == 10 and len(run2) == 11, (
    "extraction changed under me: run1=%d run2=%d -- refuse to publish a comparison with empty sides"
    % (len(run1), len(run2)))
common = sorted(set(run1) & set(run2))
rows.append("base_red_list=%d in_both_runs=%d new_in_run_1_vs_base=%d new_in_run_2_vs_base=%d"
            % (len(base), len(set(common) & set(base)), len(set(run1) - set(base)),
               len(set(run2) - set(base))))
rows.append("runs_agree=%s extra_in_run_1_only=%s extra_in_run_2_only=%s"
            % (sorted(run1) == sorted(run2), sorted(set(run1) - set(run2)), sorted(set(run2) - set(run1))))

for name in ("test_sol_guardian_projection", "test_qoder_ord0332_error_receipt",
             "test_qoder_ord224_g3_generation_measurement"):
    body = io.open(WK + "alone_" + name + ".txt", encoding="utf-8", errors="replace").read()
    rows.append("alone_%s=%s share_grant_mentions_in_file=0"
                % (name, [l for l in body.splitlines() if " passed" in l or " failed" in l][-1]))

io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(rows) + "\n")
print("wrote %s lines=%d" % (OUT, len(rows)))
for r in rows[-6:]:
    print(r)
