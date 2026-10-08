"""Regression arm: the two remaining hand-written "Stay / 住宿" kickers in HotelsPanel
converge onto the dictionary key the authoritative line ALREADY has (hub.stayLabel).

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到父字节）⇒ 本臂必须红。

Why this key and not a new one: commit 6d17cf9ab on the authoritative line already
moved the Hub today-strip to t("hub.stayLabel"). Adding a second key holding the same
sentence is a second source of truth, so this arm pins the reuse.

树根可由首参传入：臂必须能被指到一份把源文件回退到父字节的独立副本上。
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
KEY = "hub.stayLabel"


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    paths = {k: root / v for k, v in
             {"v8": V8_REL, "panel": PANEL_REL, "dict": DICT_REL, "labels": LABELS_REL}.items()}
    for k, p in paths.items():
        if not p.is_file():
            print(f"FAIL missing {k}: {p}")
            return 1
    v8 = paths["v8"].read_text(encoding="utf-8")
    panel = paths["panel"].read_text(encoding="utf-8")
    d = paths["dict"].read_text(encoding="utf-8")
    labels = paths["labels"].read_text(encoding="utf-8")

    checks: list[tuple[str, bool]] = []
    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # 1-3 the change itself
    ck("HotelsPanel 已无该内联形状", PROBE not in panel)
    ck("HotelsPanel 两格都读 hub.stayLabel", panel.count(f't("{KEY}")') == 2)
    ck("HotelsPanel 取到了取词函数", re.search(r"const \{[^}]*\bt\b[^}]*\} = useLocale\(\)", panel) is not None)

    # 4-6 reuse, not a second key
    vals = re.findall(r'^\s*"%s":\s*"(.+?)",?$' % re.escape(KEY), d, re.M)
    ck("hub.stayLabel 在两臂各一枚", len(vals) == 2)
    ck("两臂文本不同", len(set(vals)) == 2)
    ck("没有另起一枚同句新键 stay.label", '"stay.label"' not in d)

    # 7-8 the strip that already reads it must stay read (no regression of 6d17cf9ab)
    ck('V8Experience 今日条仍读 hub.stayLabel', f't("{KEY}")' in v8)
    ck("英文臂逐字 Stay、中文臂逐字 住宿", "Stay" in vals and "住宿" in vals)

    # 9-11 boundary: three OTHER contexts sharing the word must NOT be swallowed
    ck("my.stay 仍是 Me 屏独立键", re.search(r'^\s*"my\.stay":', d, re.M) is not None)
    ck("stay.kicker 仍是 Stay Explorer", "Stay Explorer" in d)
    ck("travelerLabels 的 HOTEL->Hotel 仍在（同字不同译）",
       re.search(r'HOTEL:\s*\{\s*zh:\s*"住宿"\s*,\s*en:\s*"Hotel"', labels) is not None)

    # 12 language-code bucket survives
    ck("语言码桶仍在（Intl 区域名未被误改）", 'zh ? "zh-CN" : "en-GB"' in v8)

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
