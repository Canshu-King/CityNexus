"""Landed-content re-scan: does what a closed hand shipped still exist, byte for byte, on the live line?

Why this exists: tonight this lane had a hand landed (`... anchor-form`, verified by blob at the time) and then
dropped out of the line by a rebuild, with nobody's gate noticing -- the order stayed CLOSED while the bytes
were gone.  Ancestry cannot answer this on a line that gets re-rooted, so the question has to be asked the way
the standing rule now says: per path, compare blobs.

Coordinates are read from the published refs, not typed: for each ref, the paths that hand changed are
`git diff --name-only <ref>^..<ref>` and the expected blobs are `git rev-parse <ref>:<path>`.  A ref is
immutable, so it is the one place the claim "I shipped X" is still recorded honestly.

Verdicts per path: SAME (byte-equal on the line), ABSENT (no such path on the line), CHANGED (a path exists but
with different bytes -- could be mine superseded legitimately, so it is reported, not silently accepted), and
NOT_REACHED (the ref itself cannot be read, which is never treated as a pass).
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
REFS = ["refs/heads/review/0afdb49b-ord0500-staging-door-r4",
        "refs/heads/review/newlane-ord0500-phone-anchor-form-r3",
        "refs/heads/review/0afdb49b-ord0500-staging-door-r5"]


def git(*args, **kw):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=kw.get("timeout", 300),
                       env=ENV)
    # three values, deliberately: the fatal line repeats the revision, so a caller that concatenates
    # stderr into stdout and greps for 40 hex will read a MISSING path as a CHANGED one -- which is what
    # the first two versions of this tool did
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def git2(*args, **kw):
    rc, out, err = git(*args, **kw)
    return rc, out + err


def Lgit(*args):
    return git2(*args)


def live_tip():
    rc, out, err = git("ls-remote", "--refs", "origin", TIP_REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_NO_TIP " + (out + err)[:160])
    return out.split()[0]


def coordinates(ref, tip=None):
    """The paths a published hand changed, and the blobs it changed them to -- read off the ref."""
    rc, heads, err = git("ls-remote", "--refs", "origin", ref)
    if rc or not heads.strip():
        return None, "REF_UNREADABLE " + (heads + err)[:90]
    head = heads.split()[0]
    rc, out, err = git("diff", "--name-only", "%s^..%s" % (head, head))
    if rc:
        return None, "DIFF_UNREADABLE " + err[:90]
    paths = [l.strip() for l in out.splitlines() if l.strip()]
    coords = []
    for p in paths:
        rcb, b, _e = git("rev-parse", "%s:%s" % (head, p))
        if rcb:
            # the hand deleted it; there is no blob to expect, and "deleted" is its own claim
            coords.append({"path": p, "expect": "DELETED_BY_HAND"})
        else:
            coords.append({"path": p, "expect": b.strip()})
    return {"ref": ref, "head": head, "coords": coords}, "OK"


def tree_ok(tip):
    """Can the line's own tree even be read?  Kept separate from "is this path in it": git says
    `does not exist` for BOTH cases, and folding an unusable revision into ABSENT would report a broken read
    as a vanished file -- the arms' M4 caught exactly that."""
    rc = git("rev-parse", "--verify", "--quiet", "%s^{tree}" % tip)[0]
    return rc == 0


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
            verdict = "DELETION_HELD" if on_line in ("ABSENT",) else "DELETION_UNDONE"
        elif on_line == "ABSENT":
            verdict = "ABSENT"
        elif on_line == "UNREADABLE_ON_LINE":
            verdict = "UNREADABLE_ON_LINE"  # the sentinel and the label must be the same string; they were not, and an unreadable read came out CHANGED
        elif on_line == c["expect"]:
            verdict = "SAME"
        else:
            verdict = "CHANGED"
        rows.append({"path": c["path"], "expect": c["expect"], "on_line": on_line, "verdict": verdict})
    return rows


def main():
    tip = live_tip()
    out = {"schema": "CNX_LANDED_BLOB_RESCAN_V1", "tool": "landed_blob_rescan_r1", "took_local":
               datetime.now().astimezone().isoformat(), "live_tip": tip, "refs": []}
    tally = {}
    for ref in REFS:
        cs, why = coordinates(ref)
        if cs is None:
            out["refs"].append({"ref": ref, "verdict": "NOT_REACHED", "why": why})
            tally["NOT_REACHED"] = tally.get("NOT_REACHED", 0) + 1
            continue
        rows = scan(tip, cs)
        counts = {}
        for r in rows:
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        lost = [r for r in rows if r["verdict"] in ("ABSENT", "CHANGED", "DELETION_UNDONE",
                                                     "UNREADABLE_ON_LINE")]
        out["refs"].append({"ref": ref, "head": cs["head"], "paths": len(rows), "counts": counts,
                            "verdict": "LOST_LANDED_CONTENT" if lost else "HELD",
                            "lost": lost[:20], "lost_count": len(lost)})
        for k, v in counts.items():
            tally[k] = tally.get(k, 0) + v
    out["tally"] = tally
    out["verdict"] = "LOST_LANDED_CONTENT" if any(r.get("verdict") == "LOST_LANDED_CONTENT"
                                                  for r in out["refs"]) else "HELD"
    out["method"] = ("per path, `git rev-parse <live_tip>:<path>` compared to `git rev-parse <ref>:<path>`; "
                     "ancestry is not consulted -- on a re-rooted line it answers nothing")
    dest = os.path.join(LANE, "evidence", "landed_blob_rescan_r1.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"live_tip": tip, "verdict": out["verdict"], "tally": tally,
                      "refs": [(r["ref"].split("/")[-1], r.get("verdict"), r.get("paths"), r.get("counts"))
                               for r in out["refs"]]}, ensure_ascii=False, indent=1))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
