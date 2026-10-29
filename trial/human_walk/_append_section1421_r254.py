"""Append section 14.21: the promotion writers paired against the shared gate."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.21 补（10-29 午前）：把「谁把方案推成出发态」和「谁问过那扇门」排成一张表

§14.20 那一格不是孤例的形状，得有一张表才看得清边界在哪。本班做了一把只读普查尺，
并把两枚已知答案的锚塞进去当自检。

- 尺：trial/human_walk/_cmdr_promotion_gate_pairing_r253.py:21 抓每一行 `X.status = "ACTIVE"|"SELECTED"`
  的写者，trial/human_walk/_cmdr_promotion_gate_pairing_r253.py:23 用产品自己的函数名认「问过门」，
  trial/human_walk/_cmdr_promotion_gate_pairing_r253.py:91 把「同一个函数里看得见门」的排到前面。
- 自检（两枚已知锚必须各归其栏，否则这尺不算在世）：
  backend/app/main.py:20071 所在函数就是 §14.20 里真问过门的出发门（那次调用在
  backend/app/main.py:20040），实测归「看得见」栏（回执 trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:6）；
  backend/app/operations/v9.py:761 所在函数已被真路由实测一次门都没问过，实测归「看不见」栏
  （回执 trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:20）。两枚都对上。
- 表的全形：拾陆行写者，同一函数里看得见门的 叁 行、看不见的 拾叁 行
  （回执 trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:2）。
  「看不见」这把尺只承认自己的视野边界，不判缺陷 —— 表头那一行原话就是这么写的
  （trial/human_walk/_cmdr_promotion_gate_pairing_r253.py:98）。
- 与主人真机路径直接相关的那格：backend/app/main.py:19038（接受这一版的实现函数）落在「看不见」栏
  （回执 trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:14）。它不等于没门：
  主人走的那条在按接受之前先按的是方案选用，那一格在同一函数里看得见门（
  backend/app/main.py:18289，回执 trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:5）。
  没量过的形状是「不先选用、直接接受」那一趟会不会绕开门 —— 这要一条真走查，本班不靠读码下判语。
- 剩下 拾叁 行逐格走查才能谈归属；点名清单已在回执里，按口径不代裁、0 改产品字节。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.21 补" in text:
        print("ABORT the section is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED bytes_added=%d hits=%d"
          % (len(block.encode("utf-8")), read_back.count("14.21 补")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
