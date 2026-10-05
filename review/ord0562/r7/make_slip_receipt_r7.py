# -*- coding: utf-8 -*-
"""Record the shared-tree slip and its restoration, with the commands actually run for it.

Nothing here is typed from memory: each line is the stdout of the command named above it, captured in this
same run, so the block can cite the file and a reader can re-run the two read-back commands themselves.
"""

import io
import os
import subprocess

REPO = r"D:/moodle/CityNexus"
PATH = "frontend/src/app/V8Experience.tsx"
OUT = r"D:/moodle/_ord0568_r3/r7/shared_tree_slip_r7.txt"

env = dict(os.environ)
for gone in ("HTTP_PROXY", "HTTPS_PROXY"):
    env.pop(gone, None)


def run(*args):
    proc = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, env=env)
    return proc.returncode, proc.stdout.decode("utf-8", "replace").rstrip("\r\n")


lines = []
lines.append("Shared-tree slip and restoration, lane cff87c64, every line below is the stdout of the command "
             "printed above it, read in this same run.")

rc, head = run("rev-parse", "HEAD")
lines.append("$ git -C D:/moodle/CityNexus rev-parse HEAD          # rc=%d" % rc)
lines.append(head)
lines.append("")

rc, blob = run("rev-parse", "HEAD:%s" % PATH)
lines.append("$ git -C D:/moodle/CityNexus rev-parse HEAD:%s   # rc=%d" % (PATH, rc))
lines.append(blob)
lines.append("")

rc, ho = run("hash-object", os.path.join(REPO, PATH))
lines.append("$ git -C D:/moodle/CityNexus hash-object %s          # rc=%d (worktree bytes)" % (PATH, rc))
lines.append(ho)
lines.append("")

rc, st = run("status", "--porcelain", "--", PATH)
lines.append("$ git -C D:/moodle/CityNexus status --porcelain -- %s   # rc=%d" % (PATH, rc))
lines.append(st if st else "(no output: the path is clean against HEAD, staged and unstaged)")
lines.append("")

rc, allst = run("status", "--porcelain")
others = len([x for x in allst.split("\n") if x.strip()])
lines.append("$ git -C D:/moodle/CityNexus status --porcelain | count of non-empty lines   # rc=%d" % rc)
lines.append(str(others))
lines.append("(that is everybody else's dirty set in the shared tree; this run touched one path and left it "
             "byte-identical, so none of those lines changed hands)")
lines.append("")
lines.append("byte-equal read-back: %s" % str(ho == blob))

text = "\n".join(lines) + "\n"
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)
print(text)
if ho != blob:
    raise SystemExit("REFUSED: the worktree bytes are not the committed bytes -- not restored")
print("OK: worktree hash-object equals HEAD's blob for that path")
