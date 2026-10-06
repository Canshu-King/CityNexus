# -*- coding: utf-8 -*-
"""静默车道分诊（只读）：机器睡了一觉之后，谁是真的停下、谁是干完没单。

为什么要这张尺：2026-09-29 15:47–18:33 这台机休眠了 2 小时 46 分（我自己的发帖调用
也被冻在同一段时间里），醒来后 mtime 算出的「静默分钟」把休眠期一并算进去了，
拿它当「这车道偷懒 3 小时」会误判。所以这里同时报三个数：
  1) mtime 静默（含休眠）；2) 扣掉休眠窗之后的静默；3) 末条到底是不是错误终态。
判「停没停」只看流水，不看进程、不看端口。
"""
import io
import json
import os
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
TAIL = 400 * 1024
# 本轮实测的休眠窗（起点＝我这台机最后一次有活动的 15:47 前后，终点＝18:33）
SLEEP_FROM = "15:45"
SLEEP_TO = "18:34"

NICKS = {
    "a68b0631": "rel", "1d64acf5": "S4", "e4f3490f": "道0370", "be19052c": "dt",
    "3b65af59": "map", "bac10f40": "AI", "9759f1ac": "N2", "904a042d": "Q",
    "49fe0d7b": "N3", "8ac89982": "R0417", "4033270f": "0383", "1ba48dbf": "newlane",
    "6a150e1e": "newlane2", "9cc37e57": "0421", "2d2d7428": "0441", "a6b95d59": "DSH",
    "8e5245f0": "道0369", "da46954a": "新车道", "e766b154": "新车道472",
}


def tail_lines(p):
    n = os.path.getsize(p)
    with io.open(p, "rb") as f:
        f.seek(max(0, n - TAIL))
        blob = f.read().decode("utf-8", "replace")
    return blob.split("\n")


def last_records(p):
    asst = None
    last_type = None
    last_ts = None
    err = None
    for line in tail_lines(p):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        ts = o.get("timestamp")
        if isinstance(ts, (int, float)) and ts > 1e12:
            last_ts = ts / 1000.0
        t = o.get("type")
        if t in ("user", "assistant"):
            last_type = t
        if t == "assistant":
            m = o.get("message") or {}
            txt = "".join(x.get("text", "") for x in (m.get("content") or []) if isinstance(x, dict))
            if txt.strip():
                asst = txt.strip().replace("\n", " ")
        if o.get("type") in ("user", "assistant"):
            s = json.dumps(o, ensure_ascii=False)[:1200]
            hit = ("isApiErrorMessage" in s) or ("daily usage limit" in s) or ("NetworkAttemptError" in s)
            if hit:
                err = (o.get("type") or "?") + ": " + s[:150]
            else:
                err = None   # 只有**最后一条**角色记录本身就是错，才算停在错上
    return asst, last_type, last_ts, err


def main():
    now = time.time()
    sleep_gap = 0.0
    try:
        y, mo, d = time.localtime(now)[:3]
        f = time.mktime(time.strptime("%04d-%02d-%02d %s" % (y, mo, d, SLEEP_FROM), "%Y-%m-%d %H:%M"))
        g = time.mktime(time.strptime("%04d-%02d-%02d %s" % (y, mo, d, SLEEP_TO), "%Y-%m-%d %H:%M"))
        sleep_gap = max(0.0, g - f)
    except Exception:
        pass
    print("=== 静默车道分诊 %s（休眠窗 %s–%s ≈ %.0f 分，已从静默里扣掉）" % (time.strftime("%H:%M"), SLEEP_FROM, SLEEP_TO, sleep_gap / 60.0))
    rows = []
    for sid8, nick in NICKS.items():
        cands = [f for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")]
        if not cands:
            print("  %-8s 流水找不到" % nick)
            continue
        p = os.path.join(BASE, cands[0])
        mt = os.path.getmtime(p)
        raw = (now - mt) / 60.0
        net = max(0.0, (now - mt - sleep_gap) / 60.0)
        asst, ltype, lts, err = last_records(p)
        rows.append((net, raw, nick, sid8, ltype, err, asst or ""))
    rows.sort(reverse=True)
    for net, raw, nick, sid8, ltype, err, asst in rows:
        flag = "静" if net >= 12 else "活"
        print("  [%s] %-8s %-8s 净静默 %3.0f 分（含休眠 %3.0f）末条 %s%s"
              % (flag, nick, sid8, net, raw, ltype, "  ※尾带错误字样" if err else ""))
        if net >= 12:
            print("        它在等的下一格（末助手尾 150 字）：%s" % asst[-150:])
    n = len([r for r in rows if r[0] >= 12])
    print("小结：%d 条净静默 >=12 分。『净静默』扣的是本机休眠那 %0.f 分钟——这期间所有窗口一起冻住，"
          "不是车道自己停的；醒来后仍不写的，才是要敲的那批。"  % (sleep_gap / 60.0, n))
    print("边界：只读（流水尾部 mtime 与 JSON 尾记录），0 次写账本、0 次派单、0 次改别人的枝、0 次重启任何进程。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
