# -*- coding: utf-8 -*-
"""把板子上给人看的措辞改成工地大白话（主人的话：「土老帽一点，符合农民工的气质形象」）。

只动文案，不动任何判据与数：口径、凭据、阈值、路由一律照旧。
细则（判据怎么写、坐标在哪）挪进每块抽屉里一行小字，想核的人点开还在。

改完必须跑 board_check_r1.py（13 格）并在浏览器里复读渲染文字——文案是给人看的，
自测读不到"人读着顺不顺"，但能抓到我把接口改断。
"""
import ast
import io

P = u"D:/moodle/agent_bus/board.py"
s = io.open(P, encoding="utf-8", errors="replace").read()

SWAPS = [
    # 三块主表的标题
    (u'<summary>零、要你看这一屏：要你裁的 · 通知你的 · 谁在等</summary>',
     u'<summary>零、工头你先看这块：要你点头的 · 报你一声的 · 站着等活的</summary>'),
    (u'<summary>二、光荣榜（今天真交了活的，按落地块数与真回执数排；两样都能逐枚数出来）</summary>',
     u'<summary>二、光荣榜——今天真出力的汉子（按落地的块数和真回执数排，两样都能一枚枚数出来）</summary>'),
    (u'<summary>三、耻辱墙（只挂有凭据的没干活；被平台、被排单、被回包卡住的另列「免挂」，绝不混进来）</summary>',
     u'<summary>三、耻辱墙——手里有活却没动的人（每一条都带凭据；被平台、被排单、被回包卡住的另列「免挂」，不混进来）</summary>'),
    # 三列小标题
    (u'<h3>要你裁的（按最老排，越上面越久没动）</h3>', u'<h3>要你点头的（越在上头的，压得越久）</h3>'),
    (u'<h3>通知你的（近六小时，不用回也行）</h3>', u'<h3>报你一声的（近六小时，扫一眼就行，不用回）</h3>'),
    (u'<h3>谁在等你下一句（读的是各扇自己流水的末条）</h3>', u'<h3>站着等活的（读的是他们自己写的最后一句）</h3>'),
    (u'<div class="titchips"><b id="tNeed">?</b> 件要你裁 · <b id="tNotice">?</b> 件通知你 · <b id="tWait">?</b> 扇在等你下一句</div>',
     u'<div class="titchips">工头：<b id="tNeed">?</b> 件等你点头 · <b id="tNotice">?</b> 件报你一声 · <b id="tWait">?</b> 个汉子的活断了等你续</div>'),
    # 说话那一块
    (u'<summary>六、你要说话</summary>', u'<summary>六、你要他们干一票，就这儿递话</summary>'),
    # 顶部与墙头的话
    (u"光荣榜 · ',ho.day+'：'+ho.counts.on_board+' 扇今天有落地块，合计 '+ho.counts.blocks+' 枚｜其中 '+",
     u"光荣榜 · '+ho.day+'：'+ho.counts.on_board+' 个汉子今天交了活，一共 '+ho.counts.blocks+' 块｜其中 '+"
     u"''+' 个手里还压着一格没补｜'"),
    (u"耻辱墙：'+sh.rows.length+' 扇有凭据地没干活｜同队此刻在写 '+f.counts.writing+'/'+f.rows.length+' 扇｜最长一扇 '+mx+' 分钟没产出",
     u"耻辱墙：'+sh.rows.length+' 个汉子的活没动（条条有凭据）｜同一时刻队里在写 '+f.counts.writing+'/'+f.rows.length+'｜最久一个 '+mx+' 分钟没出活"),
    (u"榜上照登，不藏", u"榜上照样登，不藏"),
    # 按钮与提示
    (u">发进 BB 机<", u">给他们递句话<"),
    (u"要它补的那一格", u"要他补的那一格"),
]

miss = []
for a, b in SWAPS:
    if s.count(a) < 1:
        miss.append(a[:44])
    else:
        s = s.replace(a, b, 1)

io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
ast.parse(s)
print("文案已土化｜没匹配上的条数:", len(miss))
for m in miss:
    print("   未命中 →", m)
