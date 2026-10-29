"""Append the 14.20 and 14.21 follow-ups to handoff section six (LF-only file)."""

import io
import sys

HANDOFF = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261029_HANDOFF_GO_FROM_BLANK_r185.md"

BLOCK = """
- 14.20 的交接句（10-29 午）：一按「选这家酒店」就出发，而那扇门一次没被问。
  分母读数在 `trial/results/20261026_gozero/bw250-stay-plan-against-select-gate.txt:3`（整条真路由走查
  对 `backend/app/main.py:20040` 那次的调用记 零，唯一一条是正控制 `:8`，所以「零」不是尺没咬）；
  成因在 `backend/app/operations/v9.py:761` 与 `backend/app/operations/v9.py:779`（住下选用直接把
  方案与行程推成出发态），其后 `backend/app/main.py:18182` 挡回方案选用、`backend/app/main.py:20015`
  幂等早退放行出发门。两条待裁口径已写进账本，本班不代裁。
- 14.21 的交接句：把「谁推出发态」和「谁问过门」排成一张表（尺
  `trial/human_walk/_cmdr_promotion_gate_pairing_r253.py:21`，自检两枚已知锚
  `trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:6` 与
  `trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:20` 各归其栏）。
  接班的人要点名的是 `backend/app/main.py:19038` 那一格（主人真机按「接受这一版」走的实现，
  同一函数里看不见门；它前面那步方案选用 `backend/app/main.py:18289` 是看得见的）。
  「不先选用、直接接受」那一趟还没走查过 —— 别把它写成缺陷，先量。
- 仪表句（本班新踩的一次）：只记拒绝的尺会把「门被问了并放行」与「门根本没被问」混成同一个零。
  `trial/human_walk/_cmdr_stay_plan_select_gate_r250.py:75` 改记每次回答，并在同进程用真数据
  直接问门一次当正控制（`trial/human_walk/_cmdr_stay_plan_select_gate_r250.py:196`），
  正控制不被 trace 看见就 ABORT。以后凡写「某扇门 0 次」都得带这一格。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(HANDOFF, encoding="utf-8", newline="").read()
    if "\r\n" in text:
        print("ABORT this file stopped being LF-only")
        return 3
    if "14.20 的交接句" in text:
        print("ABORT already appended")
        return 4
    block = BLOCK.strip("\n") + "\n"
    io.open(HANDOFF, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(HANDOFF, encoding="utf-8", newline="").read()
    if not read_back.startswith(text) or "\r\n" in read_back:
        print("ABORT bytes before the insertion point changed or endings flipped")
        return 6
    print("APPENDED bytes_added=%d hits=%d lines=%d"
          % (len(block.encode("utf-8")), read_back.count("14.20 的交接句"),
             len(read_back.split("\n"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
