"""Append section 14.7: the whole-suite red set as a cause table rather than a count.

Numbers are copied from the receipt this shift's census instrument wrote, which refuses to print a
table whose rows do not add up to pytest's own failed count.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
### 14.7 整套红第一次有了成因表：231 枚里九十七枚属同一族凭证缺失

跑法（现读，后台跑完再接尺）：`cd backend && python -m pytest -q --tb=line -p no:warnings`，
解释器 3.12.14。原始输出落 trial/results/20261026_gozero/bw163-backend-full-tbline.txt，末行
`231 failed, 2569 passed, 15 skipped, 1 xfailed, 12 errors in 283.21s (0:04:43)`；
231+2569+15+1+12 合计 2828，与本班早上那份证书的分母 2828 同一档（那格数原样抄在本节末尾）。

成因尺 trial/human_walk/_cmdr_full_red_reason_census_r164.py 干三件事：把 `--tb=line` 的续行折回所属那条
栈尾（不折就把多行断言消息读成空的 `AssertionError:`，第一次跑就因此报了百二十枚"未归因"）、
按 文件:行:原因 分组、并把分组数与 pytest 自己的 failed 对账 —— 不相等就 ABORT，不出表。
表落在 trial/results/20261026_gozero/bw163-red-census.txt。

| 成因 | 现读 |
| --- | --- |
| 私有读不带 bearer（本班已实测那族，KeyError 'active_plan' 一类） | 55 |
| 门回 401、测试当 200 比（`assert 401 == 200`，形制同、逐枚 bearer 未验） | 32 |
| 把 401 的 dict 当列表遍历（`'str' object has no attribute 'get'`） | 10 |
| 种子时钟过期（含 21 枚落在 sqlalchemy 的 `CHECK constraint failed: end_at > start_at`） | 26 |
| 假 settings 替身少字段 | 16 |
| demo scene 建立阶段就被拒（503／scene 里没有 journey_id） | 11 |
| 路由函数被直接调用、依赖没注入（`'Depends' object has no attribute`） | 3 |
| 十二字段清单过期 | 1 |
| 崩在库代码里（不在仓库文件上） | 1 |
| 仍未归因 | 76 |

三行凭证族（五十五＋三十二＋十）相加＝九十七枚，是这套 231 里最大的一块；它对应的正是本班今天挖出的那一条机制：
私有旅程读要带旅客 bearer（app/main.py:10323 那次鉴权），而夹具还在裸读。
`OUTSIDE_REPO_FRAMES 22` —— 二十二枚的栈尾落在仓库之外（sqlalchemy、urllib 等），
这不是"没归属"，是失败点本来就在库帧里，尺把它们单列出来而不是塞进未知。
`DISTINCT_TAIL_GROUPS 156` 对 231 枚红，最大的一组是廿一枚（上面那格 sqlalchemy 的 CHECK）。

与今早那张证书的代次对账（原样抄，不推算）：`255 failed, 2545 passed, 15 skipped, 1 xfailed, 12 errors in 270.29s`。
本次 231/2569 —— failed 少廿四、passed 多廿四，与 §14.3 那处夹具签名修复实测的 `52 failed → 28 failed、7 passed → 31 passed`
增量完全同幅；本班在 app/ 与 contracts/ 的写集仍是零，唯一动过的后端文件就是那枚夹具本身
（backend/tests/test_r64_member_side_quest.py:124），所以这廿四枚的位移只可能来自那一处签名补上。

仍未归因的七十六枚不硬并族：它们多是 `AssertionError:` 后带具体形状的单枚组
（如 `REQUIRE_CONFIRMATION != ALLOW_AUTO`、`KeyError: 'current_activity_id'`、
`CAPTURED_REPLAY_CITY_MISMATCH`、`V13_C4_ANCHOR_NOT_IN_INPUT`），
每组一枚，合并需要逐组读代码，属下一班或下一张单；本表的作用是把"廿四枚一类的东西"和
"一枚一类的一堆"分开，而不是把后者清零。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    original = io.open(REPORT, encoding="utf-8", newline="").read()
    if "### 14.7" in original:
        print("ABORT 14.7 is already in the report")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(original + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(original):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED 14.7 bytes_added=%d heading_hits=%d" % (
        len(block.encode("utf-8")),
        read_back.count("### 14.7"),
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
