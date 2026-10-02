"""ORD-0500 rebase assistance, second cut -- the lane moved from r6 to r7 and the line moved to day23,
so every coordinate here is taken from `git ls-remote` inside this run and written into the receipts.

Why a new file instead of reusing `o500_r6_rebase_preview_r2.py`: that one still names r6 as the operand.
An assistance reading is only worth anything if a reader can tell which two commits it talked about, so
this one keeps r6 as an explicitly-labelled comparison row and puts r7 in the seat.

Three readings, same set of shas, all derived:
  1. `git merge-tree --write-tree <tip> <candidate>` -- exit code, predicted tree, conflicted paths;
  2. per write-set path (write set measured against `git merge-base`, because the tip's own new files are
     not this branch's writes): does the merged blob equal the lane's blob;
  3. for paths the merge does NOT carry byte-equal: conflict-marker count in the predicted tree, and
     whether the lane's changed line ranges overlap any of the tip's ranges;
  4. landing scope: `git diff-tree` between the tip's own tree and the predicted tree, split into product
     paths and the lane's own `review/**` evidence -- that is what a merge would actually put on the line.

The conflict list is parsed from `--write-tree`'s stage rows (`<mode> <blob> <stage>\t<path>`), not from
the informational messages; a non-zero exit with an empty parsed list aborts the run rather than printing
"no conflicts", because a silently-blind conflict parser is the worse failure.

Read-only contract: 0 ref writes, 0 pushes, 0 checkouts, 0 writes outside the two receipt paths,
0 processes started, and no other lane's worktree opened.
"""
import io
import json
import re
import subprocess
import sys
import time

REPO = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
CAND_REFS = {
    "r6": "refs/heads/review/newlane-ord0500-phone-checkin-entry-r6",
    "r7": "refs/heads/review/newlane-ord0500-phone-checkin-entry-r7",
}
EVIDENCE = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/ord0500-r6-rebase-preview/receipts"
OUT_PREVIEW = "%s/o500_r7_rebase_preview_r1.json" % EVIDENCE
OUT_CARRY = "%s/o500_r7_byte_carry_r1.json" % EVIDENCE
OUT_REGION = "%s/o500_r7_region_check_r1.json" % EVIDENCE


def git(*args):
    result = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    return result.returncode, result.stdout, result.stderr


def head_of(ref):
    rc, out, err = git("ls-remote", "--refs", "origin", ref)
    for line in out.splitlines():
        sha, name = line.split("\t", 1)
        if name.strip() == ref:
            return sha
    raise AssertionError("REF_NOT_READABLE %s :: %s" % (ref, (err or out).strip()[:160]))


def ranges(from_ref, to_ref, path):
    rc, out, _err = git("diff", "--unified=0", from_ref, to_ref, "--", path)
    found = []
    for line in out.splitlines():
        match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if match:
            start = int(match.group(2))
            length = int(match.group(3) or "1")
            found.append([start, start + max(1, length) - 1])
    return found


def overlaps(a, b):
    return [[x, y] for x in a for y in b if not (x[1] < y[0] or y[1] < x[0])]


def tree_of(sha):
    rc, out, _err = git("rev-parse", "%s^{tree}" % sha)
    return out.strip() if rc == 0 else None


def is_evidence(path):
    return path.startswith("review/") or "/review/" in path or path.startswith("frontend/review/")


