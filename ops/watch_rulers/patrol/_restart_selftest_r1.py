# -*- coding: utf-8 -*-
"""`_restart_watch_r1.py` 的红/绿对照自测（合成流水，绝不碰真会话目录）。

09:52 与 13:22 两拍都是「停在额度 17｜在写 0」，13:31 我又实测到 6 条车道停在「daily usage limit」
那句上、号令者的复工叫醒没点到它们。探测器现在多了一路 `停在额度字样且没人接`。
但它在 13:37 之后读出来是 0 —— 0 有两种可能：真的没人卡着，或者这一路根本不会响。
所以放两份合成流水：一份必须红（尾是额度句、没人接），一份必须绿（尾是额度句，但之后有叫醒、也有回话）。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "_fixture_proj")
PYEXE = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUOTA = "You've reached your daily usage limit for Chat. Come back tomorrow to continue working with me."
WAKE = u"【额度已回 —— 全员复工】 你手上是 **ORD-0900**：继续。"


def rec(role, txt, kinds="text", ts=None):
    ts = ts or time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    return json.dumps({"timestamp": ts, "message": {"role": role, "content": [{"type": kinds, "text": txt}]}},
                      ensure_ascii=False)


def build():
    if not os.path.isdir(FIX):
        os.makedirs(FIX)
    for old in os.listdir(FIX):
        os.remove(os.path.join(FIX, old))
    now = time.time()
    # 红件：只有额度那句，之后没人接
    a = os.path.join(FIX, "aaaa1111-0000-0000-0000-000000000001.jsonl")
    io.open(a, "w", encoding="utf-8", newline="\n").write(rec("assistant", QUOTA) + "\n")
    # 绿件：额度句 → 叫醒 → 车道回了 assistant
    b = os.path.join(FIX, "bbbb2222-0000-0000-0000-000000000002.jsonl")
    io.open(b, "w", encoding="utf-8", newline="\n").write(
        "\n".join([rec("assistant", QUOTA), rec("user", WAKE), rec("assistant", u"收到，接着跑 ORD-0900。")]) + "\n")
    for f in (a, b):
        os.utime(f, (now - 4 * 3600, now - 4 * 3600))
    return a, b


def main():
    a, b = build()
    env = dict(os.environ, RESTART_PROJ=FIX, PYTHONIOENCODING="utf-8")
    r = subprocess.run([PYEXE, os.path.join(HERE, "_restart_watch_r1.py"), "720"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, cwd=HERE, timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    head = re.search(u"在场会话（最近 [\d.]+ 分钟动过）(\d+) 条｜被叫醒过 (\d+) 条｜叫醒后已回话 (\d+) 条｜叫醒后仍未回话 (\d+) 条｜停在额度字样且没人接 (\d+) 条", out)
    fails = []
    if not head:
        fails.append(u"汇总行没解析出来（探测器格式变了？自动轮那档的正则要一起改）\n" + out[:300])
    else:
        live, woke, replied, dark, stuck = [int(x) for x in head.groups()]
        print(u"读到：在场 %d｜叫醒 %d｜已回 %d｜未回 %d｜停在额度且没人接 %d" % (live, woke, replied, dark, stuck))
        if live != 2:
            fails.append(u"在场应为 2，实读 %d" % live)
        if stuck != 1:
            fails.append(u"「停在额度且没人接」应为 1（红件 aaaa1111），实读 %d ⇒ 这一路不会响，等于没装" % stuck)
        if replied != 1:
            fails.append(u"「叫醒后已回话」应为 1（绿件 bbbb2222），实读 %d" % replied)
    if u"aaaa1111" not in out:
        fails.append(u"红件没被逐条列出（清单里没有 aaaa1111）")
    if fails:
        print(u"FAIL %d 条：" % len(fails))
        for x in fails:
            print(u"   - " + x)
        return 1
    print(u"PASS：红的真响了（停在额度且没人接 1 条并逐条列出），绿的没误响（叫醒＋回话那份判为已接）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
