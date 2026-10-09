# -*- coding: utf-8 -*-
"""到点自动出「23:00 那一档」的读数件：不依赖我正好在那一刻醒着。

为什么要它：终值单本来是要**我**在 23:00:20 手动跑两条命令——可我那一拍可能在睡、可能在前一条命令里、
也可能整台机器重启过。把交付绑在自己的注意力上不是值守，是碰运气。
这一枚是脱离循环（自己睡到点），跑完就退，且**绝不覆盖已有件**：文件名撞了就往 _r2/_r3 走，
留得下坐标（字节数 + sha1）好早上回读。

边界：0 次上总线、0 次敲门、0 次写账本、0 次动权威线；只调两条既有的只读尺并落盘。
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PYEXE = sys.executable
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
LOGP = os.path.join(HERE, "_night_verdict_runner.log")
# 档点：默认 23:00:20（终值单）。同一份脚本可以守几档，看护器按命令行标记 `NVR_AT=<档点>` 分档——
# env 在进程表里看不见，只靠 env 传档点的那条腿一旦机器重启就没人认得它是哪一档：
# 10-06 03:1x 实测，22:46 那次修复安装重启带走 10:55 那枚，栈起复时 COMPONENTS 只有一条 verdict，
# 于是只补回 23:00:20，10:55 那一档静默失踪，而本班目标写的正是"守到明天 11:00"。
_SLOT = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("NVR_AT=")]
RUN_AT = (_SLOT[0] if _SLOT else os.environ.get("NVR_AT", "23:00:20"))
SLOT_TAG = RUN_AT.replace(":", "")          # 锁名用整档点：230020 / 105500（沿用旧名，不新开一把）
ART_TAG = SLOT_TAG[:4]                     # 件名用四位档点：23:00:20 那档仍是 _2300.txt，一字不改
NVR_ROLL = os.environ.get("NVR_ROLL", "1") == "1"   # 档点已过 ⇒ 顺延到明天同一刻（见 target_epoch 的成因）
LATE_LIMIT = int(os.environ.get("NVR_LATE_MIN", "90"))

# 成功过一次就认账：重启后即便再被拉起来，也不许在同一天的同一档落第二份读数
DONE = os.path.join(HERE, "_night_verdict_runner.done")
# 锁按档点分开：一天里可以有几档（11:00 前收尾、23:00 终值单），各持一把锁；
# 同一档重复起仍会被挡——那才是这把锁真正要防的"落两份件"。以前一把锁管全天，起第二档会被顶掉。
LOCK = os.path.join(HERE, "_night_verdict_runner.%s.lock" % SLOT_TAG)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def say(s):
    line = u"[%s] %s" % (time.strftime("%m-%d %H:%M:%S"), s)
    io.open(LOGP, "a", encoding="utf-8", newline="\n").write(line + chr(10))
    print(line)


def target_epoch(now=None):
    """到点取数器的目标时刻。NVR_ROLL=1（默认）：今天的档点已过就顺延到明天同一刻。

    为什么要顺延（10-05 17:0x 现场）：看护器每 900 秒会拉起缺掉的腿，而它很可能在档点之后才拉
    （今天 10:55 那一档出完，收尾那支就退场了）。旧写法只认"今天这一刻"，过了就 REFUSE 退出 ⇒
    明天 11:00 前那一档没人出，而目标写的是"守到明天 11:00"。顺延之后，任何一次重拉都会把下一档arm上。
    REFUSE 那条路没有删掉：`NVR_ROLL=0` 时仍是"过了档点加宽限期就拒出"，防止有人手慢补出一份贴错时刻的读数。
    """
    now = now if now is not None else time.time()
    d = time.strftime("%Y-%m-%d", time.localtime(now))
    t = time.mktime(time.strptime(d + " " + RUN_AT, "%Y-%m-%d %H:%M:%S"))
    if t <= now and NVR_ROLL:
        t += 86400
        d = time.strftime("%Y-%m-%d", time.localtime(t))
    return t, d


def free_path(base):
    """绝不覆盖：已存在就 _r2、_r3 …"""
    if not os.path.exists(base):
        return base
    stem, ext = os.path.splitext(base)
    n = 2
    while os.path.exists(u"%s_r%d%s" % (stem, n, ext)):
        n += 1
    return u"%s_r%d%s" % (stem, n, ext)


def run_writer(script, out_base, date_s, tries=3, gap=60):
    """跑一把只读尺，把 stdout 落到不撞名的文件里；返回 (路径, rc, 字节, sha1)。"""
    env = dict(ENV, NIGHT_DATE=date_s)
    last = None
    for k in range(1, tries + 1):
        p = subprocess.run([PYEXE, os.path.join(HERE, script)], capture_output=True, env=env,
                           cwd=HERE, timeout=1800)
        out = (p.stdout or b"") + (p.stderr or b"")
        rc = p.returncode
        last = (rc, out)
        if rc == 0 and len(out) > 300:
            break
        say(u"%s 第 %d 次 rc=%d、输出 %d B%s" % (script, k, rc, len(out), u"（重试）" if k < tries else u"（放弃重试）"))
        if k < tries:
            time.sleep(gap)
    rc, out = last
    path = free_path(os.path.join(HERE, out_base))
    io.open(path, "wb").write(out)
    return path, rc, len(out), hashlib.sha1(out).hexdigest()


def alive(lock):
    try:
        d = json.loads(io.open(lock, encoding="utf-8").read())
    except Exception:
        return False
    q = d.get("q") or {}
    if not q:
        return False
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | Select-Object -ExpandProperty CommandLine"
                          % int(q.get("pid", -1))], capture_output=True).stdout.decode("utf-8", "replace").strip()
    return bool(out) and "_night_verdict_runner_r1.py" in out


def main():
    if any(a == "--check" for a in sys.argv):
        t, d = target_epoch()
        say(u"--check：目标 %s %s（现在 %s，还差 %.1f 分）" % (
            d, RUN_AT, time.strftime("%H:%M:%S"), (t - time.time()) / 60.0))
        return 0
    t, d = target_epoch()
    try:
        # done 键带档点：这一支一天可以认几档（23:00 终值单、11:00 前收尾档），
        # 早档出完不会把晚档吃掉——以前键只有日期，起第二档就会互相顶掉。
        # 10-05 17:0x 补的一格：比较的对象必须是**目标那一天**，不是"今天"。
        # 顺延生效后（今天 10:55 已过 ⇒ 目标明天 10:55），拿今天去比会读到
        # 「2026-10-05@10:55:00」这条已完成的记录，于是刚arm好的明天那一档当场被当成重复而退出——
        # 看护器再怎么拉都拉不出收尾读数，这种红我自己看不见（它退得干干净净）。
        if io.open(DONE, encoding="utf-8").read().strip() == d + u"@" + RUN_AT:
            say(u"目标那天（%s）已出过件（done=%s@%s），这一支不再跑第二次" % (d, d, RUN_AT))
            return 0
    except Exception:
        pass
    if alive(LOCK):
        say(u"已有取数器在跑（锁 %s 里的 pid 仍带本脚本名），这一支退出——不双跑，免得落两份件" % os.path.basename(LOCK))
        return 0
    io.open(LOCK, "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"pid": os.getpid(), "at": time.strftime("%Y-%m-%d %H:%M:%S"), "q": {"pid": os.getpid()}}))
    tag = time.strftime("%m%d", time.strptime(d, "%Y-%m-%d"))
    if time.time() > t + LATE_LIMIT * 60:
        say(u"REFUSE：现在已过 %s %s 加 %d 分钟，再出的件就不是那一档的读数了" % (d, RUN_AT, LATE_LIMIT))
        return 7
    say(u"取数器起来：pid=%s，到 %s %s 开跑（现在 %s）" % (os.getpid(), d, RUN_AT, time.strftime("%H:%M:%S")))
    while time.time() < t:
        time.sleep(min(30, max(1, t - time.time())))
    say(u"到点。先跑终值单，再跑第 2 格的本地 git 补件")
    p1, rc1, b1, s1 = run_writer("night_verdict_r2.py", u"_night_verdict_" + tag + u"_" + ART_TAG + u".txt", d)
    p2, rc2, b2, s2 = run_writer("_night_tip_local_r1.py", u"_night_tipfix_" + tag + u"_" + ART_TAG + u".txt", d)
    for nm, p, rc, b, s in ((u"终值单", p1, rc1, b1, s1), (u"第 2 格补件", p2, rc2, b2, s2)):
        head = io.open(p, encoding="utf-8", errors="replace").read().split(chr(10))
        nonempty = sum(1 for x in head if x.strip())
        bad = sum(1 for x in head if u"读数不全" in x or u"不可得" in x)
        say(u"%s → %s｜rc=%d｜%d B｜sha1 %s｜非空行 %d｜带「读数不全/不可得」的行 %d" % (
            nm, os.path.basename(p), rc, b, s, nonempty, bad))
    if rc1 == 0 or rc2 == 0:
        io.open(DONE, "w", encoding="utf-8", newline=chr(10)).write(
            time.strftime("%Y-%m-%d") + "@" + RUN_AT + chr(10))
    say(u"取数完毕，这一支退场（锁留着当记录）")
    return 0 if rc1 == 0 or rc2 == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
