# -*- coding: utf-8 -*-
"""板子的读者是**主人**，包工头是名册里那一扇 qoder:494abfd7——把两者彻底分开。

主人 10-05 00:1x 指着屏幕说的：「我不是包工头，我是主人，是开发商，
494abfd7 这个会话才是包工头，你这些给包工头看才对吧。」

两处都错了，而且第二处更实质：
① 黄框与三列标题用「包工头／工头」称呼读者 ⇒ 把主人喊成了号令者；
② 「要你点头的」那一列里塞的是 `selfdecl`（车道自报下一格）与哨兵报警——
   按常设裁定，派单、验收、催活都归号令者点，这些根本不该占主人的视野。

改法：入列判据一个字不动（哪些条目算「要人动」照旧），只按**收件人**把那一列拆成两列：
「要主人定的」（to 是 human:you01 或全体）与「等包工头点的」（其余）。
人话句也分岔：落在包工头那列的，明说「这格归包工头点，你不用动」。
"""
import ast
import io
import sys

P = u"D:/moodle/agent_bus/board.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:46]))
        return
    s = s.replace(old, new, 1)


# ── 服务端 ────────────────────────────────────────────────────────────────
rep(u'HID = os.environ.get("BOARD_HUMAN", "human:you01")',
    u'''HID = os.environ.get("BOARD_HUMAN", "human:you01")
# 读这块板的是主人（开发商）；包工头＝号令者＝名册里 qoder:494abfd7 那一扇，他是**被看的对象**之一。
# 10-05 00:1x 主人指出我把黄框写成「包工头：这块是专门给你的」，等于把读者喊成了号令者。
# 这两个名字从此分开用：对读者说话称"主人"，指那一扇称"包工头"。
CMDR_LANE = u"qoder:494abfd7"
WATCH_LANE = u"qoder:42d1a6fa"''')

rep(u'''    if u"selfdecl" in low:
        return u"他自己报了下一格要干什么 ⇒ 等你回一句「准」或「换哪格」"''',
    u'''    boss = (to == HID) or (to == u"*")
    if u"selfdecl" in low:
        if boss:
            return u"有车道自己报了下一格要干什么 ⇒ 按规矩这格归包工头（号令者）点，你不用动；要驳那句才轮到你"
        return u"他自己报了下一格要干什么 ⇒ 等你回一句「准」或「换哪格」"''')

rep(u'''        return u"哨兵 %s 档报警，压在「%s」的收件框里没人取 ⇒ %s" % (
            band, who, ALARM_PLAIN.get(band, u"点开下面原文看是哪一格"))''',
    u'''        if boss:
            return u"哨兵 %s 档报警没人取（压在「%s」收件框里）⇒ 这格归包工头处置：催他去取或把这地址作废，你不用动" % (band, who)
        return u"哨兵 %s 档报警，压在「%s」的收件框里没人取 ⇒ %s" % (
            band, who, ALARM_PLAIN.get(band, u"点开下面原文看是哪一格"))''')

rep(u'''    f = fleet()
    for r in f["rows"]:
        why = []''',
    u'''    # 入列判据不动，只按收件人把「要人动的」拆两列：主人自己该定的 vs 等包工头点的。
    need_human = [x for x in need if str(x["to"]) in (HID, u"*")]
    need_cmdr = [x for x in need if str(x["to"]) not in (HID, u"*")]
    f = fleet()
    for r in f["rows"]:
        why = []''')

rep(u'''    return {"at": time.strftime("%H:%M:%S"), "need": need, "notice": notice[:24],
            "waiting": waiting, "counts": {"need": len(need), "notice": len(notice[:24]), "notice_total": len(notice),
                                           "waiting": len(waiting),''',
    u'''    return {"at": time.strftime("%H:%M:%S"), "need": need, "notice": notice[:24],
            "need_human": need_human, "need_cmdr": need_cmdr,
            "waiting": waiting, "counts": {"need": len(need), "notice": len(notice[:24]), "notice_total": len(notice),
                                           "need_human": len(need_human), "need_cmdr": len(need_cmdr),
                                           "waiting": len(waiting),''')

# ── 呈现：四列、称呼、黄框 ──────────────────────────────────────────────────
rep(u".tgrid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}",
    u".tgrid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px}")