def predict(tip, cand):
    rc, base, _ = git("merge-base", tip, cand)
    base = base.strip()
    rc, out, err = git("merge-tree", "--write-tree", tip, cand)
    lines = out.splitlines()
    # `--write-tree` prints: tree OID, then one stage row per conflicted entry
    # ("<mode> <blob> <stage>\t<path>"), then a blank line, then informational messages.
    tree = lines[0].strip() if lines and re.match(r"^[0-9a-f]{40}$", lines[0].strip()) else None
    stages = {}
    for line in lines[1:]:
        match = re.match(r"^\d{6} ([0-9a-f]{40}) ([123])\t(.+)$", line)
        if match:
            stages.setdefault(match.group(3).strip(), []).append(match.group(2))
    conflicted = sorted(stages)
    stage_counts = {}
    for path, seen in stages.items():
        for s in seen:
            stage_counts[s] = stage_counts.get(s, 0) + 1
    messages = [l for l in lines if "CONFLICT (" in l]

    rc2, names, _ = git("diff", "--name-only", base, cand)
    paths = [n for n in names.splitlines() if n.strip()]
    rows = []
    for path in paths:
        cand_blob = git("rev-parse", "%s:%s" % (cand, path))[1].strip()
        tip_blob = git("rev-parse", "%s:%s" % (tip, path))[1].strip() if git(
            "cat-file", "-e", "%s:%s" % (tip, path))[0] == 0 else None
        merged_blob = git("rev-parse", "%s:%s" % (tree, path))[1].strip() if tree else None
        rows.append({"path": path, "candidate_blob": cand_blob, "tip_blob": tip_blob,
                     "merged_blob": merged_blob,
                     "merged_equals_candidate": merged_blob == cand_blob,
                     "merged_equals_tip": merged_blob == tip_blob,
                     "in_conflict_list": path in conflicted})
    not_carried = sorted(r["path"] for r in rows if not r["merged_equals_candidate"])

    # What the merge would actually put on top of the tip: predicted tree vs the tip's tree.
    scope_rows = []
    if tree:
        _rc, scope_names, _e = git("diff-tree", "-r", "--no-commit-id", "--name-only",
                                   tree_of(tip), tree)
        for path in [n for n in scope_names.splitlines() if n.strip()]:
            merged_blob = git("rev-parse", "%s:%s" % (tree, path))[1].strip()
            tip_blob = git("rev-parse", "%s:%s" % (tip, path))[1].strip() if git(
                "cat-file", "-e", "%s:%s" % (tip, path))[0] == 0 else None
            cand_blob = git("rev-parse", "%s:%s" % (cand, path))[1].strip() if git(
                "cat-file", "-e", "%s:%s" % (cand, path))[0] == 0 else None
            blob = git("show", "%s:%s" % (tree, path))[1]
            markers = len([l for l in blob.split("\n") if l.startswith("<<<<<<<")
                           or l.startswith(">>>>>>>") or l.startswith("=======")])
            scope_rows.append({"path": path, "merged_blob": merged_blob, "tip_blob": tip_blob,
                               "candidate_blob": cand_blob, "conflict_markers": markers,
                               "is_evidence": is_evidence(path),
                               "merged_equals_candidate": merged_blob == cand_blob})

    marker_paths = sorted(r["path"] for r in scope_rows if r["conflict_markers"] > 0)
    region = {}
    for path in sorted(set(marker_paths) | set(p for p in not_carried if p in paths)):
        blob = git("show", "%s:%s" % (tree, path))[1] if tree else ""
        markers = len([l for l in blob.split("\n") if l.startswith("<<<<<<<")
                       or l.startswith(">>>>>>>") or l.startswith("=======")])
        lane = ranges(base, cand, path)
        tipside = ranges(base, tip, path)
        region[path] = {"conflict_markers_in_predicted_tree": markers,
                        "lane_regions": lane, "tip_regions": tipside,
                        "tip_region_count": len(tipside),
                        "overlapping_region_pairs": overlaps(lane, tipside)}
    product_scope = sorted(r["path"] for r in scope_rows if not r["is_evidence"])
    return {
        "fork_point": base,
        "fork_point_is_ancestor_of_tip": git("merge-base", "--is-ancestor", base, tip)[0] == 0,
        "merge_tree_exit": rc,
        "predicted_tree": tree,
        "conflicted_paths": conflicted,
        "conflicted_path_count": len(conflicted),
        "conflict_stage_counts": stage_counts,
        "conflict_message_count": len(messages),
        "conflicted_product_paths": sorted(p for p in conflicted if not is_evidence(p)),
        "conflict_marker_total": sum(r["conflict_markers"] for r in scope_rows),
        "landing_scope_path_count": len(scope_rows),
        "landing_scope_product_paths": product_scope,
        "landing_scope_evidence_paths": sorted(r["path"] for r in scope_rows if r["is_evidence"]),
        "landing_scope_product_carries_lane_blob": len([r for r in scope_rows
                                                       if not r["is_evidence"]
                                                       and r["merged_equals_candidate"]]),
        "candidate_is_ancestor_of_tip": git("merge-base", "--is-ancestor", cand, tip)[0] == 0,
        "tip_is_ancestor_of_candidate": git("merge-base", "--is-ancestor", tip, cand)[0] == 0,
        "tip_commits_behind_candidate": git("rev-list", "--count", "%s..%s" % (tip, cand))[1].strip(),
        "candidate_commits_behind_tip": git("rev-list", "--count", "%s..%s" % (cand, tip))[1].strip(),
        "predicted_tree_equals_candidate_tree": tree == tree_of(cand),
        "predicted_tree_equals_tip_tree": tree == tree_of(tip),
        "write_set": len(rows),
        "carried": len(rows) - len(not_carried),
        "not_carried": not_carried,
        "rows": rows,
        "scope_rows": scope_rows,
        "region": region,
        "stderr_head": err.strip()[:200],
    }


