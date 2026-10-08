"""Regression arm: PlanWithAiSheet's sr-only request label and the import-places
CTA read the dictionary instead of hand-writing two languages inline.

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到现尖字节）⇒ 本臂必须红。

用法：`python i18n_plan_ai_labels_arm_r1.py [tree_root]`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SHEET = "PlanWithAiSheet.tsx"
DICT = "LocaleContext.tsx"
TIP = "bdee2fc3344168ce9b1e0228e53cdffb8c5ecd8c"
PROBE_TRIP = 'zh ? "旅行需求" : "Trip request"'
PROBE_IMPORT = 'zh ? "粘贴你自己的地点，导入这趟行程" : "Paste your own places and import them into this trip"'
KEY_TRIP = "planai.tripRequest"
KEY_IMPORT = "planai.importPlacesCta"
# 反控：同文件另一枚同形内联（模块层的 title，没有 t 可用，本格不动）必须仍在
CONTROL_PROBE = 'zh ? "已取消" : "Cancelled"'

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
    sheet = lines(SHEET)
    body = "\n".join(sheet)
    d = read(DICT)
    checks: list[tuple[str, bool]] = []

    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # 1-2: 两处形状全树归零（各自现尖全树唯一）
    for label, probe in (("旅行需求", PROBE_TRIP), ("导入地点 CTA", PROBE_IMPORT)):
        hits = 0
        for p in SRC.rglob("*.tsx"):
            hits += sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if probe in ln)
        ck(f"全树「{label}」内联形状归零", hits == 0)

    # 3-6: 目标行改为读词典（行号现读于现尖）
    ck("714 那行读 planai.tripRequest", KEY_TRIP in sheet[713])
    ck("714 那行不再含中文串", "旅行需求" not in sheet[713])
    ck("1100 那行读 planai.importPlacesCta", KEY_IMPORT in sheet[1099])
    ck("1100 那行不再含中文串", "粘贴你自己的地点" not in sheet[1099])

    # 7-10: 两枚键在两臂各一、文本不同、逐字
    for key, en, zh in ((KEY_TRIP, "Trip request", "旅行需求"),
                        (KEY_IMPORT, "Paste your own places and import them into this trip",
                         "粘贴你自己的地点，导入这趟行程")):
        vals = re.findall(r'^\s*"%s":\s*"(.+)",?$' % re.escape(key), d, re.M)
        ck(f"{key} 在两臂各一处", len(vals) == 2)
        ck(f"{key} 两臂文本不同", len(set(vals)) == 2)
        ck(f"{key} 英文臂逐字", en in vals)
        ck(f"{key} 中文臂逐字", zh in vals)

    # 11: 反控 —— 模块层那枚（本格没动、无 t 可用）仍在原地内联
    ck("反控：模块层 zh ? \"已取消\" : \"Cancelled\" 仍在", CONTROL_PROBE in body)

    # 12: 分母 —— 本文件 zh ? " 形状由 23 降到 21（两处都改掉）
    cnt = sum(1 for ln in sheet if 'zh ? "' in ln)
    ck("本文件 zh ? \" 形状计数=21（现尖 23 减两处）", cnt == 21)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(f"total={len(checks)} failed={len(failed)}")
    print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
