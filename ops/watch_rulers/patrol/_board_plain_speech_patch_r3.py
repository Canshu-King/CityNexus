# -*- coding: utf-8 -*-
"""把板子改成「给包工头看」的：人话行 + 就地回话 + 全板土话；顺带修一格被改瞎的自检锚。

主人原话：「这个是给我看的吗，我又要在哪里回复呢」——两问都成立：
① 零块把机内主题（selfdecl:xxx-slice5-closed-loop／band:M:1004:codex_bbfix1）和取数命令
   直接摊在人眼前，人看不出「要我干什么」；
② 回话的框在最底下第六抽屉，跟「要你点头的」隔了一整屏，等于没有出口。

r2 版被 ABORT 咬住（22 条锚不落）：第二写者 codex:bbfix1 在这期间把展示层量词与术语换了
（扇→个窗口、额度墙→平台限流、欠一手→待回包），r2 抄的是旧字面。r3 的锚全部按 10-04 20:3x
实测文本重抄，并把「数据层一个字不动」写死：board.py:337-339／478-486／522-530 的 flags 词
（静默超 45 分／欠一手／收件框压着）仍是分级与自检第 132 格的依据，土话只在渲染时换（pl()）。

顺带：board_check_r1.py 首页那格钉着字面「工地板」，标题被改成「BB 机」后它已经红了一小时——
那是锚失效不是产品坏，换成它真正守护的东西（有 h1、有 /api/fleet、发话走 POST），成因写进注释。
"""
import ast
import io
import re
import sys

BP = u"D:/moodle/agent_bus/board.py"
CP = u"D:/moodle/agent_bus/board_check_r1.py"
b0 = io.open(BP, encoding="utf-8", errors="replace").read()
c0 = io.open(CP, encoding="utf-8", errors="replace").read()
b = b0
c = c0
miss = []


def rep(label, old, new, cnt=1):
    global b
    n = b.count(old)
    if n != cnt:
        miss.append(u"%s（命中 %d 次，要 %d 次）" % (label, n, cnt))
        return
    b = b.replace(old, new, cnt)


# ══ 一、服务端：给每条通信配一句人话（只翻话，入列判据与阈值一律不动） ══════════
rep(u"triage 前插函数", u"def triage():", u'''def _age_hm(mins):
    u"""分钟 → 人读得动的「几小时几分」。阈值没动，只是换个说法。"""
    mins = int(max(0, mins))
    if mins < 60:
        return u"%d 分钟" % mins
    h, m = divmod(mins, 60)
    return (u"%d 小时" % h) + (u" %d 分" % m if m else u"")


ALARM_PLAIN = {u"K": u"他的活回包早回来了，上头却没往下走 ⇒ 敲他一下或换个模型",
               u"M": u"他的 BB 机收件框压着信没人取 ⇒ 催他去取，或者把这个地址作废",
               u"L": u"他单子上写着要交东西，过档了还没交 ⇒ 问他那一格在哪儿",
               u"J": u"他半路停了：上一句没说完就没声了 ⇒ 让他把那一手补上"}


def _plain(kind, topic, to, names):
    u"""一条机内通信 → 包工头一眼看懂的「要你干什么」。翻不出来就照实说翻不出来。"""
    t = topic or u""
    low = t.lower()
    who = names.get(to) or to or u"?"
    if low.startswith(u"erratum"):
        return u"他更正了自己上一条 ⇒ 扫一眼就行，不用回"
    if u"selfdecl" in low:
        return u"他自己报了下一格要干什么 ⇒ 等你回一句「准」或「换哪格」"
    if kind == u"alarm":
        seg = [x for x in t.split(u":") if x]
        band = seg[1] if len(seg) > 1 else u"?"
        return u"哨兵 %s 档报警，压在「%s」的收件框里没人取 ⇒ %s" % (
            band, who, ALARM_PLAIN.get(band, u"点开下面原文看是哪一格"))
    if kind == u"order":
        return u"有一单没人接 ⇒ 点名给谁"
    if kind == u"ask":
        return u"他在等你回话 ⇒ 给一句裁语"
    if kind == u"ruling":
        return u"有条裁语等你点头 ⇒ 准或驳"
    if kind == u"deliver":
        return u"活交上来了 ⇒ 该验收了"
    if kind == u"ack":
        return u"他把话收到了 ⇒ 不用回"
    if kind == u"note":
        return u"他报了一声 ⇒ 扫一眼，不用回"
    return u"来了一条 %s ⇒ 扫一眼" % (kind or u"note")


def triage():''')