def main():
    tip = head_of(TIP_REF)
    heads = {}
    for label, ref in CAND_REFS.items():
        sha = head_of(ref)
        heads[label] = {"ref": ref, "sha": sha,
                        "subject": git("log", "-1", "--format=%s", sha)[1].strip()}
        rc, _o, _e = git("cat-file", "-e", "%s^{commit}" % sha)
        if rc != 0:
            print("OBJECT_NOT_LOCAL %s %s" % (label, heads[label]["sha"]))
            return 4
    rc, _o, _e = git("cat-file", "-e", "%s^{commit}" % tip)
    if rc != 0:
        print("OBJECT_NOT_LOCAL tip %s" % tip)
        return 4

    p = {label: predict(tip, heads[label]["sha"]) for label in heads}
    r6, r7 = p["r6"], p["r7"]

    summary = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tip_ref": TIP_REF, "live_tip": tip,
        "tip_tree": tree_of(tip),
        "candidates": {k: {kk: vv for kk, vv in v.items()
                           if kk not in ("rows", "region", "scope_rows")} for k, v in p.items()},
        "candidate_heads": heads,
        "r7_is_descendant_of_r6": git("merge-base", "--is-ancestor", heads["r6"]["sha"],
                                      heads["r7"]["sha"])[0] == 0,
        "r6_commits_only_in_r7": git("rev-list", "--count", "%s..%s" % (heads["r6"]["sha"],
                                                                        heads["r7"]["sha"]))[1].strip(),
        "r7_commits_only_in_r6": git("rev-list", "--count", "%s..%s" % (heads["r7"]["sha"],
                                                                        heads["r6"]["sha"]))[1].strip(),
        "fork_point_moved_from_r6_to_r7": r6["fork_point"] != r7["fork_point"],
        "not_carried_moved_from_r6_to_r7": r6["not_carried"] != r7["not_carried"],
        "how_counted": "write set = git diff --name-only <merge-base> <candidate>; carry = rev-parse "
                       "<predicted_tree>:<path> vs <candidate>:<path>; regions = git diff --unified=0 "
                       "hunk ranges on each side against the fork point",
    }
    carry = {"live_tip": tip, "candidate": heads["r7"]["sha"], "fork_point": r7["fork_point"],
             "predicted_tree": r7["predicted_tree"], "summary": {
                 "write_set": r7["write_set"], "carries_the_lane_blob": r7["carried"],
                 "does_not_carry": len(r7["not_carried"]), "paths_not_carried": r7["not_carried"],
                 "landing_scope_paths": r7["landing_scope_path_count"],
                 "landing_scope_product_paths": len(r7["landing_scope_product_paths"]),
                 "landing_scope_evidence_paths": len(r7["landing_scope_evidence_paths"]),
                 "r6_landing_scope_paths": r6["landing_scope_path_count"],
                 "r6_landing_scope_product_paths": len(r6["landing_scope_product_paths"]),
                 "r6_conflicted_path_count": r6["conflicted_path_count"],
                 "r6_conflicted_product_paths": r6["conflicted_product_paths"],
                 "r6_product_write_set_paths": len([r for r in r6["rows"] if not is_evidence(r["path"])]),
                 "r6_product_write_set_already_byte_equal_on_tip": len(
                     [r for r in r6["rows"] if not is_evidence(r["path"])
                      and r["tip_blob"] == r["candidate_blob"]]),
                 "r6_product_write_set_still_different_from_tip": [
                     r["path"] for r in r6["rows"] if not is_evidence(r["path"])
                     and r["tip_blob"] != r["candidate_blob"]],
                 "r7_product_write_set_paths": len([r for r in r7["rows"] if not is_evidence(r["path"])]),
             },
             "product_paths_in_landing_scope": r7["landing_scope_product_paths"],
             "rows": r7["rows"], "scope_rows": r7["scope_rows"],
             "r6_product_write_set": [r for r in r6["rows"] if not is_evidence(r["path"])],
             "r7_product_write_set": [r for r in r7["rows"] if not is_evidence(r["path"])],
             "landed_parent_subject": git("log", "-1", "--format=%s", r7["fork_point"])[1].strip()}
    region = {"live_tip": tip, "candidates": {"r6": r6["region"], "r7": r7["region"]},
              "predicted_trees": {"r6": r6["predicted_tree"], "r7": r7["predicted_tree"]}}

    # A merge that exits non-zero but yields an empty conflict list is a parse failure, not a clean
    # merge -- refuse to publish a reading that would read as "no conflicts".
    for label in ("r6", "r7"):
        row = p[label]
        if row["merge_tree_exit"] not in (0, 1):
            print("UNEXPECTED_MERGE_TREE_EXIT %s exit=%s" % (label, row["merge_tree_exit"]))
            return 5
        if row["merge_tree_exit"] == 1 and row["conflicted_path_count"] == 0:
            print("CONFLICT_PARSE_BLIND %s exit=1 conflicted=0" % label)
            return 6

    for path, body in ((OUT_PREVIEW, summary), (OUT_CARRY, carry), (OUT_REGION, region)):
        with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(body, handle, indent=1, ensure_ascii=False)
        print("WROTE %s bytes=%d" % (path, len(json.dumps(body, ensure_ascii=False).encode("utf-8"))))

    print("TIP %s tip_tree %s" % (tip, tree_of(tip)))
    for label in ("r6", "r7"):
        row = p[label]
        print("%s cand=%s fork=%s fork_anc_of_tip=%s exit=%s tree=%s conflicted=%d msg=%d "
              "conflicted_product=%d markers=%d write=%d carried=%d not_carried=%d "
              "scope=%d scope_product=%d scope_evidence=%d tip_anc_cand=%s cand_anc_of_tip=%s "
              "pred_eq_cand_tree=%s pred_eq_tip_tree=%s behind_tip=%s ahead_of_tip=%s"
              % (label, heads[label]["sha"], row["fork_point"], row["fork_point_is_ancestor_of_tip"],
                 row["merge_tree_exit"], row["predicted_tree"], row["conflicted_path_count"],
                 row["conflict_message_count"], len(row["conflicted_product_paths"]),
                 row["conflict_marker_total"], row["write_set"], row["carried"],
                 len(row["not_carried"]), row["landing_scope_path_count"],
                 len(row["landing_scope_product_paths"]), len(row["landing_scope_evidence_paths"]),
                 row["tip_is_ancestor_of_candidate"], row["candidate_is_ancestor_of_tip"],
                 row["predicted_tree_equals_candidate_tree"], row["predicted_tree_equals_tip_tree"],
                 row["candidate_commits_behind_tip"], row["tip_commits_behind_candidate"]))
        print("   conflicted_paths=%s" % row["conflicted_paths"])
        for path in row["landing_scope_product_paths"]:
            v = [r for r in row["scope_rows"] if r["path"] == path][0]
            reg = row["region"].get(path, {})
            print("   PRODUCT %s merged=%s markers=%d carries_lane_blob=%s overlaps=%s"
                  % (path, v["merged_blob"][:12], v["conflict_markers"], v["merged_equals_candidate"],
                     len(reg.get("overlapping_region_pairs", []))))
    print("R6_PRODUCT_WRITE_SET paths=%d already_byte_equal_on_tip=%d still_different=%s"
          % (carry["summary"]["r6_product_write_set_paths"],
             carry["summary"]["r6_product_write_set_already_byte_equal_on_tip"],
             carry["summary"]["r6_product_write_set_still_different_from_tip"]))
    print("R7_PRODUCT_WRITE_SET paths=%d" % carry["summary"]["r7_product_write_set_paths"])
    print("LANDED_PARENT %s | %s" % (r7["fork_point"], carry["landed_parent_subject"][:140]))
    print("r7_desc_of_r6=%s only_in_r7=%s only_in_r6=%s fork_moved=%s not_carried_moved=%s"
          % (summary["r7_is_descendant_of_r6"], summary["r6_commits_only_in_r7"],
             summary["r7_commits_only_in_r6"], summary["fork_point_moved_from_r6_to_r7"],
             summary["not_carried_moved_from_r6_to_r7"]))
    print("SUBJECT_r7 %s" % heads["r7"]["subject"][:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
