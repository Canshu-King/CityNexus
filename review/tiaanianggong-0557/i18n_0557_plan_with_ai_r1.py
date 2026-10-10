#!/usr/bin/env python
"""ORD-0557 兜底行表 · PlanWithAiSheet.tsx lane instrument (提案工).

The table's rule is "copy it and it ships": the key name and the English wording come from the
CN draft's two columns verbatim, and the Chinese wording is the sentence already painted on screen.
This tool therefore never takes a key or a sentence from me -- it parses the draft row, cuts the zh
literal out of the line the coordinate points at on the current tip, and refuses anything the draft
itself marked EXCLUDED.

    python i18n_0557_plan_with_ai_r1.py --side dict
    python i18n_0557_plan_with_ai_r1.py --side product
    python i18n_0557_plan_with_ai_r1.py --verify
    python i18n_0557_plan_with_ai_r1.py --rows          (what the draft gives this file)
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("CNX_LANE_ROOT") or os.path.dirname(os.path.dirname(HERE))
PRODUCT_REL = "frontend/src/features/planning/PlanWithAiSheet.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
PRODUCT = os.path.join(ROOT, *PRODUCT_REL.split("/"))
DICT = os.path.join(ROOT, *DICT_REL.split("/"))
DRAFT_GLOB = r"D:/moodle/_cn10_fb557draft_*.txt"
BASE = os.environ.get("CNX_LANE_BASE", "996f1b7588580a14fbbdec5301a6e4a7b70c93e4")

FAMILY_LAST_EN = re.compile(r'^  "planning\.', re.M)

# the draft's row for this coordinate carries two ternaries on one line; this is the arm we move
ARM = 'zh ? "开始规划" : "Plan my trip"'


def draft_rows():
    path = sorted(glob.glob(DRAFT_GLOB))[-1]
    rows = []
    for n, line in enumerate(io.open(path, encoding="utf-8", errors="replace"), 1):
        if PRODUCT_REL not in line:
            continue
        cols = [c.strip() for c in line.rstrip("\n").split("|")]
        if len(cols) < 4 or ":" not in cols[0]:
            continue
        rows.append({"draft_line": n, "path": path, "coord": cols[0], "text": cols[1],
                     "key": cols[2], "en": cols[3], "tail": cols[4] if len(cols) > 4 else ""})
    return rows


def shippable(rows):
    out = []
    for r in rows:
        if "EXCLUDED" in r["tail"] or r["key"] == "\u2014":
            continue
        out.append(r)
    return out


def read(path):
    return io.open(path, "r", encoding="utf-8", newline="").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def base_lines():
    """The literal pair is cut out of the BASE generation's line, so the check still works after the move."""
    import subprocess
    out = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (BASE, PRODUCT_REL)],
                         capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        raise SystemExit("ABORT cannot read base blob %s:%s" % (BASE, PRODUCT_REL))
    return out.stdout.splitlines()


def zh_en_from_line(row):
    """The zh side is whatever the screen already shows; cut it out of the base line, do not re-type it."""
    lines = base_lines()
    n = int(row["coord"].rsplit(":", 1)[1])
    body = lines[n - 1]
    if ARM not in body:
        raise SystemExit("ABORT line %d no longer carries the arm the draft names:\n%s" % (n, body))
    m = re.search(r'zh \? "([^"]*)" : "([^"]*)"', body[body.index(ARM):])
    if not m:
        raise SystemExit("ABORT cannot cut the pair out of line %d" % n)
    return m.group(1), m.group(2)


def insert_dict(text, key, en, zh):
    """Append one entry to the tail of the planning.* family on each side, keeping the two sides aligned."""
    nl = "\r\n" if "\r\n" in text else "\n"
    if '"%s":' % key in text:
        raise SystemExit("ABORT key already in dictionary: %s" % key)
    marker = "const zhCN"
    if text.count(marker) != 1:
        raise SystemExit("ABORT cannot split the two dictionary sides")
    for side, value in (("en", en), ("zh", zh)):
        head, tail = text.split(marker)
        block, base = (head, 0) if side == "en" else (tail, len(head) + len(marker))
        offs = [mm.start() for mm in FAMILY_LAST_EN.finditer(block)]
        if not offs:
            raise SystemExit("ABORT no planning.* family on the %s side" % side)
        at = base + block.index("\n", offs[-1]) + 1
        text = text[:at] + ('  "%s": "%s",' % (key, value)) + nl + text[at:]
    return text


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["dict", "product"])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--rows", action="store_true")
    a = ap.parse_args()
    rows = draft_rows()
    if a.rows:
        for r in rows:
            print("draft_line=%s coord=%s key=%s en=%s tail=%s" % (r["draft_line"], r["coord"], r["key"], r["en"], r["tail"]))
        print("rows_for_this_file=%s shippable=%s excluded=%s" % (len(rows), len(shippable(rows)), len(rows) - len(shippable(rows))))
        return 0
    ship = shippable(rows)
    if len(ship) != 1:
        raise SystemExit("ABORT expected the draft to give this file one shippable row, got %s" % len(ship))
    row = ship[0]
    key = row["key"]
    draft_en = row["en"]
    zh, line_en = zh_en_from_line(row)
    if line_en != draft_en:
        raise SystemExit("ABORT draft English wording %r is not the sentence on screen %r" % (draft_en, line_en))

    if a.verify:
        dic = read(DICT)
        prod = read(PRODUCT)
        en_pos = dic.find('  "%s": "%s",' % (key, draft_en))
        zh_pos = dic.find('  "%s": "%s",' % (key, zh))
        call = 't("%s")' % key
        prod_pos = prod.find(call)
        left = prod.count(ARM)
        ok = en_pos > 0 and zh_pos > 0 and prod_pos > 0 and left == 0
        print("%s | coord=%s | dict_en_line=%s | dict_zh_line=%s | prod_line=%s | leftover_arm=%s | wording=%s" % (
            key, row["coord"],
            line_of(dic, en_pos) if en_pos > 0 else "absent",
            line_of(dic, zh_pos) if zh_pos > 0 else "absent",
            line_of(prod, prod_pos) if prod_pos > 0 else "absent",
            left, "identical" if ok else "REFUSED"))
        return 0 if ok else 1

    if a.side == "dict":
        write(DICT, insert_dict(read(DICT), key, draft_en, zh))
        print("dict wrote one key on each side: %s" % key)
        return 0
    if a.side == "product":
        text = read(PRODUCT)
        if text.count(ARM) != 1:
            raise SystemExit("ABORT the arm occurs %s times" % text.count(ARM))
        write(PRODUCT, text.replace(ARM, 't("%s")' % key, 1))
        print("product moved one reading point onto %s" % key)
        return 0
    raise SystemExit("ABORT give --side, --verify or --rows")


if __name__ == "__main__":
    sys.exit(main())
