# -*- coding: utf-8 -*-
"""真投一次 hub_alarm，验的是「这条腿能不能把红话送到」，不是「函数存在」。

为什么单开这一格：自测里 hub_alarm 是打桩的（不能让测试去敲号令者的门），
所以那段 subprocess + 数闸 + 尾行核对从没在真账上跑过。哨兵 04:52 撞过的形状正是
「代码看着对、真消息永远投不出去」，光有打桩自测就等于没验。

只改一处常量：收件人临时指给自己（qoder:42d1a6fa），band 用 T、id8 用 selftest ⇒
topic 与生产那枚 `applier:R:<日>:verify` 不同名，**不占中枢的按天幂等键**，
今天真出事时那条 R 档照样投得出去。正文、证据、rc 判读、日志行全是生产原码。
投完按 id 回读尾行核对收尾口令，再 ack 掉——留在收件口会 aged 进 M 档，白吵一轮。
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, u"_inbox_applier_r2.py")
BUS = u"D:/moodle/agent_bus"
ME = u"qoder:42d1a6fa"
ID8 = (sys.argv[1] if len(sys.argv) > 1 else u"selftest4")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

spec = importlib.util.spec_from_file_location("apl_probe", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

LOG = os.path.join(HERE, u"_applier_alarm_leg_probe.log")
m.LOG = LOG                       # 桩日志，不混进腿日志
m.CMDR = ME                       # 唯一改动：这条测试报警指给自己
ok = m.hub_alarm(u"T", ID8,
                 u"代插腿插完再数命中，有块头转红：要么标题取不到、要么命中数不可得、"
                 u"要么不为一次。这一拍的入账不可证，别按「已入库」办；逐枚名单与原因都在"
                 u"本腿日志的转红行里，随附证据那份原样字节是本拍出处。")
print("hub_alarm 返回 %r（True=中枢收了）" % ok)
print("腿日志尾行：%s" % io.open(LOG, encoding="utf-8").read().strip().splitlines()[-1])

# 按 id 回读：数只从这一次读数里来，不复用上面那句
# 02:09–02:30 现场抓到两处仪表形制错（都是我这侧，不是中枢）：
# ① read 的返回键是 items，我按 messages 取 ⇒ 真消息在场上却数成 0；
# ② 就算改对，`read --kind alarm --all` 这一口也没把刚投的这两枚吐出来（它按游标给旧份额），
#    而账本里逐字在。**单枚回读必须走 GET /msg?id=**，列队那口不能当"投出去了"的证明。
# 所以这里先从总线账本按 topic 取回这枚的 id，再用 GET /msg?id= 读正文核对尾行。
topic_want = u"applier:T:%s:%s" % (time.strftime("%m%d"), ID8)
mid = None
for line in io.open(os.path.join(BUS, "bus.jsonl"), encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except Exception:
        continue
    if r.get("topic") == topic_want:
        mid = r.get("id")
print("账本里这枚 topic=%s 的 id=%s" % (topic_want, mid))
res = {"gate_ok": bool(ok), "readback": 0 if not mid else 1}
if mid:
    import urllib.request
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    got = json.loads(op.open(u"http://127.0.0.1:4799/msg?id=%s" % mid, timeout=30).read()
                    .decode("utf-8", "replace"))
    body = (got.get("body") or u"")
    cl = io.open(os.path.join(os.path.dirname(HERE), u"CLOSING_LINE.txt"),
                 encoding="utf-8").read().strip()
    res["tail_verbatim"] = body.rstrip().endswith(cl)
    print("GET /msg?id= 回读正文 %d 字节｜尾行逐字对得上原件：%s（原件 %d 字节）"
          % (len(body.encode("utf-8")), res["tail_verbatim"], len(cl.encode("utf-8"))))
    a = subprocess.run([sys.executable, os.path.join(BUS, "bus.py"), "ack",
                        "--id", mid, "--by", ME], cwd=BUS, capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    res["acked"] = a.returncode == 0
    print("ack rc=%d ⇒ 不留在我收件口 aged 进 M 档" % a.returncode)
else:
    res["tail_verbatim"] = False
    res["acked"] = False
print(json.dumps(res, ensure_ascii=False))
sys.exit(0 if (res["gate_ok"] and res["readback"] and res["tail_verbatim"] and res["acked"]) else 1)
