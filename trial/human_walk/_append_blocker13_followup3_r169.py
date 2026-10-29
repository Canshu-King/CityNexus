"""Add the dated third follow-up under blocker 13: the whole-suite cause table now exists."""

import io
import sys

DOC = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261027_GO_FROM_BLANK_DELIVERY.md"
ANCHOR = "而失败消息只打 `FULL_FIELDS - set(item)`，把一次形制增长读成空差异 —— 这把尺单向，要双向才看得见。"

NEW_LINE = (
    "    **10-29 晨补三（报告 §14.7）**：整套也跑了，红第一次是成因表而不是总数——末行"
    "`231 failed, 2569 passed, 15 skipped, 1 xfailed, 12 errors in 283.21s (0:04:43)`，"
    "五项相加＝2828（与证书的分母同档，代次对账写在 §14.7）；尺 trial/human_walk/_cmdr_full_red_reason_census_r164.py:44 "
    "把 `--tb=line` 的续行折回所属栈尾后按 文件:行:原因 分组，并要求分组数等于 pytest 自己的 failed，"
    "不等就 ABORT 不出表（回执 trial/results/20261026_gozero/bw163-red-census.txt:7）。"
    "最大一块是本班今天挖的那族凭证缺失：已实测 55 枚 + 形制同为 401 的 32 枚 + 把 401 dict 当列表遍历的 10 枚＝97 枚；"
    "种子时钟过期 26、假 settings 少字段 16、demo scene 建立被拒 11、依赖未注入 3、清单过期 1、库帧 1，"
    "仍未逐组读代码的 76（多是每组一枚的独立形状，本表不把它们并族）。"
    "231 对今早证书的 255 少 24，与 §14.3 那处夹具签名修复的 52→28 同幅；app/ 与 contracts/ 写集仍为零。"
)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(DOC, encoding="utf-8", newline="").read()
    if "10-29 晨补三（报告 §14.7）" in text:
        print("ABORT already present")
        return 4
    if text.count(ANCHOR) != 1:
        print("ABORT anchor hits=%d" % text.count(ANCHOR))
        return 5
    io.open(DOC, "w", encoding="utf-8", newline="").write(
        text.replace(ANCHOR, ANCHOR + "\n" + NEW_LINE, 1)
    )
    read_back = io.open(DOC, encoding="utf-8", newline="").read()
    print("INSERTED hits=%d anchor_still_1=%s" % (
        read_back.count("10-29 晨补三（报告 §14.7）"),
        read_back.count(ANCHOR) == 1,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