rep(u'''<div class="goto">包工头：这块下面第一格抽屉「<b>零</b>」是专门给你的 ——
 <b id="gotoNeed">?</b> 件等你点头 · <b id="gotoNotice">?</b> 件报你一声 · <b id="gotoWait">?</b> 个汉子的活断了等你续。
 <b>要回话不用往下翻：那块最底下就有个框，点每条上的「就这条回一句」，人已经替你选好。</b></div>''',
    u'''<div class="goto">主人：这块下面第一格抽屉「<b>零</b>」是专门给你的 ——
 <b id="gotoNeed">?</b> 件真要你定 · <b id="gotoCmdr">?</b> 件等包工头点 · <b id="gotoNotice">?</b> 件报你一声 · <b id="gotoWait">?</b> 个汉子的活断了。
 包工头是 <span class="mono">494abfd7</span>（号令者）那一扇，他的活也在第一表里看得见；派单、验收、催活按规矩都归他点，
 那些我没塞进你这列。<b>要说话就在那块最底下的框里写一句，点每条上的「就这条回一句」人已经替你选好。</b></div>''')

rep(u'<summary>零、工头你先看这块：要你点头的 · 报你一声的 · 站着等活的</summary>',
    u'<summary>零、主人你先看这块：真要你定的 · 等包工头点的 · 报你一声的 · 站着等活的</summary>')
rep(u'<div class="titchips">工头：<b id="tNeed">?</b> 件等你点头 · <b id="tNotice">?</b> 件报你一声 · <b id="tWait">?</b> 个汉子的活断了等你续</div>',
    u'<div class="titchips">主人：<b id="tNeed">?</b> 件真要你定 · <b id="tCmdr">?</b> 件等包工头点 · <b id="tNotice">?</b> 件报你一声 · <b id="tWait">?</b> 个汉子的活断了</div>')
rep(u''' <div class="tcol"><h3>要你点头的（越在上头的，压得越久）</h3><div id="tNeedList" class="dim">—</div></div>''',
    u''' <div class="tcol"><h3>真要你定的（你是开发商：要不要做、做到什么样）</h3><div id="tNeedList" class="dim">—</div></div>
 <div class="tcol"><h3>等包工头点的（派单·验收·催活归他，你不用动）</h3><div id="tCmdrList" class="dim">—</div></div>''')
rep(u'''<div class="dim" style="margin-top:6px">凭什么进这几列（口径一个字没改，写在这儿给你核）：要你点头的＝提问／派单还没人答的、他自己报了下一格要干什么的、报警没人取走的；
 报你一声的＝近六小时其余通信；站着等活的＝第一表里 45 分钟没出字、话没接上、收件框压着件，三样占一样的。</div>''',
    u'''<div class="dim" style="margin-top:6px">凭什么进这几列（入列口径一个字没改，只是按收件人分成两列）：要人动的＝提问／派单还没人答的、他自己报了下一格要干什么的、报警没人取走的；
 其中收件人是你或全体的进「真要你定的」，其余（发给号令者或值守的）进「等包工头点的」。
 报你一声的＝近六小时其余通信；站着等活的＝第一表里 45 分钟没出字、话没接上、收件框压着件，三样占一样的。</div>''')

# ── JS：两列渲染与计数 ─────────────────────────────────────────────────────
rep(u" $('#gotoNeed').textContent=t.counts.need;$('#gotoNotice').textContent=t.counts.notice_total;$('#gotoWait').textContent=t.counts.waiting;",
    u""" $('#tCmdr').textContent=t.counts.need_cmdr;
 $('#gotoNeed').textContent=t.counts.need_human;$('#gotoCmdr').textContent=t.counts.need_cmdr;
 $('#gotoNotice').textContent=t.counts.notice_total;$('#gotoWait').textContent=t.counts.waiting;""")
rep(u" $('#tNeed').textContent=t.counts.need;", u" $('#tNeed').textContent=t.counts.need_human;")
rep(u""" $('#tNeedList').innerHTML=t.need.length?t.need.map(x=>row(x,'need')).join(''):'<span class="dim">（没有要你点头的）</span>';""",
    u""" $('#tNeedList').innerHTML=(t.need_human||[]).length?t.need_human.map(x=>row(x,'need')).join(''):'<span class="dim">（这列空着：该你定的事没有）</span>';
 $('#tCmdrList').innerHTML=(t.need_cmdr||[]).length?t.need_cmdr.map(x=>row(x,'need')).join(''):'<span class="dim">（包工头那侧也没欠着的）</span>';""")
rep(u"<summary style=\"font-size:15px\">要回话就在这儿写一句（说给谁已按你点的那条选好）</summary>",
    u"<summary style=\"font-size:15px\">主人要说话就在这儿写一句（说给谁已按你点的那条选好；不点就是全体）</summary>")

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：%d 条没落上，board.py 未改动" % len(miss))
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"读者与包工头已分开｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
