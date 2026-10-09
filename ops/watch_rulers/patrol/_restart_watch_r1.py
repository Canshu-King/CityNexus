# -*- coding: utf-8 -*-
"""值守 05:0x · 软件重启之后「谁被叫醒了、谁还没动」的探测器（只读）。

场景（用户 04:57 说的话）：模型排队 → 用户重启软件 → 车道会话被打断；号令者会给每条车道发一封
「【软件又重启了……这是重启叫醒，不是新单】」。之后可能出现两种情况：
  A 叫醒发出去了，但车道一直没回话（卡在队列里 / 那轮真的掉了）；
  B 有的车道压根没被叫醒到（名单漏人）。
这一枚把这两种分开量，并给每个未动的车道产出一段**可直接粘贴**的第二次叫醒（不新派单、不改单号，
只重述它自己上一条叫醒里的单号与现尖）。

判据：
  · 在场会话＝`projects/D--moodle/*.jsonl` 里 mtime 在最近 WINDOW_MIN 分钟内的（不数历史会话）。
  · 「被叫醒过」＝流水里出现过 `软件又重启` 这条 user 记录（逐字串，不靠标题、不猜 uuid）。
  · 「已回话」＝那条叫醒之后出现过任何 assistant 记录。
  · 「叫醒时刻」＝含该串的最后一条记录的时间戳（跨日靠 ts 本身，不靠文件 mtime）。
边界：只读；不发消息（发消息由值守按规矩另做），不写账本，不动任何人的进程与目录。
"""
import glob
import io
import json
import os
import re
import sys
import time

B = os.environ.get("RESTART_PROJ") or "C:/Users/仓鼠王/.qoder/projects/D--moodle"   # 自测可指到临时目录
SKIP = ("42d1a6fa", "494abfd7")   # 我自己与号令者：叫醒名单里不该出现我们两个
SIGNS = (u"软件又重启", u"额度已回", u"全员复工")   # 05:38 自测抓到的瞎点：探测器原来只认「软件又重启」，
# 而号令者 13:30 那轮复工叫醒写的是「【额度已回 —— 全员复工】」——那一类叫醒它根本认不出来，于是把
# 「已经有人接过」的车道也算成没人接。三个形制都收。
WIN_MIN = float(sys.argv[1]) if len(sys.argv) > 1 else 720.0   # 12 小时：额度潮之后一条车道可以三四小时不落笔
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
now = time.time()


def recs_tail(path, nbytes=1200000):
    fh = io.open(path, "rb")
    fh.seek(max(0, os.path.getsize(path) - nbytes))
    lines = fh.read().decode("utf-8", "replace").split(chr(10))
    fh.close()
    out = []
    for l in lines:
        if not l.strip():
            continue
        try:
            out.append(json.loads(l))
        except Exception:
            pass
    return out


def last_quota(rs):
    """最后一条 assistant 的**正文**记录是不是「daily usage limit / 额度」字样——且它后面不能再有动静。

    22:14 实测到的假红就出在这里：旧版倒着扫到第一条带 text 的 assistant 就返回，
    于是一条**正在跑**的车道（撞过墙、被叫醒、之后一路 tool_use/tool_result）仍被判成「停在额度字样」——
    那一拍名册在写 15 条、这尺却报「停在额度且没人接 12 条」，把整面哨兵顶退过一次（20:31 那回是同一条判据的另一形状）。
    所以判「停在额度」必须要求：**那条正文之后没有任何新节点**（有 tool_use / tool_result 就说明它早就往前走了）。
    """
    idx = None
    for i in range(len(rs) - 1, -1, -1):
        m = rs[i].get("message") if isinstance(rs[i].get("message"), dict) else None
        if not m or m.get("role") != "assistant":
            continue
        c = m.get("content")
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "text" and (x.get("text") or "").strip():
                    idx = i
                    break
        if idx is not None:
            break
        return False
    if idx is None:
        return False
    for r in rs[idx + 1:]:
        m = r.get("message") if isinstance(r.get("message"), dict) else None
        c = m.get("content") if m else None
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") in ("tool_use", "tool_result"):
                    return False        # 正文之后还有工具往返 ⇒ 这条窗在跑，不算撞墙
        if r.get("type") == "user":
            return False                # 有人跟它说过话，也不算
    t = ""
    m = rs[idx].get("message")
    for x in (m.get("content") or []):
        if isinstance(x, dict) and x.get("type") == "text":
            t += x.get("text") or ""
    return (u"daily usage limit" in t) or (u"usage limit" in t) or (u"额度" in t[:120])


