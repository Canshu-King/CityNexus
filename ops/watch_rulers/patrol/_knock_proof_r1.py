# -*- coding: utf-8 -*-
"""敲门送达证明：目标流水里必须出现一条 user 节点含本次标记，且尾行逐字等于 CLOSING_LINE.txt。

回执（send 返回 ok）只证明平台收了，不证明对面读到——所以一律回读 jsonl。
"""
import hashlib
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSING = os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt")
PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"


def epoch_of(ts):
    """时间戳两形都认：ISO 带 Z（UTC，用 timegm）与 epoch（毫秒或秒，按量级判）。"""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        v = float(ts)
        return v / 1000.0 if v > 1e11 else v
    s = str(ts).strip()
    if s.endswith("Z"):
        import calendar
        for f in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return calendar.timegm(time.strptime(s[:-1], f))
            except Exception:
                continue
        return None
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return time.mktime(time.strptime(s[:19], f))
        except Exception:
            continue
    return None


def last_kind_ts(path):
    """文件最后一条记录的 type 与时间——用来分「排队未消费」和「根本没进」。"""
    size = os.path.getsize(path)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        f.seek(max(0, size - 200000))
        data = f.read()
    for line in reversed([x for x in data.split(chr(10)) if x.strip()]):
        try:
            r = json.loads(line)
        except Exception:
            continue
        ts = r.get("timestamp")
        e = epoch_of(ts)
        return u"type=%s 时间=%s｜文件 mtime %s" % (
            r.get("type"), time.strftime("%H:%M:%S", time.localtime(e)) if e else str(ts)[:19],
            time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(path))))
    return u"读不到末条"


def tail_user_texts(path, want_bytes=None):
    size = os.path.getsize(path)
    off = max(0, size - want_bytes)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        if off:
            f.seek(off)
            f.readline()          # 丢掉截断的第一行（off=0 时不能丢，否则少一条记录）
        data = f.read()
    outs = []
    for line in data.split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        m = r.get("message") if isinstance(r.get("message"), dict) else None
        if not m or m.get("role") != "user":
            continue
        c = m.get("content")
        txt = ""
        if isinstance(c, str):
            txt = c
        elif isinstance(c, list):
            txt = u"\n".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
        if txt.strip():
            outs.append((r.get("timestamp"), txt))
    return outs


def payload_carriers(path, want_bytes):
    """把可能承载一记敲门的所有形制都收进来，并标明是哪一形。

    02:34 实测出来的教训：`send_message_to_chat_session` 发出去的话，落到对面流水里是
    **`type=attachment` + `attachment.type="queued_command"` + `prompt[].text`**，
    不是 `message.role=="user"` 的节点。旧版只数 user 节点，于是 01:48 那记明明 02:29:13 已经落进他流水，
    我却连读四次「未落到」——尺瞎了比车道停了更危险，因为它会诱导我重发、或者让人干等。
    """
    size = os.path.getsize(path)
    off = max(0, size - want_bytes)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        if off:
            f.seek(off)
            f.readline()
        data = f.read()
    outs = []
    for line in data.split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        texts = []
        m = r.get("message") if isinstance(r.get("message"), dict) else None
        if m and m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                texts.append((u"user 节点", c))
            elif isinstance(c, list):
                for x in c:
                    if isinstance(x, dict) and x.get("type") == "text":
                        texts.append((u"user 节点", x.get("text") or u""))
                    elif isinstance(x, dict) and x.get("type") == "tool_result":
                        tr = x.get("content")
                        if isinstance(tr, str):
                            texts.append((u"tool_result", tr))
        at = r.get("attachment") if isinstance(r.get("attachment"), dict) else None
        if at:
            kind = u"attachment/%s" % at.get("type")
            pr = at.get("prompt")
            if isinstance(pr, str):
                texts.append((kind, pr))
            elif isinstance(pr, list):
                for x in pr:
                    if isinstance(x, dict) and x.get("text"):
                        texts.append((kind, x["text"]))
            if at.get("text"):
                texts.append((kind, str(at.get("text"))))
        for kind, t in texts:
            if t and t.strip():
                outs.append((kind, r.get("timestamp"), t))
    return outs


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else "494abfd7"
    marker = sys.argv[2] if len(sys.argv) > 2 else u"【值守敲门"
    cands = [p for p in os.listdir(PROJ) if p.startswith(sid) and p.endswith(".jsonl")]
    if not cands:
        print(u"FAIL 找不到会话文件（前缀 %s）" % sid)
        return 1
    path = os.path.join(PROJ, cands[0])
    raw = io.open(CLOSING, "rb").read()
    tail_bytes = raw.replace(b"\r", b"").replace(b"\n", b"")
    tail_txt = tail_bytes.decode("utf-8")
    wb = int(sys.argv[3]) if len(sys.argv) > 3 else 400000
    outs = payload_carriers(path, wb)
    kinds = {}
    for k, _ts, _t in outs:
        kinds[k] = kinds.get(k, 0) + 1
    print(u"{now} 回读 {f}｜尾部承载 {n} 段（读尾部 {wb} B 内）：{br}".format(
        now=time.strftime("%H:%M:%S"), f=cands[0][:13], n=len(outs), wb=wb,
        br=u"、".join(u"%s×%d" % (k, v) for k, v in sorted(kinds.items())) or u"空"))
    hit = None
    for k, ts, t in reversed(outs):
        if marker in t and (k == u"user 节点" or k.startswith(u"attachment/")):
            hit = (k, ts, t)
            break
    weak = None
    for k, ts, t in reversed(outs):
        if marker in t:
            weak = (k, ts, t)
            break
    if hit is None:
        if weak:
            print(u"FAIL：标记只出现在『%s』里（%s）⇒ 那是他读到过文本，不是话送进了这扇窗" % (
                weak[0], time.strftime("%H:%M:%S", time.localtime(epoch_of(weak[1]) or 0))))
        else:
            print(u"FAIL：尾部 %d MB 内没有任何承载含标记『%s』⇒ 这记敲门没落到" % (wb // 1000000, marker))
        for _k, ts, t in outs[-3:]:
            print(u"   最近承载[%s]：%s｜%s" % (
                _k,
                time.strftime("%H:%M:%S", time.localtime(epoch_of(ts) or 0)) if epoch_of(ts) else str(ts)[:22],
                t.replace(chr(10), u" ⏎ ")[:90]))
        print(u"   流水最后一条：%s" % last_kind_ts(path))
        return 1
    kind, ts, t = hit
    e = epoch_of(ts)
    ok_tail = t.rstrip().endswith(tail_txt)
    got = t.rstrip()[-len(tail_txt):].encode("utf-8")
    print(u"PASS 已落到：承载=%s 时刻=%s｜正文 %d 字｜尾行 sha1 %s（对照 %s）⇒ %s" % (
        kind, time.strftime("%H:%M:%S", time.localtime(e)) if e else str(ts)[:19],
        len(t), hashlib.sha1(got).hexdigest(), hashlib.sha1(tail_bytes).hexdigest(),
        u"逐字一致" if ok_tail else u"不一致"))
    if not ok_tail:
        print(u"FAIL 尾行不逐字：贴出实收尾行 → " + t.rstrip()[-120:])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
