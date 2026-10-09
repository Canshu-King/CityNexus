# -*- coding: utf-8 -*-
u"""巡检跑批：每 N 分钟自己跑一次巡逻并存档，不靠"我排前台 sleep"。

为什么要有它（10-06 18:4x–19:0x 实测）：我用 `(sleep N; python patrol > out.txt) &` 排的后台巡逻，
19:21、18:43、18:58 三排**都没落盘**——前台 sleep 会被提前回收，把整条链掐了。
而巡检本身读现网状态，早跑晚跑不改变判读，缺的只是"那一刻的档"。

三道防（19:0x 实测踩出来的）：
  ① **单实例锁**：两枚跑批同时跑，档名都是 round_<日期>_001.txt ⇒ 互相覆盖（实测两枚都在、都在写 _001）。
     锁里那个 pid 还带本脚本名就退——与值守栈「按 CommandLine 认到现支」同一形制。
  ② **档名带 pid**：即使锁失效也不会互相覆盖。
  ③ **自停闸**：过了 STOP（默认 11:05，与"守到明天 11 点"对齐、留五分钟写快照）自己收工，
     不在目标之外跑到天亮。

只读：只跑 `_bb_patrol_once_r1.py`（它自己只读）、只写 rounds/ 下的 txt；0 次上总线、0 次敲门。
跑法：python _patrol_loop_r1.py [--minutes 12]
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PATROL = os.path.join(HERE, "_bb_patrol_once_r1.py")
LOGDIR = os.path.join(HERE, "rounds")
LOCK = os.path.join(HERE, "_patrol_loop.lock")
NEEDS = os.path.join(LOGDIR, "_needs_eyes.log")
STOP = os.environ.get("PATROL_LOOP_STOP", "1105")

# 什么算"要人看"：结论行不是「全队都在动」，或这几个格出现非零/非完整。
# 判据是从实读的行里**解析出来的数**，不是写字面量（同一个教训：`_busy_wave_evidence_r1.py`）。
WATCH_CELLS = (u"\u2461", u"\u2462", u"\u2463")      # ②该敲 ③不该敲 ④包工头压着
GREEN = u"全队都在动"


def _concl_is_waiting(concl):
    u"""结论行说的是「没人该敲；缺单的那 N 扇等包工头点」⇒ 不算红（那是常态）。

    20:34 装：巡逻结论有四种形态，只有两种是真问题——
    「有扇该敲」与「N 扇末态不可判」。「没人该敲＋等单」是交活型停着（五·三十三），
    每 12 分钟都会出现一次，算红就把它淹了。
    判词从**这一拍读到的结论行**里取，取不到就当不算等待（交给别的格去判红）。
    """
    if not concl:
        return False
    return (u"没人该敲" in concl) and (u"等包工头点" in concl)


def _mark(n):
    u"""第 n 格的真圈号：①是 U+2460，圈号连续 ⇒ n 格 = U+2460+(n-1)。"""
    return unichr_(0x2460 + n - 1)


def unichr_(i):
    return chr(i)


def num_after(text, key):
    u"""抽 key 后第一个整数；抽不到返回 None（不许拿 0 冒充读数）。"""
    i = text.find(key)
    if i < 0:
        return None
    m = re.search(r"\d+", text[i + len(key):])
    return int(m.group(0)) if m else None


def judge(text):
    u"""从一拍的正文推出 (红?, 理由行)。判据全部来自**这一拍读到的行**，解析不到就当红。"""
    concl = ""
    cells = {}
    for l in text.splitlines():
        ls = l.strip()
        if ls.startswith(u"\u7ed3\u8bba"):
            concl = ls
        for n in (1, 2, 3, 6, 10):
            if ls.startswith(_mark(n)):
                cells[n] = ls
    why = []
    if not concl:
        why.append(u"\u6ca1\u8bfb\u5230\u7ed3\u8bba\u884c")
    elif GREEN not in concl and not _concl_is_waiting(concl):
        why.append(concl)
    # ②该敲：n=2。抽 "扇" 前的数；行形是 `② 该敲（…）N 扇`
    v = cells.get(2)
    if v is not None:
        n = num_after(v, u"\uff09")            # 全角右括号之后紧跟的那个数
        if n is None:
            why.append(v)
        elif n != 0:
            why.append(v)
    # ③不该敲：n=3，同样形制。20:34 改：**等单不算红**（常态，五·三十三）。
    # 信息不丢：收进 _wait，待看档那行末尾照旧打出「等单 N 扇：…」。
    # 但**读不到数**时仍算红——解析不到判据不许当绿。
    wait = []
    v = cells.get(3)
    if v is not None:
        n = num_after(v, u"\uff09")
        if n is None:
            why.append(v)
        elif n != 0:
            wait = [v]
    # ①未接 BB 机：n=1
    v = cells.get(1)
    if v is not None and u"\u672a\u63a5 BB \u673a" in v:
        n = num_after(v, u"\u672a\u63a5 BB \u673a")
        if n is None:
            why.append(v)
        elif n != 0:
            why.append(v)
    # ⑥值守栈：n=6，只要这一格在，结论行以外还要求它说"栈完整"
    v = cells.get(6)
    if v is not None and u"\u6808\u5b8c\u6574" not in v:
        why.append(v)
    elif v is None:
        why.append(u"\u6ca1\u8bfb\u5230\u503c\u5b88\u6808\u90a3\u4e00\u683c")
    # ⑩推广：n=10，两腿全无/只收不发 都得是 0 才算真接上了
    v = cells.get(10)
    if v is not None:
        for k in (u"\u4e24\u817f\u5168\u65e0", u"\u53ea\u6536\u4e0d\u53d1"):
            n = num_after(v, k)
            if n is None:
                why.append(v)
                break
            if n != 0:
                why.append(v)
                break
    return (bool(why), why, concl, cells, wait)


def logline(stamp, s):
    with io.open(os.path.join(LOGDIR, "_runner_%s.log" % stamp), "a",
                 encoding="utf-8", newline="\n") as fh:
        fh.write(s + "\n")


def note_eyes(red, why, concl, tag):
    u"""红⇒写待看，绿⇒只在**由红转绿**时写一条"已回"。文件本身保持小而稀。"""
    st = os.path.join(LOGDIR, "_needs_state.json")
    try:
        prev = json.load(io.open(st, encoding="utf-8")).get("red")
    except Exception:
        prev = None
    if prev is red and red is False:
        return False
    with io.open(st, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"red": red, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                             "tag": tag}, ensure_ascii=False))
    if not red:
        with io.open(NEEDS, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(u"%s 已回绿：%s\n" % (time.strftime("%H:%M:%S"), concl or GREEN))
        return True
    with io.open(NEEDS, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(u"%s 要人看 %s\n" % (time.strftime("%H:%M:%S"),
                                    u"；".join(why[:4]) if why else u"（判据未读到）"))
        fh.write(u"    档=%s\n" % tag)
    return True


def _alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except Exception:
        return True
    return True


def claim():
    """抢单实例锁：锁里那个 pid 还活着就退出（陈旧锁/坏锁当作没有）。"""
    if os.path.exists(LOCK):
        try:
            pid = int(json.load(io.open(LOCK, encoding="utf-8")).get("pid", 0))
        except Exception:
            pid = 0
        if pid and pid != os.getpid() and _alive(pid):
            return False
    with io.open(LOCK, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"pid": os.getpid(), "at": time.strftime("%Y-%m-%d %H:%M:%S")}))
    return True


def past_stop():
    """到点没有？把 STOP 当作一个**绝对时刻**，与取数器 NVR_ROLL 同一形制。

    今晚连踩两次（19:0x，跑批一起来就收工）：
      一、纯钟点字符串比 ⇒ `19:04 >= "1105"` 因 '9'>'1' 判 True；
      二、把钟点当**今天** ⇒ 目标那个 11:05 在今天，而现在已经 19 点，自然"已过"。
    ⇒ STOP 支持 `MMDD-HHMM`（绝对）；只给 `HHMM` 时：**今天该刻未过就用今天、已过就顺延明天**。
    """
    s = STOP
    day = time.localtime()
    if re.match(r"^\d{4}$", s):
        h, m = int(s[:2]), int(s[2:])
        today = time.strftime("%Y-%m-%d")
        cand = time.mktime(time.strptime(today + " %02d:%02d:00" % (h, m), "%Y-%m-%d %H:%M:%S"))
        if cand <= time.time():
            cand += 86400                     # 今天已过 ⇒ 顺延明天同一刻（不跨天对齐，只加一天）
        return time.time() >= cand
    m = re.match(r"^(\d{2})(\d{2})-(\d{2})(\d{2})$", s)
    if not m:
        return False
    mo, da, hh, mi = (int(x) for x in m.groups())
    year = day.tm_year
    try:
        cand = time.mktime(time.strptime("%04d-%02d-%02d %02d:%02d:00" % (year, mo, da, hh, mi),
                                           "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        return False
    return time.time() >= cand





def main():
    if not claim():
        sys.stderr.write(u"已有一枚巡检跑批（锁在），本枚退出\n")
        return 0
    if not os.path.isdir(LOGDIR):
        os.makedirs(LOGDIR)
    arg = sys.argv.index("--minutes") + 1 if "--minutes" in sys.argv else 1
    # 优先 argv；没有就用 env（PATROL_LOOP_MIN）——栈腿只能用 env 传参：
    # `_watch_stack_r1.py` 的 start() 只把 entry[4] 当**档点**塞 argv（`NVR_AT=…`），
    # 它并不转发任何额外参数，所以我加不进 `--minutes 12`，只能走 env。
    minutes = float(sys.argv[arg]) if len(sys.argv) > arg else float(
        os.environ.get("PATROL_LOOP_MIN", "12"))
    stamp = time.strftime("%Y%m%d")
    n = 0
    while True:
        if past_stop():
            logline(stamp, u"%s 到 STOP=%s，跑批收工" % (time.strftime("%H:%M:%S"), STOP))
            return 0
        n += 1
        out = os.path.join(LOGDIR, "round_%s_%d_%03d.txt" % (stamp, os.getpid(), n))
        try:
            r = subprocess.run([sys.executable, PATROL], capture_output=True, timeout=900,
                               cwd=HERE, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            body = (r.stdout or b"") + (r.stderr or b"")
            io.open(out, "wb").write(body)
            txt = (r.stdout or b"").decode("utf-8", "replace")
            line = ""
            for l in txt.splitlines():
                if l.startswith(u"\u2460") or l.startswith(u"\u7ed3\u8bba"):
                    line = l
            red, why, concl, _cells, _wait = judge(txt)
            if r.returncode != 0:
                red, why = True, [u"\u5de1\u903b rc=%d" % r.returncode] + why
            logline(stamp, u"%s rc=%d%s \u6863=%s \uff5c %s"
                    % (time.strftime("%H:%M:%S"), r.returncode,
                       u"\u3010\u7ea2\u3011" if red else u"", os.path.basename(out), concl or line))
            if _wait:
                why = list(why) + [u"等单不占红位：%s" % _wait[0]]
            if note_eyes(red, why, concl, os.path.basename(out)):
                logline(stamp, u"%s \u5f85\u770b\u6863\u5df2\u5199\uff1a%s"
                        % (time.strftime("%H:%M:%S"),
                           u"\u7ea2" if red else u"\u7531\u7ea2\u8f6c\u7eff"))
        except Exception as e:
            logline(stamp, u"%s \u8dd1\u5931\u8d25\uff1a%s: %s" % (time.strftime("%H:%M:%S"),
                                                    e.__class__.__name__, str(e)[:80]))
            note_eyes(True, [u"\u8dd1\u6279\u5f02\u5e38\uff1a%s" % e.__class__.__name__], u"",
                      os.path.basename(out))
        time.sleep(minutes * 60.0)


if __name__ == "__main__":
    sys.exit(main())
