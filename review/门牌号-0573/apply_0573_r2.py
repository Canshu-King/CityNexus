# -*- coding: utf-8 -*-
"""门牌号 ORD-0573 第二批落笔门：同族三处（两枚 JSX 形、一枚括号形），键名一律取 CN 草稿那一列。

与第一批同一套规矩，只多认一种形状：
  A 形 `(zh` + `? "中"` + `: "英")}` → 换成 `(t("键"))}`
  B 形 `{zh` + `? "中"` + `: "英"}` → 换成 `{t("键")}`
硬闸：每块整枚文件逐字命中正好一次；字典里同值或同名一律先查，撞上就 ABORT 不落笔；
插入锚用第一批留下的那枚键在各臂的整行（含值）做锚，两臂各唯一。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_menpaaihao_0558")
COMP = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
DICT = ROOT / "frontend/src/i18n/LocaleContext.tsx"
OUT = ROOT / "review/门牌号-0573/apply_r2_readout.txt"

# (汉字臂片段, 草稿给的键名, 形状)
SITES = [
    ("这台服务配了一个 AI 凭据", "plan.aiConfiguredUnverifiedNote", "paren"),
    ("模型这一侧答复了请求但拒绝了这次生成", "plan.aiProviderRefusedNote", "paren"),
    ("用你自己的话描述这趟旅行", "plan.describeTripHint", "jsx"),
]
EN_ANCHOR = '  "plan.aiStateUnknownNote": "The AI status endpoint did not answer. That means we do not know — not that it works or that it is broken.",'
ZH_ANCHOR = '  "plan.aiStateUnknownNote": "读不到 AI 状态（状态接口没有应答）。这只说明我们不知道，不代表它可用或不可用。",'
LOG: list[str] = []


def abort(why: str) -> None:
    LOG.append("ABORT " + why)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(LOG))
    raise SystemExit(3)


comp_lines = COMP.read_text(encoding="utf-8").split("\n")
dict_src = DICT.read_text(encoding="utf-8")

moved: list[tuple[str, str, str]] = []
new_lines = list(comp_lines)
for probe, key, shape in SITES:
    hits = [i for i, l in enumerate(comp_lines) if probe in l and l.strip().startswith("? ")]
    if len(hits) != 1:
        abort(f"片段「{probe[:12]}」命中 {len(hits)} 枚，必须正好一枚")
    i = hits[0]
    head, zh_line, en_line = comp_lines[i - 1], comp_lines[i], comp_lines[i + 1]
    open_tok = "(" if shape == "paren" else "{"
    if head.strip() != open_tok + "zh":
        abort(f"{key} 上一行不是裸 {open_tok}zh：{head.strip()[:24]!r}")
    m_zh = re.match(r'^(\s*)\? "((?:[^"\\]|\\.)*)"$', zh_line)
    pat = r'^(\s*): "((?:[^"\\]|\\.)*)"\)\}$' if shape == "paren" else r'^(\s*): "((?:[^"\\]|\\.)*)"\}$'
    m_en = re.match(pat, en_line)
    if not m_zh or not m_en:
        abort(f"{key} 两臂形状不合：{en_line.strip()[:28]!r}")
    if any(l is None for l in (new_lines[i - 1], new_lines[i], new_lines[i + 1])):
        abort(f"{key} 目标区间已被上一处改写")
    indent = " " * (len(head) - len(head.lstrip(" ")))
    if shape == "paren":
        new_lines[i - 1] = '%s(t("%s"))}' % (indent, key)
    else:
        new_lines[i - 1] = '%s{t("%s")}' % (indent, key)
    new_lines[i] = None  # type: ignore[assignment]
    new_lines[i + 1] = None  # type: ignore[assignment]
    moved.append((key, m_en.group(2), m_zh.group(2)))
    LOG.append("SITE 原行 %d → %s｜形状 %s｜中文 %d 字｜英文 %d 字" % (i + 1, key, shape, len(m_zh.group(2)), len(m_en.group(2))))

for key, en, zh in moved:
    if re.search(r'"%s"\s*:' % re.escape(key), dict_src):
        abort(f"键名已存在：{key}")
    if '"%s"' % en in dict_src or '"%s"' % zh in dict_src:
        abort(f"字典里已有同值，改复用别新建：{key}")
for anchor in (EN_ANCHOR, ZH_ANCHOR):
    if dict_src.count(anchor) != 1:
        abort(f"字典锚点命中 {dict_src.count(anchor)} 次")

for anchor, pick in ((ZH_ANCHOR, "zh"), (EN_ANCHOR, "en")):
    rows = "".join('  "%s": "%s",\n' % (k, zh if pick == "zh" else en) for k, en, zh in moved)
    dict_src = dict_src.replace(anchor + "\n", anchor + "\n" + rows, 1)
    LOG.append("DICT 臂 %s 插入 %d 行" % (pick, rows.count("\n")))

COMP.write_text("\n".join(l for l in new_lines if l is not None), encoding="utf-8", newline="\n")
DICT.write_text(dict_src, encoding="utf-8", newline="\n")
LOG.append("written comp=%d dict=%d" % (len(COMP.read_bytes()), len(DICT.read_bytes())))
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8", newline="\n")
print("\n".join(LOG))
raise SystemExit(0)
