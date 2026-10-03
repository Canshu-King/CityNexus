"""Re-take the two claims that depend on "the current line", at the moment the block is written.

The byte pairing is pinned to the generation that was measured, so it does not age. Two claims do: that
the four sentences' words are still identical on the live tip, and that what moved in that file between
the measured generation and now is comment only. Both are recomputed here and stored, so the block cites
a fresh artifact instead of a stale one -- the line has moved four times while this hand was open.
"""
import io
import json
import subprocess
import time

WT = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"
OUT = ("%s/frontend/review/checkin-words-real-door/receipts/pairing_recheck_at_block_write_r1.json"
       % WT)
MEASURED = "bf4f776b0ba943b88817dfcc0cb3442d75fd9e21"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
COPY_PATH = "frontend/src/features/checkin/checkinCopy.ts"
NAMES = ["journeyUnknown", "activityUnknown", "activityNotInJourney", "placeUnknown"]


def git(*args):
    r = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def row_of(text, name):
    """The row's own text block, taken by name -- compared as bytes, not as a paraphrase."""
    marker = "\n  %s: {" % name
    if marker not in text:
        return None
    rest = text.split(marker, 1)[1]
    return rest.split("\n  }", 1)[0]


def main():
    _rc, out, _e = git("ls-remote", "--refs", "origin", TIP_REF)
    tip = out.split("\t")[0].strip()
    _rc, old, _e = git("show", "%s:%s" % (MEASURED, COPY_PATH))
    _rc, now, _e = git("show", "%s:%s" % (tip, COPY_PATH))
    rows = {}
    for name in NAMES:
        a, b = row_of(old, name), row_of(now, name)
        rows[name] = {"present_at_both": a is not None and b is not None,
                      "identical": a == b and a is not None,
                      "chars_compared": len(a) if a else 0}
    _rc, diff, _e = git("diff", "-U0", MEASURED, tip, "--", COPY_PATH)
    changed = [l for l in diff.splitlines()
               if (l.startswith("+") or l.startswith("-")) and not l.startswith(("+++", "---"))]
    comment = [l for l in changed if l[1:].strip().startswith(("*", "//", "/*"))]
    body = {
        "checked_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tip_at_check": tip, "measured_generation": MEASURED,
        "measured_is_ancestor_of_tip": git("merge-base", "--is-ancestor", MEASURED, tip)[0] == 0,
        "copy_blob_measured": git("rev-parse", "%s:%s" % (MEASURED, COPY_PATH))[1].strip(),
        "copy_blob_at_check": git("rev-parse", "%s:%s" % (tip, COPY_PATH))[1].strip(),
        "rows": rows,
        "all_four_rows_identical_on_the_live_tip": all(v["identical"] for v in rows.values()),
        "diff_shape": {"changed_lines": len(changed), "comment_lines": len(comment),
                       "non_comment_lines": len(changed) - len(comment)},
        "how_compared": "the row block between `<name>: {` and the closing brace, compared as text; "
                        "the file diff classified line by line, comment = a line whose first non-space "
                        "character starts a comment",
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in body.items() if k != "rows"}, ensure_ascii=False,
                     indent=1).encode("ascii", "replace").decode("ascii")[:900])
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(body, ensure_ascii=False).encode("utf-8"))))
    return 0 if body["all_four_rows_identical_on_the_live_tip"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
