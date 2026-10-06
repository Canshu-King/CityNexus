# -*- coding: utf-8 -*-
"""把「刷新提示」那格从钉字面短语改成抽数比对。

成因（10-04 22:2x，我自咬）：我把页脚那句从「自动刷新 6 秒」改成大白话「每 6 秒自己刷一次」，
这一格立刻红——它守的语义是「人看到的秒数 == 代码里的轮询毫秒」，可它用字面短语当锚，
所以任何换措辞都会红，等于把文案焊死在旧腔调上。

改法不是放水，是**收紧**：新锚要求页脚那一行里必须出现「N 秒」，且 N*1000 必须等于
setInterval(refresh, M) 的 M。少了数字红、写错数字也红，只有措辞自由。
"""
import ast
import io
import sys

P = u"D:/moodle/agent_bus/board_check_r1.py"
s = io.open(P, encoding="utf-8", errors="replace").read()

OLD = u'''    # 回归锁住两枚浏览器才看得见的体验修复：轮询仍为 6 秒，长句表格必须可收缩换行。
    if st == 200 and u"自动刷新 6 秒" in raw and u"setInterval(refresh,6000)" in raw:
        green.append(u"刷新提示与轮询腿一致：6 秒")
    else:
        red.append(u"刷新提示/轮询腿不一致（提示=%s｜轮询=%s）"
                   % (u"自动刷新 6 秒" in raw, u"setInterval(refresh,6000)" in raw))'''

NEW = u'''    # 回归锁住两枚浏览器才看得见的体验修复：人看到的刷新秒数 == 代码轮询毫秒，长句表格可收缩换行。
    # 锚点收紧（10-04 22:2x 自咬一次）：原先钉字面「自动刷新 6 秒」，我把那句改成大白话「每 6 秒自己
    # 刷一次」它就红了——守的是数，不是腔调。现在要求页脚那行必须带「N 秒」，且 N*1000 == setInterval
    # 的毫秒；少数字红、写错数也红，只有措辞自由。
    m_hint = re.search(u'header-meta">[^<]*?(\\d+)\\s*秒', raw)
    m_iv = re.search(r"setInterval\\(refresh,(\\d+)\\)", raw)
    hint_s = int(m_hint.group(1)) if m_hint else None
    iv_ms = int(m_iv.group(1)) if m_iv else None
    if st == 200 and hint_s and iv_ms and hint_s * 1000 == iv_ms:
        green.append(u"刷新提示与轮询腿一致：页面写 %d 秒＝代码 %d 毫秒" % (hint_s, iv_ms))
    else:
        red.append(u"刷新提示/轮询腿不一致（页面那行写的秒=%s｜setInterval 毫秒=%s）" % (hint_s, iv_ms))'''

if s.count(OLD) != 1:
    sys.exit(u"ABORT：锚命中 %d 次，未改动" % s.count(OLD))
s2 = s.replace(OLD, NEW, 1)
if u"import re" not in s2:
    sys.exit(u"ABORT：这文件没 import re，用了 re 就是假绿")
ast.parse(s2)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s2)
print(u"已改：刷新格改为抽数比对（re 已在文件里）")
