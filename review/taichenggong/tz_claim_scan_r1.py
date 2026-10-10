# -*- coding: utf-8 -*-
"""ORD-0553 timezone follow-up: claim surface for frontend/src/features/execution/V10LiveExecutionPanel.tsx.

Three channels, read live, before a byte is touched:

  A  the row this order names, re-read on the tip that is answering right now;
  B  every remote review branch whose name carries 0553, this file's blob on each, and whether that
     blob differs from the tip's -- a branch carrying the tip's bytes is not an editor of this file;
  C  the ledger's claim lines naming this file, and the inbox's undelivered blocks naming it.

Run: python review/taichenggong/tz_claim_scan_r1.py
Exit: 0 surface clear / 1 someone else is in this file / 2 something could not be read
"""

import ast
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def find_moodle(start):
    cur = start
    for _ in range(8):
        cur = os.path.dirname(cur)
        if os.path.isfile(os.path.join(cur, "CITYNEXUS_AGENT_CONTROL.md")):
            return cur
    raise SystemExit("2 cannot locate the ledger above %s" % start)


MOODLE = find_moodle(HERE)
LEDGER = os.path.join(MOODLE, "CITYNEXUS_AGENT_CONTROL.md")
INBOX = os.path.join(MOODLE, "_qoder_ledger_inbox")
TARGET = "frontend/src/features/execution/V10LiveExecutionPanel.tsx"
STEM = os.path.basename(TARGET)
REF = "refs/heads/mirror/integration-frontend-apple-pass1"
ROW = 85
LANE = "review/抬秤工"
OUT = os.path.join(HERE, "tz_claim_scan_r1.txt")

lines = []
failures = []


def say(text):
    lines.append(text)


def check(name, ok, detail):
    say("%-4s %s :: %s" % ("OK" if ok else "RED", name, detail))
    if not ok:
        failures.append(name)


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def main():
    tip = git("ls-remote", "origin", REF).split()[:1]
    tip = tip[0] if tip else ""
    if not re.fullmatch(r"[0-9a-f]{40}", tip):
        raise SystemExit("2 ls-remote gave no 40-hex tip")
    say("0 tip read live: %s" % tip)
    subprocess.run(["git", "-C", REPO, "fetch", "--deepen=60", "origin", REF], capture_output=True)

    # A -- the row itself, straight off that tip
    shown = git("show", "%s:%s" % (tip, TARGET))
    if not shown:
        raise SystemExit("2 could not read the file at that tip")
    at = shown.splitlines()[ROW - 1].strip()
    say("A row %s of that tip's bytes: %s" % (ROW, at[:120]))
    check("A1 the row the order names is still the row", "toLocaleTimeString([], {" in at,
          "%s:%d reads: %s" % (TARGET, ROW, at[:90]))
    tip_blob = git("rev-parse", "%s:%s" % (tip, TARGET))
    say("A2 file blob on that tip: %s" % tip_blob)
    # The file's own history on the authoritative line, so a branch carrying an OLD version is not
    # mistaken for a branch editing the file (the first cut of this arm made exactly that mistake).
    historical = set()
    for rev in git("rev-list", tip, "--", TARGET).split():
        b = git("rev-parse", "%s:%s" % (rev, TARGET))
        if b:
            historical.add(b)
    say("A2b blobs this file has had along the fetched part of the authoritative line: %d (%s)"
        % (len(historical), " ".join(sorted(x[:10] for x in historical))))
    zoned = [(i + 1, ln.strip()[:70]) for i, ln in enumerate(shown.splitlines())
             if "timeZone: clockZone" in ln]
    say("A3 the same file already names a zone at: %s" % zoned)
    baseline = [(i + 1, ln.strip()[:70]) for i, ln in enumerate(shown.splitlines())
                if re.search(r'"en-GB"|zh-CN" \? "zh-CN"', ln)]
    say("A4 the same file's explicit-locale baseline: %s" % baseline[:4])

    # B -- sibling branches that could be editing this file right now
    refs = [ln.split()[1] for ln in git("ls-remote", "origin", "refs/heads/review/*").splitlines()
            if "-0553" in ln and not ln.split()[1].startswith("refs/heads/review/抬秤工")]
    say("B remote review branches whose name carries 0553: %d" % len(refs))
    editors = 0
    if refs:
        subprocess.run(["git", "-C", REPO, "fetch", "--depth=1", "origin"] + refs, capture_output=True)
        for ref in refs:
            sha = git("ls-remote", "origin", ref).split()[:1]
            blob = git("rev-parse", "%s:%s" % (sha[0], TARGET)) if sha else ""
            if blob and blob != tip_blob and blob not in historical:
                editors += 1
            kind = ("SAME_AS_TIP" if blob == tip_blob
                    else "a version the authoritative line already carried (stale base, not an edit)"
                    if blob in historical else "BYTES THE LINE HAS NEVER HAD - possible editor")
            say("  %-46s blob=%s %s" % (ref.split("/")[-1], blob[:12], kind))
    check("B1 no sibling 0553 branch carries other bytes for this file", editors == 0,
          "%d branch(es) differ from the tip on this file" % editors)

    # C -- the ledger and the inbox
    text = open(LEDGER, encoding="utf-8", errors="replace").read()
    claim_rx = re.compile(r"(认领|自认领|取的?是|归我|已归|归\s|道具名|开工自证|在飞|下一格)")
    hits = [i + 1 for i, ln in enumerate(text.splitlines()) if STEM in ln and claim_rx.search(ln)]
    say("C ledger lines naming this file with a claim word: %d" % len(hits))
    for n in hits[:6]:
        say("  CITYNEXUS_AGENT_CONTROL.md:%d %s" % (n, text.splitlines()[n - 1].strip()[:120]))

    named = []
    if os.path.isdir(INBOX):
        for name in sorted(os.listdir(INBOX)):
            if not name.endswith(".md"):
                continue
            body = open(os.path.join(INBOX, name), encoding="utf-8", errors="replace").read()
            if STEM in body or ("时区口径" in body and "V10" in body):
                named.append(name)
    say("C2 inbox blocks naming this file or the timezone table with this panel: %d" % len(named))
    for name in named:
        say("   %s" % name)
    check("C3 nobody has an undelivered block on this file", named == [],
          "inbox names: %s" % (named or "none"))

    say("VERDICT %s" % ("PASS surface clear for this lane" if not failures
                        else "FAIL " + ",".join(failures)))
    out = "\n".join(lines) + "\n"
    open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    sys.stdout.write(out)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    main()
