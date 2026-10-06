# -*- coding: utf-8 -*-
"""BB 机看板一键起复：`python _board_restart_r1.py`（只动 :4820 这一条腿，不碰别人的进程）。

为什么要有它：改完 board.py 必须重启才生效，而手敲 taskkill 有两个已咬过人的坑——
① `netstat | grep :4820` 会带出 TIME_WAIT（PID 0），杀错或杀空；所以只认 LISTENING。
② 用 bash 的 `env VAR=x cmd` 前缀可能什么都没起来却退 0；所以起进程走 Python 的 Popen，
   并且起完真的回连一次 /api/fleet 拿 200 才算成——不认"我敲过了"，只认"它答了"。
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

PORT = 4820
BOARD = u"D:/moodle/agent_bus/board.py"
PY = sys.executable
DETACHED = 0x00000008                     # DETACHED_PROCESS
# 坑（22:2x 自咬一次）：DETACHED_PROCESS 与 CREATE_NEW_CONSOLE 互斥，两个一起传
# CreateProcess 直接 WinError 87「参数错误」——结果旧板已被我 kill、新板没起来，
# 看板整段下线、自检 11 枚红。起不来就等于砸了主人正在看的东西，所以这里只留一个 flag，
# 并且下面必须真的回连一次拿 JSON 才算成。
NEW_GROUP = 0x00000200                    # CREATE_NEW_PROCESS_GROUP（与 DETACHED 可共存）


def listening_pids():
    out = subprocess.check_output(["netstat", "-ano", "-p", "TCP"]).decode("utf-8", "replace")
    pids = []
    for ln in out.splitlines():
        if (u"127.0.0.1:%d" % PORT) in ln and "LISTENING" in ln.upper():
            m = re.search(r"(\d+)\s*$", ln.strip())
            if m:
                pids.append(int(m.group(1)))
    return sorted(set(pids))


def main():
    before = listening_pids()
    print(u"改前听 :%d 的：%s" % (PORT, before or u"（无）"))
    for pid in before:
        subprocess.call(["taskkill", "/PID", str(pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    still = listening_pids()
    if still:
        sys.exit(u"ABORT：taskkill 后仍有进程听 :%d（%s），不重复起，免得两个板子抢一口" % (PORT, still))

    log = open(u"D:/moodle/agent_bus/_board.out.log", "ab", buffering=0)
    p = subprocess.Popen([PY, BOARD], cwd=u"D:/moodle/agent_bus",
                         env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                         stdout=log, stderr=subprocess.STDOUT,
                         creationflags=DETACHED | NEW_GROUP, close_fds=True)
    print(u"已起：pid %d（脱离本 shell，退出后继续活）" % p.pid)

    for i in range(24):
        time.sleep(0.5)
        try:
            raw = urllib.request.urlopen("http://127.0.0.1:%d/api/fleet" % PORT, timeout=3).read()
            d = json.loads(raw.decode("utf-8", "replace"))
            got = listening_pids()
            print(u"回连成功：现测 %s｜在册 %d 行｜收班 %d｜取数口 %d 字节"
                  % (d.get("at"), len(d.get("rows", [])), d.get("retired_n", -1), len(raw)))
            print(u"现在听 :%d 的：%s（应为新 pid %d）" % (PORT, got, p.pid))
            if got != [p.pid]:
                print(u"注意：端口持有者与新起 pid 不一致，去看 _board.out.log")
            sys.exit(0)
        except Exception as e:
            if i == 23:
                sys.exit(u"起了 12 秒仍连不上 /api/fleet：%s ⇒ 看 _board.out.log 尾行" % e)
    sys.exit("UNREACHABLE")


if __name__ == "__main__":
    main()
