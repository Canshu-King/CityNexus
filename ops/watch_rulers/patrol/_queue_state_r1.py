# -*- coding: utf-8 -*-
"""值守 17:10 · 模型排队状态尺：把「这条窗口是卡在排队，还是真的停了」分开量。

用户 17:0x 的现场：截图上写着「模型请求正在排队·预计等待不足 1 分」，并说别的窗口也可能这样。
这一格要紧，是因为**判错方向的代价不对称**：
  - 把「排队」误判成「停了」而去敲门 ⇒ 每条敲门都要再排一次队，等于往堵的地方加水；
  - 把「停了」误判成「排队」而干等 ⇒ 车队整晚静默没人管。
所以判据只用流水里能证的两件事，不看进程也不看界面：
  等模型：最后一个节点**不是** assistant 的正文/tool_use（也就是话已经递上去了、回音还没落纸），
         且文件已经 N 分钟没再写；
  在跑：  最近一次写盘在 2 分钟内；
  说完停：尾部是一条 assistant 正文（它把话说完了就停了）；
  在写工具：尾部是 assistant 的 tool_use 且有对应 tool_result 在后面 ⇒ 它自己在跑东西。

用法：PYTHONIOENCODING=utf-8 python _queue_state_r1.py [静默阈值分钟=3]
边界：只读 jsonl；0 次发送、0 次敲门。它给的是「该不该催」的判据，不是平台的排队深度（那个读不到）。
"""
import glob
import io
import json
import os
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_queue_state_latest.txt")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TAIL = 1200000


def tail_nodes(p):
    """取尾部若干条能解析的记录（倒着读，够判尾部形状就行，不整档扫）。"""
    out = []
    with io.open(p, encoding="utf-8", errors="replace") as f:
        f.seek(max(0, os.path.getsize(p) - TAIL))
        f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def kinds_of(r):
    if r.get("type") not in ("assistant", "user"):
        return []
    c = (r.get("message") or {}).get("content") if isinstance(r.get("message"), dict) else r.get("content")
    ks = []
    if isinstance(c, list):
        for b in c:
            if isinstance(b, dict):
                if b.get("type") == "text" and not (b.get("text") or "").strip():
                    ks.append("text空")
                else:
                    ks.append(b.get("type"))
    elif isinstance(c, str):
        ks.append("str")
    return ks


def classify(p, now, thresh_min):
    mt = os.path.getmtime(p)
    idle = (now - mt) / 60.0
    recs = tail_nodes(p)
    msgs = [r for r in recs if r.get("type") in ("assistant", "user")]
    if not msgs:
        return "读不到正文", idle, "-"
    last = msgs[-1]
    ks = kinds_of(last)
    t = last.get("type")
    if idle <= 2.0:
        return "在跑", idle, ",".join(ks) or t
    if t == "assistant" and "text" in ks:
        return "说完就停", idle, "text"
    if t == "assistant" and "tool_use" in ks:
        return "在跑工具（等结果）", idle, "tool_use"
    if t == "user" and ("tool_result" in ks or "tool_result" in json.dumps(last)[:200]):
        return (u"等模型（结果已递上去）" if idle >= thresh_min else u"刚递结果"), idle, "tool_result"
    if t == "user":
        return (u"等模型（话已递上去）" if idle >= thresh_min else u"刚收到话"), idle, "text"
    return "其它", idle, ",".join(ks) or t


def main():
    thresh = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    now = time.time()
    rows = []
    for p in glob.glob(os.path.join(PROJ, "*.jsonl")):
        sid = os.path.basename(p)[:8]
        if (now - os.path.getmtime(p)) / 3600.0 > 12:
            continue
        try:
            cat, idle, shape = classify(p, now, thresh)
        except Exception as e:
            cat, idle, shape = "读失败", -1.0, type(e).__name__
        rows.append((cat, sid, idle, shape))
    order = [u"在跑", u"刚递结果", u"刚收到话", u"等模型（结果已递上去）", u"等模型（话已递上去）",
             u"在跑工具（等结果）", u"说完就停", u"读不到正文", u"其它", u"读失败"]
    cnt = {}
    for cat, sid, idle, shape in rows:
        cnt.setdefault(cat, []).append((sid, idle, shape))
    lines = [u"_queue_state_r1.py 于 %s｜阈值：静默 >= %.1f 分且尾部不是 assistant 正文 ⇒ 记「等模型」" % (
        time.strftime("%H:%M:%S", time.localtime(now)), thresh)]
    for cat in order:
        if cat not in cnt:
            continue
        v = sorted(cnt[cat], key=lambda x: x[1])
        lines.append(u"%-14s %2d 条：%s" % (cat, len(v), u"、".join(
            u"%s(%.1f分)" % (s, i) for s, i, _sh in v[:12]) + (u"…" if len(v) > 12 else u"")))
    nq = len(cnt.get(u"等模型（结果已递上去）", [])) + len(cnt.get(u"等模型（话已递上去）", []))
    lines.append(u"")
    lines.append(u"合计 12 小时内动过的窗口 %d 条，其中判「等模型」%d 条 ⇒ %s" % (
        len(rows), nq,
        u"这一格现在不能靠敲门解决：每条敲门都要再排一次队，等它自己消化" if nq else u"没有窗口卡在等模型上（停了就是真停）"))
    lines.append(u"边界：平台的排队深度读不到，这里只按「话递上去了没有回音」判；runtimeState 会滞后（16:5x 实测：号令者那栏 updatedAt 还是 13:27），所以一律以 jsonl 为准。")
    out = u"\n".join(lines) + u"\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
