# -*- coding: utf-8 -*-
"""ORD-0552 claim surface for the plan version history panel (lane 抬秤工).

The 逐文件账 marks a slot either as belonging to a named lane (`｜ 铁盒工`) or as open
(`｜ 自认领（先写进交块者得）`).  A grep for the file name cannot tell those apart, so this does:
it splits every ledger line naming the two files into an open slot, a named owner, or a mention,
reads the same question off the undelivered inbox, and then looks at what the remote branches of
this order actually carry for these two files.

Run: python review/taichenggong/claim_scan_0552_r1.py
Exit: 0 open for this lane / 1 someone already owns it / 2 nothing could be read
"""

import ast
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FILES = ["PlanVersionHistoryPanel.tsx", "planVersionHistoryCopy.ts"]
ORDER_REFS = "-0552"


def find_moodle(start):
    cur = start
    for _ in range(8):
        cur = os.path.dirname(cur)
        if os.path.isfile(os.path.join(cur, "CITYNEXUS_AGENT_CONTROL.md")):
            return cur
    raise SystemExit("2 cannot find the ledger above %s" % start)


MOODLE = find_moodle(HERE)
LEDGER = os.path.join(MOODLE, "CITYNEXUS_AGENT_CONTROL.md")
INBOX = os.path.join(MOODLE, "_qoder_ledger_inbox")
OUT = os.path.join(HERE, "claim_scan_0552_r1.txt")
REF = "refs/heads/mirror/integration-frontend-apple-pass1"
LANE = "抬秤工"

rows = []
failures = []


def say(t):
    rows.append(t)


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def main():
    tip = (git("ls-remote", "origin", REF).split() or [""])[0]
    if len(tip) != 40:
        raise SystemExit("2 no 40-hex tip from ls-remote")
    say("0 tip read live: %s" % tip)
    lines = open(LEDGER, encoding="utf-8", errors="replace").read().splitlines()

    named_owner = []
    open_slots = []
    mentions = 0
    for i, ln in enumerate(lines, 1):
        if not any(f in ln for f in FILES):
            continue
        mentions += 1
        if "自认领" in ln:
            open_slots.append((i, ln.strip()[:110]))
        elif re.search(r"[｜|]\s*[\u4e00-\u9fff]{2,5}工", ln) or re.search(r"归\s*[\u4e00-\u9fff]{2,5}工", ln):
            named_owner.append((i, ln.strip()[:110]))
    say("1 ledger lines naming either file: %d" % mentions)
    for i, t in open_slots[:4]:
        say("2 OPEN slot  CITYNEXUS_AGENT_CONTROL.md:%d :: %s" % (i, t))
    for i, t in named_owner[:4]:
        say("3 OWNER line CITYNEXUS_AGENT_CONTROL.md:%d :: %s" % (i, t))
    say("4 lines assigning these files to another lane: %d" % len(named_owner))

    inbox_hits = []
    if os.path.isdir(INBOX):
        for name in sorted(os.listdir(INBOX)):
            if not name.endswith(".md"):
                continue
            body = open(os.path.join(INBOX, name), encoding="utf-8", errors="replace").read()
            if any(f in body for f in FILES):
                claim = bool(re.search(r"(认领|取的?是|归我|本车道)", body)) and FILES[0] in body
                inbox_hits.append((name, claim))
    say("5 inbox blocks naming these files: %d" % len(inbox_hits))
    for name, claim in inbox_hits:
        say("6   %s claims_it=%s" % (name, claim))

    refs = [ln.split()[1] for ln in git("ls-remote", "origin", "refs/heads/review/*").splitlines()
            if ORDER_REFS in ln and LANE not in ln]
    say("7 remote review branches whose name carries this order: %d" % len(refs))
    editors = 0
    if refs:
        subprocess.run(["git", "-C", REPO, "fetch", "--depth=1", "origin"] + refs, capture_output=True)
        for ref in refs:
            sha = (git("ls-remote", "origin", ref).split() or [""])[0]
            for f in FILES:
                path = ("frontend/src/features/studio/" + f)
                blob = git("rev-parse", "%s:%s" % (sha, path)) if sha else ""
                head_blob = git("rev-parse", "%s:%s" % (tip, path))
                if blob and blob != head_blob:
                    editors += 1
                    say("8   %s carries other bytes for %s (%s)" % (ref.split("/")[-1], f, blob[:12]))
    say("9 branches carrying bytes the tip does not have for these files: %d" % editors)

    if named_owner:
        failures.append("a ledger line assigns these files to another lane")
    if any(c for _, c in inbox_hits):
        failures.append("an undelivered inbox block claims them")
    if editors:
        failures.append("an in-flight branch edits them")
    say("VERDICT %s" % ("PASS open for this lane" if not failures else "FAIL " + "; ".join(failures)))
    out = "\n".join(rows) + "\n"
    open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    sys.stdout.write(out)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    main()
