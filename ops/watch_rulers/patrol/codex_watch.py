"""Codex 侧值守仪表：只读 ~/.codex/thread_history_1.sqlite，判"停没停"。

判据（实测得来，别再用文件 mtime 或目标条）：
- 有 inProgress 回合 => 在干活
- 最近 stop_grace 分钟内起过新回合 => 在自愈（容量墙会自己重试）
- 超过 stop_grace 没有任何新回合 => 真停了，需要敲一次「继续」
"""
import datetime
import sqlite3
import sys
import time

DB = r"C:\Users\仓鼠王\.codex\thread_history_1.sqlite"
TASKS = {
    "01a0c796-5741-75a0-8dc3-ed0af5f54b7c": "Harness",
    "01a0c887-274e-7753-bae5-74e2a34677f9": "MissionA",
    "01a07739-d826-7d73-a755-ee06808e6681": "心跳RevLab",
}
STOP_GRACE_MIN = 12


def hhmmss(secs):
    return datetime.datetime.fromtimestamp(secs).strftime("%H:%M:%S")


def once(grace=STOP_GRACE_MIN):
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True, timeout=8)
    now = time.time()
    out = []
    verdicts = []
    for tid, lab in TASKS.items():
        row = con.execute(
            "select status, started_at, completed_at, coalesce(error_json,'') "
            "from thread_turns where thread_id=? order by started_at desc limit 1",
            (tid,),
        ).fetchone()
        if not row:
            out.append("%s: 无回合" % lab)
            verdicts.append((lab, "NEVER"))
            continue
        st, sa, ca, err = row
        age = (now - sa) / 60.0
        live = (st == "inProgress")
        why = ""
        if "usageLimitExceeded" in err:
            why = "额度墙(不自愈)"
        elif "serverOverloaded" in err:
            why = "容量墙(自愈)"
        elif err:
            why = "err"
        if live:
            v = "在干活"
        elif age <= grace:
            v = "刚红过,在自愈窗口内"
        else:
            v = "停了>=%d分钟" % grace
        out.append("%s: %s %s->%s | %s前起 | %s%s" % (
            lab, st, hhmmss(sa), hhmmss(ca) if ca else "运行中",
            "%.1fm" % age, v, (" " + why) if why else ""))
        verdicts.append((lab, "STOPPED" if (not live and age > grace) else "OK"))
    print("[%s] %s" % (hhmmss(now), "  ||  ".join(out)))
    return verdicts


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    gap = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    for i in range(rounds):
        for lab, v in once(grace=STOP_GRACE_MIN):
            if v == "STOPPED":
                print("   ACTION_NEEDED %s" % lab)
        if i + 1 < rounds:
            time.sleep(gap)


if __name__ == "__main__":
    main()
