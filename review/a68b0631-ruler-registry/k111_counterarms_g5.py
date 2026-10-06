"""Counter-arms for the widened boundary: each mutant must make exactly one named arm go red,
and the tree must come back byte-identical.

Restores from in-memory originals (never `git checkout`, which would also drop the hand), and
compares sha256 after every restore before allowing the next mutant.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0447_wt/"
GUARD = "backend/tests/test_qoder_a68b0631_comment_anchor_drift_r1.py"
SCHEMA = "backend/db/schema.sql"
PYV = "D:/moodle/CityNexus/.venv/Scripts/python.exe"

PATHS = [GUARD, SCHEMA, "frontend/review/line_anchor_drift/CONVERTED_r1.txt"]
ORIG = {p: io.open(WT + p, encoding="utf-8", newline="").read() for p in PATHS}
ORIG_SHA = {p: hashlib.sha256(ORIG[p].encode("utf-8")).hexdigest() for p in PATHS}


def restore():
    for p in PATHS:
        io.open(WT + p, "w", encoding="utf-8", newline="").write(ORIG[p])
    for p in PATHS:
        now = hashlib.sha256(io.open(WT + p, encoding="utf-8", newline="").read().encode("utf-8")).hexdigest()
        assert now == ORIG_SHA[p], "restore did not return %s byte-for-byte (%s vs %s)" % (p, now[:12], ORIG_SHA[p][:12])


def write(path, text):
    io.open(WT + path, "w", encoding="utf-8", newline="").write(text)


def run_guard():
    r = subprocess.run([PYV, "-m", "pytest", GUARD, "-p", "no:cacheprovider", "--no-header", "-q",
                        "--tb=no", "-rA"], cwd=WT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    verdicts = {}
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in ("PASSED", "FAILED"):
            node = parts[1].replace("\\", "/")
            if node.startswith(GUARD):
                verdicts[node.split("::")[-1].split("[")[0]] = parts[0]
    assert verdicts, ("parsed no arm out of a pytest run that exited %d:\n%s" % (r.returncode, r.stdout[-600:]))
    return verdicts, r


ARMS = ["test_G1_unnumbered_citations_stay_unnumbered",
        "test_G2_no_dead_line_citation_survives_in_the_shipped_tree",
        "test_G3_no_shipped_comment_carries_a_line_number_anywhere",
        "test_G4_generated_copy_is_not_staler_than_the_source_it_came_from",
        "test_G5_the_scan_boundary_is_a_statement_not_a_habit"]

MUTANTS = {}

# M6: the old allow-list was blind to backend/db -- put a number back into a schema comment.
# If the widening is real, G3 bites.  If G3 stays green, the scan is still blind.
def m6():
    t = ORIG[SCHEMA]
    assert "`generate_replan` in `backend/app/main.py` and" in t
    write(SCHEMA, t.replace("`generate_replan` in `backend/app/main.py` and",
                           "`backend/app/main.py:12638` and", 1))
MUTANTS["M6_number_back_in_sql"] = m6

# M7: remove the SQL comment branch.  A .sql citation then reads as a clean file -- the exact
# one-directional blindness the order is about.
def m7():
    t = ORIG[GUARD]
    block = """    if rel.endswith(".sql"):
        # `--` is the only comment form here, and a file of this extension is otherwise DDL: every
        # prose line in it starts with the marker.  Without this branch the ruler reads a .sql file
        # and reports nothing from it, which is a silent blind spot rather than a clean file.
        return {i for i, line in enumerate(text.split("\\n"), start=1)
                if line.lstrip().startswith("--")}
"""
    assert block in t, "the SQL branch is not where this mutant expects it"
    g = t.replace(block, "", 1)
    # with the branch gone, G3 sees no comment region at all in a .sql, so plant the number too
    write(GUARD, g)
    s = ORIG[SCHEMA].replace("`generate_replan` in `backend/app/main.py` and",
                             "`backend/app/main.py:12638` and", 1)
    write(SCHEMA, s)
MUTANTS["M7_sql_branch_deleted_with_number"] = m7

# M8: an FROZEN entry that bites nothing -- the boundary term as rumour.
def m8():
    t = ORIG[GUARD]
    anchor = '    ("evals/", "evaluation fixtures"),'
    assert anchor in t
    write(GUARD, t.replace(anchor, anchor + '\n    ("no_such_zone/", "a boundary term with no files"),', 1))
MUTANTS["M8_frozen_entry_bites_nothing"] = m8

# M9: drop an FROZEN entry that does bite -- its files then belong to nobody, and G5 check (a)
# must name them rather than let them fall between the sets.
def m9():
    t = ORIG[GUARD]
    anchor = '    ("reports/", "generated report dumps"),'
    assert anchor in t
    write(GUARD, t.replace(anchor, "", 1))
MUTANTS["M9_frozen_entry_dropped"] = m9

# M10: register a file that lives in the frozen zone.  This one really does carry a numbered
# citation today (reports/ROADPREP_ACCEPTANCE_FEEDBACK_20260918.md), so if G1's registry and G3's
# range were allowed to describe different trees, the registry would be claiming to have converted
# a sentence that was never touched.
def m10():
    reg = ORIG["frontend/review/line_anchor_drift/CONVERTED_r1.txt"]
    write("frontend/review/line_anchor_drift/CONVERTED_r1.txt",
          reg + "reports/ROADPREP_ACCEPTANCE_FEEDBACK_20260918.md\t"
                "registry entry naming a file the scan range excludes\n")
MUTANTS["M10_registry_names_a_frozen_file"] = m10


def main():
    baseline, _ = run_guard()
    print("baseline: " + json.dumps(baseline, sort_keys=True))
    assert all(baseline.get(a) == "PASSED" for a in ARMS), "arms were not green before the mutants"

    results = {}
    for name, apply_mutant in MUTANTS.items():
        try:
            apply_mutant()
            v, r = run_guard()
            red = sorted(a for a in ARMS if v.get(a) == "FAILED")
            green = sorted(a for a in ARMS if v.get(a) == "PASSED")
            results[name] = {"red": red, "green": green, "collected_arms": len(v)}
        finally:
            restore()
        # a mutant that makes no arm go red, or that is reported as zero arms, measured nothing
        assert len(v) == len(ARMS), "%s: only %d arms reported, the run did not reach all five" % (name, len(v))
        assert red, "%s: no arm went red -- the guard does not bite this mutant" % name
        print("%-38s red=%s green=%s" % (name, [x.split("_")[1] for x in red], [x.split("_")[1] for x in green]))

    v, _ = run_guard()
    assert all(v.get(a) == "PASSED" for a in ARMS), "the restored tree is not green: %s" % v
    print("\nrestored: " + json.dumps(v, sort_keys=True))
    out = WT + "../_qoder_rel_ord0447_wk/k111_counterarms_g5.json"
    io.open(out, "w", encoding="utf-8").write(json.dumps(
        {"baseline": baseline, "mutants": results, "restored": v}, indent=2, ensure_ascii=False))
    print("wrote " + os.path.normpath(out))


if __name__ == "__main__":
    sys.exit(main())
