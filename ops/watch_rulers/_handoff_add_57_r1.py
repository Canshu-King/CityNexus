# -*- coding: utf-8 -*-
u"""交接稿补一节：五·五十七——落地表**刚出生就过期**，那是尖在动，不是表坏了。

为什么必须写（第⑨格从 19:37 起每拍报红，我 21:12–21:19 才量清）：
  21:12:51 现读尖 `4323a5ce905e` ⇒ 九张表全部过期；
  21:16 重跑 `_landing_plan_r1.py`（**纯只读**：ls-remote／merge-base／ls-tree／diff），
         rc=0，出完整表：候选 14 枚、两两互斥 3 对、谁都不冲突 11 枚；
  21:19 重定向落盘 `_landing_plan_1006_2116.txt`（3761 B，表尖 4323a5ce905e）；
  21:19:46 第⑨格**照旧报过期**：表尖 4323a5ce905e ≠ 现读 **ff7f62011821**。
⇒ 三分钟里尖又走了一格。**号令者此刻正在连续落地**，所以任何表一出生就过期。

**判据（下一班别再无限重跑）**：
  · `_landing_plan_r1.py` **不落盘**，它只打印；落盘那一向是 shell 重定向
    （旧表名 `_landing_plan_<月日>_<时分>.txt` 就是这么来的）。想留表要自己重定向。
  · 表的第一行印着自己用的那枚尖；第⑨格就是拿它跟现读尖对一次。
  · **尖在动 ⇒ 表必然过期，这不是缺陷。** 正确的处置不是重跑到"绿"为止
    （重跑也追不上每分钟都在动的尖），而是：**点单前的那一拍现跑一次、现读一次尖**，
    然后用那份当拍即用的顺序。表只提供"哪两枚改同一枚文件"的**互斥对**，那个结论
    对尖的小幅移动不敏感；真正随尖变的是"还能不能干净落地"。

**我不动手落地**：落地属权威线移动，只由号令者做（`AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1`）。
我 0 次 fetch 写、0 次 apply、0 次动那条线；只跑只读表 + 落一份档。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")

SEC = u"""## 五·五十七、落地表**刚出生就过期**：那是尖在动，不是表坏了

第⑨格从 19:37 起每拍报红，21:12–21:19 才量清（下面四个时刻都是现读）：

| 时刻 | 读数 |
|---|---|
| 21:12:51 | 权威尖 `4323a5ce905e` ⇒ 手上九张表全部过期 |
| 21:16 重跑 `_landing_plan_r1.py`（**纯只读**：ls-remote／merge-base／ls-tree／diff） | rc=0，出完整表：候选 **14 枚**、两两互斥 **3 对**、谁都不冲突 **11 枚** |
| 21:19 重定向落盘 `_landing_plan_1006_2116.txt` | 3761 字节，表尖 `4323a5ce905e` |
| 21:19:46 第⑨格照旧报过期 | 表尖 `4323a5ce905e` ≠ 现读 **`ff7f62011821`** |

⇒ **三分钟里尖又走了一格**：号令者此刻正在连续落地，所以任何表一出生就过期。

**下一班别再无限重跑**。三件事要知道：

1. `_landing_plan_r1.py` **不落盘**，它只打印；落盘那一向是 shell 重定向
   （旧表名 `_landing_plan_<月日>_<时分>.txt` 就是这么来的）。想留表要自己重定向。
2. 表的第一行印着自己用的那枚尖；第⑨格就是拿它跟现读尖对一次。
3. **尖在动 ⇒ 表必然过期，这不是缺陷。** 正确处置**不是**重跑到"绿"为止（追不上每分钟
   都在动的尖），而是：**点单前那一拍现跑一次、现读一次尖**，用那份当拍即用的顺序。
   表真正提供的东西是「哪两枚改同一枚文件」这组**互斥对**（现读 3 对，全部集中在
   `frontend/src/app/V8Experience.tsx`），那个结论对尖的小幅移动**不敏感**；
   真正随尖变的是"还能不能干净落地"。

**我不动手落地**：落地属权威线移动，只由号令者做（`AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1`）。
我这一轮 0 次 fetch 写、0 次 apply、0 次动那条线，只跑只读表 + 落一份档。
"""
ANCHOR = u"## 五·五十六、"


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if u"五·五十七" in t:
        print(u"已在 ⇒ 不重复补")
        return 0
    i = t.find(ANCHOR)
    if i < 0:
        print(u"REFUSE：找不到五·五十六锚")
        return 1
    new = t[:i] + SEC + u"\n" + t[i:]
    heads = re.findall(r"^## .+$", new, re.M)
    if any(h.startswith(u"## ##") for h in heads):
        print(u"REFUSE：标题粘连，未写盘")
        return 1
    if any(l.startswith(u"### ") for l in new.splitlines()):
        print(u"REFUSE：出现三级标题，未写盘")
        return 1
    dup = [h for h in set(heads) if heads.count(h) > 1]
    if dup:
        print(u"REFUSE：重号标题 %s" % dup)
        return 1
    bak = HAND + u".bak_57_2120"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(bak and t)
    io.open(HAND, "w", encoding="utf-8", newline="").write(new)
    print(u"已补 五·五十七；行数 %d → %d；五·小节现 %d 节"
          % (t.count(u"\n"), new.count(u"\n"),
             len(re.findall(r"^## 五·", new, re.M))))
    return 0


if __name__ == "__main__":
    sys.exit(main())