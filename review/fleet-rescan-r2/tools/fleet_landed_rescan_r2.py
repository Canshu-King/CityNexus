"""ORD-0500 lane -- fleet landed-content re-scan, second generation.

r1 (tools/fleet_landed_rescan_r1.py) scanned every refs/heads/review/* hand the fleet ever
pushed and got the per-path readings right, but it aggregated them into one label per hand, and
that is where it over-claimed:  30 hands report ~9,500-10,600 own paths because their head is
cut from an orphan root / a whole-tree snapshot, so "diff this hand against its own parent" IS
the repository.  Folding those into CHANGED read like "this lane's 9,500 artefacts were
overwritten on the line", which is not what happened and is not a claim anyone should land on.

This generation keeps every per-path count exactly as r1 measured it and changes only the
aggregate:  a hand whose own-path count is at least half the live tip's tree is labelled
SNAPSHOT_SHAPED and gets NO landed/lost verdict at all -- its numbers are printed as facts
about the whole tree, not about a candidate.

What it still does NOT do: no fetch, no write, no ref moved, nothing landed, no ancestry
predicate (the standing ruling is that landed-ness is byte equality), and a head that cannot be
read is its own class instead of ABSENT.
"""
import collections
import json
import os
import re
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
OUT = os.path.join(LANE, "evidence", "fleet_rescan_r2")
SNAPSHOT_FRACTION = float(os.environ.get("SNAP_FRACTION", "0.5"))
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"
HEX = re.compile(r"^[0-9a-f]{40}$")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
BLOBBY = (".py", ".ts", ".tsx", ".json", ".yaml", ".yml", ".md", ".sh", ".txt")


def git(*args, stdin=None, cwd=REPO):
    p = subprocess.run(["git", "-C", cwd] + list(args), input=stdin,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, timeout=900)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def lsremote(refspec="refs/heads/review/*"):
    rc, out, err = git("ls-remote", "--refs", "origin", refspec)
    if rc:
        raise SystemExit("ABORT_LS_REMOTE " + err[:200])
    rows = []
    for line in out.splitlines():
        if line.strip():
            sha, name = line.split("\t")
            if not HEX.match(sha):
                raise SystemExit("ABORT_LS_REMOTE_SHAPE " + line[:80])
            rows.append((name, sha))
    return rows


def tip_tree(tip):
    rc, out, err = git("ls-tree", "-r", tip)
    if rc:
        raise SystemExit("ABORT_TIP_TREE_UNREADABLE rc=%d %s" % (rc, err[:160]))
    tree = {}
    for line in out.splitlines():
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        mode, typ, sha = meta.split()
        tree[path] = sha
    return tree


def published_paths(heads):
    """head -> {path: {expect, deleted}} from the hand's own commit, compared against EVERY
    parent (-m) so a merge is not read as empty, and --root so an orphan root is not silently
    dropped either."""
    if not heads:
        return {}
    # The trailing newline is load-bearing:  git --stdin does not flush an unterminated final
    # line, so without it the lexically largest head silently vanishes from the roster and its
    # hand reads as "published nothing".  The roster check below is the second leg of that fix.
    rc, out, err = git("diff-tree", "-r", "--raw", "-m", "--root", "--full-index", "--stdin",
                       stdin=("\n".join(heads) + "\n").encode())
    if rc:
        raise SystemExit("ABORT_DIFF_TREE rc=%d %s" % (rc, err[:200]))
    by_head = collections.defaultdict(dict)
    cur = None
    seen = 0
    for line in out.splitlines():
        line = line.rstrip("\n")
        if not line.startswith(":"):
            if line and HEX.match(line.split()[0]):
                cur = line.split()[0]
                by_head.setdefault(cur, {})
                seen += 1
            continue
        if cur is None:
            continue
        meta, path = line[1:].split("\t", 1)
        bits = meta.split()
        status, old, new = bits[-1], bits[-3], bits[-2]
        if status == "D":
            if HEX.match(old):
                by_head[cur].setdefault(path, {"deleted": True, "expect": old})
            continue
        if new == "0" * 40 or not HEX.match(new):
            continue
        cur_paths = by_head[cur]
        if path not in cur_paths or not cur_paths[path]["deleted"]:
            cur_paths[path] = {"deleted": False, "expect": new}
    if not seen:
        raise SystemExit("ABORT_DIFF_TREE_EMITTED_NOTHING -- the readings below would be vacuous")
    return by_head


