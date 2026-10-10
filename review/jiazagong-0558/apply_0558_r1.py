"""ORD-0558 lane instrument (加闸工): copy the commander-blessed "改后整行" straight out of the
CN draft into frontend/src/features/progress/journeyProgress.ts, byte-exact, and write a
before/after readout. Refuses to run if any live line does not match the draft's 原文 column."""

import io
import json
import re
import sys

DRAFT = r"D:\moodle\_cn8_plural_fix_0126.txt"
TARGET = r"D:\moodle\_qoder_jiazagong_0558\frontend\src\features\progress\journeyProgress.ts"
IMPORT_ANCHOR = 'import { TERMINAL_ACTIVITY_STATES } from "../../lib/executionWindow";'
IMPORT_NEW = 'import { englishCountNoun } from "../../lib/plural";'
OUT = r"D:\moodle\_qoder_jiazagong_0558\apply_readout_r1.json"
ROW_IDS = (96, 99, 102)

def unpad(cell):
    # the draft separates columns with " | ", so split("|") leaves exactly one pad space per side;
    # stripping more would eat the code line's own indentation.
    if cell.startswith(" "):
        cell = cell[1:]
    if cell.endswith(" "):
        cell = cell[:-1]
    return cell

def draft_rows():
    rows = {}
    for line in io.open(DRAFT, encoding="utf-8", errors="replace").read().splitlines():
        parts = line.split("|")
        if len(parts) < 7 or not re.match(r"^\s*\d+\s*$", parts[0]):
            continue
        rid = int(parts[0].strip())
        if "journeyProgress.ts" not in parts[1]:
            continue
        rows[rid] = [p.strip() for p in parts[:2]] + [unpad(parts[2])] + [p.strip() for p in parts[3:5]] + [unpad(parts[5])] + [p.strip() for p in parts[6:]]
    return rows

def main():
    rows = draft_rows()
    missing = [r for r in ROW_IDS if r not in rows]
    if missing:
        raise SystemExit("ABORT draft rows not found: %r" % (missing,))

    live = io.open(TARGET, encoding="utf-8", newline="").read().split("\n")
    report = []
    for rid in ROW_IDS:
        parts = rows[rid]
        coord = parts[1]
        orig = parts[2]
        after = parts[5]
        lineno = int(coord.split(":")[1])
        idx = lineno - 1
        if idx >= len(live):
            raise SystemExit("ABORT live file shorter than %d" % lineno)
        if live[idx] != orig:
            print("MISMATCH at %s\n  live  : %r\n  draft : %r" % (coord, live[idx], orig))
            raise SystemExit("ABORT live line does not equal the draft 原文 column")
        if "englishCountNoun" not in after:
            raise SystemExit("ABORT draft 改后整行 carries no ruler: %s" % coord)
        report.append({"coord": coord, "before": live[idx], "after": after})
        live[idx] = after

    text = "\n".join(live)
    if IMPORT_NEW in text:
        raise SystemExit("ABORT import line already present")
    if text.count(IMPORT_ANCHOR) != 1:
        raise SystemExit("ABORT import anchor not unique")
    text = text.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + "\n" + IMPORT_NEW, 1)
    io.open(TARGET, "w", encoding="utf-8", newline="").write(text)

    after_lines = text.split("\n")
    for r in report:
        r["after_lineno_live"] = None
        n = int(r["coord"].split(":")[1])
        for cand in range(n - 3, n + 4):
            if 0 <= cand - 1 < len(after_lines) and after_lines[cand - 1] == r["after"]:
                r["after_lineno_live"] = cand
        if r["after_lineno_live"] is None:
            raise SystemExit("ABORT applied line not found back in the file")
    import_line = [i + 1 for i, l in enumerate(after_lines) if l == IMPORT_NEW]
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps({"rows": report, "import_lines": import_line}, ensure_ascii=False, indent=1))
    print("APPLIED rows=%d import_at=%s" % (len(report), import_line))
    for r in report:
        print("%s -> %s" % (r["coord"], r["after_lineno_live"]))
    return 0

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
