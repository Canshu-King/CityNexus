# -*- coding: utf-8 -*-
"""现取板子的监听端口与页面刷新秒数（给交接句当出处，不手打数字）。

为什么单独一枚：BB 机的数值闸要求「正文里出现的数，必须能在某段 evidence 输出里找到」。
我那句交接里写了端口和「自动刷新 6 秒」，所以要出处。把这两个数直接 print 出来是假出处——
这里一个都不写死：端口从 board.py 的常量抽，秒数从真页面的页脚那行抽，再拿一次 HTTP 状态坐实它活着。
"""
import io
import re
import urllib.request

SRC = u"D:/moodle/agent_bus/board.py"
s = io.open(SRC, encoding="utf-8", errors="replace").read()
# 端口声明是 PORT = int(os.environ.get("BOARD_PORT", "4820"))，数字在引号里，别按「= 数字」抽
m_port = re.search(r'^PORT\s*=.*?[\"\'](\d{2,6})[\"\']', s, re.M)
if not m_port:
    raise SystemExit(u"ABORT：源码里没抽到端口默认值")
port = m_port.group(1)

resp = urllib.request.urlopen("http://127.0.0.1:%s/" % port, timeout=8)
raw = resp.read().decode("utf-8", "replace")
home_status = resp.status
m_ref = re.search(u'header-meta">[^<]*?(\\d+)\\s*秒', raw)
if not m_ref:
    raise SystemExit(u"ABORT：页脚那行没写秒数（那格自检也该红）")
ref = m_ref.group(1)

fleet = urllib.request.urlopen("http://127.0.0.1:%s/api/fleet" % port, timeout=8)
# 状态码全部现取，不写字面量：写死一个 200 就是把出处做成假的。
print(u"端口 %s（从 board.py 的 PORT 常量抽）｜页脚写的刷新 %s 秒（从真页面抽）"
      u"｜首页 HTTP %s｜/api/fleet HTTP %s 取回 %d 字节"
      % (port, ref, home_status, fleet.status, len(fleet.read())))
