"""ORD-0500 landing presence -- does anything product-side of r6 still need landing onto the live tip?

The merge prediction (`o500_r7_rebase_preview_r1.py`) came back with a result that needs a second,
independent reading before it can be written down: merging r6 onto the tip produces the TIP's version of
`backend/app/main.py` and `contracts/openapi.yaml`, even though the lane's own blob differs from the tip's.
Two very different causes look identical from here:
  (a) the lane's change is already on the line and the tip simply grew past it -- nothing to land;
  (b) the merge silently drops the lane's change -- landing r6 would lose backend bytes.

So this file takes the lane's own added lines (its diff against its fork point, per product path) and asks
the tip's file for each one. Counting is done on the text that `git show` returned, not on file names.

Limits stated up front: line-set presence proves the words are in the file, not that the behaviour runs --
behaviour is the lane's own e2e arms to answer. Paths the tip does not carry at all are named
`PATH_NOT_ON_TIP`, not counted as missing lines.

Read-only: 0 ref writes, 0 pushes, 0 checkouts, 0 processes, receipts only.
"""
import io
import json
import subprocess
import sys
import time

REPO = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
CAND_REF = "refs/heads/review/newlane-ord0500-phone-checkin-entry-r6"
R7_REF = "refs/heads/review/newlane-ord0500-phone-checkin-entry-r7"
PREVIEW = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/"
           "ord0500-r6-rebase-preview/receipts/o500_r7_byte_carry_r1.json")
SUMMARY = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/"
           "ord0500-r6-rebase-preview/receipts/o500_r7_rebase_preview_r1.json")
OUT = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/"
       "ord0500-r6-rebase-preview/receipts/o500_landed_presence_r1.json")
MIN_LEN = 12


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


def added_lines(base, cand, path):
    rc, out, err = git("diff", "--unified=0", base, cand, "--", path)
    if rc != 0:
        raise AssertionError("DIFF_FAILED %s rc=%s %s" % (path, rc, err.strip()[:120]))
    found, keeping = [], False
    for line in out.splitlines():
        if line.startswith("@@"):
            keeping = True
            continue
        if not keeping:
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            text = line[1:].strip()
            if len(text) >= MIN_LEN and not set(text) <= set(" \t\"',()[]{}:#"):
                found.append(text)
    return found


def main():
    tip = head_of(TIP_REF)
    r6 = head_of(CAND_REF)
    r7 = head_of(R7_REF)
    carry = json.load(io.open(PREVIEW, encoding="utf-8"))
    summary = json.load(io.open(SUMMARY, encoding="utf-8"))
    if carry["live_tip"] != tip or carry["candidate"] != r7:
        print("STALE_OPERAND carry_tip=%s now=%s carry_cand=%s now=%s"
              % (carry["live_tip"], tip, carry["candidate"], r7))
        return 7
    if summary["live_tip"] != tip or summary["candidate_heads"]["r6"]["sha"] != r6:
        print("STALE_SUMMARY tip=%s r6=%s" % (summary["live_tip"],
                                              summary["candidate_heads"]["r6"]["sha"]))
        return 8
    base = summary["candidates"]["r6"]["fork_point"]
    if git("merge-base", tip, r6)[1].strip() != base:
        print("FORK_MOVED %s" % base)
        return 9

    rows = []
    for row in carry["r6_product_write_set"]:
        path = row["path"]
        tip_text = git("show", "%s:%s" % (tip, path))[1] if git(
            "cat-file", "-e", "%s:%s" % (tip, path))[0] == 0 else None
        if tip_text is None:
            rows.append({"path": path, "state": "PATH_NOT_ON_TIP"})
            continue
        added = added_lines(base, r6, path)
        present = [l for l in added if l in tip_text]
        missing = [l for l in added if l not in tip_text]
        rows.append({
            "path": path,
            "state": "ALREADY_BYTE_EQUAL" if row["candidate_blob"] == row["tip_blob"] else "BLOBS_DIFFER",
            "candidate_blob": row["candidate_blob"], "tip_blob": row["tip_blob"],
            "merged_blob": row["merged_blob"],
            "merged_equals_tip": row["merged_blob"] == row["tip_blob"],
            "added_lines_measured": len(added),
            "added_lines_present_on_tip": len(present),
            "added_lines_missing_on_tip": len(missing),
            "missing_examples": missing[:6],
        })

    verdict = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "live_tip": tip, "r6": r6, "r7": r7, "r6_fork_point": base,
        "operand_source": [PREVIEW, SUMMARY],
        "product_paths_checked": len(rows),
        "paths_already_byte_equal": len([r for r in rows
                                         if r.get("state") == "ALREADY_BYTE_EQUAL"]),
        "paths_where_blobs_differ": len([r for r in rows if r.get("state") == "BLOBS_DIFFER"]),
        "paths_not_on_tip": len([r for r in rows if r.get("state") == "PATH_NOT_ON_TIP"]),
        "added_lines_total": sum(r.get("added_lines_measured", 0) for r in rows),
        "added_lines_missing_on_tip_total": sum(r.get("added_lines_missing_on_tip", 0) for r in rows),
        "rows": rows,
        "how_counted": "added lines = git diff --unified=0 <fork> <r6> -- <path>, stripped, length >= %d, "
        "punctuation-only dropped; presence = substring test against git show <tip>:<path> text"
        % MIN_LEN,
        "limit": "line presence proves the words are in the tip's file, not that the behaviour runs; "
        "behaviour belongs to the lane's own e2e arms",
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(verdict, handle, indent=1, ensure_ascii=False)
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(verdict, ensure_ascii=False).encode("utf-8"))))
    print("TIP %s r6 %s r7 %s fork %s" % (tip, r6, r7, base))
    print("checked=%d byte_equal=%d blobs_differ=%d not_on_tip=%d added=%d missing_on_tip=%d"
          % (verdict["product_paths_checked"], verdict["paths_already_byte_equal"],
             verdict["paths_where_blobs_differ"], verdict["paths_not_on_tip"],
             verdict["added_lines_total"], verdict["added_lines_missing_on_tip_total"]))
    for r in rows:
        print("  %s %s added=%s present=%s missing=%s merged_eq_tip=%s"
              % (r["path"], r["state"], r.get("added_lines_measured", "-"),
                 r.get("added_lines_present_on_tip", "-"), r.get("added_lines_missing_on_tip", "-"),
                 r.get("merged_equals_tip", "-")))
        for l in r.get("missing_examples", [])[:3]:
            print("     MISSING | %s" % l[:110])
    return 0


if __name__ == "__main__":
    sys.exit(main())