def split_quiet_heads(heads, by_head):
    """A head that emitted no line at all is either a genuinely empty commit (its tree equals
    every parent's tree -- two of those exist on this line) or a hole in the batch pass.  Git
    prints nothing, not even the header, for the first case, so the two have to be told apart by
    asking for the trees themselves; anything that is not empty is an abort, not a silent row."""
    quiet = sorted({h for h in heads if h not in by_head})
    empty, holes = [], []
    for head in quiet:
        rc, tree, err = git("rev-parse", "%s^{tree}" % head)
        if rc:
            holes.append(head)
            continue
        rc, out, err = git("rev-list", "--parents", "-n1", head)
        if rc:
            holes.append(head)
            continue
        pars = out.split()[1:]
        ptrees = []
        for p in pars:
            rc, t, err = git("rev-parse", "%s^{tree}" % p)
            ptrees.append(t.strip() if rc == 0 else None)
        if pars and all(t == tree.strip() for t in ptrees):
            empty.append(head)
        elif not pars and tree.strip() == EMPTY_TREE:
            empty.append(head)
        else:
            holes.append(head)
    return quiet, empty, holes


def counts_for(tree, coords, present=None):
    """Pure function of (live tree, a hand's published paths) so the arms can feed it shapes the
    live line does not happen to contain.  ``present`` is the set of tip blobs confirmed to exist
    locally; None means "not measured", which is reported rather than guessed."""
    same = absent = changed = unreadable = del_held = del_undone = 0
    samples = {"absent": [], "changed": [], "unreadable": [], "deletion_undone": []}
    for path, info in sorted(coords.items()):
        on_line = tree.get(path)
        if info["deleted"]:
            if on_line is None:
                del_held += 1
            else:
                del_undone += 1
                samples["deletion_undone"].append({"path": path, "was": info["expect"], "on_line": on_line})
            continue
        if on_line is None:
            absent += 1
            samples["absent"].append({"path": path, "expect": info["expect"]})
        elif on_line == info["expect"]:
            same += 1
        else:
            if present is not None and on_line not in present:
                unreadable += 1
                samples["unreadable"].append({"path": path, "on_line": on_line})
            else:
                changed += 1
                samples["changed"].append({"path": path, "expect": info["expect"], "on_line": on_line})
    return ({"SAME": same, "ABSENT": absent, "CHANGED": changed, "UNREADABLE_ON_LINE": unreadable,
             "DELETION_HELD": del_held, "DELETION_UNDONE": del_undone},
            {k: v[:4] for k, v in samples.items()})


def aggregate(counts, paths, tip_tree_size):
    """Label a hand from its counts -- and refuse to label it at all when its shape is a whole
    tree rather than a candidate.

    The words are byte-words on purpose:  ABSENT is reported as NOT_ON_LINE, never as LOST, and
    CHANGED as DIFFERENT_ON_LINE, never as superseded, because a loss claim needs an instrument
    landing receipt naming the tip that hand once matched, and this scan reads no receipt.
    """
    if paths >= SNAPSHOT_FRACTION * tip_tree_size:
        return "SNAPSHOT_SHAPED", "own paths >= %g of the live tip tree (%d of %d) -- this hand " \
                                 "is the repository, so no landed/lost verdict is claimed" % (
                                     SNAPSHOT_FRACTION, paths, tip_tree_size)
    same, absent, changed = counts["SAME"], counts["ABSENT"], counts["CHANGED"]
    if not paths:
        return "NO_PATHS_REPORTED", "diff against its own parent reported no path at all"
    if counts["UNREADABLE_ON_LINE"] and not (same or absent or changed):
        return "UNREADABLE_ON_LINE", None
    if absent and not same and not changed:
        return "ALL_NOT_ON_LINE", None
    if changed and not same and not absent:
        return "ALL_DIFFERENT_ON_LINE", None
    if same and not absent and not changed:
        return "HELD", None
    if same:
        return "MIXED", None
    if not (absent or changed):
        if counts["DELETION_HELD"] and not counts["DELETION_UNDONE"]:
            return "ALL_DELETIONS_HELD", None
        if counts["DELETION_UNDONE"] and not counts["DELETION_HELD"]:
            return "ALL_DELETIONS_UNDONE", None
        if counts["DELETION_HELD"] or counts["DELETION_UNDONE"]:
            return "DELETIONS_SPLIT", None
    return "NONE_HELD_SPLIT", None


