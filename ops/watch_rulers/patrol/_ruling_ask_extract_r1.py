# -*- coding: utf-8 -*-
"""值守 15:16 · 那 10 条「等裁语」的车道各自到底在等什么一句话（只读流水，全文不截断）。

为什么要单独一枚：分类器只说「这条在等裁语」，但**等谁裁**决定下一步归谁——
有的等号令者选一个口径（他一个人就能发），有的其实在等用户点一下（额度、批准、删目录、物理动作），
后者我再怎么贴总线都不会动，得当成"只有用户能解的一格"报出去。所以这里只干一件事：
把每条流水最后一句助手原文取全，抽出里面带请求形状的句子（裁/请/要不要/哪一个/等你/need/should I），
再按「能不能由用户当场解决」分三档：号令者可裁 / 只有用户能做 / 车道自己还欠一步。

用法：PYTHONIOENCODING=utf-8 python _ruling_ask_extract_r1.py [ids…]     （不给 id 就取分类器判为等裁语且静默<=180 分的那些）
边界：只读 jsonl 尾部 2 MB；抽出来的是**它自己写下的句子**，不是我替它总结；一档判定按字面词族，不判它对不对。
"""
import glob
import io
import json
import os
import re
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_ruling_asks_latest.txt")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TAIL_BYTES = 2 * 1024 * 1024

ASK = re.compile(u"裁|请|要不要|哪一个|哪一档|等你|需要你|请给|给一句|一句|是否|该不该|归你|你定|"
                 u"need (one line|a ruling)|should I|awaiting|which (option|band|one)|tell me|your call|approve", re.I)
USER_ONLY = re.compile(u"额度|申请额度|点一下|点击|批准|approve|付费|购买|续费|删(除)?目|清空|重启(软件)?|拔|插|扫码|验证码|手机|键盘|密码|授权码|物理", re.I)
SELF_TODO = re.compile(u"我还欠|还差一|我下一步|待我|我再|下一步我会|我还没", re.I)


def last_assistant_text(sid8):
    g = glob.glob(os.path.join(PROJ, sid8 + "*.jsonl"))
    if not g:
        return None, None
    p = sorted(g, key=os.path.getmtime)[-1]
    with io.open(p, encoding="utf-8", errors="replace") as f:
        try:
            off = max(0, os.path.getsize(p) - TAIL_BYTES)
            f.seek(off)
            if off:                      # 只有真的往后跳过才丢半行；小文件从 0 读时丢掉第一行会漏掉第一条记录
                f.readline()
        except Exception:
            pass
        txts = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            # 这台机器的流水形制：记录的类型在 `type`，正文在 `message.content`（09-30 之后这版换了键名，
            # 我 15:17 第一版按顶层 `role`/`content` 读，结果 10 条全报「读不到原文」——那是我的键名错，不是它们没写）
            if r.get("type") != "assistant" and r.get("role") != "assistant":
                continue
            msg = r.get("message") if isinstance(r.get("message"), dict) else r
            c = msg.get("content")
            if isinstance(c, list):
                s = "".join(b.get("text") or "" for b in c if isinstance(b, dict) and b.get("type") == "text")
                if s.strip():
                    txts.append(s.strip())
            elif isinstance(c, str) and c.strip():
                txts.append(c.strip())
    mt = os.path.getmtime(p)
    if not txts:
        return None, mt
    return txts[-1], mt


def pick_ask(text):
    """从最后一段原文里挑出带请求形状的句子（按句号/换行切，取最靠后的那一/两句）。"""
    sents = [s.strip() for s in re.split(r"(?<=[。！？\n])", text) if s.strip()]
    hits = [s for s in sents if ASK.search(s)]
    return (hits[-2:] if hits else sents[-1:])


def main():
    ids = sys.argv[1:]
    if not ids:
        ids = []
        for l in io.open(os.path.join(HERE, "_idle_reason_latest.txt"), encoding="utf-8", errors="replace"):
            m = re.match(r"^\s*(\S+)\s+静默\s*([\d.]+)分\s+(\S*)", l)
            if m and u"等裁语" in m.group(3) and float(m.group(2)) <= 180:
                ids.append(m.group(1))
    buckets = {u"只有用户能当场解": [], u"号令者可裁": [], u"车道自己还欠一步": [], u"读不到原文": []}
    lines = [u"_ruling_ask_extract_r1.py 于 %s｜取每条流水最后一段助手原文（尾部 2 MB 内），抽出带请求形状的句子" % time.strftime("%Y-%m-%d %H:%M:%S")]
    for sid in ids:
        text, mt = last_assistant_text(sid)
        mins = (time.time() - mt) / 60.0 if mt else -1
        if not text:
            buckets[u"读不到原文"].append(sid)
            lines.append(u"%-10s 静默 %6.1f 分｜读不到原文（尾部 2 MB 内没有助手文本）" % (sid, mins))
            continue
        asks = pick_ask(text)
        joined = u" ".join(asks)
        if USER_ONLY.search(joined):
            cat = u"只有用户能当场解"
        elif SELF_TODO.search(joined):
            cat = u"车道自己还欠一步"
        else:
            cat = u"号令者可裁"
        buckets[cat].append(sid)
        lines.append(u"%-10s 静默 %6.1f 分｜%s" % (sid, mins, cat))
        for a in asks:
            lines.append(u"          └ %s" % a.replace("\n", " ")[:220])
    lines.append(u"")
    lines.append(u"分档合计：" + u"｜".join(u"%s %d 条（%s）" % (k, len(v), u"、".join(v)) for k, v in buckets.items() if v))
    out = u"\n".join(lines) + u"\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
