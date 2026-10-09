"""ORD-0557 claim scan for frontend/src/lib/failureAttribution.ts.

Answers one question before any byte is touched: does another lane own this file?
Both channels are read, because ls-remote cannot see a branch that only lives on this
machine and the ledger cannot see a block still sitting in the inbox.

Run: python review/taichenggong/claim_scan_r1.py   (from the repo root)
"""

import ast
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def find_moodle(start):
    """Walk up until the ledger is actually there: a worktree sits one level deeper than
    the main checkout, and a silently wrong root would read back as "no claims anywhere"."""
    cur = start
    for _ in range(8):
        cur = os.path.dirname(cur)
        if os.path.isfile(os.path.join(cur, "CITYNEXUS_AGENT_CONTROL.md")):
            return cur
    raise SystemExit("2 cannot locate CITYNEXUS_AGENT_CONTROL.md above %s" % start)


MOODLE = find_moodle(HERE)
LEDGER = os.path.join(MOODLE, "CITYNEXUS_AGENT_CONTROL.md")
INBOX = os.path.join(MOODLE, "_qoder_ledger_inbox")
TARGET = "frontend/src/lib/failureAttribution.ts"
TIP = "7f08160743b3b46e600c2c05e6863eaabd722f54"
REF = "refs/heads/mirror/integration-frontend-apple-pass1"
OUT = os.path.join(HERE, "claim_scan_r1.txt")
LANE = "review/抬秤工"


def git(*args):
    proc = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return proc.stdout.strip()


def main():
    say_lines = []
    say = say_lines.append

    live = (git("ls-remote", "origin", REF).split() or ["<no answer>"])[0]
    say("0 roots: repo=%s ledger=%s inbox=%s" % (REPO, LEDGER, INBOX))
    say("1 authoritative tip read now via ls-remote: %s" % live)
    tip_blob = git("rev-parse", "%s:%s" % (TIP, TARGET))
    say("2 target file blob on that tip: %s" % tip_blob)

    carriers = git("rev-list", "--branches", "--not", TIP, "--", TARGET).split()
    say("3 commits on this machine's branch heads that touch the target and are not in the tip: %d"
        % len(carriers))
    for sha in carriers:
        meta = git("log", "-1", "--format=%h|%ad|%s", "--date=format:%m-%d_%H:%M", sha)
        numstat = git("diff", "--numstat", "%s^" % sha, sha, "--", TARGET) or "<parent not local>"
        blob = git("rev-parse", "%s:%s" % (sha, TARGET))
        holders = [h for h in git("for-each-ref", "--contains", sha, "--format=%(refname:short)",
                                  "refs/heads/").split() if not h.startswith(LANE)]
        same = "produces the tip bytes (base drift, not an edit)" if blob == tip_blob \
            else "produces bytes the tip does not have"
        say("4 commit=%s" % meta[:90])
        say("5   numstat=[%s] blob=%s -> %s" % (numstat, blob[:12], same))
        say("6   heads carrying it: %s" % (",".join(holders)[:120] or "<none>"))

    text = open(LEDGER, encoding="utf-8", errors="replace").read()
    stem = os.path.basename(TARGET)
    say("7 ledger lines naming the file stem: %d" % len(re.findall(re.escape(stem), text)))
    claim_re = re.compile(r"(认领|自派清单取|已在飞|下一格|判过不动)")
    hits = [ln for ln in text.splitlines() if stem in ln and claim_re.search(ln)]
    say("8 ledger lines that both name the file and use a claim word: %d" % len(hits))
    for ln in hits:
        say("9 %s" % ln.strip()[:180])

    named = []
    if os.path.isdir(INBOX):
        for name in sorted(os.listdir(INBOX)):
            if not name.endswith(".md"):
                continue
            body = open(os.path.join(INBOX, name), encoding="utf-8", errors="replace").read()
            if stem in body or "ORD-0557" in body:
                named.append(name)
    say("10 inbox blocks naming the file or order 0557: %d" % len(named))
    for name in named:
        say("11 %s" % name)

    out_text = "\n".join(say_lines) + "\n"
    open(OUT, "w", encoding="utf-8", newline="\n").write(out_text)
    sys.stdout.write(out_text)


if __name__ == "__main__":
    ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    main()
