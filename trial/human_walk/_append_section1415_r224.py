"""Append section 14.15: the seven demo-door reds measured under three environment arms.

The claim being written down is deliberately narrow -- the environment can move the refusal one gate
forward and cannot make a single row green -- and the ruler that measured it aborts if that claim
turns out false.  CRLF-dominant report: explicit CRLF plus the byte-identity assertion.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.15（10-29 上午）：那七枚「演示门拒绝」现在有了一张三臂对照表 —— 环境只能把拒绝往前挪一格，挪不出绿色。

- 三臂唯一差别是环境变量（产品字节与测试一个字没动）：
  A 照今天这样跑 ⇒ 拒绝字串 `DEMO_DATABASE_NOT_ISOLATED`；
  B 只把测试库自己声明出来（`CITYNEXUS_DATABASE_URL` 与 `CITYNEXUS_DEMO_DATABASE_PATH` 指同一枚一次性库，
     再加 `CITYNEXUS_DEMO_MODE=true`）⇒ 拒绝字串换成 `DEMO_PRESENTER_REQUIRED`；
  C 在 B 之上再加一枚四十字符的**填充** presenter key ⇒ 与 B 同。
  逐臂的拒绝字串与三轮计数在 `trial/results/20261026_gozero/bw223-demo-gate-arms.txt:5`、
  `trial/results/20261026_gozero/bw223-demo-gate-arms.txt:6`、`trial/results/20261026_gozero/bw223-demo-gate-arms.txt:7`；
  七枚稳定核红名单在 `trial/results/20261026_gozero/bw223-demo-gate-arms.txt:4`。
- 于是七枚的性质判清：既不是产品缺陷，也不是「环境一对就绿」——
  是夹具既没声明隔离库、也没带 presenter 头，门按 `backend/app/demo_access.py:14` 与 `backend/app/demo_access.py:36`
  两道规矩逐格拒绝。要变绿得改夹具两处（把同一个库路径声明出来 + 把头带上），这一条等点单，本班没自取。
- 反自欺闸门装在尺里：凡在 A 每一轮都红的行若在 B 或 C 里变绿，尺当场 ABORT
  （尺 `trial/human_walk/_cmdr_demo_gate_arms_r223.py`，`trial/results/20261026_gozero/bw223-demo-gate-arms.txt:8`
  记的是这条闸的现读结果：没有一枚变绿）。
- 顺带量到一枚计时敏感的行：`test_an_abandon_from_another_process_resolves_the_terminal_write_as_abandoned`
  在九轮里红了一轮（`trial/results/20261026_gozero/bw223-demo-gate-arms.txt:9`）—— threading 与 SQLite 锁的竞态，
  既不能当成因记，也不能当「修好了」记。
- 一次性库写在 `backend/.cmdr_demo_iso/` 下、跑完即清；真库与课堂库这趟一个字没碰（课堂库只被上一节那把 mode=ro 的尺读过）。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.15（10-29 上午）" in text:
        print("ABORT section 14.15 is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = read_back.count("14.15（10-29 上午）")
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.15（10-29 上午）"):
            head_line = i
    print("APPENDED bytes_added=%d hits=%d line=%s"
          % (len(block.encode("utf-8")), hits, head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
