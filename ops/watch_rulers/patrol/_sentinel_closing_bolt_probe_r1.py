# -*- coding: utf-8 -*-
"""哨兵那枚「收尾口令装进报警腿」的闸，在**隔离实例**上真投一次。

为什么不直接在正式总线试：报警腿的收件人是号令者，拿真警报去测一条自测＝给他发假警；
而只在桩上测（像 hub_alarm 的单元测试那样）又证明不了"中枢收不收"——哨兵 04:52 撞过的
正是"代码看着对、真消息永远投不出去"。所以照用本夜里已经验过的隔离法（板的负对照、
Clash 的独立实例同一形）：把 bus_hub.py + bus.py 复制进临时目录，BUS_PORT 指到空闲端口，
账本落在临时目录，正式总线 0 字节不动。

三格都必须在真账上读数：
甲 closing_line() 从原件读出那句 83 字节的口令（逐字，不是手打）
乙 投一枚 band:T:<日>:boltprobe ⇒ 隔离账本里真有这枚，且 GET /msg?id= 回读的正文
   末尾**逐字**等于原件；投完的正文比我传进去的长，长出来的必须正好是那句
丙 负对照：把 CLOSING 指到不存在的文件再投一枚 ⇒ 必须拒发（no_closing），
   且隔离账本里**不许多出这一枚**——"拒了但还是发了"是最坏的一种假安全

临时目录是本脚本自己造的派生物，跑完删掉；正式账本与 state.json 全程只读都没碰。
"""
import importlib.util
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BUS = u"D:/moodle/agent_bus"
SENT = os.path.join(HERE, u"_sentinel_relay_r1.py")
CLOSING_ORIG = os.path.join(os.path.dirname(HERE), u"CLOSING_LINE.txt")
CMDR = u"qoder:494abfd7"
ME = u"qoder:42d1a6fa"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def main():
    tmp = os.path.join(tempdir := os.environ.get("TEMP", "."), u"cnx_sentinel_bolt_%d" % int(time.time()))
    os.makedirs(tmp)
    for f in (u"bus_hub.py", u"bus.py"):
        shutil.copy2(os.path.join(BUS, f), tmp)
    port = free_port()
    os.environ["BUS_PORT"] = str(port)          # hub_alarm 把 os.environ 原样交给子进程 ⇒ 客户端同口
    hub = subprocess.Popen([sys.executable, os.path.join(tmp, u"bus_hub.py")],
                           cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res = []
    try:
        def check(name, got, want):
            ok = got == want
            res.append(ok)
            print("%-58s %s" % (name, "PASS" if ok else "FAIL got=%r want=%r" % (got, want)))

        up = False
        for _ in range(40):
            try:
                d = json.loads(opener().open(u"http://127.0.0.1:%d/health" % port, timeout=5).read())
                if d.get("port") == port:
                    up = True
                    break
            except Exception:
                time.sleep(1)
        check(u"⓪ 隔离中枢在这一口上真起来了（正式 4799 不动）", up, True)
        if not up:
            return 6
        for who in (ME, CMDR):
            subprocess.run([sys.executable, u"bus.py", u"reg", u"--id", who,
                            u"--name", u"隔离探针·%s" % who.split(":")[-1]],
                           cwd=tmp, capture_output=True,
                           env=dict(os.environ, PYTHONIOENCODING=u"utf-8"))

        os.environ[u"SR_HUB"] = tmp              # 报警腿走隔离副本，不进正式账本
        os.environ[u"SR_HUB_OFF"] = u"0"
        spec = importlib.util.spec_from_file_location(u"sent_bolt_probe", SENT)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.LOG = os.path.join(tmp, u"sentinel_probe.log")   # 桩日志，不混进值守日志

        cl = m.closing_line()
        orig = io.open(CLOSING_ORIG, encoding=u"utf-8").read().strip()
        check(u"甲 closing_line() 逐字读到原件", cl, orig)
        check(u"甲 原件尺寸与既有一致（83 字节）", len(cl.encode(u"utf-8")), 83)

        body = u"隔离自测：这一枚只验「外发必须带逐字尾行」那道闸装到报警腿上没有，" \
               u"收件人是临时副本里的假名册，真总线与号令者都看不见它。"
        topic_want = u"band:T:%s:boltprobe" % time.strftime(u"%m%d")
        verdict, topic = m.hub_alarm(u"T", u"boltprobe", body)
        check(u"乙 隔离投送返回 sent", verdict, u"sent")

        rows = []
        for line in io.open(os.path.join(tmp, u"bus.jsonl"), encoding=u"utf-8", errors="replace"):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        mine = [r for r in rows if r.get(u"topic") == topic_want]
        check(u"乙 隔离账本里落了这一枚", len(mine), 1)
        mid = mine[0].get(u"id") if mine else None
        got = json.loads(opener().open(u"http://127.0.0.1:%d/msg?id=%s" % (port, mid),
                                       timeout=30).read())
        remote_body = got.get(u"body") or u""
        check(u"乙 GET /msg 回读的正文末尾逐字等于原件", remote_body.rstrip().endswith(cl), True)
        check(u"乙 正文长出来的部分正好是那句口令（不多不少）",
              len(remote_body.encode(u"utf-8")) - len(body.rstrip().encode(u"utf-8")),
              len(cl.encode(u"utf-8")) + 1)      # +1 = 口令前那枚换行
        check(u"乙 收件人仍是号令者（我没为了测试改路由）", mine[0].get(u"to"), CMDR) if mine else None

        # 丙：负对照——原件读不到时必须拒发，且账本不许多出一枚
        m.CLOSING = os.path.join(tmp, u"no_such_closing.txt")
        v2, t2 = m.hub_alarm(u"T", u"boltprobe-neg", u"这枚不许投出去：原件已被指到不存在的文件。")
        check(u"丙 原件不可得 ⇒ 返回 no_closing", v2, u"no_closing")
        rows2 = []
        for line in io.open(os.path.join(tmp, u"bus.jsonl"), encoding=u"utf-8", errors="replace"):
            line = line.strip()
            if line:
                rows2.append(json.loads(line))
        check(u"丙 拒发是真拒：隔离账本没有多出那一枚",
              len([r for r in rows2 if r.get(u"topic") == u"band:T:%s:boltprobe-neg" % time.strftime(u"%m%d")]), 0)
        tail = io.open(m.LOG, encoding=u"utf-8").read().strip().splitlines()[-1]
        check(u"丙 拒发在日志具名留了一行", u"不投" in tail, True)
        print(u"日志尾行：%s" % tail[:120])
        print(u"隔离账本总行数 %d（正式总线 %d 行，本脚本 0 写入）" % (
            len(rows2), sum(1 for _ in io.open(os.path.join(BUS, u"bus.jsonl"),
                                               encoding=u"utf-8", errors=u"replace"))))
    finally:
        hub.terminate()
        try:
            hub.wait(timeout=20)
        except Exception:
            hub.kill()
        shutil.rmtree(tmp, ignore_errors=True)
    n = sum(1 for x in res if x)
    print(u"\n%d/%d 过" % (n, len(res)))
    return 0 if n == len(res) else 1


if __name__ == u"__main__":
    sys.exit(main())
