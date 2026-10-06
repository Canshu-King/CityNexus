# -*- coding: utf-8 -*-
"""`_night_verdict_runner_r1.py` 的合成自测：到点才跑、失败重试、绝不覆盖、单实例、过期拒答。

为什么必须自测：这枚是「23:00 那一档」唯一的自动出件路径。它要是提前跑，拿到的不是那一档的数；
要是撞名覆盖，就把前一份读数抹了；要是双跑，早上会看到两份不一致的件还分不清哪份真。
三种都只能在这里用假时钟与假命令验，不能等到 23:00 现场试。
"""
import io
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import _night_verdict_runner_r1 as R

REAL = time
res = []


def check(name, got, want):
    ok = want in str(got)
    res.append(ok)
    print(u"%-46s %s" % (name, u"对" if ok else u"错（实读 %s｜期望含 %s）" % (str(got)[:170], want)))


class FakeP:
    def __init__(self, rc, out):
        self.returncode = rc
        self.stdout = out
        self.stderr = b""


def make_runs(seq):
    box = {"n": 0, "envs": []}

    def fake_run(args, capture_output=False, env=None, cwd=None, timeout=None):
        rc, out = seq[min(box["n"], len(seq) - 1)]
        box["n"] += 1
        box["envs"].append(dict(env or {}))
        return FakeP(rc, out)
    return fake_run, box


TMPD = tempfile.mkdtemp(prefix="nvr_selftest_")
R.LOGP = os.path.join(TMPD, "log.txt")
R.LOCK = os.path.join(TMPD, "lock.json")
R.DONE = os.path.join(TMPD, "done.txt")
R.HERE = TMPD                                # 10-02 06:14 的教训：run_writer 的路径由 HERE 拼，不把它改到临时目录，
#   自测就会把 900 B 的假件漏进 patrol，逼得 23:00 的真件只能落 _r3（今晚真的发生了这件事）      # 必须在第一次 main() 之前就改走：否则测试会把真 done 写进 patrol 目录，今晚的取数会被自己拒掉

# 1) 到点判定：时刻未到就还没跑；23:30 那拍算出的目标仍是当天 23:00:20（已过）
t_day, d_day = R.target_epoch(time.mktime(time.strptime("2026-10-02 22:00:00", "%Y-%m-%d %H:%M:%S")))
t_late, d_late = R.target_epoch(time.mktime(time.strptime("2026-10-02 23:30:00", "%Y-%m-%d %H:%M:%S")))
check("未到点：目标在现在之后", str(t_day > time.mktime(time.strptime("2026-10-02 22:00:00", "%Y-%m-%d %H:%M:%S"))), "True")
check("23:30 时目标已过期（当天 23:00:20）", str(t_late < time.mktime(time.strptime("2026-10-02 23:30:00", "%Y-%m-%d %H:%M:%S"))), "True")
check("日期跟着 now 走，不写死今天", d_late, "2026-10-02")

# 2) 失败重试：第一次 rc=1、第二次 rc=0 ⇒ 只跑两次、最终落盘
seq = [(1, b"boom"), (0, b"x" * 900)]
R.subprocess.run, box = make_runs(seq)
p, rc, b, s = R.run_writer("fake.py", os.path.join(TMPD, "a.txt"), "2026-10-02", tries=3, gap=0)
check("rc 非 0 会重试、成功就停", str([box["n"], rc, b]), "[2, 0, 900]")
check("落盘路径就是给定的 base", os.path.basename(p), "a.txt")
check("传下去的 NIGHT_DATE 是算出来的日期", str(box["envs"][-1].get("NIGHT_DATE")), "2026-10-02")

# 3) 绝不覆盖：同名已存在就 _r2
p2, rc2, b2, s2 = R.run_writer("fake.py", os.path.join(TMPD, "a.txt"), "2026-10-02", tries=1, gap=0)
check("撞名不许覆盖，要另起 _r2", os.path.basename(p2), "a_r2.txt")
check("第一份字节还在", os.path.getsize(os.path.join(TMPD, "a.txt")), "900")

# 4) 一直失败：三试都 rc=1 ⇒ 仍然留件、但 rc 报非 0（不许假装成功）
R.subprocess.run, box = make_runs([(1, b"e1"), (1, b"e2"), (1, b"e3")])
p3, rc3, b3, s3 = R.run_writer("fake.py", os.path.join(TMPD, "b.txt"), "2026-10-02", tries=3, gap=0)
check("全失败时 rc 如实非 0", str(rc3), "1")
check("全失败也要跑满三次", str(box["n"]), "3")

# 5) 过期拒答：now 已晚于目标 + LATE_LIMIT ⇒ main 返回 7，且不碰任何尺
class Shim:
    def __getattr__(self, n):
        return getattr(REAL, n)

    def time(self):
        return time.mktime(time.strptime("2026-10-03 00:45:00", "%Y-%m-%d %H:%M:%S"))
old_run = R.subprocess.run
R.subprocess.run, box = make_runs([(0, b"y" * 900)])
R.time = Shim()
R.target_epoch = lambda now=None: (time.mktime(time.strptime("2026-10-02 23:00:20", "%Y-%m-%d %H:%M:%S")), "2026-10-02")
sys.argv = ["_night_verdict_runner_r1.py"]
rc_main = R.main()
R.time = REAL
check("过期就整件拒答（返回 7）", str(rc_main), "7")
check("上面那条用的是过了 90 分钟宽限的时刻", str(rc_main != 0), "True")
check("拒答时一条尺都不许跑", str(box["n"]), "0")

# 6) 单实例：锁里那枚 pid 仍带着本脚本名 ⇒ 第二支直接退，不双跑
R.alive = lambda lock: True
sys.argv = ["_night_verdict_runner_r1.py"]
rc2_main = R.main()
check("已有取数器在跑就退（返回 0、不双跑）", str(rc2_main), "0")

# 7) 出过件就不再出第二份：done 写着今天 ⇒ 重起来也直接退，一条尺都不碰
io.open(R.DONE, "w", encoding="utf-8").write(time.strftime("%Y-%m-%d") + chr(10))
R.alive = lambda lock: False
R.subprocess.run, box = make_runs([(0, b"z" * 900)])


class Shim2:
    def __getattr__(self, n):
        return getattr(REAL, n)

    def time(self):
        return time.mktime(time.strptime("2026-10-02 23:05:00", "%Y-%m-%d %H:%M:%S"))


R.time = Shim2()
R.target_epoch = lambda now=None: (
    time.mktime(time.strptime("2026-10-02 23:00:20", "%Y-%m-%d %H:%M:%S")), "2026-10-02")
sys.argv = ["_night_verdict_runner_r1.py"]
rc_done = R.main()
R.time = REAL
check("done=今天时重起也不落第二份件", str([rc_done, box["n"]]), "[0, 0]")
io.open(R.DONE, "w", encoding="utf-8").write("2026-01-01\n")
R.subprocess.run, box = make_runs([(0, b"w" * 900), (0, b"w" * 900)])
R.time = Shim2()
sys.argv = ["_night_verdict_runner_r1.py"]
rc_stale = R.main()
R.time = REAL
check("done 是旧日期时必须照常出件（不许拿去年的账拒今天）", str(box["n"]), "2")

print("PASS %d/%d" % (sum(1 for x in res if x), len(res)))
if not all(res):
    print(u"FAIL %d 条：这枚到点取数器不可信，23:00 还得靠手动" % (len(res) - sum(1 for x in res)))
sys.exit(0 if all(res) else 1)
