# -*- coding: utf-8 -*-
"""值守 15:40 · 裁语送达审计：号令者发出去的那一句，到底有没有落到车道自己的会话里。

为什么要这一枚：今天 15:22 我敲号令者窗时学到的形制是——**回执 200 不等于送达**，
送达的凭据是对方流水里多出一条 `user` 记录。同一条形制反过来也成立：
他若给某条车道发了裁语，那条车道的流水里必须出现一条**晚于裁语书写时刻**的 user 记录；
只写进账本不算（冷车道不会自己重读账本，这是这个夜班反复踩过的坑）。

判据（每条车道各一行的三态）：
  已落到该窗   —— 尾部有晚于基线时刻的 user 记录，且正文里有单号 ORD-### 或裁/落/授权/继续 这类请求形状
  落到了但看不懂 —— 有晚于基线的 user 记录，但正文两类词都没有（照实报，不猜内容）
  未落到        —— 基线之后没有任何 user 记录（只有它自己的 assistant/tool 节点在长）
基线默认取本脚本第一次运行的时刻（落盘存住），所以第二趟之后每一轮都是拿同一把尺量增量。

用法：PYTHONIOENCODING=utf-8 python _ruling_delivery_audit_r1.py [ids…]     （不给 id 就用 _idle_reason 判为等裁语且<=180 分的那批）
边界：只读 jsonl 尾部 3 MB；0 次发送、0 次写账本、0 次改别人的东西。「未落到」不等于他没发——可能发在别的窗或只写进了账本，那一格要另量。
"""
import calendar
import glob
import io
import json
import os
import re
import sys
import time

PROJ = os.environ.get("RDA_PROJ") or r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("RDA_BASE") or os.path.join(HERE, "_ruling_delivery_baseline.txt")
OUT = os.environ.get("RDA_OUT") or os.path.join(HERE, "_ruling_delivery_audit_latest.txt")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TAIL_BYTES = 3 * 1024 * 1024

ASK = re.compile(u"裁|落|授权|继续|开工|下一|按你|你定|要不要|哪一个|指令|派", re.I)
ORD = re.compile(r"ORD-0\d{2,3}")


def baseline():
    if os.path.isfile(BASE):
        v = io.open(BASE, encoding="utf-8").read().strip()
        if v.isdigit():
            return float(v)
    v = time.time()
    io.open(BASE, "w", encoding="utf-8", newline="\n").write("%d\n" % v)
    return v


def records_since(sid8, t0):
    g = glob.glob(os.path.join(PROJ, sid8 + "*.jsonl"))
    if not g:
        return None, None, None
    p = sorted(g, key=os.path.getmtime)[-1]
    with io.open(p, encoding="utf-8", errors="replace") as f:
        try:
            off = max(0, os.path.getsize(p) - TAIL_BYTES)
            f.seek(off)
            if off:                      # 只有真的往后跳过才丢半行；小文件从 0 读时丢掉第一行会漏掉第一条记录
                f.readline()
        except Exception:
            pass
        last_user = None
        n_user = 0
        n_any = 0
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            ts = r.get("timestamp")
            epoch = None
            if isinstance(ts, (int, float)):
                # 这台机器的流水里数字时刻是**毫秒**（1.79e12），但合成件与别的导出可能是秒（1.79e9）——
                # 按量级判，别写死除 1000：写死会把秒当毫秒、每条新记录都算成 1970 年，尺整排假「未落到」。
                v = float(ts)
                epoch = v / 1000.0 if v > 1e11 else v
            elif isinstance(ts, str) and len(ts) >= 19:
                # 两种时刻形制都得认，且 UTC 的 ISO 串**不能**当本地时间解析：这台机器是 +08，
                # 用 mktime 会把每条 07:22:13Z 记成 15:22:13 之后的 8 小时，把「旧节点」算成「基线之后的新节点」。
                s = ts.replace("T", " ")[:19]
                try:
                    if ts.endswith("Z"):
                        epoch = float(calendar.timegm(time.strptime(s, "%Y-%m-%d %H:%M:%S")))
                    else:
                        epoch = time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S"))
                except Exception:
                    epoch = None
            if epoch is None:
                continue
            if epoch <= t0:
                continue
            n_any += 1
            if r.get("type") == "user" or r.get("role") == "user":
                n_user += 1
                m = r.get("message") if isinstance(r.get("message"), dict) else r
                c = m.get("content")
                s = ""
                if isinstance(c, list):
                    s = "".join(b.get("text") or "" for b in c if isinstance(b, dict) and b.get("type") == "text")
                elif isinstance(c, str):
                    s = c
                if s.strip():
                    last_user = (epoch, s.strip())
    return last_user, n_user, n_any


def main():
    ids = [x for x in sys.argv[1:] if x]
    if not ids:
        for l in io.open(os.path.join(HERE, "_idle_reason_latest.txt"), encoding="utf-8", errors="replace"):
            m = re.match(r"^\s*(\S+)\s+静默\s*([\d.]+)分\s+(\S*)", l)
            if m and u"等裁语" in m.group(3) and float(m.group(2)) <= 180:
                ids.append(m.group(1))
    t0 = baseline()
    lines = [u"_ruling_delivery_audit_r1.py 于 %s｜基线时刻 %s（此后新增的节点才算增量）｜候选 %d 条" % (
        time.strftime("%Y-%m-%d %H:%M:%S"), time.strftime("%H:%M:%S", time.localtime(t0)), len(ids))]
    cnt = {u"已落到该窗": 0, u"落到了但判不出内容": 0, u"未落到": 0, u"读不到": 0}
    for sid in ids:
        lu, n_user, n_any = records_since(sid, t0)
        if lu is None and n_any is None:
            cat = u"读不到"
            detail = "（没有这条 id 的流水）"
        elif n_user and lu:
            txt = lu[1]
            has = bool(ORD.search(txt)) or bool(ASK.search(txt))
            cat = u"已落到该窗" if has else u"落到了但判不出内容"
            # 槽位一律具名：上一版这里用 % 位置参数，把「节点条数」印进了「多少分钟前」那一格，
            # 自测里当场读出「15:45:00 前 1 分｜user 节点 -3 条」这种负数——数值没错，排位错了。
            ago_min = (time.time() - lu[0]) / 60.0
            if ago_min < -5:
                ago_note = u"（时刻在未来 %.1f 分——解析或时钟可疑，别当成交付）" % (-ago_min)
            else:
                ago_note = u"（%.1f 分前）" % ago_min
            detail = u"{at}{agenote}｜基线后 user 节点 {n} 条｜正文：{q}".format(
                at=time.strftime("%H:%M:%S", time.localtime(lu[0])),
                agenote=ago_note, n=int(n_user),
                q=txt[:110].replace("\n", " "))
        else:
            cat = u"未落到"
            detail = "基线后共 %d 个新节点，其中 user 0 条 ⇒ 只有它自己在动或完全没动" % (n_any or 0)
        cnt[cat] += 1
        lines.append(u"%-10s %s｜%s" % (sid, cat, detail))
    lines.append(u"")
    lines.append(u"合计：" + u"｜".join(u"%s %d 条" % (k, v) for k, v in cnt.items() if v))
    lines.append(u"边界：判据只看「基线之后有没有一条 user 记录、它正文里有没有单号或请求形状」；"
                u"「未落到」不等于他没发——发在别的窗、或只写进账本，这一格要另量（冷车道不会自己重读账本）。")
    out = u"\n".join(lines) + u"\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
