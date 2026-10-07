"""Regression arm: V8Experience.tsx:2915 reads the dictionary instead of hand-writing
the attribution label in two languages inline.

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到父字节）⇒ 本臂必须红。

树根可由第一个参数传入：臂必须能被指到一份把源文件回退到父字节的独立副本上，
否则它在快照上恒绿，是一把永远说「是」的尺。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TARGET_REL = "frontend/src/app/V8Experience.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
TARGET_NO = 2915
PROBE = 'zh ? "服务器给出的原因：" : "Server\'s own reason: "'
NEW_KEY = "hub.continuationServerReason"
# 同串在别处的形状：英文臂全树唯一，中文臂在 PlanWithAiSheet.tsx 里是另一枚独立
# 内联（少了尾冒号），且 recovery.serverReason 已是词典键。三处都要活着，
# 否则「这一枚消失了」是空判据。
SIBLING_PLAN = "frontend/src/features/planning/PlanWithAiSheet.tsx"
SIBLING_PLAN_PROBE = '? "服务器给出的原因"'
DICT_TWIN_KEY = "recovery.serverReason"


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    v8_path = root / TARGET_REL
    d_path = root / DICT_REL
    if not v8_path.is_file():
        print(f"FAIL target missing: {v8_path}")
        return 1
    v8 = v8_path.read_text(encoding="utf-8").splitlines()
    d = d_path.read_text(encoding="utf-8")
    plan = (root / SIBLING_PLAN).read_text(encoding="utf-8")

    checks: list[tuple[str, bool]] = []

    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    hits = [i + 1 for i, ln in enumerate(v8) if PROBE in ln]
    ck("目标文件的该形状已归零", len(hits) == 0)
    ck(f"{TARGET_NO} 那一行不再含中文串", "服务器给出的原因" not in v8[TARGET_NO - 1])
    ck(f"{TARGET_NO} 那一行改为读词典", NEW_KEY in v8[TARGET_NO - 1])

    en_keys = re.findall(r'^\s*"%s":\s*"(.+)",?$' % re.escape(NEW_KEY), d, re.M)
    ck("新键在词典里出现两处（中英各一）", len(en_keys) == 2)
    ck("两处文本不同（不是同一句复制两次）", len(set(en_keys)) == 2)
    ck("英文臂逐字为 Server's own reason: ", "Server's own reason: " in en_keys)
    ck("中文臂逐字为 服务器给出的原因：", "服务器给出的原因：" in en_keys)

    # 反控的另一半：同形三处仍存活
    ck("PlanWithAiSheet 那枚独立内联仍在", SIBLING_PLAN_PROBE in plan)
    ck("recovery.serverReason 词典孪生仍在", DICT_TWIN_KEY in d)
    ck("技术详情折标仍读词典（上格改的没被回退）",
       't("hub.continuationTechnicalDetail")' in "\n".join(v8))

    # 分母自检：语言码两桶仍在，计数器没把「码」与「文案」混起来
    joined = "\n".join(v8)
    ck("语言码桶一仍在（查表用 zh/en）", 'zh ? "zh" : "en"' in joined)
    ck("语言码桶二仍在（Intl 区域名）", 'zh ? "zh-CN" : "en-GB"' in joined)

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
