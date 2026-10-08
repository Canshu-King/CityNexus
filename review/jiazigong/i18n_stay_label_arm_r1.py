"""Regression arm: the "Stay / 住宿" label (three sites, two files) reads the
dictionary instead of hand-writing two languages inline.

Sites covered:
  frontend/src/app/V8Experience.tsx:3246      (Hub today-strip label)
  frontend/src/features/stay/HotelsPanel.tsx:151  (hotels empty-state kicker)
  frontend/src/features/stay/HotelsPanel.tsx:168  (hotels panel kicker)

This one string appeared three times, so "the inline is gone" alone would be a
weak claim; the arm pins each site by file and counts them.

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到现尖字节）⇒ 本臂必须红。

用法：`python i18n_stay_label_arm_r1.py [tree_root]`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

V8 = "V8Experience.tsx"
HP = "HotelsPanel.tsx"
DICT = "LocaleContext.tsx"
TARGET_LINE_PROBE = 'zh ? "住宿" : "Stay"'
NEW_KEY = "stay.label"
SITES = {V8: 1, HP: 2}  # 每文件应读词典的处数
# 反控：同一文件的另一枚键（Me 屏的 my.stay）必须仍在原地被读
CONTROL_CALL = 't("my.stay")'
LANGCODE_PROBE = 'zh ? "zh-CN" : "en-GB"'

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
    v8 = lines(V8)
    hp = lines(HP)
    d = read(DICT)
    checks: list[tuple[str, bool]] = []

    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # 1: 该形状全树归零（改前 3 处：V8 一处 + HotelsPanel 两处）
    tree_hits = 0
    for p in SRC.rglob("*.tsx"):
        tree_hits += sum(
            1 for ln in p.read_text(encoding="utf-8").splitlines() if TARGET_LINE_PROBE in ln
        )
    ck("全树该内联形状归零", tree_hits == 0)

    # 2-4: 每个具名站点都读词典，处数对得上
    for fname, want in SITES.items():
        body = "\n".join(lines(fname))
        got = body.count(f't("{NEW_KEY}")')
        ck(f"{fname} 读词典处数={want}", got == want)

    # 5: 目标行不再含中文串（V8 那处）
    ck("V8Experience 目标行不再含中文串", "住宿" not in v8[3245])

    # 6-7: HotelsPanel 仍保留自己的语言分支（没把 zh 误删）
    ck("HotelsPanel 仍定义 zh", any("const zh = locale.startsWith" in l for l in hp))
    ck("HotelsPanel 仍读 t（useLocale 解构里带上 t）", any("{ locale, t } = useLocale()" in l for l in hp))

    # 8-9: 词典两臂都定义了新键
    vals = re.findall(r'^\s*"%s":\s*"(.+)",?$' % re.escape(NEW_KEY), d, re.M)
    ck("新键在词典里出现两处（中英各一）", len(vals) == 2)
    ck("两处文本不同（不是同一句复制两次）", len(set(vals)) == 2)

    # 10-11: 两臂逐字
    ck("英文臂文本逐字为 Stay", "Stay" in vals)
    ck("中文臂文本逐字为 住宿", "住宿" in vals)

    # 12: 反控 —— 同文件另一枚键 my.stay 仍在原地被读（没顺手改别人）
    ck("反控：V8Experience 里 t(\"my.stay\") 仍在", CONTROL_CALL in "\n".join(v8))

    # 13: 语言码桶仍在
    ck("语言码桶仍在（zh ? \"zh-CN\" 未被误改）", LANGCODE_PROBE in "\n".join(v8))

    # 14: 分母自检 —— V8Experience 该形状从 8 降到 7
    cnt = sum(1 for ln in v8 if 'zh ? "' in ln)
    ck("V8Experience zh ? \" 形状计数=7（现尖 8 减本格一处）", cnt == 7)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(f"total={len(checks)} failed={len(failed)}")
    print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
