# -*- coding: utf-8 -*-
"""把「外发必须带逐字收尾口令」这条规矩，装进真正执行写的那两个工具里。

为什么现在动这一手（10-05 02:3x 现场抓的，不是猜的）：
· 我给代插腿补的 hub_alarm 投出一枚 alarm，`GET /msg?id=` 回读正文 282 字节，
  末尾对不上 CLOSING_LINE.txt 那 83 字节原件 ⇒ **这条腿发的警报天生缺尾行**；
· 顺着查哨兵那份 hub_alarm（4 个调用点），文件里连 CLOSING 这个词都没有，
  最近一枚真警报 `band:N:1005:disk` 的正文尾 130 字里也没有那句话——
  也就是说今天所有档位报警都少了主人定的那句口令。规矩我贴在散文里，没贴在门上。
· 我自己那条 tell_cmdr 早就有这道闸（原件读不到 ⇒ 这条通报不发），说明形制是对的，
  只是没推广到报警这条腿。

改法：把规矩做成一处 `closing_line()` + 一处「拼进正文尾行、拼不上就拒发」，
两个 hub_alarm 都装。拒发必须在日志具名留一行——抑制不是"没发生"。
不动判定、不动正文其余部分、不放宽长度门槛（83 字节那句是原件，短得可疑就当没有）。

用法：python _closing_line_bolt_patch_r1.py            # 只预检
      python _closing_line_bolt_patch_r1.py --apply    # 落盘 + 两份 py_compile
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SENT = os.path.join(HERE, u"_sentinel_relay_r1.py")
APLY = os.path.join(HERE, u"_inbox_applier_r2.py")
NL = chr(10)

S_EDITS = [
    (u"哨兵：CLOSING 常量",
     u'''HUB = os.environ.get("SR_HUB", "D:/moodle/agent_bus")   # 用正斜杠：反斜杠+a 会被 heredoc 写成 BEL（同一个坑第二次）''',
     u'''HUB = os.environ.get("SR_HUB", "D:/moodle/agent_bus")   # 用正斜杠：反斜杠+a 会被 heredoc 写成 BEL（同一个坑第二次）
CLOSING = os.environ.get("SR_CLOSING", os.path.join(os.path.dirname(HERE), u"CLOSING_LINE.txt"))'''),
    (u"哨兵：closing_line() 本体 + hub_alarm 装闸",
     u'''def hub_alarm(band, id8, text):''',
     u'''def closing_line():
    """外发尾行的原件：逐字读，不手打。读不到或短得可疑 ⇒ 返回空串，调用方据此拒发。

    这条规矩以前只贴在通报腿（tell_cmdr 那侧）和我的散文里，报警这条腿整个漏了：
    10-05 02:3x 回读自己投的 alarm，正文 282 字节里没有那 83 字节原件 ⇒ 今天所有
    band: 档警报都缺尾行。规矩要装在执行写的那个工具里，不然是我说了算、不是尺说了算。
    """
    try:
        s = io.open(CLOSING, encoding="utf-8").read().strip()
    except Exception as e:
        say(u"收尾口令原件读不到（%s: %s）⇒ 当没有" % (type(e).__name__, str(e)[:80]))
        return u""
    if len(s.encode("utf-8")) < 60:
        say(u"收尾口令原件只有 %d 字节，不像那一整句 ⇒ 当没有" % len(s.encode("utf-8")))
        return u""
    return s


def hub_alarm(band, id8, text):'''),
    (u"哨兵：hub_alarm 里拼尾行（拼不上就拒发）",
     u'''    if not HUB_ON:
        return ("skip", topic)
    try:
        # 04:52 探针暴露：alarm 正文里的数''',
     u'''    if not HUB_ON:
        return ("skip", topic)
    cl = closing_line()
    if not cl:
        say(u"收尾口令原件不可得 ⇒ %s 这枚 alarm 不投（外发必须带逐字尾行）；"
            u"红记在本日志，不当中枢没发生" % topic)
        return ("no_closing", topic)
    text = text.rstrip() + NL_CHAR + cl + NL_CHAR
    try:
        # 04:52 探针暴露：alarm 正文里的数'''),
    (u"哨兵：NL_CHAR 常量（别假设文件里有 NL）",
     u'''HUB_URL = u"http://127.0.0.1:4799"''',
     u'''HUB_URL = u"http://127.0.0.1:4799"
NL_CHAR = chr(10)'''),
]

A_EDITS = [
    (u"代插腿：hub_alarm 里拼尾行",
     u'''    topic = u"applier:%s:%s:%s" % (band, time.strftime("%m%d"), id8)
    try:''',
     u'''    topic = u"applier:%s:%s:%s" % (band, time.strftime("%m%d"), id8)
    try:
        cl = io.open(CLOSING, encoding="utf-8").read().strip()
    except Exception as e:
        cl = u""
        say(u"收尾口令原件读不到（%s: %s）" % (type(e).__name__, str(e)[:80]))
    if len(cl.encode("utf-8")) < 60:
        say(u"收尾口令原件不足 60 字节 ⇒ %s 这枚 alarm 不投（外发必须带逐字尾行）" % topic)
        return False
    text = text.rstrip() + NL + cl + NL
    try:'''),
]


def patch(path, edits, label):
    raw = io.open(path, encoding="utf-8").read()
    bad = []
    for lname, old, new in edits:
        c = raw.count(old)
        print("%-34s %-30s 锚命中 %d 次" % (label, lname, c))
        if c != 1:
            bad.append(lname)
    if bad:
        print("ABORT %s：%s 锚不是唯一命中 ⇒ 该文件未写盘" % (label, u"、".join(bad)))
        return False
    for lname, old, new in edits:
        raw = raw.replace(old, new, 1)
    io.open(path, "w", encoding="utf-8", newline=NL).write(raw)
    p = subprocess.run([sys.executable, "-m", "py_compile", path], capture_output=True)
    out = ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace")
    print("WROTE %s｜%d 字节｜py_compile rc=%d %s" % (label, os.path.getsize(path),
          p.returncode, out[-160:].replace(NL, " ")))
    return p.returncode == 0


def main():
    apply_writes = "--apply" in sys.argv[1:]
    dry = []
    for path, edits, label in ((SENT, S_EDITS, u"哨兵"), (APLY, A_EDITS, u"代插腿")):
        raw = io.open(path, encoding="utf-8").read()
        if u"closing_line()" in raw or u"收尾口令原件不足" in raw:
            print("%s 已装过闸，跳过" % label)
            continue
        if not apply_writes:
            ok = all(raw.count(old) == 1 for _, old, _ in edits)
            for lname, old, _ in edits:
                print("%-34s %-30s 锚命中 %d 次" % (label, lname, raw.count(old)))
            dry.append(ok)
            continue
        if not patch(path, edits, label):
            return 4
    if not apply_writes:
        print("DRY：%s（未写盘，要落盘加 --apply）" % ("预检通过" if all(dry) else "有锚不唯一"))
        return 0 if all(dry) else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
