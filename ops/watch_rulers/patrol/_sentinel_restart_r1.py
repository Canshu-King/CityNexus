# -*- coding: utf-8 -*-
"""改完哨兵代码后的一键起复：`python _sentinel_restart_r1.py`

为什么要有它：哨兵是常驻循环，改了 .py 不重启就等于没改——今晚「抑制名单」那条裁语
若不重启，明早 K/M 档还会照旧重复报 6efab655，而我会以为自己已经办完。

两个已咬过人的坑写在这里：
① 判活要认 CommandLine 不是进程名（一堆 python.exe 都是别的车道/别的仪表），
   且 CIM 查回 0 行往往是查询本身失败而不是"进程不存在" ⇒ 先打印它数到几行；
② 别绕过 keepalive 直接起 relay：STOP 时刻是 keepalive 往下传的（10-04 那次
   三个子腿各自到点退，就是因为有人手起了裸 relay）。keeper 不在跑时，起的是 keepalive。
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RELAY = u"_sentinel_relay_r1.py"
KEEPER = u"_sentinel_keepalive_r1.py"
PYEXE = sys.executable


def scan():
    """返回 (python 进程总数, relay 的 pid 列表, keeper 在不在)。总数用来分辨「查失败」与「真没有」。"""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name LIKE '%python%'\" | "
          "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
    out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps]).decode("utf-8", "replace")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    relay, keeper = [], False
    for ln in lines:
        parts = ln.split("\t", 1)
        cmd = parts[1] if len(parts) > 1 else ""
        if RELAY in cmd:
            relay.append(parts[0].strip())
        if KEEPER in cmd:
            keeper = True
    return len(lines), relay, keeper


def main():
    total, relay, keeper = scan()
    print(u"① 现况：python 进程 %d 行（数到 0 就是查询失败，不是没人跑）｜哨兵 %s｜keepalive %s"
          % (total, relay or u"不在", u"在" if keeper else u"不在"))
    if total == 0:
        sys.exit(u"ABORT：CIM 一行都没查到 ⇒ 先修查询，别据此判「哨兵没跑」")

    for pid in relay:
        subprocess.call(["taskkill", "/PID", str(pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(u"② 已退 哨兵 pid %s" % pid)
    if relay and not keeper:
        p = subprocess.Popen([PYEXE, os.path.join(HERE, KEEPER)], cwd=HERE,
                             stdout=open(os.path.join(HERE, u"_sentinel_keepalive.log"), "ab", buffering=0),
                             stderr=subprocess.STDOUT,
                             env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                             creationflags=0x00000008 | 0x00000200, close_fds=True)
        print(u"③ keepalive 不在，改起它（pid %d）由它带 STOP 时刻拉哨兵" % p.pid)

    for i in range(115):
        time.sleep(3)
        total2, relay2, keeper2 = scan()
        if relay2:
            print(u"④ 哨兵回来了：pid %s（第 %d 拍，约 %d 秒）｜keepalive %s"
                  % (relay2, i + 1, (i + 1) * 3, u"在" if keeper2 else u"不在"))
            logf = os.path.join(HERE, u"_sentinel_relay_latest.log")
            if os.path.isfile(logf):
                tail = open(logf, encoding="utf-8", errors="replace").read().strip().splitlines()[-2:]
                for ln in tail:
                    print(u"   日志尾：", ln[:130])
            print(u"SENTINEL_RESTARTED")
            return
    sys.exit(u"ABORT：等了三分半（盖过 keepalive 的 300 秒巡拍）哨兵仍没回来 "
             u"⇒ 去看 _sentinel_keepalive.log 与 _sentinel_relay_latest.log 尾行")


if __name__ == "__main__":
    main()
