"""Commander's read-only re-parent prediction onto the new authoritative tip.

Nothing here moves a ref: `merge-tree --write-tree` is the documented read-only form, and the two
candidates are fetched into local-only refs under refs/cmdr/* so no lane's branch is touched.  The
output exists so B and F (and the arbiter) do not have to take my bus sentence on faith - the four
40-hex values per candidate are recomputable by anyone with the commands named in `commands`.
"""
import datetime
import hashlib
import io
import json
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = r"D:\moodle\CityNexus"
TIP = "5aff3722d5c36c760a424f5fea5c3a771298f9ac"
OLD = "dc964086c9d412573ac19d70b24b30e6c3ee6168"
CANDS = [("ORD-0296 r3 / F", "refs/cmdr/f_r3", "fd8eaf3644b66b44c44ce3178a7babac2bf561c0", "review/ord0296-write-deadline-f-r3"),
         ("ORD-0281 gen-2 / B", "refs/cmdr/b_gen2", "64d14b205263ec03fd4810b1b0877418495b87b0", "review/0281-write-deadline-keyed-b2")]


def git(*a):
    r = subprocess.run(["git"] + list(a), cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


rows = []
for label, ref, want, branch in CANDS:
    rc, sha, _ = git("rev-parse", ref)
    _, parent, _ = git("rev-parse", ref + "^")
    _, mb, _ = git("merge-base", "refs/cmdr/tip", ref)
    mrc, mout, merr = git("merge-tree", "--write-tree", "refs/cmdr/tip", ref)
    predicted = mout.splitlines()[0] if mout else None
    conflict_section = mout.splitlines()[1:] if mrc else []
    # independent proof the prediction is a real tree object and what it differs from
    tfiles = None
    if predicted and len(predicted) == 40:
        trc, tout, _ = git("diff", "--name-only", "--no-renames", TIP, predicted)
        tfiles = [l for l in tout.splitlines() if l.strip()]
    rows.append({
        "order_and_lane": label, "ref": ref, "remote_branch": branch,
        "candidate_sha": sha, "cited_by_lane": want, "sha_matches_citation": sha == want,
        "parent": parent, "parent_equals_old_tip": parent == OLD,
        "merge_base_with_new_tip": mb, "merge_base_equals_old_tip": mb == OLD,
        "ff_only_possible_onto_new_tip": mb == OLD,
        "merge_tree_exit": mrc, "predicted_tree": predicted,
        "conflict_section_lines": len(conflict_section), "conflict_section": conflict_section[:6],
        "predicted_tree_vs_tip_files": tfiles, "predicted_tree_vs_tip_file_count": len(tfiles or []),
        "stderr": merr[:200] or None})

py = sys.executable
out = {
    "schema": "CNX_CMDR_REPARENT_PREDICTION_V1",
    "at_local": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).isoformat(timespec="seconds") + "+08",
    "tool": r"live_checks\derive_reparent_prediction_r1.py",
    "tool_sha1": hashlib.sha1(io.open(__file__, "rb").read()).hexdigest(),
    "interpreter": py,
    "repo": REPO,
    "commands": ["git rev-parse <ref>", "git rev-parse <ref>^", "git merge-base refs/cmdr/tip <ref>",
                 "git merge-tree --write-tree refs/cmdr/tip <ref>",
                 "git diff --name-only --no-renames %s <predicted_tree>" % TIP],
    "new_tip": TIP, "old_tip": OLD,
    "tip_verified_locally": git("rev-parse", "refs/cmdr/tip")[1] == TIP,
    "read_only_discipline": {"refs_pushed": 0, "authority_line_moved": 0, "worktree_written": 0,
                            "note": "candidates live only in local refs/cmdr/*; nothing was merged, checked out or pushed"},
    "per_candidate": rows,
    "scope": "This proves the merge shape only: it says the two candidates can be taken onto the new tip "
             "without conflict and which product files that would change. It does NOT certify either "
             "candidate's own gates - those belong to their lanes' re-run, and the levels to the verifier."}
io.open("_cmdr_reparent_prediction_r1.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
for r in rows:
    print(r["order_and_lane"], "| cited==measured", r["sha_matches_citation"],
          "| parent==old tip", r["parent_equals_old_tip"], "| ff-only possible", r["ff_only_possible_onto_new_tip"],
          "| merge-tree rc", r["merge_tree_exit"], "| predicted tree", r["predicted_tree"],
          "| conflicts", r["conflict_section_lines"], "| files vs tip", r["predicted_tree_vs_tip_file_count"])
print("tool sha1", out["tool_sha1"])
print("wrote _cmdr_reparent_prediction_r1.json", len(json.dumps(out)), "chars")
