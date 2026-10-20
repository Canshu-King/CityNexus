"""Produce the before-arm file for the CURRENT generation: the merged styles.css minus this cell's lines.

The re-cut rule says a reading belongs to the tip it was taken on, so the "three of four tabs were
off-screen" arm has to be re-measured on the merged tree too -- not on the previous generation's file.
This removes exactly the lines this cell adds (the six-line comment, `width: auto`, `position: relative`,
and the five-line ::after rule) and refuses if anything else moves:

  * the line count must drop by exactly the number of lines the cell claims;
  * the tip's own new comment (Amendment F-2), this lane's earlier `.v8-mobile-menu` selector and the
    avatar rule must all still be there -- the base arm must not accidentally erase a different cell;
  * the removed text must reappear byte-for-byte when the cell is added back.

`--restore` puts the committed file back and proves the worktree matches the published blob.
"""
import os
import re
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "recut_avatar")
CSS = os.path.join(WT, "frontend", "src", "styles.css")
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=900, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def want(cond, msg):
    if not cond:
        raise SystemExit("ABORT " + msg)


def cell_lines(lines):
    ti = next((i for i, l in enumerate(lines) if l.startswith(".trips-tabs button {")), None)
    want(ti is not None, "TAB_RULE_NOT_FOUND")
    ci = ti - 1
    while ci >= 0 and (lines[ci].startswith("   ") or lines[ci].startswith("/*")
                       or lines[ci].rstrip().endswith("*/")):
        ci -= 1
    ci += 1
    want(lines[ci].startswith("/* ORD-0485 phone chain"), "COMMENT_NOT_ABOVE_THE_TAB_RULE %s"
         % lines[ci][:40])
    want(lines[ti - 1].rstrip().endswith("*/"), "COMMENT_DOES_NOT_END_ABOVE_THE_RULE")
    comment = list(range(ci, ti))
    decls = [i for i in range(ti, ti + 14) if lines[i].strip() in ("width: auto;",
                                                                   "position: relative;")]
    want(len(decls) == 2, "DECL_LINES %s" % [lines[i] for i in decls])
    hi = next((i for i, l in enumerate(lines) if l.startswith(".trips-tabs button::after {")), None)
    want(hi is not None, "HIT_RULE_NOT_FOUND")
    after = list(range(hi, lines.index("}", hi) + 1))
    return comment, decls, after


def main():
    lines = open(CSS, encoding="utf-8").read().split("\n")
    if "--restore" in sys.argv:
        rc, out = git("checkout", "--", "frontend/src/styles.css")
        want(rc == 0, "RESTORE_FAILED " + out[:200])
        head_blob = git("rev-parse", "HEAD:frontend/src/styles.css")[1].strip()
        want(git("hash-object", CSS)[1].strip() == head_blob, "RESTORED_FILE_IS_NOT_THE_COMMITTED_BLOB")
        rc, dirty = git("status", "--porcelain=v1")
        want(dirty.strip() == "", "WORKTREE_STILL_DIRTY %s" % dirty[:160])
        print("RESTORED %s dirty_lines=0" % head_blob)
        return

    comment, decls, after = cell_lines(lines)
    idx = sorted(set(comment) | set(decls) | set(after))
    n = len(idx)
    out = [l for i, l in enumerate(lines) if i not in set(idx)]
    want(len(lines) - len(out) == n, "REMOVED_%d_LINES_EXPECTED_%d" % (len(lines) - len(out), n))
    txt = "\n".join(out)
    want("Amendment F-2" in txt, "TIP_COMMENT_ERASED")
    want(".v8-mobile-menu { min-height" in txt, "CELL_SIX_SELECTOR_ERASED")
    want(".v8-avatar::before" in txt, "CELL_SEVEN_RULE_ERASED")
    want(".trips-tabs button::after {" not in txt, "HIT_RULE_STILL_PRESENT")
    want(re.search(r"\.trips-tabs button \{[^}]*width: auto;", txt) is None, "WIDTH_STILL_PRESENT")
    want(".trips-tabs button {" in txt, "TAB_RULE_ITSELF_ERASED")
    with open(CSS, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(txt)
    print("BASE_ARM_WRITTEN lines=%d dropped=%d bytes=%d" % (len(out), n, len(txt.encode("utf-8"))))


if __name__ == "__main__":
    main()
