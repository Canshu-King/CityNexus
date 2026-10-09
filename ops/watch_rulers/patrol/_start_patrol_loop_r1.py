# -*- coding: utf-8 -*-
u"""起巡检跑批：真 detached（DETACHED_PROCESS 单独给，不与 CREATE_NEW_PROCESS_GROUP 并用）。

为什么不能并用：`DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` 在这台机器上抛 WinError 87
（memory 里记过：杀了服务没起，下线五分）。所以这里只用 DETACHED_PROCESS。
为什么非 detached 不可：19:0x 实测——用后台 Bash 起的跑批（pid 4676）跑完第一拍就被回收，
19:21 的第二拍没落盘；这和"前台 sleep 被回收"是同一个坑。

用法：python _start_patrol_loop_r1.py [--minutes 12]
起来后先看 stdout 打印的 pid，再自己数 rounds/ 里带那个 pid 的档（≥2 拍才叫活着）。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOOP = os.path.join(HERE, "_patrol_loop_r1.py")
PYEXE = sys.executable

DETACHED_PROCESS = 0x00000008
CREATE_NEW_CONSOLE = 0x00000010


def main():
    arg = sys.argv.index("--minutes") + 1 if "--minutes" in sys.argv else 1
    minutes = sys.argv[arg] if len(sys.argv) > arg else "12"
    out = os.path.join(HERE, "rounds", "_loop_stdout.log")
    # 先清锁：上枚要是被回收了，锁还在（陈旧锁当没有，脚本自己会处理，这里只是不让它误判）
    # 不主动删锁——脚本的 claim() 已能认陈旧锁，删了就绕过那道门。
    fh = open(out, "ab", 0)
    p = subprocess.Popen([PYEXE, LOOP, "--minutes", minutes],
                         cwd=HERE, stdout=fh, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL,
                         env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                         creationflags=DETACHED_PROCESS)
    fh.close()
    print(u"已起 pid=%d minutes=%s stdout=%s" % (p.pid, minutes, out))
    print(u"验活：数 rounds/round_*_%d_*.txt，≥2 拍才算它自己活着" % p.pid)
    return 0


if __name__ == "__main__":
    sys.exit(main())