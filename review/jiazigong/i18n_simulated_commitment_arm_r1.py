"""Regression arm: the WalletCommitments "simulated commitment" marker reads the
dictionary instead of hand-writing two languages inline.

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到现尖字节）⇒ 本臂必须红。

判据锚在具名元素 `data-testid="wallet-commitment-simulated"` 上，不靠裸行号
（同串两臂全树各一处，但行号会随他人在飞改动漂移）。

用法：`python i18n_simulated_commitment_arm_r1.py [tree_root]`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TARGET = "V8Experience.tsx"
DICT = "LocaleContext.tsx"
TESTID = 'data-testid="wallet-commitment-simulated"'
TARGET_LINE_PROBE = 'zh ? "模拟承诺" : "simulated commitment"'
NEW_KEY = "bookings.simulatedCommitment"
TIP_LINE_PROBE = 'zh ? "高级详情" : "Advanced detail"'  # 别人在飞的折叠, 守着不被误改
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
    v8 = lines(TARGET)
    d = read(DICT)
    checks: list[tuple[str, bool]] = []

    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # 1: 该形状在全树归零（这两臂在现尖全树各一处, 故不是空判据）
    tree_hits = 0
    for p in SRC.rglob("*.tsx"):
        tree_hits += sum(
            1 for ln in p.read_text(encoding="utf-8").splitlines() if TARGET_LINE_PROBE in ln
        )
    ck("全树该内联形状归零", tree_hits == 0)

    # 2-3: 具名元素那两行（testid 行 +1）已改为读词典
    idx = [i for i, ln in enumerate(v8) if TESTID in ln]
    ck("具名元素 wallet-commitment-simulated 仍在（一处）", len(idx) == 1)
    if idx:
        window = "\n".join(v8[idx[0] + 1: idx[0] + 4])
        ck("该元素后三行内不再含中文串", "模拟承诺" not in window)
        ck("该元素后三行内改为读词典", NEW_KEY in window)
    else:
        ck("该元素后三行内不再含中文串", False)
        ck("该元素后三行内改为读词典", False)

    # 4-5: 词典两臂都定义了新键
    vals = re.findall(r'^\s*"%s":\s*"(.+)",?$' % re.escape(NEW_KEY), d, re.M)
    ck("新键在词典里出现两处（中英各一）", len(vals) == 2)
    ck("两处文本不同（不是同一句复制两次）", len(set(vals)) == 2)

    # 6-7: 两臂逐字
    ck("英文臂文本逐字为 simulated commitment", "simulated commitment" in vals)
    ck("中文臂文本逐字为 模拟承诺", "模拟承诺" in vals)

    # 8: 反控 —— 同族另一处（别人在飞的一枚）必须仍在
    ck("同族另一处「高级详情」仍在现尖的原地内联", TIP_LINE_PROBE in "\n".join(v8))

    # 9: 语言码桶仍在（计数器没把「码」与「文案」混起来）
    ck("语言码桶仍在（zh ? \"zh-CN\" 未被误改）", LANGCODE_PROBE in "\n".join(v8))

    # 10: 分母自检 —— 本文件该形状从 8 降到 7
    cnt = sum(1 for ln in v8 if 'zh ? "' in ln)
    ck("本文件 zh ? \" 形状计数=7（现尖 8 减本格一处）", cnt == 7)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(f"total={len(checks)} failed={len(failed)}")
    print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
