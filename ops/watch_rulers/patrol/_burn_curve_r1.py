# -*- coding: utf-8 -*-
"""按小时列出 credits 消耗曲线，用来判「现在这一小时的速率」是不是深夜假象。

口径与 credits_burn_r2.py 相同：逐条 jsonl 记录的 message.usage.credits 直接求和。
为什么不直接用总时长平均：夜里 00:00-02:00 这一段是「昨晚收尾 + 夜班交接」，
拿它外推 21 小时会把晚间高峰当成全天常态。这里改成同一钟点对同一钟点：
昨天 01 时花了多少、今天 01 时花了多少，两边都摆出来才算得准。
"""
import glob
import io
import json
import os
import sys
import time

PROJ = os.environ.get("RDA_PROJ", r"C:\Users\仓鼠王\.qoder\projects\D--moodle")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_burn_curve_latest.txt")
PER_FILE_BUDGET = 12.0
TOTAL_BUDGET = 90.0


def epoch_of(ts):
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        v = float(ts)
        return v / 1000.0 if v > 1e11 else v
    s = str(ts).strip()
    if s.endswith("Z"):
        s = s[:-1]
        import calendar
        for f in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return calendar.timegm(time.strptime(s, f)) + 0.0
            except Exception:
                continue
        return None
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return time.mktime(time.strptime(s[:19], f))
        except Exception:
            continue
    return None


def hourly(day0, day1, budget_left):
    """返回 {小时: credits}、总 credits、有消耗的会话数、截断清单、耗时秒。"""
    per_hour = {}
    sess = set()
    total = 0.0
    truncated = []
    t_start = time.time()
    for p in sorted(glob.glob(os.path.join(PROJ, "*.jsonl"))):
        if time.time() - t_start > budget_left:
            truncated.append(os.path.basename(p)[:8] + "(整个没读)")
            continue
        sid = os.path.basename(p)[:8]
        fstart = time.time()
        try:
            f = io.open(p, encoding="utf-8", errors="replace")
        except Exception as ex:
            truncated.append(sid + "(开不了 %s)" % type(ex).__name__)
            continue
        with f:
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
                    c = float(u["credits"])
                    h = time.localtime(e).tm_hour
                    per_hour[h] = per_hour.get(h, 0.0) + c
                    total += c
                    sess.add(sid)
    return per_hour, total, len(sess), truncated, time.time() - t_start


def day0_of(dstr):
    return time.mktime(time.strptime(dstr + " 00:00:00", "%Y-%m-%d %H:%M:%S"))


def main():
    now = time.time()
    today = time.strftime("%Y-%m-%d", time.localtime(now))
    ystr = time.strftime("%Y-%m-%d", time.localtime(now - 86400))
    t0 = day0_of(today)
    y0 = day0_of(ystr)
    # 只与「昨天同一钟点为止」比：昨天 00:00→hh:59，对上今天 00:00→同一点。
    hh = int(time.strftime("%H", time.localtime(now)))
    cur_end = t0 + (hh + 1) * 3600.0
    y_end = y0 + (hh + 1) * 3600.0      # 昨天同一钟点末；曾用 min(cur_end, y0+86400) 把它夹回昨天全天，得出恒等式假读数

    yh, ytot, yn, ytr, ys1 = hourly(y0, y0 + 86400.0, TOTAL_BUDGET)
    th, ttot, tn, ttr, ts2 = hourly(t0, min(now, t0 + 86400.0), TOTAL_BUDGET)
    ysame, ysame_tot, ysame_n, _, _ = hourly(y0, min(y_end, y0 + 86400.0), TOTAL_BUDGET)
    used_h = max(0.01, (now - t0) / 3600.0)

    lines = []
    lines.append(u"_burn_curve_r1.py 于 %s｜口径：逐条 usage.credits 求和，同一钟点对同一钟点" % (
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))))
    lines.append(u"扫了 %d 秒（昨天 %d 秒 + 今天 %d 秒），截断：%s" % (
        int(ys1 + ts2), int(ys1), int(ts2),
        (u"、".join((ytr + ttr)[:6]) if (ytr or ttr) else u"无")))
    lines.append(u"")
    lines.append(u"今天 %s 至 %s（%.2f 小时）：累计 %.1f credits、%d 条会话有消耗" % (
        today, time.strftime("%H:%M", time.localtime(now)), used_h, ttot, tn))
    lines.append(u"  逐小时：" + u" ".join(u"%02d时%.0f" % (h, th[h]) for h in sorted(th)))
    lines.append(u"昨天 %s 全天：累计 %.1f credits、%d 条会话有消耗" % (ystr, ytot, yn))
    lines.append(u"  逐小时：" + u" ".join(u"%02d时%.0f" % (h, yh[h]) for h in sorted(yh)))
    lines.append(u"")
    # 关键判据：拿「昨天同钟点为止的用量」当作今天到同一点的参照，比全天空心平均更不容易被深夜样本骗。
    if ysame_tot > 0 and ytot > 0:
        share = ttot / ysame_tot
        proj_full = ytot * share
        rate = ttot / used_h
        need_h = max(0.0, (day0_of(today) + 23.0 * 3600.0 - now) / 3600.0)
        lines.append(u"同钟点份额：今天 00:00→%02d:39 用 %.1f，昨天同一段用 %.1f ⇒ 今天跑到昨天的 %.0f%%" % (
            hh, ttot, ysame_tot, share * 100.0))
        lines.append(u"按同钟点形状外推今天全天：昨天全天 %.1f × %.2f ≈ %.1f credits" % (
            ytot, share, proj_full))
        lines.append(u"  ——这一条是外推不是预测：它假设今天的钟点分布与昨天同形；"
                    u"若白天有人补跑或夜里提前收工，份额会变。")
        lines.append(u"钱袋下界：昨天真实花掉 %.1f 才撞墙 ⇒ 今天的钱袋至少这么宽。"
                    u"外推的 %.1f %s ⇒ %s" % (
                        ytot, proj_full,
                        (u"≤ 下界" if proj_full <= ytot else u"> 下界（超支 %0.f）" % (proj_full - ytot)),
                        (u"照今天这个节奏，23:00 之前不像会比昨天更早见底"
                         if proj_full <= ytot else
                         u"照今天这个节奏会在 23:00 前撞墙，缺口约 %.0f credits（≈ %.1f 小时的量）" % (
                             proj_full - ytot, (proj_full - ytot) / rate if rate > 0 else 0.0))))
        lines.append(u"另一口径（此刻别看它）：拿今天到现在的空心平均 %.1f credits/小时，"
                    u"若一直跑满到 23:00 是 %d 小时 × %.1f ≈ %.1f credits，比昨天钱袋 %.1f 还多 %.1f "
                    u"——那是假设全天不停，而深夜样本本就偏高（昨天 00–01 时花 %.1f、今天这段花 %.1f），"
                    u"所以这条只能当上界，不能当成撞墙时刻。" % (
                        rate, int(need_h), rate, need_h * rate, ytot,
                        need_h * rate - ytot, ysame_tot, ttot))
    else:
        lines.append(u"同钟点对照不可得：昨天那一段读到 0 credits，说明这份日志里昨天此刻还没开跑——不猜今天几点见底。")
    out = u"\n".join(lines) + u"\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
