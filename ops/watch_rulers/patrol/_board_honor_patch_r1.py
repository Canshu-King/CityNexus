# -*- coding: utf-8 -*-
"""把「光荣榜」装进工地板（服务端函数 + 路由 + 页面抽屉 + 前端渲染）。

为什么单独一个补丁脚本而不是手改：board.py 现在是两个人一起写的，手改容易撞；
这里每一步都 assert 命中一次，改完立刻 ast.parse，任何一步对不上就整块不落盘。

光荣榜的判据只有两件，都能在磁盘与账上逐枚数出来：
  · 落地块数 = `_qoder_ledger_inbox/_processed` 里今天带 .inserted_ 戳的归档件（文件名前缀就是车道 id8）；
  · 真回执数 = BB 机账上该扇发出的 deliver／ack／自申报件。
"""
import ast
import io

P = u"D:/moodle/agent_bus/board.py"
NL = chr(10)
s = io.open(P, encoding="utf-8", errors="replace").read()

HONOR_FN = u'''
LANDED = u"D:/moodle/_qoder_ledger_inbox/_processed"


def honor():
    """光荣榜：谁今天真交了活。判「卖力」不靠感觉，只用两件可逐枚数出来的东西——
    `_processed` 里今天带 .inserted_ 戳的归档件（前缀就是车道 id8），和 BB 机账上该扇发出的
    deliver／ack／自申报件。与耻辱墙的关系也写明：同一枚扇可以今天交了几块、同时有一格待补，
    榜上照登并标出来，不藏。"""
    day = time.strftime("%Y-%m-%d")
    lands = {}
    err = u""
    try:
        for f in os.listdir(LANDED):
            if ".inserted_" not in f:
                continue
            fp = os.path.join(LANDED, f)
            try:
                if time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(fp))) != day:
                    continue
            except Exception:
                continue
            lands.setdefault(f.split("_")[0], []).append(f)
    except Exception as e:
        err = u"%s: %s" % (type(e).__name__, str(e)[:80])
    agents = load_state().get("agents", {})
    rec = {}
    for m in load_ledger(900):
        frm = unicode_of(m.get("from"))
        if not frm.startswith(u"qoder:"):
            continue
        k = unicode_of(m.get("kind"))
        if k in (u"deliver", u"ack") or u"selfdecl" in unicode_of(m.get("topic")).lower():
            rec.setdefault(frm[6:14], []).append(k)
    onwall = set(r["id8"] for r in shame()["rows"])
    rows = []
    for id8, fs in lands.items():
        ag = agents.get(u"qoder:" + id8, {})
        rows.append({"id8": id8, "name": ag.get("name") or id8, "blocks": len(fs),
                     "replies": len(rec.get(id8, [])), "latest": sorted(fs)[-1],
                     "verified": bool(ag.get("verified")), "also_pending": id8 in onwall})
    rows.sort(key=lambda r: (-r["blocks"], -r["replies"], r["id8"]))
    return {"at": time.strftime("%H:%M:%S"), "day": day, "rows": rows, "read_err": err,
            "counts": {"on_board": len(rows),
                       "blocks": sum(r["blocks"] for r in rows),
                       "pending_together": len([r for r in rows if r["also_pending"]])}}


'''

anchor = u"def unicode_of(x):"
assert s.count(anchor) == 1, u"anchor unicode_of"
s = s.replace(anchor, HONOR_FN.lstrip(NL) + anchor, 1)

old = u'        if self.path.startswith("/api/triage"):'
assert s.count(old) == 1, u"anchor route"
s = s.replace(old, u'        if self.path.startswith("/api/honor"):' + NL +
              u'            return self._s(200, json.dumps(honor(), ensure_ascii=False))' + NL + old, 1)

old2 = u'<details class="dr" open><summary>二、耻辱墙'
assert s.count(old2) == 1, u"anchor wall"
new2 = (u'<details class="dr" open><summary>二、光荣榜（今天真交了活的，按落地块数与真回执数排；两样都能逐枚数出来）</summary>' + NL +
        u'<div id="honor"></div></details>' + NL +
        u'<details class="dr" open><summary>三、耻辱墙')
s = s.replace(old2, new2, 1)
for a, b in ((u'<summary>三、不在本机流水里的账号', u'<summary>四、不在本机流水里的账号'),
             (u'<summary>三·补、收班名单', u'<summary>四·补、收班名单'),
             (u'<summary>四、他们互相说过什么', u'<summary>五、他们互相说过什么'),
             (u'<summary>五、你要说话', u'<summary>六、你要说话')):
    assert s.count(a) == 1, a
    s = s.replace(a, b, 1)

CSS = u'''.honor{border:2px solid var(--warn);border-radius:10px;padding:9px;background:#1c1710}
.honor .top{font-size:15px;font-weight:700;margin-bottom:6px;color:#ffe6b8}
.hrow{display:grid;grid-template-columns:44px 1fr 150px;gap:8px;align-items:center;border-bottom:1px dashed #4a3d22;padding:6px 0}
.hrow:last-child{border-bottom:0}
.hrank{font-size:20px;font-weight:800;color:var(--warn);text-align:center}
.hbar{height:9px;background:#3a3018;border-radius:6px;overflow:hidden;margin-top:4px}
.hbar i{display:block;height:100%;background:var(--warn)}
.hnum{font-size:17px;font-weight:800;text-align:right;color:#ffe6b8}
'''
mark = u'#hint{margin-top:6px}'
assert s.count(mark) == 1, u"anchor css"
s = s.replace(mark, CSS + mark, 1)

JS = [u" let ho;try{ho=await (await fetch('/api/honor')).json()}catch(e){ho=null}",
      u" if(ho){const hx=Math.max.apply(null,ho.rows.map(r=>r.blocks).concat([1]));",
      u"  const ht='<div class=\"honor\"><div class=\"top\">光荣榜 · '+ho.day+'：'+ho.counts.on_board+' 扇今天有落地块，合计 '+ho.counts.blocks+' 枚｜其中 '+ho.counts.pending_together+' 扇同时有一格待补（榜上照登，不藏）</div>';",
      u"  $('#honor').innerHTML=ho.rows.length?(ht+ho.rows.map((r,i)=>{const w=Math.round(100*r.blocks/hx);",
      u"    return '<div class=\"hrow\"><div class=\"hrank\">'+(i+1)+'</div><div>'+('<b>'+esc(r.name)+'</b> <span class=\"dim mono\">'+esc(r.id8)+'</span>')+",
      u"      (r.verified?' <span class=\"badge w\">自证</span>':'')+(r.also_pending?' <span class=\"badge i\">也有一格待补</span>':'')+",
      u"      '<div class=\"dim\">落账 '+r.blocks+' 块 · BB 机真回执 '+r.replies+' 件</div><div class=\"hbar\"><i style=\"width:'+w+'%\"></i></div>'+",
      u"      '<div class=\"dim\">最近一块：'+esc(r.latest)+'</div></div><div class=\"hnum\">'+r.blocks+'</div></div>'}).join('')+'</div>')",
      u"   :'<div class=\"dim\">（今天还没有归档的落地块；第一块交进来这里就有名字）</div>')}",
      u" "]
hook = u" $('#shame').innerHTML="
assert s.count(hook) == 1, u"anchor js"
s = s.replace(hook, NL.join(JS) + hook, 1)

io.open(P, "w", encoding="utf-8", newline=NL).write(s)
ast.parse(s)
print("HONOR_PATCHED AST_OK")
