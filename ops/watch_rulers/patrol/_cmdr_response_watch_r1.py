# -*- coding: utf-8 -*-
"""值守 15:15 · 「号令者有没有回应那两贴」观察器（只读，早退条件是动作不是等待）。

为什么要有它：15:05 那贴给了「先落这 3 枚零互斥候选」，15:12 那贴给了「10 条车道各等一句裁语」。
这两步都只能他做（权威线单写者、裁语权在他），所以我不能靠自己动手来确认链路通不通——
只能把「他动了没有」变成一条可观测的判据，动了我立刻记时刻，没动我按点升级报警。

三个早退判据（任一为真即退，并把现场落进日志）：
  1 权威尖离开了基线那枚 sha           ⇒ 他开始落地了
  2 今日入账的块数比基线多              ⇒ 车道重新交得上件（裁语生效）
  3 名册「在写」升到 >= 6 条            ⇒ 车队复工的面铺开了
基线取的是启动那一刻的实测值，不是写死的数。每轮还顺手记 停在额度/静默非闸/根目录待插，供事后写读数档。

用法：PYTHONIOENCODING=utf-8 python _cmdr_response_watch_r1.py [分钟=45] [每轮秒=120]
边界：只读（ls-remote + 读日志 + 列目录），0 次发送、0 次上总线、0 次写账本、0 次落地。
"""
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"D:\moodle\CityNexus"
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
LOGF = os.path.join(HERE, "autumn_watch.log")
OUT = os.path.join(HERE, "_cmdr_response_watch_latest.log")
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def tip():
    p = subprocess.run(["git", "-C", REPO, "ls-remote", "origin", TIPREF], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=ENV, timeout=240)
    return ((p.stdout or "").split("\t") or [""])[0].strip()


def roster():
    """从自动轮日志取最后一条完整的名册行；返回 (停在额度, 在写, 静默非闸, 那一刻) 或 None。"""
    last = None
    try:
        with io.open(LOGF, encoding="utf-8", errors="replace") as f:
            for l in f:
                m = re.search(u"\\[(\\d{2}:\\d{2}:\\d{2})\\] 额度名册：[^｜]*名册：停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", l)
                if m:
                    last = m
    except Exception:
        return None
    if not last:
        return None
    return int(last.group(2)), int(last.group(3)), int(last.group(4)), last.group(1)


def today_inserts():
    t0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d"))
    n = 0
    for f in os.listdir(PROC):
        p = os.path.join(PROC, f)
        if ".inserted_" in f and os.path.isfile(p) and os.path.getmtime(p) >= t0:
            n += 1
    return n


def root_pending():
    return len([f for f in os.listdir(INBOX)
                if f.endswith(".md") and os.path.isfile(os.path.join(INBOX, f))])


def say(x):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), x)
    with io.open(OUT, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    print(line)


def main():
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 45
    period = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    base_tip = tip()
    ins0 = today_inserts()
    r0 = roster()
    w0 = r0[1] if r0 else -1
    if not re.match(r"^[0-9a-f]{40}$", base_tip):
        say("基线尖取不到（%s）——观察器不起，别拿空值当基线" % base_tip[:20])
        return 2
    deadline = time.time() + minutes * 60
    say("观察起来：基线尖 %s…｜今日入账 %d 枚｜名册在写 %d 条（那拍 %s）｜根目录待插 %d 枚｜跑 %d 分钟、每 %d 秒一轮" % (
        base_tip[:12], ins0, w0, (r0[3] if r0 else "-"), root_pending(), minutes, period))
    while time.time() < deadline:
        t = tip()
        r = roster()
        ins = today_inserts()
        moved = bool(re.match(r"^[0-9a-f]{40}$", t)) and t != base_tip
        w = r[1] if r else -1
        if moved:
            say("动了①：权威尖 %s… -> %s…（今日入账 %d 枚、在写 %d 条）" % (base_tip[:12], t[:12], ins, w))
            return 0
        if ins > ins0:
            say("动了②：今日入账 %d -> %d 枚 ⇒ 有车道重新交得上件（尖仍 %s…，在写 %d 条）" % (ins0, ins, t[:12], w))
            return 0
        if w >= 6:
            say("动了③：名册在写 %d -> %d 条 ⇒ 复工面铺开（那拍 %s，尖仍 %s…）" % (w0, w, r[3], t[:12]))
            return 0
        say("未动：尖 %s…｜今日入账 %d｜在写 %d（停在额度 %s、静默 %s，那拍 %s）｜待插 %d" % (
            t[:12], ins, w, (r[0] if r else "?"), (r[2] if r else "?"), (r[3] if r else "?"), root_pending()))
        time.sleep(min(period, max(30, int(deadline - time.time()))))
    say("跑满 %d 分钟仍未动：尖仍 %s… ⇒ 那两贴没有换来动作，该升级报警" % (minutes, base_tip[:12]))
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
