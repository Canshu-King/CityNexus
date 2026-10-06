# -*- coding: utf-8 -*-
u"""把 _patrol_loop_r1.py 主循环里"存档 + 记一行"那几行，换成"存档 + 判红 + 写待看"。

只重写 173–182 行那一段，其余原样。用行号定位是为了避开锚匹配的老毛病。
改前自动备份 .bak_needseyes2_1911；改后 ast.parse 自检并打印新段。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_patrol_loop_r1.py")

NEW = u'''            body = (r.stdout or b"") + (r.stderr or b"")
            io.open(out, "wb").write(body)
            txt = (r.stdout or b"").decode("utf-8", "replace")
            line = ""
            for l in txt.splitlines():
                if l.startswith(u"\\u2460") or l.startswith(u"\\u7ed3\\u8bba"):
                    line = l
            red, why, concl, _cells = judge(txt)
            if r.returncode != 0:
                red, why = True, [u"\\u5de1\\u903b rc=%d" % r.returncode] + why
            logline(stamp, u"%s rc=%d%s \\u6863=%s \\uff5c %s"
                    % (time.strftime("%H:%M:%S"), r.returncode,
                       u"\\u3010\\u7ea2\\u3011" if red else u"", os.path.basename(out), concl or line))
            if note_eyes(red, why, concl, os.path.basename(out)):
                logline(stamp, u"%s \\u5f85\\u770b\\u6863\\u5df2\\u5199\\uff1a%s"
                        % (time.strftime("%H:%M:%S"),
                           u"\\u7ea2" if red else u"\\u7531\\u7ea2\\u8f6c\\u7eff"))
        except Exception as e:
            logline(stamp, u"%s \\u8dd1\\u5931\\u8d25\\uff1a%s: %s" % (time.strftime("%H:%M:%S"),
                                                    e.__class__.__name__, str(e)[:80]))
            note_eyes(True, [u"\\u8dd1\\u6279\\u5f02\\u5e38\\uff1a%s" % e.__class__.__name__], u"",
                      os.path.basename(out))
'''


def main():
    lines = io.open(SRC, encoding="utf-8", newline="").read().split("\n")
    # 定位：subprocess.run 之后的 io.open(out...) 那行，到 time.sleep 之前
    a = None
    b = None
    for i, l in enumerate(lines):
        if l.strip().startswith("io.open(out, \"wb\").write("):
            a = i
        if a is not None and l.strip() == "time.sleep(minutes * 60.0)":
            b = i
            break
    if a is None or b is None:
        print(u"REFUSE：定位失败 a=%s b=%s" % (a, b))
        return 1
    old = lines[a:b]
    print(u"替换前 %d 行（%d–%d）：" % (len(old), a + 1, b))
    for l in old:
        print(u"  - " + l.rstrip())
    if u"judge(txt)" in "\n".join(old):
        print(u"已改过 ⇒ 不重复改")
        return 0
    bak = SRC + u".bak_needseyes2_1911"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write("\n".join(lines))
    new = lines[:a] + NEW.rstrip("\n").split("\n") + lines[b:]
    text = "\n".join(new)
    try:
        ast.parse(text)
    except SyntaxError as e:
        print(u"REFUSE：新文 SyntaxError，未写盘：%s" % e)
        return 1
    io.open(SRC, "w", encoding="utf-8", newline="").write(text)
    print(u"已写：%s（备份 %s）" % (os.path.basename(SRC), os.path.basename(bak)))
    for l in new[a:a + len(NEW.rstrip("\n").split("\n"))]:
        print(u"  + " + l.rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())