rep(u"names 表", u'    st = load_state(); acks = st.get("acks", {}); now = time.time()',
    u'''    st = load_state(); acks = st.get("acks", {}); now = time.time()
    names = {}
    for aid, a in (st.get("agents") or {}).items():
        nm = unicode_of(a.get(u"name") or u"")
        if nm:
            names[unicode_of(aid)] = nm''')

rep(u"it 加人话字段", u'''        it = {"id": m.get("id"), "from": unicode_of(m.get("from")), "to": unicode_of(m.get("to")),
              "kind": k, "topic": tp, "age_min": int((now - float(m.get("ts", now))) / 60.0),
              "taken": bool(m.get("delivered_at") or a), "answered": bool(ans),
              "verdict": unicode_of(a.get("verdict")), "body": (m.get("body") or u"")[:200]}''',
    u'''        frm = unicode_of(m.get("from")); to = unicode_of(m.get("to"))
        age = int((now - float(m.get("ts", now))) / 60.0)
        it = {"id": m.get("id"), "from": frm, "to": to,
              "kind": k, "topic": tp, "age_min": age,
              "taken": bool(m.get("delivered_at") or a), "answered": bool(ans),
              "verdict": unicode_of(a.get("verdict")), "body": (m.get("body") or u"")[:200],
              "plain": _plain(k, tp, to, names), "who": names.get(frm) or u"",
              "age_h": _age_hm(age), "to_who": names.get(to) or u""}''')

rep(u"waiting 加小时", u'''            waiting.append({"id8": r["id8"], "name": r["name"], "idle_min": r["idle_min"],
                            "live": r["live"], "unread": r["unread"], "why": why,
                            "last": (r["last"] or u"")[:150]})''',
    u'''            waiting.append({"id8": r["id8"], "name": r["name"], "idle_min": r["idle_min"],
                            "idle_h": _age_hm(r["idle_min"]), "live": r["live"],
                            "unread": r["unread"], "why": why,
                            "last": (r["last"] or u"")[:150]})''')

# ══ 二、样式与顶部直达条 ═════════════════════════════════════════════════════
rep(u"CSS", u".titchips{font-size:15px;margin:2px 0 8px}.titchips b{color:var(--warn)}",
    u""".titchips{font-size:15px;margin:2px 0 8px}.titchips b{color:var(--warn)}
.goto{margin:8px auto 0;max-width:1400px;padding:9px 12px;border:1px solid var(--warn);border-radius:8px;font-size:15px;line-height:1.5}
.goto b{color:var(--warn)}
.ph{font-size:15px;margin-bottom:2px;line-height:1.45}
.trow.answered{opacity:.45}
.ansbtn{font-size:12px;padding:2px 9px;margin:3px 0}
.trow details summary{font-size:12px}""")

rep(u"直达条", u"</header>\n<main>",
    u"""</header>
<div class="goto">包工头：这块下面第一格抽屉「<b>零</b>」是专门给你的 ——
 <b id="gotoNeed">?</b> 件等你点头 · <b id="gotoNotice">?</b> 件报你一声 · <b id="gotoWait">?</b> 个汉子的活断了等你续。
 <b>要回话不用往下翻：那块最底下就有个框，点每条上的「就这条回一句」，人已经替你选好。</b></div>
<main>""")

# ══ 三、零块：标题与三列（按 10-04 20:3x 实测文本重抄锚） ═════════════════════
rep(u"零块标题", u'<summary>零、要你看这一屏：要你裁的 · 通知你的 · 谁在等</summary>',
    u'<summary>零、工头你先看这块：要你点头的 · 报你一声的 · 站着等活的</summary>')
