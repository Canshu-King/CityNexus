# -*- coding: utf-8 -*-
"""修 invite_text 的前缀重复：生成的命令一度是 `--id qoder:qoder:deadbe1`。

成因：JOIN.txt 里那行写的是 `--id qoder:<你的会话id前8位>`，占位符自带 transport 前缀；
我把整枚 id（含 qoder:）填进占位符 ⇒ 前缀出现两次。

为什么后端直测没抓到：我只断言了"文本长度"和"join 命令命中"，没读生成的那一行字。
浏览器里真点一次才看见——同一条老教训：报质量前先自己当用户走一遍。

修法：先替换**带前缀**的占位形（`qoder:<…>`），再替换裸占位形，两种写法都覆盖；
并把"占位符没被填掉"做成硬失败：只要输出里还剩 `<` 开头的占位，就具名报出来，宁可不给。
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
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:44]))
        return
    s = s.replace(old, new, 1)


rep(u'''    join_cmd = re.search(r"python \\S*bus\\.py join --id .*", txt)
    send_cmd = re.search(r"python \\S*bus\\.py send --from .*", txt)''',
    u'''    join_cmd = re.search(r"python \\S*bus\\.py join --id .*", txt)
    send_cmd = re.search(r"python \\S*bus\\.py send --from .*", txt)

    def fill(cmd):
        u"""占位符两种写法都要吃：JOIN.txt 里是 `qoder:<你的会话id前8位>`（自带前缀）。"""
        for ph in (u"qoder:<你的会话id前8位>", u"qoder:<你的id前8位>", u"qoder:<你自己的 id>",
                   u"<你的会话id前8位>", u"<你的id前8位>", u"<你自己的 id>"):
            if ph in cmd:
                cmd = cmd.replace(ph, aid)
        return cmd''')

rep(u'''    lines = [u"【BB 机接入·贴进新窗口即可】",
             u"第 1 步 认领身份并读收件框（一条命令做完两件事）：",
             join_cmd.group(0).replace(u"<你的会话id前8位>", aid).replace(u"<你的id前8位>", aid),
             u"第 2 步 要问裁语或交活时，正文里每个数都要带一条会真跑的取数命令："]
    if send_cmd:
        lines.append(send_cmd.group(0).replace(u"<你的id前8位>", aid))''',
    u'''    j1 = fill(join_cmd.group(0))
    lines = [u"【BB 机接入·贴进新窗口即可】",
             u"第 1 步 认领身份并读收件框（一条命令做完两件事）：",
             j1,
             u"第 2 步 要问裁语或交活时，正文里每个数都要带一条会真跑的取数命令："]
    if send_cmd:
        lines.append(fill(send_cmd.group(0)))''')

rep(u'''    return {"id": aid, "text": u"\\n".join(lines),
            "source": JOIN_TXT, "join_step_found": bool(join_cmd), "send_step_found": bool(send_cmd)}''',
    u'''    text = u"\\n".join(lines)
    # 硬失败：还有没填掉的占位就别给出去，给了就是让新窗口照抄尖括号
    left = re.findall(r"<[^>\\n]{1,24}>", text)
    left = [x for x in left if x not in (u"<transport>", u"<4 位以上字母数字>")]
    if left:
        return {"error": u"JOIN.txt 里这些占位符我不认识，先不去猜：%s"
                         u"——把 invite_text 的占位表补上再发" % u"、".join(left[:4]),
                "source": JOIN_TXT}
    dup = [ln for ln in text.splitlines() if re.search(r"(qoder|codex|file):\\1?:", ln)]
    if dup:
        return {"error": u"生成的命令里 transport 前缀重复了（%s）" % dup[0][:60], "source": JOIN_TXT}
    return {"id": aid, "text": text,
            "source": JOIN_TXT, "join_step_found": bool(join_cmd), "send_step_found": bool(send_cmd)}''')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：%d 条没落上，board.py 未改动" % len(miss))
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"前缀重复已修＋加了硬失败｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
