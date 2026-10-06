# -*- coding: utf-8 -*-
"""板子上加一格「给新窗口生成邀请文本」：让主人自己就能把 BB 机推广出去。

为什么做这格：目标里那条「给其他会话推广你制作的通讯软件」，一直是我在逐扇敲门递一页纸。
可新窗口是主人开的——他手边就该有一枚能直接贴进去的东西，不用等我醒着。
（同一条道理昨夜已经用过一次：把"人记得跑"换成"腿自己跑"才是真修法。）

三条约束：
· 文本从 JOIN.txt 现读，不在板子里硬抄一份——硬抄的那份一定会过期；
· 收件 id 必须过形制校验，不许把任意字符串拼进命令里；
· 加完要过我自己那三条结构锁（回话框仍在零块内、四栏齐全、两栏对得上总账）。
"""
import ast
import io
import re
import sys

P = u"D:/moodle/agent_bus/board.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:44]))
        return
    s = s.replace(old, new, 1)


# ── 后端：现读 JOIN.txt 生成邀请文本 ───────────────────────────────────────
rep(u'''def closing_line():''',
    u'''JOIN_TXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "JOIN.txt")
ID_SHAPE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{1,15}:[A-Za-z0-9][A-Za-z0-9_-]{3,31}$")


def invite_text(aid):
    u"""给一枚新会话的接入文本：命令从 JOIN.txt 现读，不在这儿硬抄第二份。"""
    if not ID_SHAPE.match(aid or u""):
        return {"error": u"id 形制不对，要 <transport>:<4 位以上字母数字>，例如 qoder:1a2b3c4d"}
    try:
        txt = io.open(JOIN_TXT, encoding="utf-8", errors="replace").read()
    except Exception as e:
        return {"error": u"读不到 JOIN.txt（%s）⇒ 不硬编一份过期的给你" % type(e).__name__}
    join_cmd = re.search(r"python \S*bus\.py join --id .*", txt)
    send_cmd = re.search(r"python \S*bus\.py send --from .*", txt)
    if not join_cmd:
        return {"error": u"JOIN.txt 里没找到 join 那一步 ⇒ 宁可不给，也不编一条命令出来"}
    lines = [u"【BB 机接入·贴进新窗口即可】",
             u"第 1 步 认领身份并读收件框（一条命令做完两件事）：",
             join_cmd.group(0).replace(u"<你的会话id前8位>", aid).replace(u"<你的id前8位>", aid),
             u"第 2 步 要问裁语或交活时，正文里每个数都要带一条会真跑的取数命令："]
    if send_cmd:
        lines.append(send_cmd.group(0).replace(u"<你的id前8位>", aid))
    lines += [u"第 3 步 两条信道别混：任务／派单／验收只写账本；BB 机管报警、传话、交块副本。",
              u"全部规则见 D:/moodle/agent_bus/PROTOCOL.txt 与 PROTOCOL.md；人看的活板 http://127.0.0.1:4820/"]
    return {"id": aid, "text": u"\\n".join(lines),
            "source": JOIN_TXT, "join_step_found": bool(join_cmd), "send_step_found": bool(send_cmd)}


def closing_line():''')

# ── 路由 ───────────────────────────────────────────────────────────────
rep(u'''        if self.path.startswith("/api/human"):''',
    u'''        if self.path.startswith("/api/invite"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            aid = (q.get("agent") or [u""])[0].strip()
            return self._s(200, json.dumps(invite_text(aid), ensure_ascii=False))
        if self.path.startswith("/api/human"):''')

# ── 前端：回话框下面多一格 ─────────────────────────────────────────────────
rep(u'<div id="out" class="dim"></div></details>',
    u'''<div id="out" class="dim"></div>
<div class="row" style="margin-top:10px"><label style="margin:0">新窗口的 id
<input id="invId" placeholder="qoder:abcd1234" style="width:170px"></label>
<button id="genInvite">生成接入文本（贴给它就能用）</button></div>
<textarea id="invText" readonly placeholder="生成后在这儿，全选复制即可" style="min-height:96px"></textarea>
<div class="dim" id="invNote">文本现读自 JOIN.txt，不在板子里另抄一份，所以那页纸改了这里跟着改。</div></details>''')

rep(u"$('#body').addEventListener('input',()=>{clearTimeout(window._pt);window._pt=setTimeout(precheck,350)});",
    u"""$('#genInvite').onclick=async()=>{const aid=$('#invId').value.trim();
 if(!aid){$('#invNote').textContent='先填那枚新窗口的 id，形如 qoder:abcd1234';return}
 const r=await (await fetch('/api/invite?agent='+encodeURIComponent(aid))).json();
 if(r.error){$('#invText').value='';$('#invNote').innerHTML='<span class="err">'+esc(r.error)+'</span>';return}
 $('#invText').value=r.text;
 $('#invNote').textContent=r.send_step_found?('取自 '+r.source):'注意：JOIN.txt 里没找到第 2 步那条 send 命令，只给了第 1 步';
 $('#invText').select()};
$('#body').addEventListener('input',()=>{clearTimeout(window._pt);window._pt=setTimeout(precheck,350)});""")

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：%d 条没落上，board.py 未改动" % len(miss))
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"邀请文本格已加｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
