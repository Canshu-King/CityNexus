"""Append section 14.14: two pending rulings now carry numbers instead of hypotheses.

The matrix guard's "oversized must fail closed" premise and the seeded-clock family's repair surface
were both awaiting a ruling.  This puts a measured fact in front of each: what the product actually
does with a 121-cell request, and how wide the fixture-date surface actually is, plus where a
reference time is already accepted today.

CRLF-dominant report: explicit CRLF block and a byte-identity assertion for everything before it.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.14（10-29 上午）：两条本来悬着的裁语，现在各带一个实测数，不再靠假设。

- 「越界矩阵必须判 FAILED」那一枚（`backend/tests/test_qoder_anywhere_matrix_truth.py:375`，形是 CAPTURED）：
  产品这一侧不是没门，而是已经改成分块发包 —— `backend/app/integrations/mobility/runtime.py:320` 起的注释写死了
  provider 的上限是一百格（按 cells 数不是按它错误文本里的 locations），实现先做 10×10 的方块
  （`backend/app/integrations/mobility/runtime.py:324`），跨块再切成五键并集并在并集超过一百格时才抛
  `matrix chunk exceeds the 100-cell provider cap`（`backend/app/integrations/mobility/runtime.py:348`、
  `backend/app/integrations/mobility/runtime.py:350`）。⇒ 十一键＝121 格在今天的实现里是**合法地分块捕获成功**，
  而那条护壁句的前提（N=11 ⇒ 400）是它自己文档里记的旧实测（`backend/tests/test_qoder_anywhere_matrix_truth.py:11`）。
  所以这一红是「前提被产品能力取代」，不是「门没咬」；要留哪一半断言（不留半张产物那部分仍然成立）等裁。
- 「种子时钟过期」那一族（普查里二十六枚，`trial/results/20261026_gozero/bw195-red-census-extended.txt:9` 表内那一项）：
  先把修面量出来再说口径 —— 整套 `backend/tests/` 里的绝对 ISO 日期时间字面量现读为 1207 处、分布在 347 个文件
  （两把尺同一条命令现读：按行计数与按文件计数），所以「逐枚改日期」是最贵的一条路。
  另一条路是夹具时钟旋钮：按四个词面（`_now`、`freezegun`、`CLOCK`、`clock`）在 `backend/tests/conftest.py` 现读命中为零 ——
  这只说明词面没有，不等于别处没有这种能力；但产品侧今天**已经**接受一个参考时间
  （`backend/app/fact_acquisition.py:380` 的 `_reference_date` 接受 str/datetime/date 三形），
  而旅客孪生口也早已按查询参数收 `now`（现读用例 `backend/tests/test_wp06_postgate_hardening_next.py:169`）。
  ⇒ 也就是说「把种子与断言都挂在一个可注入的参考时间上」在产品里已有先例，缺的只是夹具那侧的口径；等裁。
- 两条都没自取修法：本节只给数与坐标，不动测试、不动产品。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.14（10-29 上午）" in text:
        print("ABORT section 14.14 is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = read_back.count("14.14（10-29 上午）")
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.14（10-29 上午）"):
            head_line = i
    print("APPENDED bytes_added=%d hits=%d line=%s"
          % (len(block.encode("utf-8")), hits, head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
