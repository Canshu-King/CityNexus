# -*- coding: utf-8 -*-
u"""第⑪格 cell11_backlog() 的合成反证：喂假尺跑**真函数**，验坏的一侧写成"不可得"。

为什么这么测（10-03 那条）：每加一格要故意造一次该报的输入。
第⑪格有两种坏：尺 rc≠0、尺 rc=0 但输出里没有「甲类」；还有一种是 runner 直接抛。
现网恰好只走"好的那一侧"，所以光跑现网不算覆盖——坏的一侧一旦被读成"没积压"，
下一班就会以为验收口干净，那才是真事故。

注入位是函数自己的 runner/emit 参数 ⇒ 这里不复制判据、不碰生产文件、不起服务。
跑法：PYTHONIOENCODING=utf-8 python _patrol_cell11_selftest_r1.py
"""
import io
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bb_patrol_once_r1 as P   # noqa: E402  只 import：模块级只有常量赋值，无网络与发帖

GOOD_OUT = (u"收件人 qoder:deadbeef｜已送未拆 7 条（现读 04:24）\n"
            u"甲类 5 条（交付物已在账本：按块头命中 2 条、按 _processed 代插回执命中 3 条）\n"
            u"乙类 2 条（块头与回执都对不上）\n").encode("utf-8")

fails = []


def fake(stdout=b"", rc=0, boom=None):
    def _r(argv, **kw):
        if boom:
            raise boom
        return types.SimpleNamespace(returncode=rc, stdout=stdout, stderr=b"")
    return _r


def cap(runner):
    buf = []
    P.cell11_backlog(u"/tmp/fake-here", runner=runner, emit=buf.append)
    return u"\n".join(buf)


o = cap(fake(GOOD_OUT))
if u"甲类 5" not in o or u"乙类 2" not in o or u"deadbeef" not in o:
    fails.append(u"正例三行没原样带出：%s" % o[:120])

o = cap(fake(b"", rc=1))
if u"不可得" not in o or u"rc=1" not in o:
    fails.append(u"尺 rc=1 没落到不可得那一侧：%s" % o[:120])

# 这一枚的输出里**不能**出现「甲类」三字——我第一版写的反例句子自己就带着这个词，
# 于是尺被判成"答了"，报了条假红（错在测试，不在代码）。
o = cap(fake(u"收件人 qoder:deadbeef｜只有一行无关的话".encode("utf-8") + b"\n", rc=0))
if u"不可得" not in o:
    fails.append(u"尺 rc=0 但输出缺「甲类」时没落到不可得：%s" % o[:120])

o = cap(fake(boom=OSError("CIM 忙")))
if u"取不到" not in o or u"OSError" not in o:
    fails.append(u"runner 抛异常时没写成取不到：%s" % o[:120])

# 负对照：确认这一格真的会把"没数"和"没积压"分开——上面三例坏的一侧都该含"不许当'没积压'"或"不当零"
for bad in (cap(fake(b"", rc=1)), cap(fake(boom=OSError("x")))):
    if u"没积压" not in bad and u"不当零" not in bad:
        fails.append(u"坏的一侧措辞没写明不许当成没积压：%s" % bad[:120])

if fails:
    for x in fails:
        print(u"FAIL：" + x)
    print(u"⇒ 红 %d 条" % len(fails))
    raise SystemExit(1)
print(u"⇒ 绿：四形各验到（正例三行原样带出｜rc=1→不可得｜rc=0 缺关键词→不可得｜runner 抛→取不到），"
      u"坏的一侧措辞都写明「不许当没积压」；跑的是巡逻里那个真函数，判据没有第二份")
