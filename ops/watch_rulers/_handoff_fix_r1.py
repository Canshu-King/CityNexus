# -*- coding: utf-8 -*-
u"""交接稿体检与修复：行首 `## ## ` 粘连 + 小节编号统一 + 几类结构性重影。

为什么必须留这把尺：这份东西是**给下一班读**的。10-06 那天我往里插了十四节，
其中九节标题变成 `## ## 五·…`（Markdown 渲染成一级套一级，目录也乱），
而且**肉眼与 grep 都扫不出来**——`grep "^## 五"` 看不见那一行，因为行首是 `## ##`。
病因只有一个：插入时 `sec` 自带 `## ` 开头，又拿同样以 `## ` 开头的锚替换，拼成 `## ## `。

两条设计教训都落在这版里：
  一、**只修行首**。正文里引用 `## ##` 这个字符串（下面那段正是在讲它）不是缺陷；
     第一版按全文件 count 数粘连，把自己的说明也数进去 ⇒ 报假红。
  二、**编号命中 0 次是正常**（已统一过一遍）；命中 1 次才替换；命中 2 次以上是异常形状，拒写交给人看。

跑法：python _handoff_fix_r1.py --dry   # 只体检
      python _handoff_fix_r1.py         # 改并自检（改完仍不干净就整批不写）
"""
import io
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")

RENUM = [
    (u"五·一一、", u"五·十一、"),
    (u"五·一二、", u"五·十二、"),
    (u"五·一三、", u"五·十三、"),
    (u"五·一四、", u"五·十四、"),
    (u"五·一五、", u"五·十五、"),
    (u"五·一六、", u"五·十六、"),
    (u"五·一七、", u"五·十七、"),
    (u"五·一八、", u"五·十八、"),
    (u"五·一九、", u"五·十九、"),
    (u"五·二〇、", u"五·二十、"),
    (u"五·二一、", u"五·二十一、"),
    (u"五·二二、", u"五·二十二、"),
    (u"五·二三、", u"五·二十三、"),
    (u"五·二四、", u"五·二十四、"),
]

GLUED_RE = re.compile(r"(?m)^(## )(?:## )+")
DUPHEAD_KEYS = (u"glued", u"dup_head", u"adj_dup", u"bad_head")


def _empty_body_heads(lines):
    u"""标题下正文为空：只认两种真形态——标题行本身是空的 `##`，或它后面只剩空行就走到文末/下一个标题。

    为什么这么写：第一版把"标题 + 空行 + 正文"（Markdown 的**正常**格式，全文七十个标题都这样）
    也判成空正文 ⇒ 满屏假红。真正的空正文是"写丢了正文、光剩一行标题"。
    """
    out = []
    for i, l in enumerate(lines):
        if not l.startswith(u"## "):
            continue
        rest = lines[i + 1:]
        while rest and not rest[0].strip():
            rest = rest[1:]
        if l.strip() == u"##" or not rest:
            out.append(l[:34])
    return out


def report(t):
    lines = t.splitlines()
    heads = [l for l in lines if l.startswith(u"## ")]
    c = Counter(heads)
    glued = [(i + 1, l[:48]) for i, l in enumerate(lines)
             if l.startswith(u"## ") and l[3:].startswith(u"## ")]
    return {
        u"lines": len(lines),
        u"chars": len(t),
        u"glued": len(glued),
        u"glued_where": glued,
        u"dup_head": [(k[:40], v) for k, v in c.items() if v > 1],
        # 标题被**正文引用**的次数：不是缺陷，但它是"拿它当锚会 AssertionError"的来源
        # （10-06 18:33 我连栽两回：把"字符串出现 2 次"误读成"标题重影"，
        #  而那第 2 次其实是正文里的引用）。报出来，下一班就知道别拿它当唯一锚。
        u"head_mentioned": sorted((k[:34], t.count(k)) for k in c if t.count(k) > len([l for l in lines if l == k])),
        u"adj_dup": [(i + 1, l[:40]) for i, l in enumerate(lines[:-1])
                     if l.strip() and l == lines[i + 1].strip()],
        u"bad_head": [l[:48] for l in lines
                      if l.startswith(u"##") and not l.startswith(u"## ")],
        # 决策单在不在：它被删了、而交接稿还指着它，下一班就扑空
        u"decision_sheet": os.path.exists(os.path.join(HERE, u"DECISION_1006.md")),
        # 标题下正文为空（写丢了正文、光剩一行标题）：结构体检查不出，必须单独判。
        # 注意：Markdown 里"标题 + 空行 + 正文"是**正常**格式（全文七十个标题都这样），
        # 我第一版把"标题后是空行"也判成空正文 ⇒ 满屏假红。真正的空正文只有一种：
        # 标题之后只剩空行就走到文末（这一节被写成了光杆），或紧跟着下一个标题。
        u"empty_body_head": _empty_body_heads(lines),
    }


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    print(u"修前：%s" % report(t))
    if u"--dry" in sys.argv:
        return 0

    changed = 0
    fixed = sum(1 for l in t.splitlines()
                if l.startswith(u"## ") and l[3:].startswith(u"## "))
    if fixed:
        t = GLUED_RE.sub(u"\\1", t)
        changed += fixed
    for old, new in RENUM:
        c = t.count(old)
        if c > 1:
            print(u"REFUSE：编号 %s 出现 %d 次 ⇒ 整批不写（这形状得人看）" % (old, c))
            return 1
        if c == 1:
            t = t.replace(old, new)
            changed += c

    after = report(t)
    if any(after[k] for k in DUPHEAD_KEYS):
        print(u"REFUSE：改完仍不干净 ⇒ 未写盘：%s" % after)
        return 1
    io.open(HAND, "w", encoding="utf-8", newline="").write(t)
    print(u"已写：改动 %d 处" % changed)
    print(u"修后：%s" % after)
    print(u"五·小节序列：%s" % u"、".join(re.findall(r"^## 五·([^、]+)、", t, re.M)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
