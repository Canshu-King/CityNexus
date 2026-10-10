"""Repair the desktop note: my append helper had the section filename hardcoded, so the 21:35 block
went in four times while the 21:56 / 22:35 blocks never landed.

Safe by construction:
  * backs the current file up first (nothing unrecoverable),
  * keeps the user-visible original verbatim up to the first duplicated header,
  * rebuilds from the on-disk section files in chronological order,
  * writes to a temp file, verifies every marker count == 1, and only then swaps it in,
  * re-reads after the swap and reports counts again.
"""

import io
import os
import re
import shutil
import sys

NOTE = r"C:\Users\仓鼠王\Desktop\CityNexus_包工头留言.txt"
BAK = r"C:\Users\仓鼠王\Desktop\CityNexus_包工头留言_bak_2235.txt"
TMP = r"C:\Users\仓鼠王\Desktop\CityNexus_包工头留言.rebuild.tmp"
SECTION_DIR = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
SECTIONS = ("note_section_2135.txt", "note_section_2156.txt", "note_section_2235.txt")
MARKERS = ("包工头留言（2026-09-21 18:4x）", "包工头: 21:35 现场快报", "包工头: 21:56 补充", "包工头: 22:3x 补充")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cur = io.open(NOTE, encoding="utf-8", newline="").read()
    print("current bytes", len(cur.encode()), "| 21:35 copies:", cur.count("包工头: 21:35 现场快报"))

    first = cur.find("包工头: 21:35 现场快报")
    if first < 0:
        print("ABORT: no duplicated header found - refusing to rebuild from an unexpected shape")
        return 2
    head = cur[:first].rstrip("\n") + "\n"
    if not head.startswith("包工头留言（2026-09-21 18:4x）"):
        print("ABORT: the original note does not start where expected")
        return 2

    parts = [head]
    for name in SECTIONS:
        p = os.path.join(SECTION_DIR, name)
        body = io.open(p, encoding="utf-8", newline="\n").read().strip("\n") + "\n"
        if "包工头" not in body.split("\n")[0]:
            print("ABORT: section file lacks its own header:", name)
            return 2
        parts.append("\n" + body)
    new = "".join(parts)

    for m in MARKERS:
        c = new.count(m)
        if c != 1:
            print("ABORT: marker count %d for %r" % (c, m))
            return 3

    shutil.copyfile(NOTE, BAK)
    io.open(TMP, "w", encoding="utf-8", newline="").write(new)
    rb = io.open(TMP, encoding="utf-8", newline="").read()
    if rb != new:
        print("ABORT: temp readback mismatch")
        return 4
    os.replace(TMP, NOTE)
    final = io.open(NOTE, encoding="utf-8", newline="").read()
    print("after swap: bytes %d (was %d), lines %d" % (len(final.encode()), len(cur.encode()), final.count("\n")))
    print("backup at", BAK, len(io.open(BAK, 'rb').read()), "bytes")
    for m in MARKERS:
        print("   %dx  %s" % (final.count(m), m[:34]))
    dup = re.findall(r"包工头: 2[12]:\d+x? [^\n]{0,24}", final)
    print("section headers in order:", [d[:22] for d in dup])
    print("tail:", final[-120:].replace("\n", " | "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