rep(u"零块计数", u' <div class="titchips"><b id="tNeed">?</b> 件要你裁 · <b id="tNotice">?</b> 件通知你 · <b id="tWait">?</b> 个窗口在等你下一句</div>',
    u' <div class="titchips">工头：<b id="tNeed">?</b> 件等你点头 · <b id="tNotice">?</b> 件报你一声 · <b id="tWait">?</b> 个汉子的活断了等你续</div>')
rep(u"列1", u'<h3>要你裁的（按最老排，越上面越久没动）</h3>', u'<h3>要你点头的（越在上头的，压得越久）</h3>')
rep(u"列2", u'<h3>通知你的（近六小时，不用回也行）</h3>', u'<h3>报你一声的（近六小时，扫一眼就行，不用回）</h3>')
rep(u"列3", u'<h3>谁在等你下一句（读的是各窗口自己流水的末条）</h3>', u'<h3>站着等活的（读的是他们自己写的最后一句）</h3>')
rep(u"判据行", u'''<div class="dim" style="margin-top:6px">判据：ask／order 且还没 answered 的、车道自申报（主题里带 selfdecl）、以及没被取走的报警，都算「要你裁」；
 剩下的近六小时通信算「通知」；「谁在等」来自第一表——静默超四十五分、待回包、收件框压着件，三样任一即入列。</div>''',
    u'''<div class="dim" style="margin-top:6px">凭什么进这几列（口径一个字没改，写在这儿给你核）：要你点头的＝提问／派单还没人答的、他自己报了下一格要干什么的、报警没人取走的；
 报你一声的＝近六小时其余通信；站着等活的＝第一表里 45 分钟没出字、话没接上、收件框压着件，三样占一样的。</div>''')

# ══ 四、回话框搬到零块底部，第六抽屉改成「刚才递出去的话」 ════════════════════
TALK_START = u'<details class="dr" open><summary>六、你要说话</summary>'
TALK_END = u'<div id="out" class="dim"></div></details>'
i0 = b.find(TALK_START)
i1 = b.find(TALK_END, i0) if i0 >= 0 else -1
if i0 < 0 or i1 < 0:
    miss.append(u"回话框整块（起止标记没找到）")
else:
    talk = b[i0:i1 + len(TALK_END)]
    b = b[:i0] + u'''<details class="dr"><summary>六、你刚才递出去的话（板子只替你记账，不改判据）</summary>
<div class="dim">递话的框已经挪到最上面那块「零」的底下了——看见要点的，直接在那儿写一句就行。</div>
<div id="sentlog" class="dim">—</div></details>''' + b[i1 + len(TALK_END):]
    talk = talk.replace(u'<summary>六、你要说话</summary>',
                        u'<summary style="font-size:15px">要回话就在这儿写一句（说给谁已按你点的那条选好）</summary>')
    talk = talk.replace(u'>发进 BB 机<', u'>给他们递句话<')
    talk = talk.replace(u'placeholder="例：夜里别堆新单，先把未取的读掉；A 组先交清点再开下一单"',
                        u'placeholder="例：准了，按你那格走／这格先放，去把未取的读掉／换哪格我重新点"')
    talk = talk.replace(u'<label style="margin:0">收件人', u'<label style="margin:0">说给谁')
    talk = talk.replace(u'全体（*）', u'全体都听（*）')
    talk = talk.replace(u'带上看板现测作出处（正文里有数字时才需要）',
                        u'带上板子现测作出处（你这句话里有数字时才勾）')
    talk = talk.replace(u'走的是车道同一道闸，不给人开后门。每条外发会自动补这一行尾行（逐字取自 CLOSING_LINE.txt）：',
                        u'你这条走的是跟车道同一道闸，不给人开后门；发出去会自动补这一行尾行（逐字取自 CLOSING_LINE.txt）：')
    anchor = u"</details>\n<details class=\"dr\" open><summary>一、"
    if b.count(anchor) != 1:
        miss.append(u"回话框落点（锚不唯一：%d）" % b.count(anchor))
    else:
        b = b.replace(anchor, talk + u"\n" + anchor, 1)

