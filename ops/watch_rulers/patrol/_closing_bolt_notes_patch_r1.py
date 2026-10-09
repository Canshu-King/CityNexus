# -*- coding: utf-8 -*-
"""把「外发必须带逐字收尾口令」这条规矩也装进两条车道原话腿（门原话 / 硬闸原话）。

现读的反证（不是推的）：正式账本里 16:49:05 那枚 `gate-words:1005:e766b154_1605.md` 正文末尾
没有那句原件——报警腿（hub_alarm）今天已经钉过闸了，两条 note 腿还是散在外面的。
规矩装在写的那个工具里：原件取不到就退 "no_closing" 不投，绝不允许"发出一条缺尾行的外发"。
用法：python _closing_bolt_notes_patch_r1.py [--check]
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "_sentinel_relay_r1.py")
NL = chr(10)

A1 = (u'    cmd = [PYEXE, os.path.join(HUB, "bus.py"), "send", "--from", u"qoder:42d1a6fa",' + NL
      + u'           "--to", rid, u"--kind", u"note", u"--topic",')
B1 = (u'    cl = closing_line()' + NL
      + u'    if not cl:' + NL
      + u'        say(u"收尾口令原件不可得 ⇒ 门原话这条不投（%s）：外发必须带逐字尾行" % block_name)' + NL
      + u'        return u"no_closing"' + NL
      + u"    body = body.rstrip() + NL_CHAR + cl + NL_CHAR" + NL
      + A1)

A2 = (u'    cmd = [PYEXE, os.path.join(HUB, "bus.py"), "send", "--from", SENTINEL_ID,' + NL
      + u'           "--to", rid, "--kind", "note", "--topic",')
B2 = (u'    cl = closing_line()' + NL
      + u'    if not cl:' + NL
      + u'        say(u"收尾口令原件不可得 ⇒ 硬闸原话这条不投（%s）：外发必须带逐字尾行" % block_name)' + NL
      + u'        return u"no_closing"' + NL
      + u"    msg = msg.rstrip() + NL_CHAR + cl + NL_CHAR" + NL
      + A2)


def main():
    src = io.open(T, encoding="utf-8").read()
    for i, (a, _b) in enumerate([(A1, B1), (A2, B2)], 1):
        n = src.count(a)
        if n != 1:
            print(u"锚 %d 命中 %d 次（必须 1）⇒ 不写盘" % (i, n))
            return 1
    for a, b in [(A1, B1), (A2, B2)]:
        src = src.replace(a, b, 1)
    try:
        ast.parse(src)
    except SyntaxError as e:
        print(u"改完语法不过：%s（行 %s）⇒ 不写盘" % (e.msg, e.lineno))
        return 2
    if "--check" in sys.argv:
        print(u"两处锚各命中一次、改后语法过（未写盘）")
        return 0
    io.open(T, "w", encoding="utf-8", newline=NL).write(src)
    print(u"已打补丁：两条 note 腿也认收尾口令原件，取不到就不投")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
