# -*- coding: utf-8 -*-
"""值守 16:25 · credits 消耗与「今天还能跑到几点」的估算（只读会话流水里的 usage.credits）。

为什么要重做一枚：夜里真正会让车队停摆的不是谁偷懒，是**每日额度墙**（昨天 22:0x 起 17 条车道一起撞墙）。
用户要的是「保证他们至少工作到晚上 23:00」，所以这一格必须能被量出来，而不是等墙到了才发现。

口径（三条都是实测，不猜）：
  1. `usage.credits` 是**每次请求**的值（09-29 之后这台机器就这么写），所以直接对时间窗内的记录求和，
     不再像旧尺那样做差分（旧尺 `credits_burn_r1.py` 的 DAY0 还硬写死在 09-29，跨度算成 64.41 小时）。
  2. 按会话 id8 汇总（文件名前 8 位），fork 不再去重——因为求和的是每条记录自己的 credits，与累计无关。
  3. 「到墙前的累计」用**昨天实测的墙起点**来定：昨天第一次出现「有车道停在 'daily usage limit' 上」的时刻，
     与那一刻之前的昨天累计消耗 —— 那是这台机器实际撞墙时的用量，不是官方额度；所以只做外推、不做承诺。

预算与诚实：整目录是几百 MB 量级，逐枚文件限时（单枚 90 秒、总共 480 秒）；超时就标「截断」，
截断的文件只把已读到的部分计入「下限」，并在读数里写明有多少没读完——绝不拿半份数据当一个总数报。

用法：PYTHONIOENCODING=utf-8 python credits_burn_r2.py [YYYY-MM-DD]
边界：只读 jsonl；0 次发送、0 次写账本、0 次点申请额度。
"""
import glob
import io
import json
import os
import re
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
WATCH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autumn_watch.log")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_credits_burn_latest.txt")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PER_FILE_BUDGET = 90.0
TOTAL_BUDGET = 300.0


def epoch_of(ts):
    if isinstance(ts, (int, float)):
        v = float(ts)
        return v / 1000.0 if v > 1e11 else v
    if isinstance(ts, str) and len(ts) >= 19:
        s = ts.replace("T", " ")[:19]
        try:
            import calendar
            if ts.endswith("Z"):
                return float(calendar.timegm(time.strptime(s, "%Y-%m-%d %H:%M:%S")))
            return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S"))
        except Exception:
            return None
    return None


def scan(day0, day1, budget_left):
    """返回 (每会话 credits, 总 credits, 有消耗的会话数, 截断文件列表, 用掉的秒数)。"""
    per = {}
    total = 0.0
    truncated = []
    t_start = time.time()
    files = sorted(glob.glob(os.path.join(PROJ, "*.jsonl")))
    for p in files:
        if time.time() - t_start > budget_left:
            truncated.append(os.path.basename(p)[:8] + "(整个没读)")
            continue
        sid = os.path.basename(p)[:8]
        fstart = time.time()
        got = 0.0
        try:
            with io.open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if time.time() - fstart > PER_FILE_BUDGET:
                        truncated.append(sid + "(读到一半)")
                        break
                    if '"credits"' not in line:
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    e = epoch_of(r.get("timestamp"))
                    if e is None or not (day0 <= e < day1):
                        continue
                    u = (r.get("message") or {}).get("usage") if isinstance(r.get("message"), dict) else None
                    if isinstance(u, dict) and isinstance(u.get("credits"), (int, float)):
                        got += float(u["credits"])
        except Exception as ex:
            truncated.append(sid + "(读失败 %s)" % type(ex).__name__)
        if got:
            per[sid] = per.get(sid, 0.0) + got
            total += got
    return per, total, len(per), truncated, time.time() - t_start


def first_quota_hit(day0, day1):
    """窗口内第一次「有车道停在每日额度墙上」的时刻——从**会话流水**里取，不从自动轮日志取。

    为什么换来源（16:32 实测到旧写法会算出锚 = 321.7 credits 这种荒谬值）：
    `autumn_watch.log` 的行首只有 [HH:MM:SS] 没有日期，而我这枚尺要把时刻落回某一天，
    跨日就会拿 09-29 夜里或 09-30 凌晨 00:46 那种「一两条车道的零头」当整队撞墙的起点。
    流水里的记录自带 UTC 时间戳，且 'daily usage limit' 是墙的本体语句；
    阈值另加：要**同一天里至少 3 条不同会话**都出现这句，才算一堵墙（一条偶尔撞的不算队墙）。
    """
    hits = {}
    for p in glob.glob(os.path.join(PROJ, "*.jsonl")):
        sid = os.path.basename(p)[:8]
        try:
            with io.open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "daily usage limit" not in line:
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    e = epoch_of(r.get("timestamp"))
                    if e is None or not (day0 <= e < day1):
                        continue
                    hits.setdefault(sid, e)
        except Exception:
            continue
    if len(hits) < 3:
        return None
    return min(hits.values())


def quota_wave(day0, day1):
    """把窗口内出现『daily usage limit』的记录按**本地小时**分桶，返回 {小时: 不同会话数}。

    为什么不是「第一次出现」：16:40 实测——09-30 的 00:13:19 就有 >=3 条会话带着这句话，
    那是前一天晚上那堵墙的尾巴与零星复述，拿它当「昨天什么时候撞墙」会算出「到墙前只用了 12.3 credits」这种荒谬锚。
    真正的一堵墙在小时分布上是一次抬升，所以这里给分布、由读数判峰值。
    """
    per_hour = {}
    for p in glob.glob(os.path.join(PROJ, "*.jsonl")):
        sid = os.path.basename(p)[:8]
        try:
            with io.open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "daily usage limit" not in line:
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    e = epoch_of(r.get("timestamp"))
                    if e is None or not (day0 <= e < day1):
                        continue
                    per_hour.setdefault(time.strftime("%H", time.localtime(e)), set()).add(sid)
        except Exception:
            continue
    return dict((h, len(s)) for h, s in sorted(per_hour.items()))


