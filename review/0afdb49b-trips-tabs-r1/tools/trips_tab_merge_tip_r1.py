"""Resolve the second re-cut's only conflict in styles.css, keeping BOTH sides' work.

The tip moved again after my first merge (364304f3 -> a9719623), and that wave edited the very line this
lane's cell six had edited: the phone floor's selector list.  Their side added a comment naming the status
banner's dismiss button (Amendment F-2) and left the list ending at `.v8-message button`; my side appended
`, .v8-mobile-menu` to that same list.  Dropping either one would silently delete a landed or pending fix,
so the door here is a byte check, not a judgement call:

  * exactly one conflict region in the file, and it is this line;
  * the resolved line must equal THEIR line with one contiguous insertion and nothing else changed
    (proved by removing that insertion again and comparing bytes);
  * the two lines only my side carries (the avatar comment and its rule) must survive verbatim;
  * after writing, no conflict markers may remain, and the diff from the tip to the merged file must be
    pure insertions.
"""
import os
import re
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "recut_avatar")
CSS = os.path.join(WT, "frontend", "src", "styles.css")
TIP = "a9719623d8df06b22e461fa905d8e892e5ccf727"
INSERT = ", .v8-mobile-menu"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=900, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def want(cond, msg):
    if not cond:
        raise SystemExit("ABORT " + msg)


def main():
    if "--verify-only" in sys.argv:
        lines = open(CSS, encoding="utf-8").read().split("\n")
        want(not [l for l in lines if re.match(r"^(<<<<<<<|=======|>>>>>>>)", l)], "MARKERS_STILL_PRESENT")
        json_line({"resolved": True, "lines": len(lines)})
        return
    raw = open(CSS, encoding="utf-8").read()
    lines = raw.split("\n")
    starts = [i for i, l in enumerate(lines) if l.startswith("<<<<<<< ")]
    already = [l for l in lines if re.match(r"^(<<<<<<<|=======|>>>>>>>)", l)]
    want(not already or starts, "STRAY_MARKER_WITHOUT_A_CONFLICT %s" % already[:2])
    if starts:
        want(len(starts) == 1, "CONFLICT_COUNT %s" % starts)
        i = starts[0]
        j = next(k for k in range(i, len(lines)) if lines[k] == "=======")
        k = next(m for m in range(j, len(lines)) if lines[m].startswith(">>>>>>> "))
        mine, theirs = lines[i + 1:j], lines[j + 1:k]
        want(len(theirs) == 1, "THEIR_SIDE_LINES %s" % len(theirs))
        want(len(mine) == 3, "MY_SIDE_LINES %s" % len(mine))
        want("v8-mode-chips button, .v8-compare-button" in theirs[0]
             and "v8-mode-chips button, .v8-compare-button" in mine[0], "NOT_THE_FLOOR_LINE")
        want("Amendment F-2" in theirs[0], "THEIR_COMMENT_MISSING")
        want(INSERT + " { min-height: var(--cn-touch-min); } }" in mine[0],
             "MY_SELECTOR_NOT_AT_LINE_END")
        want(theirs[0].endswith(".v8-message button { min-height: var(--cn-touch-min); } }"),
             "THEIR_LINE_SHAPE_UNEXPECTED")
        resolved = theirs[0].replace(".v8-message button { min-height",
                                     ".v8-message button" + INSERT + " { min-height")
        want(resolved.replace(INSERT, "", 1) == theirs[0], "RESOLUTION_IS_NOT_A_PURE_INSERTION")
        want(resolved.count(INSERT) == 1, "INSERTION_APPLIED_TWICE")
        want(mine[1].startswith("/* ORD-0485 phone chain: the avatar")
             and ".v8-avatar::before" in mine[2], "MY_AVATAR_LINES_NOT_WHERE_EXPECTED")
        out = lines[:i] + [resolved] + mine[1:] + lines[k + 1:]
        want(not [l for l in out if re.match(r"^(<<<<<<<|=======|>>>>>>>)", l)], "MARKERS_LEFT_BEHIND")
        for probe in ("v8-avatar::before", "trips-tabs button::after", "Amendment F-2",
                      ".v8-mobile-menu" + " { min-height"):
            want(probe in "\n".join(out), "LOST_A_RULE %s" % probe)
        with open(CSS, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(out))
    else:
        out = lines
    rc, diff = git("diff", "--no-color", TIP, "--", "frontend/src/styles.css")
    want(rc == 0, "DIFF_FAILED " + diff[:200])
    removed = [l[1:] for l in diff.split("\n") if l.startswith("-") and not l.startswith("---")]
    added = [l[1:] for l in diff.split("\n") if l.startswith("+") and not l.startswith("+++")]
    # a tip line may only disappear because this lane's pending selector was appended to it
    want(sorted(removed) == sorted(a.replace(INSERT, "", 1) for a in added if INSERT in a),
         "MERGE_DELETES_TIP_CONTENT %s" % [l[:80] for l in removed][:3])
    json_line({"markers_left": 0, "tip_lines_kept": True,
               "added_lines": len(added),
               "added_kinds": sorted({re.sub(r"[0-9]+", "N", a.strip())[:70] for a in added})})


def json_line(d):
    import json
    print(json.dumps(d, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
