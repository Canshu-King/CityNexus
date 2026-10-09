"""Qoder 车队值守（Codex 已交还用户）。每轮一行：六条会话距上次写入的分钟数；
任何一条超过 IDLE_FLAG 分钟就顺手把它最后一条 assistant 文本尾巴抄进日志，
这样下一拍的我不用重新调用就能判断是"交完单等验收"还是"死尾"。

用法：python qoder_watch.py <轮数> <间隔秒>
"""
import glob
import io
import json
import os
import re
import sys
import time
import datetime

_STAMP = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LANES = {
    "494abfd7": "包工头",
    "8ccd71d8": "F",
    "aad2d1f2": "HJ-P3",
    "e345b9d6": "D",
    "c01d72a3": "B",
    "d2305848": "E",
    "a17ae861": "S3", "8e094dec": "S1", "d9e2c9ae": "S2", "1d64acf5": "S4",
}
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "watch_qoder.log")
IDLE_FLAG = 20.0


def path_of(key):
    p = glob.glob(os.path.join(BASE, key + "*.jsonl"))
    return max(p, key=os.path.getmtime) if p else None


def age_min(key):
    p = path_of(key)
    if not p:
        return -1.0
    return (time.time() - os.stat(p).st_mtime) / 60.0


def tail_text(key, limit=260):
    """最后一条 assistant 文本（只看最后一条，避免把我自己的敲门文字当成它的输出）。"""
    p = path_of(key)
    if not p:
        return ""
    try:
        with io.open(p, "rb") as f:
            f.seek(0, 2)
            sz = f.tell()
            f.seek(max(0, sz - 900000))
            chunk = f.read()
    except Exception as e:
        return "<read_err %s>" % e
    last = ""
    for line in chunk.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line.decode("utf-8", "replace"))
        except Exception:
            continue
        m = r.get("message") or {}
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        parts = []
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text":
                    parts.append(b.get("text", ""))
        t = " ".join(parts).strip()
        if t:
            last = t
    return last.replace("\r\n", " / ").replace("\n", " / ")[:limit]


def ledger_line():
    """顺手报一句账本远端体积（独立哨兵，见 ledger_guard.py 头注）。"""
    try:
        p = os.popen('python -X utf8 "%s" 2>&1' % os.path.join(HERE, "ledger_guard.py"))
        out = p.read().strip()
        p.close()
        return out.splitlines()[-1] if out else "<no output>"
    except Exception as e:
        return "<ledger_guard_err %s>" % e


def run_pending():
    """账本点名了她、她却在睡觉 —— 这类才值得敲（判据见 pending_check.py，自带 4 向自检）。"""
    try:
        p = os.popen('python -X utf8 "%s" 2>&1' % os.path.join(HERE, "pending_check.py"))
        out = p.read()
        p.close()
    except Exception as e:
        return "<pending_check_err %s>" % e, []
    cands = [l.strip() for l in out.splitlines() if "WAKE_CANDIDATE" in l or "DECLINED" in l]
    tail = [l for l in out.splitlines() if l.startswith("candidates=")]
    return (tail[0] if tail else "?"), cands


def run_fleet():
    """名册自动发现（写死六条会漏掉号令者半夜新开的工具车道）。返回 (摘要行, 需要看的行)。"""
    try:
        p = os.popen('python -X utf8 "%s" 2>&1' % os.path.join(HERE, "fleet_state.py"))
        out = p.read()
        p.close()
    except Exception as e:
        return "<fleet_state_err %s>" % e, []
    lines = out.splitlines()
    stale = [l.strip() for l in lines if "idle>" in l and not l.startswith("idle>20min")]
    summary = lines[0] if lines else "?"
    tail = [l for l in lines if l.startswith("idle>20min")]
    return summary + "  " + (tail[0] if tail else ""), stale


def run_quota():
    """被日额度掐死的车道：敲门无效，只有用户能解。报出来是为了**不去敲**。"""
    try:
        p = os.popen('python -X utf8 "%s" 2>&1' % os.path.join(HERE, "quota_check.py"))
        out = p.read()
        p.close()
    except Exception as e:
        return ["<quota_check_err %s>" % e]
    return [l.strip() for l in out.splitlines() if "QUOTA_DEAD" in l or l.startswith("quota_dead=")]


def run_inbox():
    """LEDGER_SINGLE_WRITER_V1 之后，车道交付要先过号令者的收件箱代插——那是唯一瓶颈。"""
    try:
        p = os.popen('python -X utf8 "%s" 2>&1' % os.path.join(HERE, "inbox_check.py"))
        out = p.read()
        p.close()
    except Exception as e:
        return "?", ["<inbox_check_err %s>" % e]
    lines = out.splitlines()
    back = [l.strip() for l in lines if "INBOX_BACKLOG" in l]
    return (lines[0] if lines else "?"), back


def prev_stamp():
    """上一拍的时间戳，用来发现**我自己**的盲区（01:13 那批静默死掉，86 分钟没人发现）。"""
    try:
        with io.open(LOG, "rb") as f:
            f.seek(0, 2)
            sz = f.tell()
            f.seek(max(0, sz - 20000))
            tail = f.read().decode("utf-8", "replace")
        for line in reversed(tail.splitlines()):
            s = line.strip()
            m = _STAMP.match(s)
            if m:
                return m.group(1)
    except Exception:
        return None
    return None


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    gap = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    for i in range(rounds):
        p = prev_stamp()
        if p:
            try:
                pt = time.mktime(time.strptime(p, "%Y-%m-%d %H:%M:%S"))
                mins = (time.time() - pt) / 60.0
                if mins > 2.5 * (gap / 60.0):
                    with io.open(LOG, "a", encoding="utf-8", newline="\n") as f:
                        f.write("!!! WATCH_GAP 上一拍 %s（%.0f 分钟前，节奏应为 %d 分钟）⇒ 中间是盲区，别把'没记录'当'没出事'\n"
                                % (p, mins, gap // 60))
            except Exception:
                pass
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cols, flags = [], []
        for k, n in LANES.items():
            a = age_min(k)
            cols.append("%s:%.1fm" % (n, a))
            if a > IDLE_FLAG:
                flags.append((k, n, a))
        block = "[%s] %s" % (now, " ".join(cols))
        for k, n, a in flags:
            block += "\n   IDLE>%.0f %s(%s) %.1fm 尾句: %s" % (IDLE_FLAG, n, k, a, tail_text(k))
        if i % 3 == 0:
            block += "\n   " + ledger_line()
        fs = run_fleet()
        block += "\n   " + fs[0]
        if len(fs[1]) > 6:
            block += "\n   名册里有 %d 条 idle>20 分钟（超过写死名册的 6 条 ⇒ 有新车道要认）" % len(fs[1])
        qd = run_quota()
        if qd:
            block += "\n   " + "\n   ".join(qd)
        ib = run_inbox()
        if ib[1]:
            block += "\n   " + ib[0] + "\n   " + "\n   ".join(ib[1])
        pc = run_pending()
        if pc[1]:
            block += "\n   " + "\n   ".join(pc[1])
        with io.open(LOG, "a", encoding="utf-8", newline="\n") as f:
            f.write(block + "\n")
        print(block, flush=True)
        if i + 1 < rounds:
            time.sleep(gap)


if __name__ == "__main__":
    main()