def main():
    day_s = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y-%m-%d")
    d0 = time.mktime(time.strptime(day_s, "%Y-%m-%d"))
    y0 = d0 - 86400
    now = time.time()
    lines = [u"credits_burn_r2.py 于 %s｜口径：窗口内每条记录的 usage.credits 直接求和（那是每次请求的值）" % time.strftime("%Y-%m-%d %H:%M:%S")]
    yp, ytot, ysess, ytr, ysec = scan(y0, d0, TOTAL_BUDGET)
    ywall = first_quota_hit(y0, d0)
    ywave = quota_wave(y0, d0)
    peak_h = max(ywave.items(), key=lambda x: x[1])[0] if ywave else None
    lines.append(u"昨日 %s：累计 %.1f credits（%d 条会话有消耗，扫了 %.0f 秒%s）｜昨天带『daily usage limit』的会话按小时分布 %s"
                 u"（峰值 %s 时 %d 条）｜首次出现 %s" % (
                     time.strftime("%m-%d", time.localtime(y0)), ytot, ysess, ysec,
                     u"、截断 %d 枚：%s" % (len(ytr), u"、".join(ytr[:4])) if ytr else u"、无截断",
                     u"、".join("%s:%d" % (h, n) for h, n in list(ywave.items())[-10:]) if ywave else "空",
                     peak_h, ywave.get(peak_h, 0) if peak_h else 0,
                     time.strftime("%H:%M:%S", time.localtime(ywall)) if ywall else "无"))
    tp, ttot, tsess, ttr, tsec = scan(d0, now, TOTAL_BUDGET)
    elapsed = (now - d0) / 3600.0
    rate = ttot / elapsed if elapsed > 0 else 0.0
    lines.append(u"今日 %s 至 %s（%.2f 小时）：累计 %.1f credits（%d 条会话有消耗，扫了 %.0f 秒%s）⇒ 速率 %.1f credits/小时" % (
        day_s, time.strftime("%H:%M:%S", time.localtime(now)), elapsed, ttot, tsess, tsec,
        u"、截断 %d 枚：%s" % (len(ttr), u"、".join(ttr[:4])) if ttr else u"、无截断", rate))
    need_s = time.mktime(time.strptime(day_s + " 23:00:00", "%Y-%m-%d %H:%M:%S")) - now
    need_h = max(0.0, need_s / 3600.0)
    if ytot > 0 and rate > 0:
        # 锚只能这样定：官方额度值读不到，但**昨天真实用掉了 ytot**，所以「一天的可用量」至少是 ytot —— 这是下界，不是额度。
        floor = ytot
        left = floor - ttot
        lines.append(u"锚（下界，不是额度）：昨天一天真实用掉 %.1f credits ⇒ 今天至少也能用到这个数；今天已用 %.1f ⇒ 还剩 >= %.1f" % (
            floor, ttot, left if left > 0 else 0.0))
        if elapsed >= 3.0:
            lines.append(u"按今天 %.1f credits/小时外推：**最早可能撞墙 ≈ %s**（还能跑 >= %.1f 小时）；到 23:00 要 %.1f 小时 × %.1f ≈ %.1f credits" % (
                rate, time.strftime("%m-%d %H:%M", time.localtime(now + (left / rate * 3600.0))) if left > 0 else u"已经过了下界",
                (left / rate) if left > 0 else 0.0, need_h, rate, need_h * rate))
            lines.append(u"结论口径：23:00 那一档%s（差 %.1f credits ≈ %.1f 小时的量）；这是外推不是预测，"
                         u"且假设今天剩下的时间用同样速率——真要保 23:00，可行的动作是在 %s 前把关键交付与验收做完，或让部分车道在晚间降速。" % (
                             u"够用得挺紧" if left < need_h * rate else u"够用",
                             max(0.0, need_h * rate - left), max(0.0, need_h * rate - left) / rate,
                             time.strftime("%H:%M", time.localtime(now + (left / rate * 3600.0))) if left > 0 else "现在"))
        else:
            # 深夜/清晨的空心平均会把「昨晚收尾那一波」当成全天常态：10-02 01:38 这一径给出 17:20 撞墙，
            # 而同钟点份额口径量到的是「今天只跑到昨天同一钟点的 51%」——所以窗口不足 3 小时就不许报撞墙时刻。
            lines.append(u"撞墙时刻这一格拒答：今天才跑了 %.2f 小时，样本里全是深夜收尾，拿它当全天速率会把上界当预测。"
                         u"要看钱袋请跑 _burn_curve_r1.py（同一钟点对同一钟点）。" % elapsed)
    else:
        lines.append(u"外推不可得：昨天全天累计或今天的速率有一枚取不到（y=%s rate=%.1f）——不猜额度。" % (ytot, rate))
    top = sorted(tp.items(), key=lambda x: -x[1])[:8]
    names = {"42d1a6fa": u"值守(我)", "494abfd7": u"号令者"}
    lines.append(u"今日用量前 8 条：" + u"、".join(u"%s%s %.0f" % (names.get(s, ""), s, v) for s, v in top))
    out = u"\n".join(lines) + u"\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