# ══ 五、其余抽屉与指标条土话（量词跟主人要的气质走：人＝汉子） ════════════════
rep(u"页头副标", u'<span class="dim">现场工作总览</span>', u'<span class="dim">现场谁在干什么</span>')
rep(u"一、", u'<summary>一、谁在干活（判据＝该窗口自己产出的最后一个节点时刻；红＝静默超 45 分；紫＝平台限流；「待回包」＝工具结果早回来了却没往下写）</summary>',
    u'<summary>一、谁在干活（看的是他自己最后一次产出；红＝45 分钟没出字；紫＝额度用完；「话没接上」＝命令早跑回来了他没往下写）</summary>')
rep(u"一、表头", u'<th>它自己最后写的那句（逐字截断）</th>', u'<th>他自己写的最后一句（逐字，截一点）</th>')
rep(u"二、", u'<summary>二、光荣榜（今天真交了活的，按落地块数与真回执数排；两样都能逐枚数出来）</summary>',
    u'<summary>二、光荣榜——今天真出力的汉子（按落地的块数和真回执数排，两样都能一枚枚数出来）</summary>')
rep(u"三、", u'<summary>三、耻辱墙（只挂有凭据的没干活；被平台、被排单、被回包卡住的另列「免挂」，绝不混进来）</summary>',
    u'<summary>三、耻辱墙——手里有活却没动的人（每一条都带凭据；被平台、被排单、被回包卡住的另列「免挂」，不混进来）</summary>')
rep(u"四、", u'<summary>四、不在本机流水里的账号（Codex / 文件腿：只看 jsonl 会整批漏掉）</summary>',
    u'<summary>四、不在本机流水里的那些人（Codex 和走文件递话的：只看流水会整批漏掉）</summary>')
rep(u"四·补", u'<summary>四·补、收班名单（流水 6–12 小时没动的窗口：不进上面任何比例，只给点名与续扫用。「板上没有」不等于「没人卡着」）</summary>',
    u'<summary>四·补、收班的人（流水 6–12 小时没动的：不进上面任何比例，只给点名和续扫用。「板上没有」不等于「没人卡着」）</summary>')
rep(u"五、", u'<summary>五、他们互相说过什么（最近 40 条，含取走/回执态）</summary>',
    u'<summary>五、他们互相说过什么（最近 40 条，谁取走了、谁回了话都在里面）</summary>')
rep(u"页脚说明", u'<span class="dim header-meta">自动刷新 6 秒 · 判活看窗口自己最后一次产出；平台错误回话单列为掉线</span>',
    u'<span class="dim header-meta">每 6 秒自己刷一次 · 判活只看他自己最后一次产出 · 被平台掐掉的那类单列，不算偷懒</span>')
rep(u"状态键1", u'<span class="status-key">此刻：思考 <b id="nThink">?</b></span>', u'<span class="status-key">此刻：脑子在转 <b id="nThink">?</b></span>')
rep(u"状态键2", u'<span class="status-key">终端 <b id="nTool">?</b></span>', u'<span class="status-key">敲命令 <b id="nTool">?</b></span>')
rep(u"状态键3", u'<span class="status-key">等回包 <b id="nModel">?</b></span>', u'<span class="status-key">等上头回话 <b id="nModel">?</b></span>')
rep(u"状态键4", u'<span class="status-key">未出字 <b id="nIdle">?</b></span>', u'<span class="status-key">没出字 <b id="nIdle">?</b></span>')

# 指标条：按 id 定位换 <em>，不钉中文措辞（第二写者改过一轮，钉字面必再落空）
EM_NEW = {u"nW": u"在干活", u"nI": u"25分没出字", u"n45": u"45分没出字", u"nOwe": u"话没接上",
          u"nDrop": u"被掐了要重发", u"nQ": u"额度用完", u"nA": u"在册窗口", u"nM": u"BB机消息"}
