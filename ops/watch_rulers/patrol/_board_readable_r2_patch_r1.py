# -*- coding: utf-8 -*-
"""板子第二版可读性：短句、同类合并、细节折叠（主人 10-05 00:2x 指着屏幕说的）。

原话：「感觉这个的可读性很差，并且能不能让他们说话都像农民工，要不然我看不懂他们在说什么。」

截图上看得见的三个毛病，逐个治：
① 句子太长还带箭头术语（「有车道自己报了下一格要干什么 ⇒ 等包工头回一句『准』或『换哪格』」），
   一列里两行几乎一样 ⇒ 改成短句：「他说：下一件我这么干，等包工头点头」；
② 「报你一声的」24 条里一大半是同一句「他把话收到了 ⇒ 不用回」⇒ 按人＋事类合并成一行
   （"质检员·老周 回执 3 件 · 最久 23 小时"），逐条折进「看这几件是什么」；
③ 站着等活的那列每人占三四行 ⇒ 一人一行，末句折起来。

判据与入列口径照旧一个字不动：合并只是把同一人同一类的事摆在一行，条数、年龄、分母都还是现取的数。
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


# ── 一、服务端：把人话句改短，去掉箭头术语 ──────────────────────────────────
rep(u'''    boss = (to == HID) or (to == u"*")
    who2 = u"你" if boss else (u"包工头" if to == CMDR_LANE else u"值守")
    if u"selfdecl" in low:
        if boss:
            return u"有车道自己报了下一格要干什么 ⇒ 按规矩这格归包工头（号令者）点，你不用动；要驳那句才轮到你"
        return u"有车道自己报了下一格要干什么 ⇒ 等%s回一句「准」或「换哪格」，不用你动手" % who2''',
    u'''    boss = (to == HID) or (to == u"*")
    who2 = u"你" if boss else (u"包工头" if to == CMDR_LANE else u"值守")
    if u"selfdecl" in low:
        if boss:
            return u"有人报了下一件怎么干，这归包工头点，你不用管"
        return u"他说：下一件我这么干，等%s点头" % who2''')

rep(u'''        if boss:
            return u"哨兵 %s 档报警没人取（压在「%s」收件框里）⇒ 这格归包工头处置：催他去取或把这地址作废，你不用动" % (band, who)
        return u"哨兵 %s 档报警，压在「%s」的收件框里没人取 ⇒ %s" % (
            band, who, ALARM_PLAIN.get(band, u"点开下面原文看是哪一格"))''',
    u'''        if boss:
            return u"哨兵喊了一声没人应（压在「%s」那儿）——归包工头处置，你不用管" % who
        return u"哨兵喊：「%s」那儿的信压着没人取 ⇒ %s" % (who, ALARM_PLAIN.get(band, u"点开看是哪一格"))''')

rep(u'''    if kind == u"order":
        return u"有一单没人接 ⇒ 等%s点名给谁" % who2
    if kind == u"ask":
        return (u"他在等你回话 ⇒ 给一句裁语" if boss
                else u"他在等%s回话 ⇒ 该给一句裁语，不用你动手" % who2)
    if kind == u"ruling":
        return u"有条裁语等%s点头 ⇒ 准或驳" % who2
    if kind == u"deliver":
        return u"活交上来了 ⇒ 等%s验收" % who2
    if kind == u"ack":
        return u"他把话收到了 ⇒ 不用回"
    if kind == u"note":
        return u"他报了一声 ⇒ 扫一眼，不用回"
    return u"来了一条 %s ⇒ 扫一眼" % (kind or u"note")''',
    u'''    if kind == u"order":
        return u"有单没人接，等%s派" % who2
    if kind == u"ask":
        return u"他在等你回话" if boss else u"他问了句话，等%s答" % who2
    if kind == u"ruling":
        return u"有条裁语等%s点头" % who2
    if kind == u"deliver":
        return u"他交了活，等%s验收" % who2
    if kind == u"ack":
        return u"他回话：收到了"
    if kind == u"note":
        return u"他报了个信"
    return u"来了条 %s" % (kind or u"note")''')

rep(u'        return u"他更正了自己上一条 ⇒ 扫一眼就行，不用回"',
    u'        return u"他改口了：上一条说错了"')

# ── 二、样式：字大一点、行少一点、能一眼扫完 ────────────────────────────────
rep(u".ph{font-size:15px;margin-bottom:2px;line-height:1.45}",
    u".ph{font-size:17px;margin-bottom:3px;line-height:1.5;font-weight:600}")
rep(u".tcol{border:1px solid var(--line);border-radius:8px;padding:8px;background:#0f1319;max-height:330px;overflow:auto;scrollbar-gutter:stable}",
    u".tcol{border:1px solid var(--line);border-radius:8px;padding:8px;background:#0f1319;max-height:420px;overflow:auto;scrollbar-gutter:stable}")
rep(u".titchips{font-size:15px;margin:2px 0 8px}.titchips b{color:var(--warn)}",
    u".titchips{font-size:17px;margin:2px 0 10px}.titchips b{color:var(--warn)}\n"
    u".tcol h3{font-size:15px!important;color:var(--fg)!important}\n"
    u".grp{margin:0 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}\n"
    u".grp:last-child{border-bottom:0}")

# ── 三、渲染：同一人同一类合并成一行，逐条折进 details ──────────────────────
rep(u""" $('#tNeedList').innerHTML=(t.need_human||[]).length?t.need_human.map(x=>row(x,'need')).join(''):'<span class="dim">（这列空着：该你定的事没有）</span>';
 $('#tCmdrList').innerHTML=(t.need_cmdr||[]).length?t.need_cmdr.map(x=>row(x,'need')).join(''):'<span class="dim">（包工头那侧也没欠着的）</span>';""",
    u""" $('#tNeedList').innerHTML=grp(t.need_human||[],'need')||'<span class="dim">（这列空着：该你定的事没有）</span>';
 $('#tCmdrList').innerHTML=grp(t.need_cmdr||[],'need')||'<span class="dim">（包工头那侧也没欠着的）</span>';""")
rep(u" $('#tNoticeList').innerHTML=t.notice.length?t.notice.map(x=>row(x,'notice')).join(''):'<span class=\"dim\">（近六小时没有）</span>';",
    u" $('#tNoticeList').innerHTML=grp(t.notice||[],'notice')||'<span class=\"dim\">（近六小时没有）</span>';")

rep(u""" const row=(x,mode)=>{const done=x.id&&DONE.indexOf(x.id)>=0;""",
    u""" const item=(x)=>{const who=x.who?esc(x.who)+' ':'<span class="mono">'+esc(T(x.from).replace('qoder:',''))+'</span>';
  return '<div class="trow"><div class="dim">'+who+'· '+esc(x.plain||'')+' · '+esc(x.age_h||(x.age_min+' 分'))+'前</div>'+
   '<details><summary>看原话</summary><div class="last">'+esc(T(x.body))+'</div>'+
   '<div class="dim mono">'+esc(T(x.topic))+'</div></details></div>'};
 const grp=(list,mode)=>{const g={};list.forEach(x=>{const k=x.from+'|'+(x.plain||x.kind);(g[k]=g[k]||[]).push(x)});
  const keys=Object.keys(g);if(!keys.length)return '';
  return keys.map(k=>{const it=g[k].slice().sort((a,b)=>b.age_min-a.age_min);const x0=it[0];
   const old=it[0];const nm=x0.who?'<b>'+esc(x0.who)+'</b>':'<span class="mono">'+esc(T(x0.from).replace('qoder:',''))+'</span>';
   return '<div class="grp"><div class="ph">'+esc(x0.plain||'')+'</div>'+
    '<div class="dim">'+nm+(it.length>1?('　一共 '+it.length+' 件'):'')+
     '　最久 '+esc(old.age_h||(old.age_min+' 分'))+
     (x0.to_who?'　说给「'+esc(x0.to_who)+'」':'')+'</div>'+
    (mode==='notice'?'':'<button class="ansbtn" data-to="'+esc(x0.from)+'" data-id="'+esc(T(x0.id))+'">就这条回一句</button> ')+
    '<details><summary>'+(it.length>1?('看这 '+it.length+' 件分别是什么'):'看他的原话')+'</summary>'+
     it.map(item).join('')+'</details></div>'}).join('')};
 const row=(x)=>{const done=x.id&&DONE.indexOf(x.id)>=0;""")

# 站着等活的：一人一行，末句折起来
rep(u"""   return '<div class="trow"><div class="ph">'+ph+'</div>'+
    '<div class="dim">'+nm+' · 已经 '+esc(w.idle_h||(Math.round(w.idle_min)+' 分'))+'没出字 · 收件框 '+(w.unread||0)+' 条</div>'+
    '<div>'+w.why.map(x=>'<span class="sflag">· '+esc(pl(x))+'</span>').join(' ')+'</div>'+
    '<button class="ansbtn" data-to="qoder:'+esc(w.id8)+'" data-id="">催他一句</button> '+
    '<details><summary>看他自己写的最后一句</summary><div class="last">'+esc(w.last)+'</div></details></div>'}).join('')""",
    u"""   return '<div class="trow"><div class="ph">'+ph+'</div>'+
    '<div class="dim">'+nm+'　'+esc(w.idle_h||(Math.round(w.idle_min)+' 分'))+'没出字'+
     (w.unread?('　信压 '+(w.unread)+' 条'):'')+'　'+esc(w.why.map(x=>pl(x)).join('；'))+'</div>'+
    '<button class="ansbtn" data-to="qoder:'+esc(w.id8)+'" data-id="">催他一句</button> '+
    '<details><summary>看他自己写的最后一句</summary><div class="last">'+esc(w.last)+'</div></details></div>'}).join('')""")

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：%d 条没落上，board.py 未改动" % len(miss))
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"可读性第二版已落｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
