# -*- coding: utf-8 -*-
"""ORD-0557/0558-era claim surface: which product files do the six new tables name, and who is named on each.

One pass over the ledger text plus the archived inbox receipts. Nothing is inferred from memory: a file
is claimable only when the count of claim lines naming it is zero.

Run: python review/taichenggong/claim_surface_r2.py
Exit: 0 with a table / 2 if the ledger cannot be read.
"""

import ast
import os
import re
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
PROCESSED = os.path.join(INBOX, "_processed")
OUT = os.path.join(HERE, "claim_surface_r2.txt")

# The six tables the commander published, matched by their own heading words.
TABLES = [("单复数", "单复数 56 行"), ("缺键", "字典里没有的键"), ("空态缺动作", "空态缺动作"),
          ("时区口径", "时区口径"), ("大表", "内联双语「照抄就能交」施工表（大表"),
          ("兜底行", "内联双语兜底行")]
FILE_RX = re.compile(r"frontend/src/[\w./\-]+\.(?:tsx|ts)")
LANE_RX = re.compile(r"[\u4e00-\u9fff]{2,4}(?:工|匠|手|者)")
CLAIM_RX = re.compile(r"(认领|自认领|取的?是|归我|已归|＝|归\s|道具名|开工自证|下一格)")

rows = []
say = rows.append


def main():
    text = open(LEDGER, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    say("0 ledger lines read: %d" % len(lines))

    # headings of the six tables, located by their own words rather than by a stored line number
    heads = {}
    for i, ln in enumerate(lines, 1):
        if not ln.startswith("### "):
            continue
        for name, needle in TABLES:
            if needle in ln and name not in heads:
                heads[name] = (i, ln.strip()[:110])
    say("1 table headings found by their own words: %d of 6" % len(heads))
    for name, (n, h) in sorted(heads.items(), key=lambda kv: kv[1][0]):
        say("2 %-8s CITYNEXUS_AGENT_CONTROL.md:%d :: %s" % (name, n, h))

    # every product file named anywhere in the ledger, with the count of claim lines naming it
    per_file = {}
    for i, ln in enumerate(lines, 1):
        for f in set(FILE_RX.findall(ln)):
            entry = per_file.setdefault(f, {"named": 0, "claims": [], "lines": []})
            entry["lines"].append(i)
            if CLAIM_RX.search(ln):
                entry["named"] += 1
                lane = LANE_RX.search(ln)
                who = lane.group(0) if lane else "?"
                entry["claims"].append("CITYNEXUS_AGENT_CONTROL.md:%d(%s)" % (i, who))
    say("3 distinct product files named in the ledger: %d" % len(per_file))

    # which of those appear inside one of the six tables' blocks (the actionable denominator)
    in_tables = {}
    for name, (start, _) in heads.items():
        body = []
        for ln in lines[start:]:
            if ln.startswith("### "):
                break
            body.append(ln)
        for f in set(x for ln in body for x in FILE_RX.findall(ln)):
            in_tables.setdefault(f, []).append(name)

    say("4 files named inside the six tables: %d" % len(in_tables))
    free = []
    for f, tables in sorted(in_tables.items()):
        entry = per_file.get(f, {"named": 0, "claims": []})
        if entry["named"] == 0:
            free.append((f, tables))
        say("5 %-58s tables=%s claim_lines=%d %s"
            % (f, "/".join(tables), entry["named"], "; ".join(entry["claims"][:2])[:110]))
    say("6 claimable by that count (zero claim lines): %d" % len(free))
    for f, tables in free:
        say("7 FREE %-55s in %s" % (f, "/".join(tables)))

    # archived receipts: a lane that already delivered a file is out of play
    delivered = {}
    if os.path.isdir(PROCESSED):
        for name in os.listdir(PROCESSED):
            if not name.endswith(".md") and ".inserted_" not in name:
                continue
            p = os.path.join(PROCESSED, name)
            try:
                body = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for f in set(FILE_RX.findall(body)):
                delivered.setdefault(f, []).append(name)
    say("8 files named in archived inbox receipts: %d" % len(delivered))
    for f, tables in free:
        d = delivered.get(f)
        if d:
            say("9 %-55s already named in receipts: %s" % (f, d[0][:70]))

    out = "\n".join(rows) + "\n"
    open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    sys.stdout.write(out)


if __name__ == "__main__":
    ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    main()
