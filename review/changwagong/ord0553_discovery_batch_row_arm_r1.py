#!/usr/bin/env python3
"""ORD-0553 / 长瓦工 -- the discovery batch read-back row must ask `formatWhen`, not slice an ISO.

The defect this arm guards: `RealCityDiscoveryPanel.tsx` rendered
`row.start_at.slice(0, 16).replace("T", " ")`, i.e. the server's ISO-8601 instant cut to sixteen
characters and put on the screen.  The stored value carries an offset (`2026-10-10T09:00:00+08:00`),
so the cut keeps the itinerary city's wall clock and drops the only thing that says so.

Deliberately NOT asserted here: the shape of the rendered string.  That is a screen reading and it
belongs to the e2e evidence, not to a static arm.  This arm says which function produced the text,
that the key it passes exists on BOTH books, and that the day list beside it was left alone.
"""

import argparse
import re
import sys

PANEL = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
HELPER = "frontend/src/lib/formatWhen.ts"
BATCH_ROW = '<li key={row.activity_id} data-testid="v13-discovery-batch-row">'
OLD_SHAPE = 'row.start_at.slice(0, 16).replace("T", " ")'
IMPORT_SHAPE = 'import { formatWhen } from "../../lib/formatWhen";'
DAYS_SHAPE = "landed.map((item) => item.start_at.slice(0, 10))"
CALL_SHAPE = "formatWhen(row.start_at"
BOOKS = [("en", re.compile(r"^const en: Dict = \{")), ("zhCN", re.compile(r"^const zhCN: Dict = \{"))]


def read(root, rel):
    with open(root + "/" + rel, encoding="utf-8") as fh:
        return fh.read()


def line_of(text, needle):
    for i, ln in enumerate(text.splitlines(), start=1):
        if needle in ln:
            return i, ln
    return None, None


def book_starts(text):
    starts = {}
    for i, ln in enumerate(text.splitlines(), start=1):
        for name, rx in BOOKS:
            if rx.match(ln):
                starts[name] = i
    return starts


def book_of(line, starts):
    en, zh = starts.get("en", 0), starts.get("zhCN", 0)
    if zh and line >= zh:
        return "zhCN"
    if en and line >= en:
        return "en"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True, help="tree root to measure")
    ap.add_argument("--out", help="write the reading here")
    args = ap.parse_args()
    root = args.tree.rstrip("/\\")

    panel = read(root, PANEL)
    dict_text = read(root, DICT)
    helper = read(root, HELPER)

    results = []

    def check(name, detail, ok):
        results.append((name, bool(ok), detail))

    row_line, _ = line_of(panel, BATCH_ROW)
    check("A1 batch row li still carries its testid", "%s:%s" % (PANEL, row_line), row_line)

    call_line, call_txt = line_of(panel, CALL_SHAPE)
    check("A2 the row time is produced by formatWhen", "%s:%s" % (PANEL, call_line), call_line)

    imp_line, _ = line_of(panel, IMPORT_SHAPE)
    check("A3 the helper is imported, not re-implemented here", "%s:%s" % (PANEL, imp_line), imp_line)

    old_line, _ = line_of(panel, OLD_SHAPE)
    check("A4 the raw ISO slice is gone from this file",
          "%s:%s" % (PANEL, old_line if old_line else "0 hits"), old_line is None)

    days_line, _ = line_of(panel, DAYS_SHAPE)
    check("A5 the day list beside it was left alone", "%s:%s" % (PANEL, days_line), days_line)

    m = re.search(r'pending:\s*t\("([^"]+)"\)', call_txt or "")
    key = m.group(1) if m else None
    check("A6 the fallback names a dictionary key, not a written literal",
          "%s:%s" % (PANEL, call_line), key)

    starts = book_starts(dict_text)
    arms = {}
    for i, ln in enumerate(dict_text.splitlines(), start=1):
        if '"%s"' % key in ln if key else False:
            arms[book_of(i, starts)] = (i, ln.strip())
    check("A7 that key exists on BOTH books",
          "%s:%s,%s" % (DICT, arms.get("en", (0,))[0], arms.get("zhCN", (0,))[0]),
          set(arms) == {"en", "zhCN"})

    helper_line, _ = line_of(helper, "export function formatWhen(")
    check("A8 the helper really exports formatWhen", "%s:%s" % (HELPER, helper_line), helper_line)

    fails = [r for r in results if not r[1]]
    lines = ["DISCOVERY_BATCH_ROW_ARM %s" % ("RED" if fails else "GREEN"), "tree=%s" % root]
    for name, ok, detail in results:
        lines.append("%s %s | %s" % ("PASS" if ok else "FAIL", name, detail))
    for book, (i, ln) in sorted(arms.items()):
        lines.append("book=%s %s:%d %s" % (book, DICT, i, ln))
    text = "\n".join(lines) + "\n"
    sys.stdout.buffer.write(text.encode("utf-8"))
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
