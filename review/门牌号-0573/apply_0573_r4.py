# -*- coding: utf-8 -*-
"""门牌号 ORD-0573 第四批落笔门：statusCopy 那张家族表剩下的四枚 body 双臂（承 r3 那八枚）。

形同 r3 的 C 形：`X: zh` + `? "中"` + `: "英",` → 合成一行 `X: t("键"),`；键名取 CN 草稿第四列。
与 r3 同一套硬闸，另外把「合成行形状」当成写前闸（r3 第一次落笔漏了一枚冒号，是整套类型检查先撞红，
这条闸就是那一次换来的）：合成行不合 `^ *\\w+: t\\("[A-Za-z0-9.]+"\\),$` 就 ABORT，两枚文件零字节不动。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_menpaaihao_0558")
COMP = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
DICT = ROOT / "frontend/src/i18n/LocaleContext.tsx"
OUT = ROOT / "review/门牌号-0573/apply_r4_readout.txt"

SITES = [
    ("无法确认本次是否生成了新方案", "plan.baselineUnavailableBody"),
    ("服务器说这次没排出可行方案", "plan.noPlansProducedBody"),
    ("规划助手这次没能连上", "plan.assistantUnreachableBody"),
    ("这次没能生成方案。你的行程没有被改动", "plan.couldNotFinishBody"),
]
EN_ANCHOR = ('  "plan.plansWithoutAiBody": "These were assembled from places already found for '
             'this city; they do not show that your request was understood. Retry to plan from '
             'what you typed — the reason is under “Technical detail”.",')
ZH_ANCHOR = ('  "plan.plansWithoutAiBody": "这些方案是按已经找到的城市地点重新排的，'
             '不代表系统理解了你刚才那段话。想按你的要求排，请重试；原因在“技术详情”里。",')
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
for probe, key in SITES:
    hits = [i for i, l in enumerate(comp_lines) if probe in l and l.strip().startswith("? ")]
    if len(hits) != 1:
        abort("片段「%s」命中 %d 枚，必须正好一枚" % (probe[:12], len(hits)))
    i = hits[0]
    head, zh_line, en_line = comp_lines[i - 1], comp_lines[i], comp_lines[i + 1]
    m_head = re.match(r'^(\s*)([A-Za-z]\w*): zh$', head)
    m_zh = re.match(r'^(\s*)\? "((?:[^"\\]|\\.)*)"$', zh_line)
    m_en = re.match(r'^(\s*): "((?:[^"\\]|\\.)*)",$', en_line)
    if not m_head:
        abort("%s 上一行不是 `X: zh`：%r" % (key, head.strip()[:32]))
    if not m_zh or not m_en:
        abort("%s 两臂形状不合：%r" % (key, en_line.strip()[:32]))
    if any(new_lines[j] is None for j in (i - 1, i, i + 1)):
        abort("%s 目标区间已被上一处改写" % key)
    merged = '%s%s: t("%s"),' % (m_head.group(1), m_head.group(2), key)
    if not re.match(r'^[ \t]*[A-Za-z]\w*: t\("[A-Za-z0-9.]+"\),$', merged):
        abort("%s 合成行形状不合（写之前先拦，不留坏行给类型检查）：%r" % (key, merged))
    new_lines[i - 1] = merged
    new_lines[i] = None  # type: ignore[assignment]
    new_lines[i + 1] = None  # type: ignore[assignment]
    moved.append((key, m_en.group(2), m_zh.group(2)))
    LOG.append("SITE 原行 %d → %s｜字段 %s｜中文 %d 字｜英文 %d 字" % (
        i + 1, key, m_head.group(2), len(m_zh.group(2)), len(m_en.group(2))))

for key, en, zh in moved:
    if re.search(r'"%s"\s*:' % re.escape(key), dict_src):
        abort("键名已存在：%s" % key)
    if '"%s"' % en in dict_src or '"%s"' % zh in dict_src:
        abort("字典里已有同值，改复用别新建：%s" % key)
for anchor in (EN_ANCHOR, ZH_ANCHOR):
    if dict_src.count(anchor) != 1:
        abort("字典锚点命中 %d 次：%r" % (dict_src.count(anchor), anchor[:40]))

for anchor, pick in ((EN_ANCHOR, "en"), (ZH_ANCHOR, "zh")):
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
