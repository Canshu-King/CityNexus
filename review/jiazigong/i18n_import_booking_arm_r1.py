"""Regression arm: the Bookings aside kicker reads the dictionary instead of
hand-writing two languages inline.

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到现尖字节）⇒ 本臂必须红。

用法：`python i18n_import_booking_arm_r1.py [tree_root]`
tree_root 缺省为 arm 文件自身所在树（`review/jiazigong/` 的上两级）。
把它指到一份「把两枚源文件回退到现尖字节」的独立副本上时本臂应咬红。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TARGET = "V8Experience.tsx"
DICT = "LocaleContext.tsx"
TARGET_LINE_PROBE = 'zh ? "导入预订" : "Import a booking"'
NEW_KEY = "bookings.importBooking"

if len(sys.argv) > 1:
    SRC = Path(sys.argv[1]).resolve() / "frontend" / "src"
else:
    SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def read(rel: str) -> str:
    for root in SRC.rglob(rel):
        return root.read_text(encoding="utf-8")
    raise SystemExit(f"missing {rel}")


def lines(rel: str) -> list[str]:
    for root in SRC.rglob(rel):
        return root.read_text(encoding="utf-8").splitlines()
    raise SystemExit(f"missing {rel}")


def main() -> int:
    v8 = lines(TARGET)
    d = read(DICT)
    checks: list[tuple[str, bool]] = []

    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # 1: 该形状在全树归零（本串全树唯一，故「内联消失」在本串上不是空判据）
    tree_hits = 0
    for p in SRC.rglob("*.tsx"):
        tree_hits += sum(
            1 for ln in p.read_text(encoding="utf-8").splitlines() if TARGET_LINE_PROBE in ln
        )
    ck("全树该内联形状归零", tree_hits == 0)

    # 2-3: 目标行改为读词典
    line4562 = v8[4561]
    ck("4562 那一行不再含中文串", "导入预订" not in line4562)
    ck("4562 那一行改为读词典", NEW_KEY in line4562)

    # 4-5: 词典两臂都定义了新键
    vals = re.findall(r'^\s*"%s":\s*"(.+)",?$' % re.escape(NEW_KEY), d, re.M)
    ck("新键在词典里出现两处（中英各一）", len(vals) == 2)
    ck("两处文本不同（不是同一句复制两次）", len(set(vals)) == 2)

    # 6-7: 两臂逐字
    ck("英文臂文本逐字为 Import a booking", "Import a booking" in vals)
    ck("中文臂文本逐字为 导入预订", "导入预订" in vals)

    # 8: 语言码桶仍在（计数器没把「码」与「文案」混起来）
    ck(
        '语言码桶仍在（zh ? "zh-CN" 未被误改）',
        'zh ? "zh-CN" : "en-GB"' in "\n".join(v8),
    )

    # 9: 分母自检 —— 本文件该形状从 10 降到 9（改一处）
    cnt = sum(1 for ln in v8 if 'zh ? "' in ln)
    ck("本文件 zh ? \" 形状计数=9（现尖 10 减本格一处）", cnt == 9)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(f"total={len(checks)} failed={len(failed)}")
    print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
