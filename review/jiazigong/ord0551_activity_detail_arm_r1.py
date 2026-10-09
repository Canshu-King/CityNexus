"""ORD-0551 convergence arm: ActivityDetail's two opening-hours labels read the
dictionary keys the table names, with the on-screen text unchanged.

What "convergence" means here: the two words were ALREADY in the dictionary
(`detail.hoursProvided`, `detail.hoursProviderText`) and were ALSO hand-written
inline. So this change adds no key and edits no wording -- it makes one fact have
one wording. The arm therefore proves three separate things:
  1. the inline pair is gone from that line, and the line reads the named key;
  2. the dictionary text is byte-identical to the literals it replaced
     (that is the byte-level half of "屏上文案一字不改");
  3. neighbours this order does not cover stay exactly as they were --
     the `Not available` branch two lines below is NOT in the table, so touching
     it would be scope creep, and the survival controls fail loudly if I did.

Coordinates were read fresh off tip 259ed27d14b62224eb1a23b244c281288a012fc5.

MUTUALLY_EXCLUSIVE_VARIANT: run me against a copy of the tip bytes and I go red.

Usage: `python ord0551_activity_detail_arm_r1.py [tree_root]`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AD = "ActivityDetail.tsx"
DICT = "LocaleContext.tsx"
TIP = "259ed27d14b62224eb1a23b244c281288a012fc5"

# 表给的两枚：键 -> (被替换掉的中文臂, 被替换掉的英文臂)
CONVERGED = {
    "detail.hoursProvided": ("已提供", "Provided"),
    "detail.hoursProviderText": (" · 供应商原文", " · provider's own text"),
}
LINE_216 = 216
NEIGHBOUR_UNTOUCHED = '"暂无数据"'       # 第 218 行那支，表里没有，不许动
NEIGHBOUR_EN = '"Not available"'

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
    ad = lines(AD)
    body = "\n".join(ad)
    d = read(DICT)
    checks: list[tuple[str, bool]] = []

    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    line216 = ad[LINE_216 - 1]

    # 一、两枚都改为读键，且那一行不再手写任何一臂
    # NB: compare the QUOTED literal. The bare word `Provided` is a substring of the
    # key name `detail.hoursProvided`, so an unquoted check fails on a line that is
    # actually correct -- which is exactly how this arm read red on its own fix.
    for key, (zh_txt, en_txt) in CONVERGED.items():
        ck(f"{key}: 第 {LINE_216} 行读这枚键", f't("{key}")' in line216)
        ck(f"{key}: 中文面已从该行消失", f'"{zh_txt}"' not in line216)
        ck(f"{key}: 英文面已从该行消失", f'"{en_txt}"' not in line216)
        pair = f'zh ? "{zh_txt}" : "{en_txt}"'
        hits = sum(
            1
            for p in SRC.rglob("*.tsx")
            for ln in p.read_text(encoding="utf-8").splitlines()
            if pair in ln
        )
        ck(f"{key}: 该内联形状全树归零", hits == 0)

    # 二、屏上文案未变：字典两侧逐字等于被替换掉的那两串
    for key, (zh_txt, en_txt) in CONVERGED.items():
        vals = re.findall(r'^\s*"%s":\s*"(.+)",$' % re.escape(key), d, re.M)
        ck(f"{key}: 字典里两臂各一处", len(vals) == 2)
        ck(f"{key}: 字典文本逐字等于被替换的中文臂", zh_txt in vals)
        ck(f"{key}: 字典文本逐字等于被替换的英文臂", en_txt in vals)

    # 三、邻面未动：表外那支仍在原地
    ck("表外那支「暂无数据」仍在原地（本格未越界）", NEIGHBOUR_UNTOUCHED in body)
    ck("表外那支英文 \"Not available\" 仍在原地", NEIGHBOUR_EN in body)

    # 四、取词函数在本组件里是真取到的（不是靠调用点传参）
    ck("本文件 useLocale 解构里带上 t", any("{ locale, t } = useLocale()" in l for l in ad))

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(f"total={len(checks)} failed={len(failed)}")
    print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
