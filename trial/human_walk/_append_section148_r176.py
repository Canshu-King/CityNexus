"""Append section 14.8: the cause table's second pass and the gate step's runner-side proof."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
### 14.8 成因表的第二遍：未归因从七十六降到五十四，新门在 runner 上自证成功

§14.7 那张表出完之后，本班在自己那把尺上找到两处会让数偏的地方，都改了并同代重跑
（同一条 `pytest` 原始输出 trial/results/20261026_gozero/bw163-backend-full-tbline.txt 再没重跑，
只重算了分组，所以两次讲的是同一批二十三八枚红）：

1. 归一化函数原来从第一个 `{` 截断，而 `AssertionError` 的消息体正是以 `{` 开头的 JSON —— 于是十二枚
   `PlanVersion <id> is not authoritative` 被读成空的 `AssertionError:`。改法见
   trial/human_walk/_cmdr_full_red_reason_census_r164.py:25。
2. 保留消息体之后又暴露第二格：体里带 uuid，十二枚各成一组，"最大的一组"就看不见了。
   现在按掩掉 id/receipt 的形状分组（trial/human_walk/_cmdr_full_red_reason_census_r164.py:55）。

第二遍的数（回执 trial/results/20261026_gozero/bw163-red-census.txt 第七行）：分组 143 组，
未归因从七十六降到五十四；新增成因为 `plan version refused as not authoritative` 十五次、
`autonomy decided differently than the test expects` 三次、`commitment anchor rejected by the v13 planner` 二次、
`replay city does not match` 一次、`test reads a router shape that changed` 一次。
凭证族仍是最大一块：五十五＋三十二＋十＝九十七次（同五行）。
剩下五十四次是一枚一形的长尾（如 `KeyError: 'current_activity_id'`、`'_IncludedRouter' object has no attribute 'path'`），
并族需要逐组读代码，不在本班自取范围内。

新门在 runner 上自证：代次 `47a463e018d8bc01166ce74ae553fd817a9cdce8` 的那次发布门三个 job 全 success，
其中本班新加的那步原话为
`JOB Frontend typecheck and Vite build | STEP Typecheck every file under src, not the five named ones | CONCLUSION success`
（回执 trial/results/20261026_gozero/bx175-gate-step-proof.txt:8，取件尺
trial/human_walk/_write_gate_step_proof_r175.py:49 —— 它要求这步恰好出现一次且判 success，否则不落盘）。
同一次跑里 `Prove a commit can only carry the paths it names` 也判 success，说明本班早先装上的提交门在
runner 上也仍在咬。宽的这步是加闸不是放闸：窄的那步（只列五枚文件）保留未动。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    original = io.open(REPORT, encoding="utf-8", newline="").read()
    if "### 14.8" in original:
        print("ABORT 14.8 already present")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(original + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(original):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED 14.8 bytes_added=%d heading_hits=%d" % (
        len(block.encode("utf-8")),
        read_back.count("### 14.8"),
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
