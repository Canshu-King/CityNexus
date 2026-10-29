"""Correct one coordinate inside section 14.10 without rewriting the section.

The inventory receipt's own lines are: header at 1, the bucket count at 2, the group count at 4 and
the file count at 5.  The section cited the header line for all three numbers, so the correction is
appended rather than edited in place, matching how every other wrong coordinate in this report has
been handled.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.10 勘误（同班次）：那行「回执 bw194-unattributed-inventory.txt:1」的坐标写偏了一格 —— 三个数各自在
`trial/results/20261026_gozero/bw194-unattributed-inventory.txt:2`（桶里的枚数）、`:4`（分组数）、`:5`（文件数），
`:1` 只是标题行。正文照旧不改，勘误另起一行。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.10 勘误" in text:
        print("ABORT the correction is already there")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED bytes_added=%d hits=%d" % (
        len(block.encode("utf-8")), read_back.count("14.10 勘误")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
