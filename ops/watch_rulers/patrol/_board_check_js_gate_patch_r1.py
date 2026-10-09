# -*- coding: utf-8 -*-
"""给 board_check_r1.py 补一格：页面里那段 JS 必须能解析。

为什么这一格非加不可（10-04 11:0x 实测到的）：我给板子加光荣榜时，Python 侧 ast.parse 全过、
`board_check_r1.py` 十三格全绿，而**整页数据一处都不渲染**——因为我把 JS 的一处三元括号写坏，
整个 <script> 解析不了。旧自检读的是首页里有没有「工地板」和 `method:'POST'` 这些字面，
看不见语法坏了的脚本，于是它在我把板改坏的那一刻仍然报绿。这就是一把单向致盲的尺。
"""
import ast
import io

P = u"D:/moodle/agent_bus/board_check_r1.py"
NL = chr(10)
s = io.open(P, encoding="utf-8", errors="replace").read()

NEW = '''    # 页面里那段 <script> 必须能解析：整页数据都靠它填，它坏了就等于板子瞎了。
    # 优先交给 node --check（这台机器有 node）；没有 node 时退回括号/引号配平，至少抓得住今天这类错误。
    m = re.search(r"<script>(.*?)</script>", page, re.S)
    if not m:
        red.append(u"首页里没有 <script> 段 ⇒ 无法验证前端逻辑")
    else:
        js = m.group(1)
        tmp = os.path.join(HERE, "_board_extract_check.js")
        io.open(tmp, "w", encoding="utf-8", newline=chr(10)).write(js)
        try:
            q = subprocess.run([NODE, "--check", tmp], capture_output=True, timeout=120)
            if q.returncode == 0:
                green.append(u"首页脚本 node --check 通过（%d 字符，整页数据都靠它渲染）" % len(js))
            else:
                red.append(u"首页脚本解析不过 ⇒ 整页会是空表： %s"
                           % ((q.stderr or b"").decode("utf-8", "replace").strip()[:200])
            os.remove(tmp)
        except Exception as e:
            for ch, opp in ((u"(", u")"), (u"{", u"}"), (u"[", u"]")):
                if js.count(ch) != js.count(opp):
                    red.append(u"没有 node（%s），且括号不配平：%s×%d 对 %s×%d"
                               % (type(e).__name__, ch, js.count(ch), opp, js.count(opp)))
                    break
            else:
                green.append(u"node 不可用（%s），退回括号配平检查：通过" % type(e).__name__)

'''

anchor = u"    st, ct, raw = fetch(\"/api/log\")"
assert s.count(anchor) == 1, "找不到插入锚"
s = s.replace(anchor, NEW.lstrip(NL) + anchor, 1)
if u"NODE = " not in s:
    s = s.replace(u"import re" + NL, u"import re" + NL + u"NODE = os.environ.get(\"NODE_EXE\", \"node\")" + NL, 1)
io.open(P, "w", encoding="utf-8", newline=NL).write(s)
ast.parse(s)
print("CHECK_JS_GATE_ADDED AST_OK")
