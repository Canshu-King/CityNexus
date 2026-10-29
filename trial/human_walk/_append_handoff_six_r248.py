"""Append the 14.19 follow-up to the handoff, byte-preserving (this file is LF-only)."""

import io
import sys

HANDOFF = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261029_HANDOFF_GO_FROM_BLANK_r185.md"

BLOCK = """
## 六、10-29 午前补：那三十九枚「方案不是权威」已经落到某一臂，待点的是一格声明

- 归因（正文 `trial/results/20261026_GO_FROM_BLANK_REPORT.md:3464`）：三十九次拒绝全部出自
  `backend/app/services.py:799`，命中维度只有一处 —— 营业时间那个词。夹具 helper 在
  `backend/tests/test_v12_authoritative_trip_execution.py:104` 写 `NORMALIZED`，判据只认
  `backend/app/services.py:599` 的四个词；成本那一维 132 处地点行全部已解（回执
  `trial/results/20261026_gozero/bw245-sealed-arm-state-v13.txt:10`）。封套豁免读的键在
  `backend/app/services.py:791`，那批行的 metadata 全没写（同一回执 `:7`）。
- 待点二选一，动的都只是夹具字节：甲＝compose 之后补一次
  `backend/tests/test_v12_authoritative_trip_execution.py:122` 那步封套（同树先例
  `backend/tests/test_r28_execution_truth.py:80`、`backend/tests/test_r55_live_progress_drift_product.py:88`）；
  乙＝把 `:104` 那个词换成判据认的四词之一。没人点单就不动，也别把它算进"产品坏了"。
- 只登记不判死：`backend/app/operations/v9.py:358` 也写同一个词，而
  `backend/app/main.py:19305` 把它的 provider 归成服务器自有结构、选用门却没排除它
  （排除条件 `backend/app/services.py:768`）。真路由那一臂实测根本没走到这扇门
  （`trial/results/20261026_gozero/bw245-sealed-arm-state-staylife.txt:3`），所以这条留给裁决，不写成用户面缺陷。
- 本班踩到的仪表坑（接班直接用）：同一把尺跑多条臂，回执必须按臂分文件。这一条原本没做，
  第二臂直接把第一臂的读数覆盖了一次；补救是给探针加一枚 tag（
  `trial/human_walk/_cmdr_sealed_arm_state_r245.py:25`，环境变量 `CITYNEXUS_PROBE_RECEIPT_TAG`），
  再把三臂全部重放，三份回执各自现读才敢写进正文。
- 观察-only 的自证方式记一次：判"探针没改变判定"用的是同数对照（带与不带插件都是
  18 条失败加 9 条通过），只承认耗时变长，不认"应该没影响"。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(HANDOFF, encoding="utf-8", newline="").read()
    if "\r\n" in text:
        print("ABORT this file stopped being LF-only")
        return 3
    if "## 六、10-29 午前补" in text:
        print("ABORT the section is already appended")
        return 4
    block = BLOCK.strip("\n") + "\n"
    if "\r\n" in block:
        print("ABORT refusing to introduce CRLF")
        return 5
    io.open(HANDOFF, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(HANDOFF, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 6
    if "\r\n" in read_back:
        print("ABORT the write flipped line endings")
        return 7
    lines = read_back.split("\n")
    head = [i + 1 for i, line in enumerate(lines) if line.startswith("## 六、10-29 午前补")]
    print("APPENDED bytes_added=%d hits=%d head_line=%s lines=%d"
          % (len(block.encode("utf-8")), read_back.count("## 六、10-29 午前补"),
             head, len(lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
