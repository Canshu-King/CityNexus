# -*- coding: utf-8 -*-
"""ORD-0557 push readback, taken live.

Every line pairs a command with the answer it actually gave, so whoever lands this block can re-fetch
each coordinate instead of trusting a transcription.  Generation arithmetic (HEAD~n) is avoided on
purpose: the branch was rebased twice while this order was in flight, and an offset would silently
point at a different commit than the one the readings were taken against.

Run: python review/taichenggong/push_readback_r1.py
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TARGET = "frontend/src/lib/failureAttribution.ts"
REF = "refs/heads/mirror/integration-frontend-apple-pass1"
BRANCH = "refs/heads/review/抬秤工-0557-r1"
OUT = os.path.join(HERE, "push_readback_r1.txt")
# The generation the arms, the differential and the screen readings compare against: the last tip
# whose copy of this file still carried the hardcoded Chinese fallbacks.
PINNED = "24a50a8aecf0a1fe4704400c687540d3e05d74fb"


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def main():
    rows = []
    say = rows.append

    def run(label, *args):
        say("$ %s" % label)
        say(git(*args) or "<empty answer>")

    run("git ls-remote origin %s" % BRANCH, "ls-remote", "origin", BRANCH)
    run("git ls-remote origin %s" % REF, "ls-remote", "origin", REF)
    run("git rev-parse HEAD  (local branch tip)", "rev-parse", "HEAD")
    run("git rev-parse --abbrev-ref HEAD  (branch name)", "rev-parse", "--abbrev-ref", "HEAD")
    say("$ is the pinned generation an ancestor of this branch?  git merge-base --is-ancestor %s HEAD"
        % PINNED)
    anc = subprocess.run(["git", "-C", REPO, "merge-base", "--is-ancestor", PINNED, "HEAD"],
                         capture_output=True, text=True)
    say("rc=%d (zero means yes)" % anc.returncode)

    blob_pinned = git("rev-parse", "%s:%s" % (PINNED, TARGET))
    blob_head = git("rev-parse", "HEAD:%s" % TARGET)
    say("$ git rev-parse %s:%s  (the bytes BEFORE this lane's edit)" % (PINNED[:12], TARGET))
    say(blob_pinned)
    say("$ git rev-parse HEAD:%s  (the bytes ON THIS BRANCH)" % TARGET)
    say(blob_head)
    say("$ git cat-file -t for each of the two blobs above")
    say("%s / %s" % (git("cat-file", "-t", blob_pinned), git("cat-file", "-t", blob_head)))
    say("$ git diff --numstat %s HEAD -- %s" % (PINNED, TARGET))
    say(git("diff", "--numstat", PINNED, "HEAD", "--", TARGET))

    live = (git("ls-remote", "origin", REF).split() or [""])[0]
    if len(live) == 40:
        subprocess.run(["git", "-C", REPO, "fetch", "--deepen=12", "origin", REF],
                       capture_output=True, text=True)
        blob_live = git("rev-parse", "%s:%s" % (live, TARGET))
        say("$ does the live tip already carry this branch's bytes for the file?")
        say("live tip %s blob %s ; branch blob %s ; equal=%s"
            % (live, blob_live, blob_head, blob_live == blob_head))

    bad = [r for r in rows if r == "<empty answer>" or not re.search(r"\S", r)]
    say("")
    say("VERDICT %s (empty answers: %d)" % ("PASS" if not bad else "RE-READ NEEDED", len(bad)))
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(rows) + "\n")
    sys.stdout.write("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
