"""Append a dated correction to section 14.17: the ledger lumped unidentified rows onto the product side.

The first version of the node ledger split the run into two sides and put the 'not yet attributed'
bucket on the product/seed side by elimination.  That is not a measured claim -- no cause was
measured for those rows -- so the ruler now reports three sides and the numbers are restated here.
The section's own text is kept verbatim; the correction is appended, as everywhere else in this
report.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.17 补（同班次）：那本 node id 账的第一版只分两侧，把「未定性」的三十九枚按排除法记到了产品/种子侧——
那不是量出来的因，是把没因的算成有因。尺现在分三侧重出，数也跟着改：
夹具侧一百三十枚（`trial/results/20261026_gozero/bw234-red-node-ledger.txt:5`）、
产品与种子侧**已判因**的六十二枚（`trial/results/20261026_gozero/bw234-red-node-ledger.txt:6`）、
侧别未知三十九枚（`trial/results/20261026_gozero/bw234-red-node-ledger.txt:7`，
桶头同文件 `:8` 现读标着 `side unknown`），三侧之和仍等于 pytest 自报的那枚数（`:4` 的求和闸）。
上一段里「产品与种子侧一百零一枚」那句以这条为准；种子时钟二十六、方案版本不权威十五、演示场景准备九
那三块不变，它们本就在已判因的六十二枚里。
另外记一条尺自己的过程：这次改动第一版把 `unknown` 定义放在了使用之后，跑当场抛 `UnboundLocalError`
且**没写回执** —— 所以那几秒钟账本文件里仍是上一版有效数，没出现"半新半旧"的第三种数。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.17 补" in text:
        print("ABORT the correction is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.17 补"):
            head_line = i
    print("APPENDED bytes_added=%d hits=%d line=%s"
          % (len(block.encode("utf-8")), read_back.count("14.17 补"), head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
