"""ORD-0461 r2: the mutation proof the commander asked for -- remove one check, the matching arm must go red.

Four mutants, one per named refusal.  Each one replaces exactly the guard that raises that name with a
dead predicate, runs only the arms that assert that name, and then puts the file back byte for byte --
the restore is verified by blob, not by trust.  A mutant that still leaves its arm green would mean the
arm does not read the server's decision, so this script is the non-vacuity proof of the counterexamples.
"""
import io
import json
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0461_wt"
MAIN = WT + "/backend/app/main.py"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
OUT = "D:/moodle/_qoder_rel_ord0461_wk/r3g_mutation_r1.txt"

MUTANTS = [
    {
        "name": "MEMBER_JOURNEY_RECYCLED",
        "anchor": "    if journey.deleted_at is not None:\n        # 409 and not 404 for the same reason",
        "replace": "    if False:\n        # 409 and not 404 for the same reason",
        "arms": "test_a_journey_in_the_recycle_bin_takes_neither_member_write_on_either_door",
    },
    {
        "name": "MEMBER_ACTOR_NOT_A_MEMBER",
        "anchor": '    if actor is None or not _member_is_in_force(\n        session, journey_id, (actor_traveler_id or "").strip(), datetime.now(timezone.utc)\n    ):',
        "replace": "    if False:",
        "arms": "test_an_actor_that_is_not_in_the_member_set_is_refused_by_name_on_both_doors or test_a_membership_that_is_no_longer_in_force_gives_its_holder_no_voice",
    },
    {
        "name": "MEMBER_ACTOR_NOT_PERMITTED",
        "anchor": "    if granted is None:",
        "replace": "    if False:",
        "arms": "test_a_role_the_capability_table_does_not_grant_is_refused_by_name or test_the_permission_answer_is_read_off_the_acl_table_and_not_a_role_list",
    },
    {
        "name": "MEMBER_UNKNOWN",
        "anchor": "    if member is None or member.journey_id != journey.id:",
        "replace": "    if False:",
        "arms": "test_an_id_that_is_not_a_member_of_this_journey_is_refused_by_name_on_both_doors",
    },
]


def blob_of(path):
    return subprocess.run(["git", "-C", WT, "hash-object", path], capture_output=True,
                          text=True).stdout.strip()


def committed_blob():
    return subprocess.run(["git", "-C", WT, "rev-parse", "HEAD:backend/app/main.py"],
                          capture_output=True, text=True).stdout.strip()


original = io.open(MAIN, encoding="utf-8", newline="").read()
start_blob = blob_of(MAIN)
print("main_py_head=%s" % committed_blob())
print("main_py_before_mutants=%s matches_the_commit=%s" % (start_blob, start_blob == committed_blob()))

results = []
for mutant in MUTANTS:
    count = original.count(mutant["anchor"])
    assert count == 1, "%s: anchor matched %d times, not the one guard" % (mutant["name"], count)
    io.open(MAIN, "w", encoding="utf-8", newline="").write(
        original.replace(mutant["anchor"], mutant["replace"]))
    mutated_blob = blob_of(MAIN)
    run = subprocess.run([PY, "-m", "pytest", "-q", "-rf", "--tb=no",
                          "backend/tests/test_qoder_ord0461_member_write_doors_r2.py",
                          "-k", mutant["arms"].replace(" or ", " or ")],
                         cwd=WT, capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    last = [l.strip() for l in run.stdout.splitlines() if " passed" in l or " failed" in l]
    io.open(MAIN, "w", encoding="utf-8", newline="").write(original)
    restored = blob_of(MAIN)
    results.append({
        "code": mutant["name"],
        "arm_filter": mutant["arms"],
        "summary": last[-1] if last else "NO_SUMMARY",
        "mutated_blob_differs": mutated_blob != start_blob,
        "restored_byte_identical": restored == start_blob,
        "exit": run.returncode,
    })
    print("%s -> %s (exit=%d, mutated=%s, restored_identical=%s)"
          % (mutant["name"], results[-1]["summary"], run.returncode,
             results[-1]["mutated_blob_differs"], results[-1]["restored_byte_identical"]))

all_went_red = all(int(r["summary"].split(" failed")[0]) > 0 for r in results)
all_restored = all(r["restored_byte_identical"] for r in results)
print("every_mutant_made_its_arm_red=%s" % all_went_red)
print("file_restored_after_every_mutant=%s final_blob=%s" % (all_restored, blob_of(MAIN)))
io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(
    {"head": committed_blob(), "before": start_blob, "results": results,
     "every_mutant_made_its_arm_red": all_went_red,
     "file_restored_after_every_mutant": all_restored}, ensure_ascii=False, indent=2) + "\n")
