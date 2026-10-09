# -*- coding: utf-8 -*-
"""`_sentinel_keepalive_r1.py` 的红/绿对照自测（含一次真实的「起一支再收掉」）。

为什么要有它：续跑器的价值全在「认得出有没有现支」这一格——认错会起两支（两份日志、双倍 ls-remote），
认漏则一支都不起（整夜没人盯）。这两种失败都得在上线前当场看到。

用法：PYTHONIOENCODING=utf-8 python _sentinel_keepalive_selftest_r1.py
边界：真起的那一支只活几秒，验完按 PID 收掉；不碰自动轮、不碰号令者的助手。
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import _sentinel_keepalive_r1 as K


def check(name, got, want):
    ok = want in str(got)
    print("%-34s %s（实读 %s）" % (name, "对" if ok else "错", got))
    return ok


def main():
    res = []
    now = time.time()
    stop_at = now + 3600
    res.append(check("决策：有现支就等", K.decide(["1234"], now, stop_at), "wait"))
    res.append(check("决策：没现支就起", K.decide([], now, stop_at), "launch"))
    mins = K.decide([], now, stop_at)[1]
    res.append(check("起的分钟数按剩余算", str(mins), "60"))
    res.append(check("决策：到点收工", K.decide([], stop_at + 5, stop_at), "stop"))
    res.append(check("到点就算有现支也收工", K.decide(["1"], stop_at + 5, stop_at), "stop"))
    res.append(check("剩余不足 5 分钟兜成 5", str(K.decide([], stop_at - 30, stop_at)[1]), "5"))

    before = K.instances()
    print("现支（真查）：%s" % (before or "无"))
    K.launch(6)
    time.sleep(12)
    after = K.instances()
    print("起一支之后：%s" % after)
    res.append(check("真起一支后数量 +1", "%d->%d" % (len(before), len(after)), "%d->%d" % (len(before), len(before) + 1)))
    new = [p for p in after if p not in before]
    for p in new:
        subprocess.run(["powershell", "-NoProfile", "-Command", "Stop-Process -Id %s -Force" % p],
                       capture_output=True, text=True, timeout=60)
    time.sleep(6)
    back = K.instances()
    print("收掉后：%s" % (back or "无"))
    res.append(check("收掉后回到原状", "%d" % len(back), "%d" % len(before)))
    # 收工时刻新增的「跨天」形制：objective 要值守到明天 11:00，旧写法只认当天，过午夜就自己收工
    _t1 = K.stop_today("2335")
    _t2 = K.stop_today("1004-1100")
    res.append(check("当天形制仍是今天 23:35", time.strftime("%H:%M", time.localtime(_t1)), "23:35"))
    res.append(check("跨天形制解析成 10-04 11:00", time.strftime("%m-%d %H:%M", time.localtime(_t2)), "10-04 11:00"))
    res.append(check("跨天必须晚于当天（不许倒退）", str(_t2 > _t1), "True"))
    print("PASS %d/%d" % (sum(1 for x in res if x), len(res)))
    if not all(res):
        print("FAIL %d 条" % (len(res) - sum(1 for x in res if x)))
        return 1
    print("认支、起支、收工三形制都对，且真起的那支能被按 PID 收掉 ⇒ 续跑器可以上线。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