em_done, em_miss = 0, []
for eid, lab in EM_NEW.items():
    pat = re.compile(u'(<strong id="' + eid + u'">\\?</strong><em>)[^<]*(</em>)')
    b, n = pat.subn(lambda m: m.group(1) + lab + m.group(2), b)
    if n != 1:
        em_miss.append(u"%s（%d 次）" % (eid, n))
    else:
        em_done += 1
if em_miss:
    miss.append(u"指标条：" + u"、".join(em_miss))

# ══ 六、渲染层词表：数据层 flags 的词一个不改，只在显示时换话 ═════════════════
rep(u"badge 土话", u'''function badge(s,min){
 if(s==='writing')return '<span class="badge w" title="25 分内自己产出过；此刻在干什么看下一列">动过</span>';
  if(s==='dropped')return '<span class="badge q">掉线，需重发</span>';
  if(s==='quota')return '<span class="badge q">平台限流</span>';
 if(s==='quiet45')return '<span class="badge x">静 '+min+' 分</span>';
 return '<span class="badge i">静 '+min+' 分</span>'}''',
    u'''function badge(s,min){
 if(s==='writing')return '<span class="badge w" title="25 分钟内他自己产出过；此刻在干什么看下一列">手上在动</span>';
  if(s==='dropped')return '<span class="badge q">被链路掐了·要重发</span>';
  if(s==='quota')return '<span class="badge q">额度用完了</span>';
 if(s==='quiet45')return '<span class="badge x">'+min+' 分没出字</span>';
 return '<span class="badge i">'+min+' 分没出字</span>'}
// 数据层的凭据词（board.py:337-339／522-530 生成，分级与自检都锚它）不动，这里只在显示时换话。
const PLW=[['静默超 45 分','45 分钟没出字'],['欠一手：工具结果 ','话没接上：命令 '],[' 分前就回来了，它没往下写',' 分前就回来了，他没往下写'],
 ['收件框压着 ','收件框里压着 '],['条不取，已静 ','条没取，人已经 '],['静默超','超过静默线 '],['欠一手','话没接上'],
 ['收件框压着','收件框里压着'],['它自己写的','他自己写的'],['（是外壳被碰过，不是它在写）','（是外壳被人碰过，不是他在写）']];
function pl(x){return PLW.reduce((a,p)=>a.split(p[0]).join(p[1]),String(x==null?'':x))}''')

rep(u"四态词表", u''' const LB={thinking:['w','在思考'],running_tool:['w','跑终端（已坐实）'],'running_tool?':['i','跑终端（未坐实）'],
    awaiting_model:['i','等模型回包'],idle:['g','此刻没在出字'],dropped:['q','掉线'],quota_wall:['q','平台限流']};''',
    u''' const LB={thinking:['w','脑子在转'],running_tool:['w','在敲命令（看得见）'],'running_tool?':['i','像在敲命令（没坐实）'],
    awaiting_model:['i','等上头回话'],idle:['g','没在出字'],dropped:['q','被链路掐了'],quota_wall:['q','额度用完']};''')

rep(u"自证徽章", u"  const bb=r.verified?'<span class=\"badge w\">自证</span>':(r.in_hub?'<span class=\"badge i\">在册待自证</span>':'<span class=\"badge g\">未接</span>');",
    u"  const bb=r.verified?'<span class=\"badge w\">已自证</span>':(r.in_hub?'<span class=\"badge i\">在册·待自证</span>':'<span class=\"badge g\">没接 BB 机</span>');")

rep(u"欠一手徽章", u"   const owe=r.owed?' <span class=\"badge x\">待回包</span>':(r.stalled?' <span class=\"badge g\">断在半路</span>':'');",
    u"   const owe=r.owed?' <span class=\"badge x\">话没接上</span>':(r.stalled?' <span class=\"badge g\">半路停了</span>':'');")

rep(u"比例条", u"  $('#ratio').textContent='比例（分母＝本机在册 '+N+' 个窗口）：在干活 ",
    u"  $('#ratio').textContent='比例（队里一共 '+N+' 个汉子）：在干活 ")

