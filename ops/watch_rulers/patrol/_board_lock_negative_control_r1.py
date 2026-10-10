# -*- coding: utf-8 -*-
"""负对照：证明刚加的三条结构锁真会咬人（不咬人的锁等于假锁）。

做法：在 agent_bus 同目录放一份**故意破坏**的看板副本（只改一处：把回话框的
`id="body"` 换成 `id="bodyX"`，模拟"回话框被搬走/改名"），用 BOARD_PORT 起在另一个端口上，
让自检指向那个端口跑——线上主人正在看的那一屏全程不动（自检与看板都读同一个环境变量）。

跑完必做两件收尾：杀掉隔离实例、核对线上 SHAME.md 的 sha 没被副本写过
（看板会生成那份产物，同源数据理应字节不变；一旦变了就说明它有我没预期的副作用）。
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = u"D:/moodle/agent_bus"
SRC = os.path.join(ROOT, "board.py")
DUP = os.path.join(ROOT, u"_negcheck_board_tmp.py")
def free_port():
    """自己挑一枚真空闲的端口：板子有端口守卫，占了别人的服务它会 REFUSE。"""
    import socket
    sk = socket.socket()
    sk.bind(("127.0.0.1", 0))
    port = str(sk.getsockname()[1])
    sk.close()
    return port


PORT = None
PYEXE = sys.executable


def sha(path):
    import hashlib
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()[:16] if os.path.isfile(path) else u"（无）"


def main():
    if not os.path.isfile(SRC):
        sys.exit(u"ABORT：没有 board.py")
    shame = os.path.join(ROOT, "SHAME.md")
    before = sha(shame)
    s = io.open(SRC, encoding="utf-8", errors="replace").read()
    if s.count(u'id="body"') < 1:
        sys.exit(u"ABORT：源码里没有 id=\"body\" 可破坏，负对照无从做起")
    io.open(DUP, "w", encoding="utf-8", newline=chr(10)).write(s.replace(u'id="body"', u'id="bodyX"', 1))
    print(u"破坏副本已放（只改回话框 id）；线上 SHAME.md sha=%s" % before)

    global PORT
    PORT = free_port()
    print(u"挑到空闲端口 :%s" % PORT)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", BOARD_PORT=PORT)
    errlog = os.path.join(ROOT, u"_negcheck_boot.log")
    eh = io.open(errlog, "wb")
    p = subprocess.Popen([PYEXE, DUP], cwd=ROOT, env=env,
                         stdout=eh, stderr=subprocess.STDOUT,
                         creationflags=0x00000008 | 0x00000200, close_fds=True)
    try:
        for i in range(20):
            time.sleep(0.6)
            try:
                json.loads(urllib.request.urlopen(
                    "http://127.0.0.1:%s/api/fleet" % PORT, timeout=3).read().decode("utf-8", "replace"))
                break
            except Exception:
                if i == 19:
                    eh.flush()
                    tail = io.open(errlog, encoding="utf-8", errors="replace").read().strip()[-700:]
                    sys.exit(u"ABORT：隔离实例起不来，它的报错尾：\n%s" % (tail or u"（没留下任何输出）"))
        print(u"隔离实例 pid=%d 在 :%s 上活了，线上 :4820 未动" % (p.pid, PORT))
        q = subprocess.run([PYEXE, os.path.join(ROOT, "board_check_r1.py")],
                           cwd=ROOT, capture_output=True, env=env)
        out = q.stdout.decode("utf-8", "replace")
        reds = [ln for ln in out.splitlines() if u"红：" in ln]
        print(u"自检 rc=%d（要的不是绿，是它肯红）" % q.returncode)
        for ln in reds:
            print(u"  " + ln.strip()[:150])
        hit = [ln for ln in reds if u"回话" in ln]
        if not hit:
            print(u"FAIL：破坏了回话框，锁却没咬 ⇒ 那条锁是假的")
        else:
            print(u"负对照通过：破坏回话框，锁当场红了（不是靠我读代码推的）")
    finally:
        subprocess.call(["taskkill", "/PID", str(p.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.isfile(DUP):
            os.remove(DUP)
        after = sha(shame)
        print(u"收尾：副本已删、隔离实例已退。SHAME.md sha %s → %s"
              u"（它是每轮自变的现测产物，不能当不变量用——上一版拿它做判据是我错了）"
              % (before, after))


if __name__ == "__main__":
    main()