def main():
    os.makedirs(OUT, exist_ok=True)
    tip_rows = [r for r in lsremote("refs/heads/*") if r[0] == TIP_REF]
    if len(tip_rows) != 1:
        raise SystemExit("ABORT_TIP_NOT_ANSWERED %d" % len(tip_rows))
    tip = tip_rows[0][1]
    tree = tip_tree(tip)
    review = [(n, s) for n, s in lsremote() if n.startswith("refs/heads/review/")]
    heads = sorted({s for _, s in review})

    rc, out, err = git("cat-file", "--batch-check", stdin=("\n".join(heads) + "\n").encode())
    kinds = collections.Counter()
    unresolvable = set()
    for line in out.splitlines():
        bits = line.split()
        if len(bits) >= 2 and bits[1] == "commit":
            kinds["commit"] += 1
        else:
            kinds[bits[1] if len(bits) > 1 else "absent"] += 1
            unresolvable.add(bits[0])

    by_head = published_paths(heads)
    quiet, empty_heads, hole_heads = split_quiet_heads(heads, by_head)
    if hole_heads:
        raise SystemExit("ABORT_HEADS_MISSING_FROM_BATCH %d first=%s -- the roster must cover every "
                         "head the remote answers for" % (len(hole_heads), hole_heads[0][:12]))
    rc, out, err = git("cat-file", "--batch-check", stdin="\n".join(sorted(set(tree.values()))).encode())
    if rc:
        raise SystemExit("ABORT_BLOB_BATCHCHECK " + err[:160])
    present = {l.split()[0] for l in out.splitlines() if len(l.split()) >= 2 and l.split()[1] == "blob"}
    tip_blobs_missing = len(set(tree.values())) - len(present)
    # --no-walk: the question is how many parents THESE heads have, not what lies beneath them.
    # Without it rev-list walks the whole DAG and the distribution describes the ancestry, not
    # the roster (that mistake made 3,000 rows look like 1,035 heads in the first pass).
    rc, out, err = git("rev-list", "--parents", "--no-walk", "--stdin",
                       stdin=("\n".join(heads) + "\n").encode())
    if rc:
        raise SystemExit("ABORT_REV_LIST " + err[:160])
    npar = {bits[0]: len(bits) - 1 for bits in (l.split() for l in out.splitlines()) if bits}
    par_tally = collections.Counter(npar.values())
    rows = []
    tally = collections.Counter()
    for name, sha in sorted(review):
        if sha in unresolvable:
            tally["NOT_REACHED"] += 1
            rows.append({"ref": name, "head": sha, "class": "NOT_REACHED", "paths": 0,
                         "counts": {}, "product_paths": 0})
            continue
        coords = by_head.get(sha, {})
        counts, samples = counts_for(tree, coords, present=present)
        if sha in empty_heads:
            # its tree equals every parent's tree, so it published no path of its own; calling
            # that "the line lost nothing" and "this hand holds nothing" are different sentences.
            cls, why = "EMPTY_COMMIT", "head tree equals every parent tree -- nothing was published " \
                                       "by this commit itself"
        else:
            cls, why = aggregate(counts, len(coords), len(tree))
        tally[cls] += 1
        product = sum(1 for p in coords if p.lower().endswith(BLOBBY) and not p.startswith("review/"))
        rows.append({"ref": name, "head": sha, "class": cls, "why": why, "paths": len(coords),
                     "counts": counts, "product_paths": product, "empty_commit": sha in empty_heads,
                     "n_parents": npar.get(sha), "samples": samples})

    shared = collections.Counter(r["head"] for r in rows)
    dup = {h: c for h, c in shared.items() if c > 1}

    cand = [r for r in rows if r["class"] not in ("SNAPSHOT_SHAPED", "NOT_REACHED",
                                                  "NO_PATHS_REPORTED", "EMPTY_COMMIT")]
    lane = collections.defaultdict(lambda: collections.Counter())
    lost_product = collections.Counter()
    for r in cand:
        key = r["ref"].split("/")[-1].split("-")[0]
        lane[key][r["class"]] += 1
        lost_product[key] += r["counts"].get("ABSENT", 0)
    top_lost = sorted(lane.items(), key=lambda kv: -sum(kv[1].values()))[:10]
    lost_rank = sorted(((v, k) for k, v in lost_product.items()), reverse=True)[:8]

    doc = {
        "tool": "fleet_landed_rescan_r2",
        "supersedes_reading_of": "fleet_landed_rescan_r1 (aggregate labels only; per-path counts unchanged)",
        "tip_ref": TIP_REF, "tip": tip, "tip_tree_paths": len(tree),
        "review_refs": len(review), "distinct_review_heads": len(heads),
        "refs_sharing_a_head": len(dup), "distinct_heads_shared": len(dup),
        "head_object_kinds": dict(kinds), "heads_unresolvable_locally": len(unresolvable),
        "heads_quiet_in_batch": len(quiet), "heads_empty_commit": len(empty_heads),
        "empty_commit_refs": [r["ref"] for r in rows if r["class"] == "EMPTY_COMMIT"],
        "snapshot_fraction": SNAPSHOT_FRACTION,
        "tip_tree_distinct_blobs": len(set(tree.values())),
        "tip_tree_blobs_missing_locally": tip_blobs_missing,
        "parent_count_distribution": {str(k): v for k, v in sorted(par_tally.items())},
        "class_tally": dict(tally),
        "candidate_hands_judged": len(cand),
        "snapshot_shaped_paths_total": sum(r["paths"] for r in rows if r["class"] == "SNAPSHOT_SHAPED"),
        "candidate_paths_total": sum(r["paths"] for r in cand),
        "candidate_same": sum(r["counts"].get("SAME", 0) for r in cand),
        "candidate_absent": sum(r["counts"].get("ABSENT", 0) for r in cand),
        "candidate_changed": sum(r["counts"].get("CHANGED", 0) for r in cand),
        "candidate_deletion_undone": sum(r["counts"].get("DELETION_UNDONE", 0) for r in cand),
        "lanes_top10": [{"lane": k, "classes": dict(v)} for k, v in top_lost],
        "absent_by_lane_top8": [{"lane": k, "absent_paths": v} for v, k in lost_rank],
        "rows": rows,
    }
    with open(os.path.join(OUT, "fleet_rescan_r2.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")

    print("tip=%s tip_tree_paths=%d review_refs=%d distinct_heads=%d refs_sharing_a_head=%d"
          % (tip, len(tree), len(review), len(heads), len(dup)))
    print("head_object_kinds=%s unresolvable_locally=%d quiet_heads=%d empty_commit=%d"
          % (dict(kinds), len(unresolvable), len(quiet), len(empty_heads)))
    print("class_tally=%s" % dict(tally))
    print("candidate_hands_judged=%d candidate_paths_total=%d same=%d absent=%d changed=%d deletion_undone=%d"
          % (len(cand), doc["candidate_paths_total"], doc["candidate_same"], doc["candidate_absent"],
             doc["candidate_changed"], doc["candidate_deletion_undone"]))
    print("snapshot_shaped_paths_total=%d" % doc["snapshot_shaped_paths_total"])
    print("absent_by_lane_top8=%s" % doc["absent_by_lane_top8"])
    print("--- classes with named hands ---")
    for cls in ("HELD", "MIXED", "ALL_ABSENT", "ALL_SUPERSEDED_ON_LINE", "OTHER",
                "SNAPSHOT_SHAPED", "NO_PATHS_REPORTED", "NOT_REACHED"):
        sel = [r for r in rows if r["class"] == cls]
        if not sel:
            continue
        print("%-24s refs=%-5d paths=%-7d same=%-6d absent=%-6d changed=%-6d"
              % (cls, len(sel), sum(r["paths"] for r in sel),
                 sum(r["counts"].get("SAME", 0) for r in sel),
                 sum(r["counts"].get("ABSENT", 0) for r in sel),
                 sum(r["counts"].get("CHANGED", 0) for r in sel)))
        for r in sorted(sel, key=lambda x: -x["paths"])[:3]:
            print("      %-58s head=%s paths=%d %s" % (r["ref"].split("/")[-1][:58], r["head"][:10],
                                                        r["paths"], r["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
