"""Append a second correction line to section 14.17: the node ledger now cross-reads the extended ruler.

The census published 'not yet attributed = 0' while the first node ledger still carried a
'not yet attributed' bucket of thirty-nine, because it used only the base class table.  Both artifacts
now read the same refinement set, so a commander cross-reading them sees one story; the label was also
fixed to say what is actually missing (the side, not the cause).

CRLF-dominant report: explicit CRLF and the byte-identity assertion.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.17 补二（同班次）：两把尺对同一枚数各说一套的隐患也一并收了 —— node id 账现在直接 import §14.10 那把扩展尺的类别表，
不再自带一份「未定性」桶。现读：账本里 `not yet attributed` 这一桶行数为零
（`trial/results/20261026_gozero/bw234-red-node-ledger.txt:4` 现读二十七个桶求和仍等于 pytest 自报的那枚数），
而原来那三十九枚的去向逐桶可查：带因未定侧的（如答复被服务端判 `VALIDATION_ERROR` 那八枚，
`trial/results/20261026_gozero/bw234-red-node-ledger.txt:208`）、护壁句自报漂移的、以及两把尺都读不出因的。
桶头字样也从 `side unknown` 改成 `side not measured`，因为缺的是侧别判据、不是因 —— 名字骗人比空桶更坏。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.17 补二" in text:
        print("ABORT the second correction is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.17 补二"):
            head_line = i
    print("APPENDED bytes_added=%d line=%s" % (len(block.encode("utf-8")), head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
