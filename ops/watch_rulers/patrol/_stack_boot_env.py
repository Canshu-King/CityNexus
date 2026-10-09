# -*- coding: utf-8 -*-
u"""开机起复前先把四枚收工时刻算成"未来"，打印成 set 行给 .bat 用。

为什么要有这一枚（10-06 04:0x 现算）：各腿的 STOP 默认值是**上一班留下的日期形制**——
`_inbox_applier_r2.py` 默认 `1005-1100`、`_stack_keeper_r1.py` 默认 `1004-1100`，
而今天已经是 10-06，这两枚换算出来早已在过去 ⇒ 不带 env 冷启动的那条腿会**一起步就自退**
（"到 STOP 收工"）。现算实测：applier 默认 → 10-05 11:00，距现 −1029 分。
那条腿正是 10-04 为了"收件口不能靠值守记得跑"才装的：静默自退之后，
栈那一格照样会打"栈完整"，只有块龄会说话——这类单向致盲别再留一晚。

为什么不干脆"过期就顺延到明天"：那会把**下班收工**这条真语义抹掉
（keeper 日志里"收工：已到 1004-1100，不再起复"是故意写给人看的）。
所以顺延只发生在**开机这一拍**、由这里显式算给你看，不塞进各腿的默认值里。

输出形制（每行一枚 KEY=VALUE，给 `for /f … do set %%E` 吃）：
  SUP_STOP / SENTINEL_STOP / APPLIER_STOP / STACK_KEEPER_STOP，全部 `MMDD-HHMM` 带日期。
跑法：PYTHONIOENCODING=utf-8 python _stack_boot_env.py [--now "YYYY-MM-DD HH:MM:SS"]
"""
import datetime
import sys

# 每条腿自己的钟点默认（照源码抄，别自创）：supervise 2340 / keepalive·哨兵 2335 /
# 代插腿与看门人跟着 SENTINEL_STOP 走，这里统一给到当日 23:40，保证覆盖整班。
LEG_HM = {
    "SUP_STOP": "2340",
    "SENTINEL_STOP": "2335",
    "APPLIER_STOP": "2340",
    "STACK_KEEPER_STOP": "2340",
}


def now_from(argv):
    if "--now" in argv:
        s = argv[argv.index("--now") + 1]
        return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    return datetime.datetime.now()


def next_occurrence(now, hhmm):
    u"""把 HHMM 落到"今天或明天的这一刻"，取**未来**的那一枚；返回 (datetime, 'MMDD-HHMM')。"""
    h, m = int(hhmm[:2]), int(hhmm[2:])
    today = now.replace(hour=h, minute=m, second=0, microsecond=0)
    cand = today if today > now else today + datetime.timedelta(days=1)
    return cand, u"%02d%02d-%s" % (cand.month, cand.day, hhmm)


def main():
    now = now_from(sys.argv)
    out = []
    for key, hhmm in LEG_HM.items():
        cand, val = next_occurrence(now, hhmm)
        out.append(u"%s=%s" % (key, val))
        sys.stderr.write(u"# %s → %s（本地 %s，距现 %+.0f 分）\n"
                         % (key, val, cand.strftime("%Y-%m-%d %H:%M"),
                            (cand - now).total_seconds() / 60.0))
    print(chr(10).join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