def to_ep(ts):
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        v = float(ts)
        return v / 1000.0 if v > 1e11 else v
    if isinstance(ts, str) and ts.isdigit():
        v = float(ts)
        return v / 1000.0 if v > 1e11 else v
    try:
        return time.mktime(time.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    except Exception:
        return None


rows = []
for f in glob.glob(B + "/*.jsonl"):
    id8 = os.path.basename(f)[:8]
    age = (now - os.path.getmtime(f)) / 60.0
    if age > WIN_MIN or id8 in SKIP:
        continue
    rs = recs_tail(f)
    wake_ep = None
    wake_body = ""
    assist_after = None
    for r in rs:
        m = r.get("message") if isinstance(r.get("message"), dict) else None
        if not m:
            continue
        c = m.get("content")
        txt = c if isinstance(c, str) else " ".join(
            (x.get("text") or "") for x in c if isinstance(x, dict)) if isinstance(c, list) else ""
        if m.get("role") == "user" and any(s in txt for s in SIGNS):
            wake_ep = to_ep(r.get("timestamp"))
            wake_body = txt
            assist_after = None
        elif m.get("role") == "assistant" and wake_ep is not None:
            assist_after = to_ep(r.get("timestamp"))
        q = last_quota(lines_all if False else rs)
    rows.append({"id8": id8, "age": age, "wake_ep": wake_ep, "wake": bool(wake_ep),
                 "replied": assist_after is not None, "body": wake_body, "quota_stuck": q,
                 "since_wake": ((now - wake_ep) / 60.0) if wake_ep else None})

rows.sort(key=lambda x: -(x["since_wake"] or 0))
nw = sum(1 for r in rows if r["wake"])
nr = sum(1 for r in rows if r["wake"] and r["replied"])
nq = sum(1 for r in rows if r["quota_stuck"] and not (r["wake"] and r["replied"]))
print("在场会话（最近 %g 分钟动过）%d 条｜被叫醒过 %d 条｜叫醒后已回话 %d 条｜叫醒后仍未回话 %d 条｜停在额度字样且没人接 %d 条" % (
    WIN_MIN, len(rows), nw, nr, nw - nr, nq))
print("\n叫醒后没动过的（按等了多久排序）：")
quiet = [r for r in rows if r["wake"] and not r["replied"]]
for r in quiet:
    mm = re.search(u"你手上是 \\*\\*(ORD-\\d{4}[^*]{0,60})", r["body"])
    tip = re.search(r"`([0-9a-f]{40})`", r["body"])
    print("   %s  等了 %5.1f 分｜单号：%s｜叫醒里给的尖：%s" % (
        r["id8"], r["since_wake"] or -1, (mm.group(1)[:34] if mm else "（叫醒正文里没写单号）"),
        (tip.group(1)[:12] if tip else "-")))
if not quiet:
    print("   无")
print("\n叫醒没发到的（在场但流水里没有那句叫醒）：")
missed = [r for r in rows if not r["wake"]]
for r in missed:
    print("   %s  静默 %5.1f 分" % (r["id8"], r["age"]))
if not missed:
    print("   无（在场会话人人都被叫醒到了）")
print("\n给值守的第二次叫醒草稿（只重述它自己那条叫醒，不新派单；粘贴前请先复核现尖）：")
for r in quiet:
    mm = re.search(u"你手上是 \\*\\*(ORD-\\d{4}[^*]{0,60})", r["body"])
    tip = re.search(r"`([0-9a-f]{40})`", r["body"])
    if r["since_wake"] is not None and r["since_wake"] < 10:
        continue
    print("   给 %s：%s" % (r["id8"], (u"【值守第二次叫醒，仍不是新单】上一条重启叫醒你 %s 分钟没回话。"
                                     u"你手上是 %s；叫醒里给的尖是 %s。看到这条先回一句「在跑」，"
                                     u"再按那条叫醒的形制继续：块落 `D:\\moodle\\_qoder_ledger_inbox\\%s_<HHMM>.md`，"
                                     u"交前自己跑 `claim_coordinate_check_r7.py --text <块> --expect-clean` 取 rc=0。"
                                     % (("%.0f" % r["since_wake"]), (mm.group(1) if mm else "（见上一条叫醒原文）"),
                                        (tip.group(1)[:12] if tip else "-"), r["id8"]))))
print("\n边界：叫醒时刻取的是那条 user 记录里的时间戳；「没回话」不等于「死了」——队列里排着也会这样，"
      "所以要连同 bus/账本一起看它有没有交付痕迹。本脚本 0 发送、0 写盘（除 stdout）。")
