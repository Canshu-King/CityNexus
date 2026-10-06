"""额度死亡检测：区分"她在等验收"与"她被 Qoder 日额度掐死了"。

23:06 起 B、23:31 F、23:34 D 依次吐出同一句
`You've reached your daily usage limit for Chat. Come back tomorrow to continue working with me.`
—— 这种停摆**敲门是没用的**（消息只会排进一个已经起不来的回合），
而且额度是全账号共享的，所以剩下的车道会一个一个跟着撞墙。
值守必须能一眼分开这两种 idle。

判据：只看该会话**最后一条 assistant 文本**（不看 user 条目——我自己的敲门里可能引用过这句话，
这条坑今晚踩过一次）。命中额度字样 ⇒ QUOTA_DEAD。

用法：python quota_check.py ;  python quota_check.py --selftest
"""
import glob
import io
import json
import os
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LANES = {
    "494abfd7": "包工头",
    "8ccd71d8": "F",
    "aad2d1f2": "HJ-P3",
    "e345b9d6": "D",
    "c01d72a3": "B",
    "d2305848": "E",
    # 09-26 凌晨新开的工具车道（06:48 发现这把尺的名册也漏了它们 —— 同一个 bug 的第三处）
    "a17ae861": "S3",
    "8e094dec": "S1",
    "d9e2c9ae": "S2",
    "1d64acf5": "S4", "352ef353": "N1", "9759f1ac": "N2"}
# 必须用**官方整句**，不能用 "usage limit" 这种短词：
# 我自己在敲门/日志里引用过这句话，短词会把"提到额度"误判成"被额度掐死"（自检第二例就是这条反控）。
NEEDLES = ["reached your daily usage limit"]


def last_assistant(path, back=2_500_000):
    with io.open(path, "rb") as f:
        f.seek(0, 2)
        sz = f.tell()
        f.seek(max(0, sz - back))
        chunk = f.read()
    last = ""
    for line in chunk.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line.decode("utf-8", "replace"))
        except Exception:
            continue
        m = r.get("message") or {}
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        parts = []
        if isinstance(c, str):
            parts = [c]
        elif isinstance(c, list):
            parts = [b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"]
        t = " ".join(x for x in parts if x).strip()
        if t:
            last = t
    return last


def is_quota_dead(text):
    low = (text or "").lower()
    return any(n in low for n in NEEDLES)


def selftest():
    cases = [
        ("正控 官方原话", is_quota_dead("You've reached your daily usage limit for Chat. Come back tomorrow to continue working with me."), True),
        ("反控 我自己的敲门里引用了这句话（在 user 条目里，不该被读到）", is_quota_dead("提醒：如果看到 daily usage limit 请等重置"), False),
        ("反控 正常收尾", is_quota_dead("ORD-0315 交完并验证过了，等号令者验收。"), False),
        ("反控 空文本", is_quota_dead(""), False),
    ]
    bad = 0
    for name, got, want in cases:
        ok = (got == want)
        print("  %-56s got=%-5s want=%-5s %s" % (name[:56], got, want, "OK" if ok else "FAIL"))
        bad += 0 if ok else 1
    # 关键一条：needle 不能匹配"引用式"句子 —— 上面第二例就是它的反控
    print("selftest %s (%d/%d)" % ("PASS" if bad == 0 else "FAIL", len(cases) - bad, len(cases)))
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    now = time.time()
    dead = 0
    for key, name in LANES.items():
        ps = glob.glob(os.path.join(BASE, key + "*.jsonl"))
        if not ps:
            print("  %-6s NO FILE" % name)
            continue
        p = max(ps, key=os.stat)
        idle = (now - os.stat(p).st_mtime) / 60.0
        t = last_assistant(p)
        if is_quota_dead(t):
            dead += 1
            print("  QUOTA_DEAD %s(%s) idle=%.1fm —— 敲门无效，只有用户能解（充值/换档/等重置）" % (name, key, idle))
        else:
            print("  %-6s(%s) idle=%5.1fm ok" % (name, key, idle))
    print("quota_dead=%d/%d" % (dead, len(LANES)))
    return 1 if dead else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
