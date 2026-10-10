"""Regression arm: the CopilotDock raw-event fold summary reads the dictionary
instead of hand-writing two languages inline.

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到现尖字节）⇒ 本臂必须红。

用法：`python i18n_runtime_details_arm_r1.py [tree_root]`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOCK = "CopilotDock.tsx"
DICT = "LocaleContext.tsx"
TARGET_LINE_PROBE = 'zh ? "运行详情" : "Runtime details"'
NEW_KEY = "agent.runtimeDetails"
# 反控（语义判据）：同文件另一枚同形折叠已由他笔改成读词典，本格不许把它拽回内联
SIBLING_READ = 't("agent.obsAdvancedDetail")'
# 反控：语言码查表两处（toolLabels[...]?.[zh ? "zh" : "en"]）必须仍在
LANGCODE_PROBE = '[zh ? "zh" : "en"]'

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
    dock = lines(DOCK)
    dock_body = "\n".join(dock)
    d = read(DICT)
    checks: list[tuple[str, bool]] = []

    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # 1: 该形状全树归零（改前这一串全树各一处）
    tree_hits = 0
    for p in SRC.rglob("*.tsx"):
        tree_hits += sum(
            1 for ln in p.read_text(encoding="utf-8").splitlines() if TARGET_LINE_PROBE in ln
        )
    ck("全树该内联形状归零", tree_hits == 0)

    # 2-3: 目标行改为读词典（行号现读于现尖 95da0f27）
    line332 = dock[331]
    ck("332 那一行不再含中文串", "运行详情" not in line332)
    ck("332 那一行改为读词典", NEW_KEY in line332)

    # 4-5: 词典两臂都定义了新键
    vals = re.findall(r'^\s*"%s":\s*"(.+)",?$' % re.escape(NEW_KEY), d, re.M)
    ck("新键在词典里出现两处（中英各一）", len(vals) == 2)
    ck("两处文本不同（不是同一句复制两次）", len(set(vals)) == 2)

    # 6-7: 两臂逐字
    ck("英文臂文本逐字为 Runtime details", "Runtime details" in vals)
    ck("中文臂文本逐字为 运行详情", "运行详情" in vals)

    # 8: 反控（语义判据）—— 他笔落地的同形折叠仍是读词典，本格没把它拽回内联
    ck("反控：同文件那处折叠摘要仍读 agent.obsAdvancedDetail（未被本格回退）", SIBLING_READ in dock_body)

    # 9: 反控 —— 语言码查表两处仍在（没把「码」当文案改掉）
    ck("反控：语言码查表 [zh ? \"zh\" : \"en\"] 仍在", LANGCODE_PROBE in dock_body)

    # 10: 分母自检 —— 本文件含 zh ? 的行数, 现读于尖 b9f1dd53 为 35, 本格改掉一处 => 34
    cnt = sum(1 for ln in dock if "zh ?" in ln)
    ck("本文件含 zh ? 的行计数=34（现尖 35 减本格一处）", cnt == 34)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(f"total={len(checks)} failed={len(failed)}")
    print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
