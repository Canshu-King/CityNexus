"""Regression arm: V8Experience.tsx:2912 reads the dictionary instead of hand-writing
two languages inline.

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到现尖字节）⇒ 本臂必须红。
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

TARGET = "V8Experience.tsx"
TARGET_LINE_PROBE = 'zh ? "技术详情" : "Technical detail"'
DICT = "LocaleContext.tsx"
NEW_KEY = "hub.continuationTechnicalDetail"
# 同形存活对照：同一串在四个文件各一处。本格只按行号改 V8Experience.tsx:2912，
# 另外三处必须仍在（否则「内联消失了吗」是空判据）。
SIBLINGS = [
    ("PlanWithAiSheet.tsx", '{zh ? "技术详情" : "Technical detail"}'),
    ("V14RecoveryTruthPanel.tsx", '{zh ? "技术详情" : "Technical detail"}'),
    ("JourneyTrialSetup.tsx", '{zh ? "技术详情" : "Technical detail"}'),
]

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

    # 1-3: 目标行不再手写两臂
    hits = [i + 1 for i, ln in enumerate(v8) if TARGET_LINE_PROBE in ln]
    ck("目标文件的该形状已归零", len(hits) == 0)
    ck("2912 那一行不再含中文串", "技术详情" not in v8[2911])
    ck("2912 那一行改为读词典", NEW_KEY in v8[2911])

    # 4-5: 词典两臂都定义了新键
    en_keys = re.findall(r'^\s*"%s":\s*"(.+)",?$' % re.escape(NEW_KEY), d, re.M)
    ck("新键在词典里出现两处（中英各一）", len(en_keys) == 2)
    ck("两处文本不同（不是同一句复制两次）", len(set(en_keys)) == 2)

    # 6: 英文臂写的就是那句英文
    ck("英文臂文本逐字为 Technical detail", "Technical detail" in en_keys)
    # 7: 中文臂写的就是那句中文
    ck("中文臂文本逐字为 技术详情", "技术详情" in en_keys)

    # 8-10: 反控的另一半 —— 同形三处存活
    for i, (fname, probe) in enumerate(SIBLINGS, start=8):
        ck(f"同形对照 {i - 7}: {fname} 仍手写该串", probe in read(fname))

    # 11: 分母自检 —— 全树该形状总数（本格后应为三，不是零）
    total = 0
    for p in SRC.rglob("*.tsx"):
        total += sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if TARGET_LINE_PROBE in ln)
    ck("全树同形计数=三（改一处、留三处）", total == 3)

    # 12: 语言码那一桶仍在（计数器没把「码」与「文案」混起来）
    ck("语言码桶仍在（zh ? \"zh-CN\" 未被误改）", 'zh ? "zh-CN" : "en-GB"' in "\n".join(v8))

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
