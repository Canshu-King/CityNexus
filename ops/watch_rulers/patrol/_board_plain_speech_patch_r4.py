# -*- coding: utf-8 -*-
"""r3 落地后我自己当用户复读，抓到的三处不一致（都是文案精度，判据不动）。

截图 23:25 实测读到的：
① 状态行已说「等上头回话／没出字／被掐了」，同一屏的比例条却还写「等模型／此刻没在出字／掉线额度」
   ⇒ 同一屏两套腔，人不知道是不是同一件事。
② 「报你一声的」列每行尾巴写「已经 23 小时 52 分没人管」——通知本来就不用人管，这句把人往错方向指。
③ 「站着等活的」里 木工·小孙 显示「已经 0 分钟没出字」却排在等活列，主句仍是「手上一格没走完」；
   他真实的情况是收件框压着 1 条没去取（入列判据是 unread，不是静默）。
"""
import ast
import io
import sys

P = u"D:/moodle/agent_bus/board.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(label, old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"%s（命中 %d 次）" % (label, s.count(old)))
        return
    s = s.replace(old, new, 1)


# ① 比例条与状态行同腔
rep(u"等模型", u"'+P(run)+'% · 等模型 '+", u"'+P(run)+'% · 等上头回话 '+")
rep(u"没在出字", u"+'% · 此刻没在出字 '+f.counts.live_idle", u"+'% · 没出字 '+f.counts.live_idle")
rep(u"掉线额度", u"· 掉线/额度 '+bad", u"· 被掐了或额度用完 '+bad")

# ② 通知列不再说「没人管」
rep(u"row 带 mode", u" const row=(x)=>{const done=x.id&&DONE.indexOf(x.id)>=0;",
    u" const row=(x,mode)=>{const done=x.id&&DONE.indexOf(x.id)>=0;")
rep(u"年龄措辞", u"""   '<div class="dim">'+who+to+' · 已经 '+esc(x.age_h||(x.age_min+' 分'))+'没人管'+""",
    u"""   '<div class="dim">'+who+to+(mode==='notice'?' · 到这儿 '+esc(x.age_h||(x.age_min+' 分'))+'了'
     :' · 已经 '+esc(x.age_h||(x.age_min+' 分'))+'没人管')+""")
rep(u"need 调用", u"t.need.length?t.need.map(row).join('')", u"t.need.length?t.need.map(x=>row(x,'need')).join('')")
rep(u"notice 调用", u"t.notice.length?t.notice.map(row).join('')", u"t.notice.length?t.notice.map(x=>row(x,'notice')).join('')")

# ③ 等活列的主句跟着真实入列原因走（数据层词不动，只读它判一下）
rep(u"等活主句", u"""   return '<div class="trow"><div class="ph">手上一格没走完，等你点下一格</div>'+""",
    u"""   const ph=w.unread&&!w.why.some(x=>String(x).indexOf('静默超')>=0)
     ?'BB 机的信压在收件框里没去取（'+w.unread+' 条）':'手上一格没走完，等你点下一格';
   return '<div class="trow"><div class="ph">'+ph+'</div>'+""")

if miss:
    for m in miss:
        print(u"未命中 →", m)
    sys.exit(u"ABORT：%d 条没落上，board.py 未改动" % len(miss))
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"三处已修｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
