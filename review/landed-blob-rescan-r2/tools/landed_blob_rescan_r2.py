"""Landed-content re-scan, second generation: the first scan named three things wrongly and I am fixing the
names before anyone lands a decision on them.

What r1 got wrong, found by reading its own output rather than by being told:

1. It called a ref `LOST_LANDED_CONTENT` when the line simply never carried it.  Two of my hands that the
   commander is still holding (`anchor-form-r3`, `staging-door-r5`) were printed as "lost" while the same block
   asked him to land them -- `ABSENT` means "not on the line", which is only a loss if the ref was ever on it.
   r2 needs a landing receipt to say "lost": pass one in `RESCAN_LANDED_RECEIPTS` (a JSON naming the ref, the
   tip it was read back on, and where that claim lives) and only then does an absent/changed path become
   `LOST_LANDED_CONTENT`.  Without a receipt the honest class is `NOT_ON_LINE`.
2. It ran `git merge-tree --write-tree` and reported `conflict_markers: 0` for all thirty-one refs, every one of
   which exited 128 ("refusing to merge unrelated histories") -- the number came out of a command that never
   produced a merge.  A zero from a failed command is not a clean merge, so r2 reports `prediction` first and
   only counts conflicts when the exit is 0 or 1.
3. It called `git diff --name-only <tip>..<head>` "paths outside review", which made a ref look like it was
   claiming product files when the number was really how far its generation sits from the line (one stale-base
   ref answered 603).  r2 keeps the generation distance under its own name and computes the stray-write question
   from the hand's own diff, which `coordinates()` already read.
4. It enumerated my published refs by a name key, and the key silently missed five hands this lane pushed as
   `newlane-ord0485-phone-walkthrough-r1..r5` -- the lane directory is named for ORD-0485 and the key only knew
   about ORD-0500.  r2 cannot prove authorship from a name, so it reports what the key did not match but the
   lane's own order numbers did: `CANDIDATE_MISSED` lines, printed, not swallowed.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"
KEYS = tuple(os.environ.get("RESCAN_KEYS", "0afdb49b,newlane-ord0500-phone").split(","))
ORDER_TOKENS = tuple(os.environ.get("RESCAN_ORDER_TOKENS", "0485,0500").split(","))


def git(*args, **kw):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=kw.get("timeout", 300),
                       env=ENV)
    # three values: git's fatal line repeats the revision, and a caller that folds stderr into stdout reads a
    # MISSING path as a blob it found -- which is how r1's arms caught the first version
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def live_tip():
    rc, out, err = git("ls-remote", "--refs", "origin", TIP_REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_NO_TIP " + (out + err)[:160])
    return out.split()[0]


def all_review_refs():
    rc, out, err = git("ls-remote", "--refs", "origin", "refs/heads/review/*")
    if rc:
        raise SystemExit("ABORT_LS_REMOTE " + (out + err)[:160])
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].startswith("refs/heads/review/"):
            rows.append((parts[1], parts[0]))
    return rows


def my_refs(rows):
    """Refs matching the name key, plus the blind spot printed alongside: a name key is not an authorship
    proof, so the refs it did not match but this lane's own order numbers did are returned as candidates."""
    heads = [r for r, _ in rows if any(k in r.split("/")[-1] for k in KEYS)]
    candidates = []
    for r, sha in rows:
        name = r.split("/")[-1]
        if any(k in name for k in KEYS):
            continue
        if any(("ord" + t) in name or (t + "-phone") in name for t in ORDER_TOKENS):
            candidates.append([r, sha])
    return sorted(heads), sorted(candidates)


def receipts():
    path = os.environ.get("RESCAN_LANDED_RECEIPTS", "")
    if not path:
        return {}
    if not os.path.exists(path):
        raise SystemExit("ABORT_RECEIPT_FILE_MISSING " + path[:120])
    data = json.load(open(path, encoding="utf-8"))
    return {e["ref"]: e for e in data.get("landed", [])}


def coordinates(ref, head=None):
    """The paths a published hand changed and the blobs it changed them to -- read off the ref."""
    if head is None:
        rc, out, err = git("ls-remote", "--refs", "origin", ref)
        if rc or not out.strip():
            return None, "REF_UNREADABLE " + (out + err)[:90]
        head = out.split()[0]
    rc, out, err = git("diff", "--name-only", "%s^..%s" % (head, head))
    if rc:
        return None, "DIFF_UNREADABLE " + err[:90]
    paths = [l.strip() for l in out.splitlines() if l.strip()]
    coords = []
    for p in paths:
        rcb, b, _e = git("rev-parse", "%s:%s" % (head, p))
        coords.append({"path": p, "expect": "DELETED_BY_HAND" if rcb else b.strip()})
    own_product = [p for p in paths if not p.startswith("review/")]
    return {"ref": ref, "head": head, "coords": coords, "own_product_paths": len(own_product),
            "own_product": own_product[:8]}, "OK"


def tree_ok(tip):
    return git("rev-parse", "--verify", "--quiet", "%s^{tree}" % tip)[0] == 0


