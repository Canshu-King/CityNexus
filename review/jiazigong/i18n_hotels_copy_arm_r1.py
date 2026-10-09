"""Regression arm: five HotelsPanel labels read the dictionary instead of
hand-writing two languages inline.

Sites covered (line numbers read fresh off the tip this branch was built on):
  frontend/src/features/stay/HotelsPanel.tsx:145  loading line
  frontend/src/features/stay/HotelsPanel.tsx:156  empty-state title
  frontend/src/features/stay/HotelsPanel.tsx:178  re-acquire CTA
  frontend/src/features/stay/HotelsPanel.tsx:201  panel title
  frontend/src/features/stay/HotelsPanel.tsx:246  arrival/departure fit term

Each of these five strings was counted across the whole tree BEFORE the change and
both arms appeared exactly once, so "the inline is gone" is not a vacuous claim here.
The two sites this lane does NOT touch (the shared Stay kicker, and labels whose
wording genuinely belongs to another screen) are pinned as survival controls.

MUTUALLY_EXCLUSIVE_VARIANT: revert to the tip bytes => this arm must go red.

Usage: `python i18n_hotels_copy_arm_r1.py [tree_root]`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HP = "HotelsPanel.tsx"
DICT = "LocaleContext.tsx"
SITES = {
    "stay.loading": ('zh ? "正在获取住宿…" : "Loading stays…"', 145),
    "stay.noneToCompare": ('zh ? "暂时没有可比较的住宿" : "No stays to compare yet"', 156),
    "stay.reacquire": ('zh ? "重新采集这家城市的住宿" : "Re-acquire stays for this city"', 178),
    "stay.chooseTitle": ('zh ? "选一家住的地方" : "Choose where to stay"', 201),
    "stay.arrivalFit": ('zh ? "到达/离开衔接" : "Arrival / departure fit"', 246),
}
EN_TEXT = {
    "stay.loading": "Loading stays…",
    "stay.noneToCompare": "No stays to compare yet",
    "stay.reacquire": "Re-acquire stays for this city",
    "stay.chooseTitle": "Choose where to stay",
    "stay.arrivalFit": "Arrival / departure fit",
}
ZH_TEXT = {
    "stay.loading": "正在获取住宿…",
    "stay.noneToCompare": "暂时没有可比较的住宿",
    "stay.reacquire": "重新采集这家城市的住宿",
    "stay.chooseTitle": "选一家住的地方",
    "stay.arrivalFit": "到达/离开衔接",
}
SHARED_KICKER = 't("hub.stayLabel")'  # 别人收敛的那枚, 本格不许动

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
    hp = lines(HP)
    body = "\n".join(hp)
    d = read(DICT)
    checks: list[tuple[str, bool]] = []

    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # per site: the inline shape is gone from the whole tree, and this line reads the key
    for key, (probe, lineno) in SITES.items():
        hits = 0
        for p in SRC.rglob("*.tsx"):
            hits += sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if probe in ln)
        ck(f"{key}: 该内联形状全树归零", hits == 0)
        ck(f"{key}: 第 {lineno} 行读词典", f't("{key}")' in hp[lineno - 1])

    # dictionary: every key defined in both arms, with different, exact wording
    for key in SITES:
        vals = re.findall(r'^\s*"%s":\s*"(.+)",?$' % re.escape(key), d, re.M)
        ck(f"{key}: 两臂各一处", len(vals) == 2)
        ck(f"{key}: 两臂文本不同", len(set(vals)) == 2)
        ck(f"{key}: 英臂逐字", EN_TEXT[key] in vals)
        ck(f"{key}: 中臂逐字", ZH_TEXT[key] in vals)

    # survival controls -- these pin facts that must hold in BOTH states
    ck("反控：共享的 Stay 眉标仍读 hub.stayLabel（未回退他笔）", body.count(SHARED_KICKER) == 2)
    ck("反控：本文件仍定义 zh（没顺手把语言分支拆掉）",
       any("const zh = locale.startsWith" in l for l in hp))

    # denominator: this file had 18 zh-? lines at the tip, five fewer now
    cnt = sum(1 for l in hp if "zh ?" in l)
    ck(f"本文件含 zh ? 的行计数=13（现尖 18 减本格五处）", cnt == 13)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(f"total={len(checks)} failed={len(failed)}")
    print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
