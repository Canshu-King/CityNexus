# -*- coding: utf-8 -*-
"""门牌号 ORD-0573 落笔的门（本轮三处，全在同族形状里）。

每处都是同一个三行形状：`  (zh` + `? "汉字"` + `: "英文")}`。整块换成一枚 `  (t("planai.键"))`，
两臂原文逐字节搬进字典两侧、成对插在同族末尾。三条硬规矩：
1. 每一块在整枚文件里必须逐字命中正好一次，否则 ABORT，一个字节不落；
2. 字典里已有同值的另一枚键就不新建（本轮三枚都现读过：字典里没有这三串）；键名本身也不许撞；
3. 两臂插入的行文本由组件里取到的原文（含内部转义、含破折号）逐字节拼出，不是我另写的。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_menpaaihao_0558")
COMP = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
DICT = ROOT / "frontend/src/i18n/LocaleContext.tsx"
OUT = ROOT / "review/门牌号-0573/apply_r1_readout.txt"

# (汉字臂片段, 键名)
SITES = [
    ("这台服务没有配置 AI 凭据", "planai.aiCredentialNotConfigured"),
    ("这台服务的 AI 开关处于关闭状态", "planai.aiSwitchedOffByOperator"),
    ("读不到 AI 状态（状态接口没有应答）", "planai.aiStatusUnreadable"),
]
EN_ANCHOR = '  "planai.importPlacesCta": "Paste your own places and import them into this trip",'
ZH_ANCHOR = '  "planai.importPlacesCta": "粘贴你自己的地点，导入这趟行程",'
LOG: list[str] = []


def abort(why: str) -> None:
    LOG.append("ABORT " + why)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(LOG))
    raise SystemExit(3)


comp_src = COMP.read_text(encoding="utf-8")
dict_src = DICT.read_text(encoding="utf-8")
comp_lines = comp_src.split("\n")

moved: list[tuple[str, str, str]] = []  # 键名, 英文原文, 中文原文
new_comp_lines = list(comp_lines)
for probe, key in SITES:
    hits = [i for i, l in enumerate(comp_lines) if probe in l and l.strip().startswith("? ")]
    if len(hits) != 1:
        abort(f"片段「{probe[:12]}」命中 {len(hits)} 枚，必须正好一枚")
    i = hits[0]
    head, zh_line, en_line = comp_lines[i - 1], comp_lines[i], comp_lines[i + 1]
    if head.strip() != "(zh":
        abort(f"{key} 上一行不是裸 (zh：{head.strip()[:20]!r}")
    m_en = re.match(r'^(\s*): "((?:[^"\\]|\\.)*)"\)\}$', en_line)
    m_zh = re.match(r'^(\s*)\? "((?:[^"\\]|\\.)*)"$', zh_line)
    if not m_en or not m_zh:
        abort(f"{key} 两臂形状不合：{en_line.strip()[:24]!r}")
    indent = " " * (len(head) - len(head.lstrip(" ")))
    new_line = '%s(t("%s"))}' % (indent, key)
    if new_comp_lines[i - 1] != head:
        abort(f"{key} 目标区间已被上一处改写，顺序有冲突")
    new_comp_lines[i - 1] = new_line
    new_comp_lines[i] = None  # type: ignore[assignment]
    new_comp_lines[i + 1] = None  # type: ignore[assignment]
    moved.append((key, m_en.group(2), m_zh.group(2)))
    LOG.append("SITE 行 %d → %s｜中文 %d 字｜英文 %d 字" % (i + 1, key, len(m_zh.group(2)), len(m_en.group(2))))

if any(l is None and False for l in new_comp_lines):
    abort("不可能分支")
comp_out = "\n".join(l for l in new_comp_lines if l is not None)

# 字典侧：先查不撞，再两臂各插三行
for key, en, zh in moved:
    if re.search(r'"%s"\s*:' % re.escape(key), dict_src):
        abort(f"键名已存在：{key}")
    if en in dict_src or ('"%s"' % zh) in dict_src:
        abort(f"字典里已有同值，改复用别新建：{key}")
for anchor, arm in ((ZH_ANCHOR, 2), (EN_ANCHOR, 1)):
    if dict_src.count(anchor) != 1:
        abort(f"字典锚点命中 {dict_src.count(anchor)} 次：arm {arm}")
for anchor, pick in ((ZH_ANCHOR, "zh"), (EN_ANCHOR, "en")):
    rows = "".join('  "%s": "%s",\n' % (k, zh if pick == "zh" else en) for k, en, zh in moved)
    dict_src = dict_src.replace(anchor + "\n", anchor + "\n" + rows, 1)
    LOG.append("DICT 臂 %s 插入 %d 行，锚点字节数 %d" % (pick, rows.count("\n"), len(anchor)))

COMP.write_text(comp_out, encoding="utf-8", newline="\n")
DICT.write_text(dict_src, encoding="utf-8", newline="\n")
LOG.append("written comp=%d dict=%d" % (len(COMP.read_bytes()), len(DICT.read_bytes())))
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8", newline="\n")
print("\n".join(LOG))
raise SystemExit(0)
