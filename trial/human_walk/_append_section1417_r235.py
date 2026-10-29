"""Append section 14.17: the 231 reds as one batched-ruling ledger, node id by node id.

CRLF-dominant report: explicit CRLF block, byte-identity assertion for everything before the
insertion point.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.17（10-29 上午）：整套二百三十一枚红合成一本「按 node id 落、按桶裁」的账 —— 夹具侧一百三十枚、产品与种子侧一百零一枚。

- 账本尺：`trial/human_walk/_cmdr_red_node_ledger_r234.py`；逐枚名单全量写在
  `trial/results/20261026_gozero/bw234-red-node-ledger.txt`（`:3` 现读 distinct node ids 二百三十一、
  `:4` 十八个桶求和同为二百三十一、`:5` 与 `:6` 是两侧的分项和，四道对账全装在尺里，任一不等等就 ABORT）。
  对齐法本身带闸：崩溃行与 `FAILED` 摘要行必须同为 pytest 自报的那枚数才敢 zip。
- 这一趟还纠了自己一处：先用 `FAILED (\S+)::(\w+)` 抓 node id 时，参数化用例的 `[case]` 后缀被吞掉，
  尺当场报「二百三十一枚失败但只认出二百一十八个不同 id」而 ABORT —— 换成整段 node id 才对上。
  正则是这把尺自己的缺陷，不是数据的缺陷，记在这里免得下一把尺再犯。
- 夹具侧（一次裁能罩住一百三十枚）：

| 桶 | 行数 | 回执行 |
| --- | --- | --- |
| 私有读口没 bearer（`active_plan` 那形） | 三十九 | `trial/results/20261026_gozero/bw234-red-node-ledger.txt:7` |
| 私有读口没 bearer（KeyError 那形，§14.13 并入） | 二十五 | `trial/results/20261026_gozero/bw234-red-node-ledger.txt:147` |
| 门答 401、测试要 200 | 三十二 | `trial/results/20261026_gozero/bw234-red-node-ledger.txt:113` |
| 答复被当列表迭代（401 体的形） | 十 | `trial/results/20261026_gozero/bw234-red-node-ledger.txt:206` |
| 假设置缺字段（五枚属性，§14.16） | 十六 | `trial/results/20261026_gozero/bw234-red-node-ledger.txt:173` |
| 课堂/演示门拒绝（§14.15 三臂实测） | 七 | `trial/results/20261026_gozero/bw234-red-node-ledger.txt:227` |
| `error_type` 只在异常支路才有 | 一 | `trial/results/20261026_gozero/bw234-red-node-ledger.txt:250` |

- 前四桶合起来就是一百零六枚那一族（三十九＋二十五＋三十二＋十），与 §14.13 报给号令者的数同码；
  「未定性」那一桶也从五十四降到三十九（`trial/results/20261026_gozero/bw234-red-node-ledger.txt:63`），
  降的正是本班次逐枚读断言读出来的那十枚（九枚并入凭证族、一枚归 `error_type`）。
- 产品与种子侧一百零一枚里最大三块：种子时钟过期二十六（`:146`）、方案版本被判不权威十五（`:190`）、
  演示场景准备被拒九（`:217`）—— 三块都各自有裁语在前（时钟口径见 §14.14、权威版本见 `backend/tests/test_v13_integrity.py:50`
  那一组、演示场景见 §14.15）。
- 本班不自取任何一刀：这本账的作用是把「裁一次」与「裁十五次」的差别摆平；名单逐枚可点，改谁由号令者定。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.17（10-29 上午）" in text:
        print("ABORT section 14.17 is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = read_back.count("14.17（10-29 上午）")
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.17（10-29 上午）"):
            head_line = i
    print("APPENDED bytes_added=%d hits=%d line=%s"
          % (len(block.encode("utf-8")), hits, head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