rep(u"光荣榜句", u"光荣榜 · '+ho.day+'：'+ho.counts.on_board+' 个窗口今天有落地块，合计 '+ho.counts.blocks+' 枚｜其中 '+ho.counts.pending_together+' 个窗口同时有一格待补（榜上照登，不藏）</div>';",
    u"光荣榜 · '+ho.day+'：'+ho.counts.on_board+' 个汉子今天交了活，一共 '+ho.counts.blocks+' 块｜其中 '+ho.counts.pending_together+' 个手里还压着一格没补（榜上照样登，不藏）</div>';")
rep(u"光荣榜行", u"'<div class=\"dim\">落账 '+r.blocks+' 块 · BB 机真回执 '+r.replies+' 件</div>",
    u"'<div class=\"dim\">落了 '+r.blocks+' 块账 · BB 机真回执 '+r.replies+' 件</div>")
rep(u"光荣榜空", u"（今天还没有归档的落地块；第一块交进来这里就有名字）",
    u"（今天还没有归档的落地块；第一块交进来这儿就有名字）")
rep(u"耻辱墙句", u"耻辱墙：'+sh.rows.length+' 个窗口有凭据地没干活｜同队此刻在写 '+f.counts.writing+'/'+f.rows.length+' 个窗口｜最长一项 '+mx+' 分钟没产出",
    u"耻辱墙：'+sh.rows.length+' 个汉子的活没动（条条有凭据）｜同一时刻队里在写 '+f.counts.writing+'/'+f.rows.length+' 个｜最久一个 '+mx+' 分钟没出活")
rep(u"耻辱墙 flags", u"     '<div>'+r.flags.map(x=>'<span class=\"sflag\">· '+esc(x)+'</span>').join(' ')+'</div>'+",
    u"     '<div>'+r.flags.map(x=>'<span class=\"sflag\">· '+esc(pl(x))+'</span>').join(' ')+'</div>'+")
rep(u"耻辱墙证据", u"     '<div class=\"last\">证据·它自己写的原话：'+esc(r.proof)+'</div>'+",
    u"     '<div class=\"last\">凭据·他自己写的原话：'+esc(r.proof)+'</div>'+")
rep(u"耻辱墙动作", u"     (r.action?'<div class=\"dim\">要它补的那一格：'+esc(r.action)+'</div>':'')+'</div>'+",
    u"     (r.action?'<div class=\"dim\">要他补的那一格：'+esc(r.action)+'</div>':'')+'</div>'+")
rep(u"耻辱墙空", u"本轮墙上没有窗口：没有任何窗口同时满足「静默有时长凭据」与「不是被卡住」。",
    u"这一轮墙上没人：没有一个人既「多久没出字有凭据」、又「不是被卡住的」。")
rep(u"待重发行", u"待重发（末条是平台错误回话／平台限流，被链路掐掉的，不算偷懒）：",
    u"要重发的（最后一句是平台报错／额度用完，被链路掐掉的，不算偷懒）：")
rep(u"通讯状态行", u"通讯状态（未接 BB 机或没有主动发话，不作为待处理证据）：",
    u"BB 机接没接（没接、或没主动发过话的，只当通讯状态，不算没干活的凭据）：")
rep(u"免挂行", u"免挂（不是偷懒，是被平台/别人/排单卡住）：", u"免挂（不是偷懒，是被平台、被别人、被排单卡住）：")
rep(u"收班行", u"（12 小时内没有收班窗口——不是没人，是真的都还在动）",
    u"（12 小时内没有人收班——不是没人，是真的都还在动）")
rep(u"下拉标签", u"   const st=r.state==='writing'?'25 分内动过':(r.state==='quota'?'平台限流':('静 '+Math.round(r.idle_min)+' 分'));",
    u"   const st=r.state==='writing'?'25 分内动过':(r.state==='quota'?'额度用完':(Math.round(r.idle_min)+' 分没出字'));")

