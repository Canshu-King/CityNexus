"""Gate: a ledger block counts as delivered only when the ledger itself says so.

Twice in this shift the applier printed INSERTED for a block that never reached the ledger: once I
reported it without reading the ledger back, and the check that finally read it found zero hits, so
the block had to be inserted again.  "The tool said OK" is not delivery - the ledger is.

What it asserts for a block title, all three together:
  * the title appears exactly once in CITYNEXUS_AGENT_CONTROL.md (zero = never landed, two = double-
    posted);
  * an archive copy named *.inserted_* exists under _qoder_ledger_inbox/_processed whose text contains
    that title (so the block that landed is the block that was written);
  * no un-inserted copy of that title is still sitting in the inbox.

--selftest proves the gate bites: a title nobody ever posted must read RED, and a real one from this
session must read GREEN.  A gate that cannot tell those two apart is not a gate.

A wrong --title now also prints the most recent landed titles.  This shift produced one false alarm of
that shape - I searched the ledger for a phrase the block never contained, read zero hits, and had to
check whether the ledger had lost a block when in fact I had mistyped.  A typo must not look like an
accident, so the gate shows what it did find.
"""

import argparse
import io
import os
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROCESSED = os.path.join(INBOX, "_processed")


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def recent_landed(limit):
    """The titles that actually landed recently, newest first - so a wrong --title reads as a typo."""
    entries = []
    for name in os.listdir(PROCESSED):
        if ".inserted_" not in name:
            continue
        path = os.path.join(PROCESSED, name)
        try:
            entries.append((os.stat(path).st_mtime, name, read(path).split("\n")[0].strip()))
        except OSError:
            continue
    entries.sort(key=lambda item: -item[0])
    return [(name, title) for _mtime, name, title in entries[:limit]]


def check(title, hint_limit=5):
    ledger_hits = read(LEDGER).count(title)
    archived = []
    for name in sorted(os.listdir(PROCESSED)):
        if ".inserted_" not in name:
            continue
        try:
            if title in read(os.path.join(PROCESSED, name)):
                archived.append(name)
        except OSError:
            continue
    pending = []
    for name in sorted(os.listdir(INBOX)):
        if not name.endswith(".md") or name.startswith("selftest"):
            continue
        try:
            if title in read(os.path.join(INBOX, name)):
                pending.append(name)
        except OSError:
            continue
    green = ledger_hits == 1 and len(archived) >= 1 and not pending
    print("LEDGER_HITS %d | ARCHIVED %s | STILL_IN_INBOX %s | VERDICT %s"
          % (ledger_hits, archived or "none", pending or "none", "GREEN" if green else "RED"))
    hinted = False
    if ledger_hits == 0:
        candidates = recent_landed(hint_limit)
        print("HINT the title matched nothing in the ledger; these are the %d most recent landed "
              "blocks (a wrong --title reads as a typo, not as an accident):" % len(candidates))
        for name, landed in candidates:
            print("     %s  <- %s" % (landed[:100], name))
        hinted = bool(candidates)
    return 0 if green else 7, hinted


def selftest():
    known = "交「屏上拿到英文原句」的分母与那条键的真实产地"
    bogus = "这块标题在本机任何账本里都不存在_zzz_selftest"
    print("SELFTEST known=%r" % known)
    rc_known, _ = check(known)
    print("SELFTEST bogus=%r (expected RED)" % bogus)
    rc_bogus, hinted = check(bogus)
    if rc_known != 0:
        print("SELFTEST_RED the gate could not confirm a block that is in the ledger")
        return 8
    if rc_bogus != 7:
        print("SELFTEST_RED the gate called an unseen title GREEN")
        return 9
    if not hinted:
        print("SELFTEST_RED an unseen title gave no recent-landed candidates to compare against")
        return 10
    print("SELFTEST_OK known block reads GREEN, an unseen title reads RED and lists what did land")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--title")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if not args.title:
        print("USE --title <block heading substring> | --selftest")
        sys.exit(2)
    sys.exit(check(args.title)[0])
