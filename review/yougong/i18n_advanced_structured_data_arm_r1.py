"""Regression arm: V8Experience.tsx:4565 reads the dictionary instead of hand-writing
two languages inline for the bookings "Advanced: structured data" summary.

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
TARGET_NO = 4565
PROBE = 'zh ? "高级：结构化数据" : "Advanced: structured data"'
NEW_KEY = "bookings.advancedStructuredData"
# 同串在别处的形状：CSS 注释里有一枚中文串（styles.css:284，纯注释不是文案），
# 英文臂全树唯一。本格按行号改，并断言 styles.css 那枚注释仍在（它本来就不是
# 文案，动它才是引入缺陷）、英文臂无第二处出现。
STYLE_COMMENT_REL = "frontend/src/styles.css"
STYLE_PROBE = "高级：结构化数据"


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    v8_path = root / TARGET_REL
    d_path = root / DICT_REL
    if not v8_path.is_file():
        print(f"FAIL target missing: {v8_path}")
        return 1
    v8 = v8_path.read_text(encoding="utf-8").splitlines()
    d = d_path.read_text(encoding="utf-8")
    style = (root / STYLE_COMMENT_REL).read_text(encoding="utf-8") if (root / STYLE_COMMENT_REL).is_file() else ""

    checks: list[tuple[str, bool]] = []
    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    hits = [i + 1 for i, ln in enumerate(v8) if PROBE in ln]
    ck("目标文件的该形状已归零", len(hits) == 0)
    ck(f"{TARGET_NO} 那一行不再含中文串", "高级：结构化数据" not in v8[TARGET_NO - 1])
    ck(f"{TARGET_NO} 那一行改为读词典", NEW_KEY in v8[TARGET_NO - 1])

    en_keys = re.findall(r'^\s*"%s":\s*"(.+)",?$' % re.escape(NEW_KEY), d, re.M)
    ck("新键在词典里出现两处（中英各一）", len(en_keys) == 2)
    ck("两处文本不同（不是同一句复制两次）", len(set(en_keys)) == 2)
    ck("英文臂逐字为 Advanced: structured data", "Advanced: structured data" in en_keys)
    ck("中文臂逐字为 高级：结构化数据", "高级：结构化数据" in en_keys)

    # 反控的另一半：同形对照仍存活
    ck("styles.css 那枚注释仍在（它不是文案，不动）", STYLE_PROBE in style)
    ck("bookings.reservationJson 同块键仍在（上邻已被接典，未回退）", "bookings.reservationJson" in d)

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