# ══ 七、零块渲染：人话主句 +「就这条回一句」+ 原文折叠（判据不变，只换呈现） ══
JS_START = u" let t;try{t=await (await fetch('/api/triage')).json()}catch(e){t=null}\n if(t){const T=(s)=>String(s===null||s===undefined?'':s);"
JS_END = u"'<div class=\"dim last\">它自己写的末条：'+esc(w.last)+'</div></div>').join(''):'<span class=\"dim\">（没有窗口在等）</span>';}"
j0 = b.find(JS_START)
j1 = b.find(JS_END, j0) if j0 >= 0 else -1
if j0 < 0 or j1 < 0:
    miss.append(u"零块渲染段（起止标记没找到：start=%d end=%d）" % (j0, j1))
else:
    NEW_JS = u''' let t;try{t=await (await fetch('/api/triage')).json()}catch(e){t=null}
 if(t){const T=(s)=>String(s===null||s===undefined?'':s);
 const DONE=(()=>{try{return JSON.parse(localStorage.getItem('cn.board.answered')||'[]')}catch(e){return []}})();
 window._pa='';
 const row=(x)=>{const done=x.id&&DONE.indexOf(x.id)>=0;
  const who=x.who?'<b>'+esc(x.who)+'</b> <span class="dim mono">'+esc(T(x.from).replace('qoder:',''))+'</span>'
                 :'<b class="mono">'+esc(T(x.from).replace('qoder:',''))+'</b>';
  const to=x.to_who?'　说给「'+esc(x.to_who)+'」':'';
  return '<div class="trow'+(done?' answered':'')+'">'+
   '<div class="ph">'+(x.plain?esc(x.plain):'<span class="dim">这条板子没学会说人话，原文在下面折叠里</span>')+'</div>'+
   '<div class="dim">'+who+to+' · 已经 '+esc(x.age_h||(x.age_min+' 分'))+'没人管'+
     (x.answered?' · <span class="k">他答过了：'+esc(x.verdict)+'</span>':'')+(done?' · <span class="k">你回过一句（本机标记）</span>':'')+'</div>'+
   '<button class="ansbtn" data-to="'+esc(x.from)+'" data-id="'+esc(T(x.id))+'">就这条回一句</button> '+
   '<details><summary>看他的原话与取数命令</summary><div class="last">'+esc(T(x.body))+'</div>'+
     '<div class="dim mono">'+esc(T(x.topic))+'</div></details></div>'};
 $('#tNeed').textContent=t.counts.need;$('#tNotice').textContent=t.counts.notice+(t.counts.notice_total>t.counts.notice?('（共 '+t.counts.notice_total+'，只列最近）'):'');$('#tWait').textContent=t.counts.waiting;
 $('#gotoNeed').textContent=t.counts.need;$('#gotoNotice').textContent=t.counts.notice_total;$('#gotoWait').textContent=t.counts.waiting;
 $('#tNeedList').innerHTML=t.need.length?t.need.map(row).join(''):'<span class="dim">（没有要你点头的）</span>';
 $('#tNoticeList').innerHTML=t.notice.length?t.notice.map(row).join(''):'<span class="dim">（近六小时没有）</span>';
 $('#tWaitList').innerHTML=t.waiting.length?t.waiting.map(w=>{
   const nm=w.name&&w.name!=='qoder:'+w.id8?'<b>'+esc(w.name)+'</b> <span class="dim mono">'+esc(w.id8)+'</span>':'<b class="mono">'+esc(w.id8)+'</b>';
   return '<div class="trow"><div class="ph">手上一格没走完，等你点下一格</div>'+
    '<div class="dim">'+nm+' · 已经 '+esc(w.idle_h||(Math.round(w.idle_min)+' 分'))+'没出字 · 收件框 '+(w.unread||0)+' 条</div>'+
    '<div>'+w.why.map(x=>'<span class="sflag">· '+esc(pl(x))+'</span>').join(' ')+'</div>'+
    '<button class="ansbtn" data-to="qoder:'+esc(w.id8)+'" data-id="">催他一句</button> '+
    '<details><summary>看他自己写的最后一句</summary><div class="last">'+esc(w.last)+'</div></details></div>'}).join('')
   :'<span class="dim">（没有人站着等活）</span>';
 document.querySelectorAll('.ansbtn').forEach(btn=>{btn.onclick=()=>{const to=btn.getAttribute('data-to');const sel=$('#to');
   if(to&&to!=='undefined'){let hit=false;for(const o of sel.options){if(o.value===to){hit=true;break}}
     if(!hit){const o=document.createElement('option');o.value=to;o.textContent=to;sel.appendChild(o)}sel.value=to}
   window._pa=btn.getAttribute('data-id')||'';
   $('#out').textContent='说给谁已选好：'+to+'。写完按「给他们递句话」；真发出去了，这条才在你电脑上标成「回过一句」（只标显示，不改账本）。'
   $('#body').focus();$('#body').scrollIntoView({behavior:'smooth',block:'center'})}})}'''
    b = b[:j0] + NEW_JS + b[j1 + len(JS_END):]

