# -*- coding: utf-8 -*-
"""门牌号 ORD-0573 第三批落笔门：statusCopy 那张家族表的八枚 body 双臂（同族表格最多八处）。

只认这一种形：
  C 形 `X: zh` + `? "中"` + `: "英",` → 合成一行 `X: t("键"),`
键名一律取 CN 草稿 `E:/cn_0574/_cn_0574_0456.txt` 第四列，不自造、不改措辞。
两臂的字面不是我抄的：从组件那两行现读，摘下来直接写进字典，所以「屏上文案一字不改」这条
在这一批里是构造性成立，再用 text_identity 尺逐字节对拍一次。
硬闸：探针在整枚文件里逐字命中必须正好一枚；上一行必须正好是 `X: zh`；两臂形状不合就 ABORT；
键名或同值已在字典里就 ABORT（复用不新建）；字典锚点必须唯一。任何一条不合，两个文件零字节不动。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_menpaaihao_0558")
COMP = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
DICT = ROOT / "frontend/src/i18n/LocaleContext.tsx"
OUT = ROOT / "review/门牌号-0573/apply_r3_readout.txt"

SITES = [
    ("去“今天”对比这几个方案", "plan.plansReadyBody"),
    ("请求已中止，你的行程没有被改动", "plan.cancelledBody"),
    ("请求本身已经发出去了", "plan.cancelledAfterSendBody"),
    ("这台设备停止等待了", "plan.keylessWriteDeadlineBody"),
    ("网络或后端没有响应", "plan.unreachableBody"),
    ("服务端说明了原因", "plan.refusedRequestBody"),
    ("这次是服务端出错", "plan.serverErroredBody"),
    ("这些方案是按已经找到的城市地点重新排的", "plan.plansWithoutAiBody"),
]
EN_ANCHOR = ('  "plan.describeTripHint": "Describe the trip in your own words '
             '— the more specific the better.",')
ZH_ANCHOR = '  "plan.describeTripHint": "用你自己的话描述这趟旅行，越具体越好。",'
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
