"""Regression arm: the traveller-facing "Stay / 住宿" label reads one dictionary key
in all three places that hand-wrote it inline.

Sites (at parent bytes):
  frontend/src/app/V8Experience.tsx:3246   (Hub today-strip)
  frontend/src/features/stay/HotelsPanel.tsx:151  (empty-state kicker)
  frontend/src/features/stay/HotelsPanel.tsx:168  (panel kicker)

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到父字节）⇒ 本臂必须红。

Boundary this arm also protects: `my.stay` (Me-screen field), `stay.kicker`
("Stay Explorer") and the travelerLabels STAY/HOTEL token map (住宿 -> "Stay" AND
住宿 -> "Hotel") are DIFFERENT contexts that must NOT be collapsed into one key.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

V8_REL = "frontend/src/app/V8Experience.tsx"
PANEL_REL = "frontend/src/features/stay/HotelsPanel.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
LABELS_REL = "frontend/src/i18n/travelerLabels.ts"
PROBE = 'zh ? "住宿" : "Stay"'
NEW_KEY = "stay.label"


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    need = {
        "v8": root / V8_REL,
        "panel": root / PANEL_REL,
        "dict": root / DICT_REL,
        "labels": root / LABELS_REL,
    }
    for k, p in need.items():
        if not p.is_file():
            print(f"FAIL missing {k}: {p}")
            return 1
    v8 = need["v8"].read_text(encoding="utf-8")
    panel = need["panel"].read_text(encoding="utf-8")
    d = need["dict"].read_text(encoding="utf-8")
    labels = need["labels"].read_text(encoding="utf-8")

    checks: list[tuple[str, bool]] = []
    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # 1-3: the inline shape is gone from both files, and each site reads the key
    ck("V8Experience 的内联那枚已归零", PROBE not in v8)
    ck("HotelsPanel 的两枚内联已归零", PROBE not in panel)
    ck("V8Experience 那格读 stay.label", 't("stay.label")' in v8)
    ck("HotelsPanel 两格读 stay.label", panel.count('t("stay.label")') == 2)

    # 4-7: the dictionary defines the one key in both arms
    vals = re.findall(r'^\s*"%s":\s*"(.+?)",?$' % re.escape(NEW_KEY), d, re.M)
    ck("新键在两臂各一枚", len(vals) == 2)
    ck("两臂文本不同", len(set(vals)) == 2)
    ck("英文臂逐字 Stay", "Stay" in vals)
    ck("中文臂逐字 住宿", "住宿" in vals)

    # 8-10: boundary — three OTHER contexts sharing the word 住宿 must NOT be swallowed
    ck("my.stay 仍是 Me 屏那枚独立键（未被并进 stay.label）",
       re.search(r'^\s*"my\.stay":', d, re.M) is not None)
    ck("stay.kicker 仍是 Stay Explorer（未被并掉）", "Stay Explorer" in d)
    ck("travelerLabels 的 HOTEL->Hotel 仍在（同字不同译，不能合并）",
       re.search(r'HOTEL:\s*\{\s*zh:\s*"住宿"\s*,\s*en:\s*"Hotel"', labels) is not None)

    # 11: 语言码桶仍在（计数器没把「码」与「文案」混起来）
    ck("语言码桶仍在（zh ? \"zh-CN\" 未被误改）", 'zh ? "zh-CN" : "en-GB"' in v8)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(f"total={len(checks)} failed={len(failed)}")
    if failed:
        print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
        return 1
    print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
