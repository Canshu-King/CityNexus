"""Erratum for section 14.13: two marker counts were read with a line-counting ruler.

Section 14.13 quoted counts taken with grep -c, which counts lines.  The tracked artifact
bw213 counts occurrences, and the two differ for one file.  The conclusion is unaffected -- what
matters is that the failing call itself attaches no credential, and that is now quoted line by line
in the artifact -- but the numbers on the page have to match the artifact a reader can fetch.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.13 勘误（同班次）：那两枚「auth 痕迹计数」用的是按行数数的尺（grep -c），换到落盘的那把按出现次数数的尺上读数不同 ——
`tests/test_agent_mission_runtime.py` 现读两处（不是正文写的一处），`tests/test_v12_authoritative_trip_execution.py` 三处不变；
逐枚计数与出事那一行的调用原文都在 `trial/results/20261026_gozero/bw213-keyerror-family-evidence.txt:5` 往下
（分家闸：那一族在普查表里的行数 `trial/results/20261026_gozero/bw213-keyerror-family-evidence.txt:2` 读数为十，
与本尺点数强制相等）。正文结论不动：出事那一行本身没挂任何头，所以是同一族私有读口的 401 体。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.13 勘误" in text:
        print("ABORT the erratum is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.13 勘误"):
            head_line = i
    print("APPENDED bytes_added=%d hits=%d line=%s"
          % (len(block.encode("utf-8")), read_back.count("14.13 勘误"), head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
