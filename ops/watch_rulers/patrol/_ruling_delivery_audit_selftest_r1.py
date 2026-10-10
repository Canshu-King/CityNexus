# -*- coding: utf-8 -*-
"""`_ruling_delivery_audit_r1.py` 的红/绿对照自测（合成流水，绝不碰真会话目录）。

为什么要有它：这枚尺以后要决定「我是不是该替谁把话送到」，判错方向的代价比不判大。
它自己有一个刚踩过两次的坑：流水里的 ISO 时刻带 Z（UTC），本机是 +08——
按本地时间解析会把每条早于基线的旧 user 记录算成「基线之后的新节点」，于是整排假绿「已落到该窗」。
所以四条各验一条，第 4 条就是那枚 UTC 陷阱的回归件。

用法：PYTHONIOENCODING=utf-8 python _ruling_delivery_audit_selftest_r1.py   （全对退 0）
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "_fixture_rda_proj")
PYEXE = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_T = 1790840000.0            # 固定基线：合成件的时刻都绕它摆
def rec(t, typ, text):
    return json.dumps({"type": typ, "timestamp": t,
                       "message": {"role": "user" if typ == "user" else "assistant",
                                   "content": [{"type": "text", "text": text}]}}, ensure_ascii=False)


def build():
    if not os.path.isdir(FIX):
        os.makedirs(FIX)
    for f in os.listdir(FIX):
        os.remove(os.path.join(FIX, f))
    iso_ms = lambda e: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(e))
    cases = {
        "aAAAAAAA": [rec(BASE_T - 600, "assistant", "上一轮的收尾"),
                     rec(BASE_T + 60, "user", u"ORD-0520 按甲落，接着做下一格"),
                     rec(BASE_T + 120, "assistant", "收到，开工")],
        "bBBBBBBB": [rec(BASE_T + 30, "user", u"今天天气不错，随便一句与本题无关的话"),
                     rec(BASE_T + 90, "assistant", "嗯")],
        "cCCCCCCC": [rec(BASE_T + 45, "assistant", "还在自己跑 tool_use，没人跟我说话")],
        "dDDDDDDD": [rec(iso_ms(BASE_T - 900), "user", u"这是基线**之前**的旧裁语（UTC 串，必须被算成旧节点）"),
                     rec(iso_ms(BASE_T + 700), "user", u"这条才在基线之后：ORD-0431 授权开那两行")],
    }
    for sid, rs in cases.items():
        io.open(os.path.join(FIX, sid + "-x.jsonl"), "w", encoding="utf-8", newline="\n").write("\n".join(rs) + "\n")
    io.open(os.path.join(HERE, "_fixture_rda_base.txt"), "w", encoding="utf-8", newline="\n").write("%d\n" % int(BASE_T))


def main():
    build()
    env = dict(os.environ, RDA_PROJ=FIX, RDA_BASE=os.path.join(HERE, "_fixture_rda_base.txt"),
               RDA_OUT=os.path.join(HERE, "_fixture_rda_out.txt"), PYTHONIOENCODING="utf-8")
    r = subprocess.run([PYEXE, os.path.join(HERE, "_ruling_delivery_audit_r1.py"),
                        "aAAAAAAA", "bBBBBBBB", "cCCCCCCC", "dDDDDDDD"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, cwd=HERE, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    want = {
        "aAAAAAAA": u"已落到该窗",
        "bBBBBBBB": u"落到了但判不出内容",
        "cCCCCCCC": u"未落到",
        "dDDDDDDD": u"已落到该窗",
    }
    fails = []
    for sid, exp in want.items():
        line = [l for l in out.split("\n") if l.startswith(sid)]
        if not line:
            fails.append("%s：读数里没有这一行" % sid)
            continue
        if exp not in line[0]:
            fails.append("%s：期望「%s」，实读：%s" % (sid, exp, line[0][:120]))
    # 第 4 条还要验它**没有**把基线前那条旧 UTC 记录当成交付：正文里应引到基线后的那条
    dl = [l for l in out.split("\n") if l.startswith("dDDDDDDD")]
    if dl and u"旧裁语" in dl[0]:
        fails.append("dDDDDDDD 把基线之前的 UTC 旧记录当成了新交付（时区解析回退了）")
    # 槽位形制：节点条数与「多少分钟前」不能互换（上一版就是这里串位，读出了负数分钟）
    al = [l for l in out.split("\n") if l.startswith("aAAAAAAA")]
    if al:
        if u"user 节点 1 条" not in al[0]:
            fails.append("aAAAAAAA 的 user 节点条数印错了：%s" % al[0][:150])
        if re.search(u"（-\\d", al[0]):
            fails.append("aAAAAAAA 的「多少分前」是负数（槽位又串了）：%s" % al[0][:150])
    print(out)
    if fails:
        print("FAIL %d 条：" % len(fails))
        for x in fails:
            print("   - " + x)
        return 1
    print(u"PASS：三态各判对，且带 Z 的旧 UTC 记录没有被误算成基线之后的新节点 ⇒ 这枚尺可以拿去判「话送到没有」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