def scan(tip, coord_set):
    rows = []
    readable = tree_ok(tip)
    for c in coord_set["coords"]:
        if not readable:
            on_line = "UNREADABLE_ON_LINE"
        else:
            rcl, out, err = git("rev-parse", "%s:%s" % (tip, c["path"]))
            blob = re.match(r"([0-9a-f]{40})", out.strip()) if rcl == 0 else None
            on_line = blob.group(1) if blob else ("ABSENT" if rcl else "UNREADABLE_ON_LINE")
        if c["expect"] == "DELETED_BY_HAND":
            verdict = "DELETION_HELD" if on_line == "ABSENT" else "DELETION_UNDONE"
        elif on_line in ("ABSENT", "UNREADABLE_ON_LINE"):
            verdict = on_line
        elif on_line == c["expect"]:
            verdict = "SAME"
        else:
            verdict = "CHANGED"
        rows.append({"path": c["path"], "expect": c["expect"], "on_line": on_line, "verdict": verdict})
    return rows


def classify(counts, has_receipt):
    """A loss claim needs a receipt; without one, an absent path is a hand that has not landed yet."""
    classes = []
    if counts.get("UNREADABLE_ON_LINE"):
        classes.append("UNREADABLE_ON_LINE")
    if counts.get("DELETION_UNDONE"):
        classes.append("DELETION_REVERSED")
    if counts.get("CHANGED"):
        classes.append("SUPERSEDED_ON_LINE")
    if counts.get("ABSENT"):
        classes.append("LOST_LANDED_CONTENT" if has_receipt else "NOT_ON_LINE")
    if not classes:
        return "HELD"
    return "+".join(classes)


def prediction(tip, head):
    """merge-tree is read-only, and on a re-rooted line it exits 128 without merging anything -- that answer is
    'no prediction', never 'zero conflicts'."""
    rc, out, err = git("merge-tree", "--write-tree", tip, head)
    if rc not in (0, 1):
        return {"prediction": "NO_PREDICTION_EXIT_%d" % rc, "merge_tree_exit": rc,
                "predicted_tree": "", "conflicts": None,
                "why": (err or out).strip().splitlines()[-1][:120] if (err or out).strip() else ""}
    return {"prediction": "PREDICTED", "merge_tree_exit": rc,
            "predicted_tree": (out or "").splitlines()[0].strip(),
            "conflicts": len([l for l in (out + "\n" + err).splitlines() if "CONFLICT" in l]), "why": ""}


def gen_distance(tip, head):
    rc, out, err = git("diff", "--name-only", "%s..%s" % (tip, head))
    if rc:
        return {"gen_distance_error": err.strip()[:120]}
    paths = [l.strip() for l in out.splitlines() if l.strip()]
    return {"gen_distance_product_paths": sum(1 for p in paths if not p.startswith("review/")),
            "gen_distance_review_paths": sum(1 for p in paths if p.startswith("review/"))}


def main():
    tip = live_tip()
    rows = all_review_refs()
    refs, candidates = my_refs(rows)
    if not os.environ.get("RESCAN_ALL"):
        keep = os.environ.get("RESCAN_REFS", "").split(",")
        refs = [r for r in refs if r in keep] if keep and keep != [""] else refs
    got = dict(rows)
    land = receipts()
    out = {"schema": "CNX_LANDED_BLOB_RESCAN_V2", "tool": "landed_blob_rescan_r2",
           "took_local": datetime.now().astimezone().isoformat(), "live_tip": tip,
           "review_refs_on_line": len(rows), "keys": list(KEYS), "refs": [],
           "candidates_missed_by_key": [{"ref": r, "head": h} for r, h in candidates],
           "receipted_refs": sorted(land)}
    tally = {}
    for ref in refs:
        cs, why = coordinates(ref, got.get(ref))
        if cs is None:
            out["refs"].append({"ref": ref, "verdict": "NOT_REACHED", "why": why})
            tally["NOT_REACHED"] = tally.get("NOT_REACHED", 0) + 1
            continue
        scan_rows = scan(tip, cs)
        counts = {}
        for r in scan_rows:
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        for k, v in counts.items():
            tally[k] = tally.get(k, 0) + v
        bad = [r for r in scan_rows if r["verdict"] not in ("SAME", "DELETION_HELD")]
        entry = {"ref": ref, "head": cs["head"], "paths": len(scan_rows), "counts": counts,
                 "own_product_paths": cs["own_product_paths"], "own_product": cs["own_product"],
                 "has_landing_receipt": ref in land,
                 "not_held_count": len(bad), "not_held": bad[:20],
                 "verdict": classify(counts, ref in land)}
        if os.environ.get("RESCAN_PREDICT"):
            entry["prediction"] = prediction(tip, cs["head"])
            entry.update(gen_distance(tip, cs["head"]))
        out["refs"].append(entry)
    out["path_tally"] = tally
    out["verdict"] = "SOMETHING_NOT_HELD" if any(
        r.get("verdict") != "HELD" for r in out["refs"] if "verdict" in r) else "ALL_HELD"
    out["method"] = ("per path, `git rev-parse <live_tip>:<path>` vs `git rev-parse <ref>:<path>`; ancestry is "
                     "not consulted and merge-tree is not trusted for a verdict on this line")
    dest = os.path.join(LANE, "evidence",
                        os.environ.get("RESCAN_DEST", "landed_blob_rescan_r2.json"))
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"live_tip": tip, "review_refs_on_line": len(rows), "scanned": len(out["refs"]),
                      "candidates_missed": len(candidates), "verdict": out["verdict"], "tally": tally},
                     ensure_ascii=False))
    for r in out["refs"]:
        print("%-46s %-34s paths=%-3d own_product=%-3d rec=%d %s" % (
            r["ref"].split("/")[-1], r.get("verdict"), r.get("paths", 0),
            r.get("own_product_paths", -1), int(r.get("has_landing_receipt", False)),
            json.dumps((r.get("prediction") or {}).get("prediction", ""), ensure_ascii=False)))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