rep(u"发送标记", u" else{$('#out').innerHTML='<span class=\"good\">已投进 BB 机：'+esc(r.id||'')+(r.deduped?'（同键已有，未重投）':'')+'</span>';$('#body').value='';$('#hint').textContent='';refresh()}}",
    u""" else{const note=(r.deduped?'（同键已有，未重投）':'');
  if(window._pa){try{const D=JSON.parse(localStorage.getItem('cn.board.answered')||'[]');
   if(D.indexOf(window._pa)<0){D.push(window._pa);localStorage.setItem('cn.board.answered',JSON.stringify(D))}}catch(e){}
   window._pa=''}
  $('#out').innerHTML='<span class=\"good\">已递进 BB 机：'+esc(r.id||'')+'</span>'+esc(note)+'　<span class=\"dim\">他取走或回话之后，会出现在第五块</span>';
  $('#body').value='';$('#hint').textContent='';refresh()}}""")

# ══ 八、自检那格：把钉死「工地板」的锚换成它真正守护的东西 ═══════════════════
G_START = c.find(u"    if st == 200 and u\"工地板\" in raw")
if G_START < 0:
    miss.append(u"自检首页格锚点（找不到）")
else:
    G_END = c.find(u"\n", c.find(u"u\"method:'POST'\" in raw))", G_START)) + 1
    if G_END <= 0:
        miss.append(u"自检首页格结尾（找不到）")
    else:
        NEW_G = u'''    # 锚点更正（10-04 20:3x 实测）：这一格原先钉字面「工地板」，第二写者把 <h1> 改成「BB 机」
        # 之后它红了约一小时——那是锚失效，不是首页坏了（同期 /api/fleet 等 13 格全绿）。
        # 它真正要守的是三件事：首页有标题、取数口在页里、发话走 POST（20:0x 主人在浏览器真按
        # 发送键撞出过 GET 掉进兜底分支、被回整张页那一形）。所以锚换成这三样，不再钉措辞。
    has_h1 = u"<h1>" in raw
    has_api = u"/api/fleet" in raw
    if st == 200 and has_h1 and has_api and u"method:'POST'" in raw:
        green.append(u"首页有标题、取数口在页里、发话用 POST（不钉死标题措辞）")
    else:
        red.append(u"首页不对（%s｜有 h1=%s｜页里有 /api/fleet=%s｜发话用 POST=%s）"
                   % (st, has_h1, has_api, u"method:'POST'" in raw))
'''
        c = c[:G_START] + NEW_G + c[G_END:]

if miss:
    for m in miss:
        print(u"未命中 →", m)
    sys.exit(u"ABORT：有 %d 条没落上，两个文件都未改动" % len(miss))

ast.parse(b)
ast.parse(c)
io.open(BP, "w", encoding="utf-8", newline=chr(10)).write(b)
io.open(CP, "w", encoding="utf-8", newline=chr(10)).write(c)
print(u"已落：board.py %d → %d 字节｜board_check_r1.py %d → %d 字节"
      % (len(b0.encode("utf-8")), len(b.encode("utf-8")),
         len(c0.encode("utf-8")), len(c.encode("utf-8"))))
