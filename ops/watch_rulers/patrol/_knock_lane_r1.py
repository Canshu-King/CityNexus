# -*- coding: utf-8 -*-
"""给一条车道编一记敲门件：正文来自文件，尾行逐字取自 CLOSING_LINE.txt（不手打、不复制粘贴）。

为什么要有它：夜里给车道传话是我这条线的主要动作，而尾行是硬规则；
手打过一次就打错过一次（10-01 有过要发勘误的）。这里把「读文件—校验字节—落盘—给标记串」装进一处。
"""
import hashlib
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
EXPECT_LEN = 83
EXPECT_SHA1 = "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    if len(sys.argv) < 3:
        print(u"用法：python _knock_lane_r1.py <车道 id8> <正文文件>")
        return 2
    lane, body_p = sys.argv[1], sys.argv[2]
    if not re.match(r"^[0-9a-f]{8}$", lane):
        print(u"REFUSE：车道 id 不是 8 位十六进制（%s）——点名点错扇窗比不点更糟" % lane)
        return 7
    body = io.open(body_p, encoding="utf-8").read().rstrip()
    if not body.strip():
        print(u"REFUSE：正文是空的")
        return 7
    raw = io.open(CLOSING, "rb").read()
    if len(raw) != EXPECT_LEN or hashlib.sha1(raw).hexdigest() != EXPECT_SHA1:
        print(u"REFUSE：收尾口令字节不吻合（len=%d sha1=%s），不发" % (
            len(raw), hashlib.sha1(raw).hexdigest()))
        return 7
    tail = raw.decode("utf-8").strip()
    stamp = time.strftime("%m-%d %H:%M:%S")
    marker = u"【值守敲门 · %s · %s】" % (lane, stamp)
    if marker not in body:
        body = marker + u"\n\n" + body
    full = body + u"\n\n" + tail + u"\n"
    if not full.rstrip().endswith(tail) or full.count(tail) != 1:
        print(u"REFUSE：尾行没接上或接了两遍")
        return 7
    out = os.path.join(HERE, "_knock_%s_%s.txt" % (lane, time.strftime("%H%M")))
    io.open(out, "w", encoding="utf-8", newline="\n").write(full)
    b = full.encode("utf-8")
    print(u"[落盘 %s｜%d B｜sha1 %s]" % (os.path.basename(out), len(b), hashlib.sha1(b).hexdigest()))
    print(u"[回读用标记：%s]" % marker)
    print(u"")
    print(full)
    return 0


if __name__ == "__main__":
    sys.exit(main())
