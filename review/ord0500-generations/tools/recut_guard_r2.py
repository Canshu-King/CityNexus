"""Re-parent the two pending hands onto whatever the tip is right now, and prove that ONLY the parent moved.

The commander lands by recut, and the standing rules are that a recut must not smuggle in anyone else's bytes
and must not rewrite a published path.  So this tool compares, for every path the hand publishes, the blob on
the old ref against the blob on the new one, and refuses if any of them changed -- a recut that silently
re-shipped a file is exactly the thing that made tonight's 0485 walkthrough refs unreadable from their own names.

Before anything is pushed it also hashes the local lane files and requires them to equal the old ref's blobs:
if the working copies drifted, the "recut" would be a new hand wearing an old name, and that is stopped here
rather than discovered by whoever lands it.
"""
import json
import os
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
sys.path.insert(0, os.path.join(LANE, "tools"))
import publish_side_ref_r20 as PUB

TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
HANDS = {
    "anchor-form": {"old_ref": "refs/heads/review/newlane-ord0500-phone-anchor-form-r4",
                    "new_ref": "refs/heads/review/newlane-ord0500-phone-anchor-form-r5",
                    "manifest": "run/r28_manifest.json",
                    "msg": "run/commit_r29_anchor_msg.txt",
                    "allow_landed": "backend/tests/test_qoder_ord0500_journey_refusal.py"},
    "staging-door": {"old_ref": "refs/heads/review/0afdb49b-ord0500-staging-door-r6",
                     "new_ref": "refs/heads/review/0afdb49b-ord0500-staging-door-r7",
                     "manifest": "run/r25_manifest.json",
                     "msg": "run/commit_r29_door_msg.txt", "allow_landed": ""},
}


def blob_at(head, path):
    rc, out = PUB.git("rev-parse", "%s:%s" % (head, path))
    return out.strip()[:40] if rc == 0 and len(out.strip()) == 40 else "ABSENT"


def head_of(ref):
    rc, out = PUB.git("ls-remote", "--refs", "origin", ref)
    if rc or not out.strip():
        raise SystemExit("ABORT_REF_UNREADABLE " + ref)
    return out.split()[0]


def check(which):
    h = HANDS[which]
    old_head = head_of(h["old_ref"])
    tip = head_of(TIP_REF)
    files = [tuple(x) for x in json.load(open(os.path.join(LANE, h["manifest"]), encoding="utf-8"))]
    drift, rows = [], []
    for e in files:
        rel = e[0]
        p = os.path.join(LANE, rel)
        if not os.path.exists(p):
            raise SystemExit("ABORT_LOCAL_ARTIFACT_MISSING " + rel)
        loc = PUB.lf_blob(rel)
        dest = dest_for(e, old_head)
        on_old = blob_at(old_head, dest)
        rows.append({"path": dest, "local": loc, "on_old_ref": on_old})
        if on_old != "ABSENT" and on_old != loc:
            drift.append({"path": dest, "on_old_ref": on_old, "local_bytes": loc})
    return {"hand": which, "live_tip": tip, "old_head": old_head, "new_ref": h["new_ref"],
            "manifest_paths": len(files), "checked": len(rows),
            "absent_on_old_ref": sum(1 for r in rows if r["on_old_ref"] == "ABSENT"), "drift": drift}


def dest_for(entry, old_head):
    """Where a manifest entry lands on the ref: a three-part entry names its own path, a plain one goes under
    the hand's own review directory -- read off the old ref, not typed here."""
    rel = entry[0]
    if len(entry) == 3:
        return entry[2]
    return find_sub(old_head, rel, entry[1]) + "/" + entry[1] + "/" + os.path.basename(rel)


def find_sub(head, rel, group):
    """Read the directory the published file actually lives under, from that ref's own tree -- the basename
    plus the group is enough, and nothing here is typed.  r5's own diff is a counter-example for the cheaper
    rule: two of its three paths already sat on its parent, so `head^..head` answers one line."""
    want = "/%s/%s" % (group, os.path.basename(rel))
    rc, out = PUB.git("ls-tree", "-r", "--name-only", head)
    if rc:
        raise SystemExit("ABORT_LS_TREE " + head)
    hits = [l for l in out.splitlines() if l.endswith(want)]
    if len(hits) == 1:
        return hits[0][: -len(want)]
    if len(hits) > 1:
        raise SystemExit("ABORT_AMBIGUOUS_DEST " + rel + " " + json.dumps(hits))
    dirs = sorted({l.split("/")[0] + "/" + l.split("/")[1] for l in out.splitlines()
                   if l.startswith("review/ord0500-")})
    raise SystemExit("ABORT_PUBLISHED_PATH_NOT_FOUND_FOR %s (review dirs: %s)"
                     % (rel, json.dumps(dirs)))


def compare(which, new_head=None):
    h = HANDS[which]
    old_head = head_of(h["old_ref"])
    real_new = head_of(h["new_ref"])
    if new_head and new_head != real_new:
        raise SystemExit("ABORT_TYPED_HEAD_NOT_WHAT_THE_REF_ANSWERS typed=%s ref=%s" % (new_head, real_new))
    new_head = real_new
    files = [tuple(x) for x in json.load(open(os.path.join(LANE, h["manifest"]), encoding="utf-8"))]
    changed, missing = [], []
    for e in files:
        dest = dest_for(e, old_head)
        a, b = blob_at(old_head, dest), blob_at(new_head, dest)
        if b == "ABSENT":
            missing.append(dest)
        elif a != "ABSENT" and a != b:
            changed.append({"path": dest, "old": a, "new": b})
    verdict = "RECONTENT_RECUT_REFUSED" if changed else ("PATH_MISSING_ON_NEW_REF" if missing
                                                         else "PARENT_ONLY")
    return {"hand": which, "old_ref": h["old_ref"], "old_head": old_head, "new_ref": h["new_ref"],
            "new_head": new_head, "pair": "%s..%s" % (h["old_ref"].split("/")[-1],
                                                      h["new_ref"].split("/")[-1]),
            "heads_read_from_refs": True, "paths_compared": len(files), "changed_bytes": changed,
            "missing_on_new": missing, "verdict": verdict}


def main():
    mode = sys.argv[1]
    if mode == "check":
        for w in ("anchor-form", "staging-door"):
            r = check(w)
            print(json.dumps(r, ensure_ascii=False))
            if r["drift"]:
                raise SystemExit("ABORT_LOCAL_BYTES_NOT_WHAT_THE_REF_CARRIES " + w)
    elif mode == "compare":
        which = sys.argv[2]
        head = sys.argv[3] if len(sys.argv) > 3 else None
        r = compare(which, head)
        print(json.dumps(r, ensure_ascii=False))
        dest = os.path.join(LANE, "evidence", "recut_%s_compare_r1.json" % which.replace("-", "_"))
        json.dump(r, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("WROTE " + dest)
        if r["verdict"] != "PARENT_ONLY":
            raise SystemExit("ABORT_NOT_A_PARENT_ONLY_RECUT " + r["verdict"])
    else:
        raise SystemExit("USAGE: check | compare <hand> <new head>")


if __name__ == "__main__":
    main()
