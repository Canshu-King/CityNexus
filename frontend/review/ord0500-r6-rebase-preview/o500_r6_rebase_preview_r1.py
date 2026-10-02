"""ORD-0500 r6 rebase 协助 -- a read-only prediction of what that branch has to move, computed
against the live tip, so the owning lane (or the landing sequencer) can re-cut without guessing.

Why this file exists and what it refuses to do: CMDR 17:39 told `0afdb49b` to rebase
`refs/heads/review/newlane-ord0500-phone-checkin-entry-r6` onto the tip, and named the two blocking
files. Nothing here touches that branch: no checkout, no stash, no push, no write to another lane's
worktree. It is the standing rule of this fleet -- 分叉先 `git merge-tree --write-tree` 只读预测 --
run once, and printed.

Readings it produces, all from git itself:
  * the live tip, read by `ls-remote`, and whether the candidate commit resolves locally at all;
  * the fork point (`git merge-base`), because a write set measured against the tip counts other
    lanes' files as yours -- the ORD-0500 lane got bitten by exactly that and said so;
  * the merge prediction: conflicted paths, or a clean tree oid;
  * for each conflicted path: the hunks *that branch* adds over the fork point, and the hunks *the tip*
    adds over the same fork point -- which is the whole content of a rebase, in two lists;
  * a byte check: whether any of the branch's own touched paths already equals the tip's blob, i.e.
    already landed and needs no move at all.
"""
import json
import subprocess
import sys

REPO = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
CAND_REF = "refs/heads/review/newlane-ord0500-phone-checkin-entry-r6"
OUT = "D:/moodle/_qoder_e766b154_ord0528_20261001/run/o500_r6_rebase_preview_r1.json"


def git(*args, **kwargs):
    result = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                            encoding="utf-8", errors="replace", **kwargs)
    return result.returncode, result.stdout, result.stderr


def lsremote_head(ref):
    rc, out, err = git("ls-remote", "--refs", "origin", ref)
    for line in out.splitlines():
        sha, name = line.split("\t", 1)
        if name.strip() == ref:
            return sha
    return "NOT_READABLE:" + (err.strip()[:120] or out.strip()[:120] or "empty")


def hunks(base, side, path):
    """The hunk headers one side adds over the merge base -- line ranges, not content."""
    rc, out, _err = git("diff", "--unified=0", base, side, "--", path)
    return [line for line in out.splitlines() if line.startswith("@@")]


def main():
    tip = lsremote_head(TIP_REF)
    cand = lsremote_head(CAND_REF)
    report = {"live_tip": tip, "candidate": cand}
    if tip.startswith("NOT_") or cand.startswith("NOT_"):
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 2

    rc, base, _ = git("merge-base", tip, cand)
    base = base.strip()
    report["fork_point"] = base
    report["fork_point_verdict"] = git("log", "-1", "--format=%H %ad %s", "--date=iso", base)[1].strip()[:120]
    report["candidate_is_ancestor_of_tip"] = git("merge-base", "--is-ancestor", cand, tip)[0] == 0

    rc, out, err = git("merge-tree", "--write-tree", tip, cand)
    prediction = {"exit": rc, "stdout_lines": out.splitlines()[:40]}
    report["merge_tree_prediction"] = prediction
    conflicted = []
    if rc != 0:
        body = out.split("\nCONFLICT", 1)
        for line in ("CONFLICT" + body[1] if len(body) > 1 else "").splitlines():
            if "both modified" in line or "added by both" in line or "deleted by" in line:
                conflicted.append(line.split(":", 1)[-1].strip())
    else:
        report["predicted_tree"] = out.splitlines()[0] if out.strip() else "NO_OID"
    report["conflicted_paths"] = sorted(set(conflicted))

    # the branch's own write set, measured against the fork point
    rc, names, _ = git("diff", "--name-only", base, cand)
    write_set = [n for n in names.splitlines() if n.strip()]
    report["branch_write_set"] = write_set
    report["write_set_size"] = len(write_set)

    per_path = {}
    for path in write_set:
        tip_blob = git("rev-parse", "%s:%s" % (tip, path))[1].strip()
        cand_blob = git("rev-parse", "%s:%s" % (cand, path))[1].strip()
        base_blob = git("rev-parse", "%s:%s" % (base, path))[1].strip() if git(
            "cat-file", "-e", "%s:%s" % (base, path))[0] == 0 else "ABSENT_AT_BASE"
        per_path[path] = {
            "already_equal_to_tip": bool(tip_blob) and tip_blob == cand_blob,
            "branch_changed_it_over_fork": cand_blob != base_blob,
            "tip_changed_it_over_fork": bool(tip_blob) and tip_blob != base_blob,
            "branch_hunks": hunks(base, cand, path)[:12],
            "tip_hunks": hunks(base, tip, path)[:12],
        }
    report["per_path"] = per_path
    report["needs_a_move"] = sorted(p for p, v in per_path.items()
                                    if v["branch_changed_it_over_fork"] and not v["already_equal_to_tip"]
                                    and v["tip_changed_it_over_fork"])
    report["clean_paths_already_landed"] = sorted(p for p, v in per_path.items() if v["already_equal_to_tip"])

    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)

    print("TIP %s" % tip)
    print("CAND %s  fork %s  ancestor_of_tip=%s" % (cand, base[:12], report["candidate_is_ancestor_of_tip"]))
    print("merge-tree exit=%s conflicted=%s" % (rc, report["conflicted_paths"]))
    print("write_set=%d needs_a_move=%d already_landed=%d"
          % (report["write_set_size"], len(report["needs_a_move"]), len(report["clean_paths_already_landed"])))
    for path in report["needs_a_move"]:
        print("  MOVE %s  branch_hunks=%d tip_hunks=%d"
              % (path, len(per_path[path]["branch_hunks"]), len(per_path[path]["tip_hunks"])))
    print("WROTE %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
