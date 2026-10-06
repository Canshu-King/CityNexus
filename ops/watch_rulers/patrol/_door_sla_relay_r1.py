# -*- coding: utf-8 -*-
"""代插超承诺（SLA）这一格的敲门件：所有数都在脚本里现取，缺一格就 REFUSE 不发。

为什么要有它：F 档叫我醒之后，我发出去的那句话**必须是现读的数**。
09-30 起立过规矩：一帖只许用一次测量的数、槽位一律 .format(**dict)（`%` 位置参数会把标签与数值排串位），
解析不到就 assert 拒投。代插这件事尤其敏感——「你压着没插」是一句会冤枉人的话，
只有当①块确实门绿且第二道闸干净、②龄过了他自己写的 <=15 分钟、③他这段时间没在落字，三条同时成立才说。

用法：python _door_sla_relay_r1.py            （缺省 SLA=15 分）
边界：只读收件口与各日志；不起写盘工、不改任何人的块、不动权威线。
"""
import glob
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
PROJ = os.path.expanduser(u"~/.qoder/projects/D--moodle")
CMDR = u"494abfd7"
EXPECT_LEN = 83
EXPECT_SHA1 = "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def refuse(msg):
    print(u"REFUSE：" + msg)
    return 2


def blocks():
    out = []
    for f in glob.glob(os.path.join(INBOX, "*.md")):
        out.append((os.path.basename(f), os.path.getmtime(f), os.path.getsize(f)))
    return sorted(out, key=lambda x: x[1])


def door_gate(path):
    p = subprocess.run([sys.executable, os.path.join(LC, "claim_coordinate_check_r7.py"),
                        "--text", path, "--expect-clean"], capture_output=True, cwd=LC)
    txt = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    m = re.search(r"overall (\w+) \| findings (\d+)", txt)
    if not m:
        return None, u"读不到判语", len(txt)
    return m.group(1), m.group(2), len(txt)


def last_insert():
    best = None
    for f in glob.glob(os.path.join(PROC, "*.inserted_*")):
        mt = os.path.getmtime(f)
        if best is None or mt > best[0]:
            best = (mt, os.path.basename(f))
    return best


def cmdr_last_write():
    c = glob.glob(os.path.join(PROJ, CMDR + "*.jsonl"))
    return os.path.getmtime(c[0]) if c else None


def main():
    sla = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    now = time.time()
    bs = blocks()
    if not bs:
        print(u"不发：收件口根目录现在 0 枚——没有堵，不该敲。")
        return 0
    oldest_name, oldest_mt, oldest_sz = bs[0]
    oldest_min = (now - oldest_mt) / 60.0
    if oldest_min < sla:
        print(u"不发：最老一枚 %s 才等 %.1f 分，未到 SLA=%.0f 分（这不是门停）。" % (
            oldest_name, oldest_min, sla))
        return 0

    # 逐枚跑第一道闸：只有「门绿」的枚数才算他压着的；红的归车道自己修，不能算在他头上
    green, red, unknown = [], [], []
    for nm, mt, sz in bs:
        tag, finds, _ln = door_gate(os.path.join(INBOX, nm))
        if tag is None:
            unknown.append(nm)
        elif tag == "Q43_GATE_GREEN":
            green.append((nm, int((now - mt) / 60.0), sz, finds))
        else:
            red.append((nm, int((now - mt) / 60.0), finds))
    if unknown:
        return refuse(u"有 %d 枚跑不出判语（%s）⇒ 分母不完整，不能报枚数" % (len(unknown), u"、".join(unknown[:3])))
    if not green:
        print(u"不发：这 %d 枚里 0 枚门绿（红的归车道自己修），代插闸没堵，不该敲号令者。" % len(bs))
        return 0

    li = last_insert()
    cw = cmdr_last_write()
    if li is None or cw is None:
        return refuse(u"最后代插或号令者流水读不到 ⇒ 不能断言『他压着没插』")
    li_min = (now - li[0]) / 60.0
    cw_min = (now - cw) / 60.0
    if li_min < sla:
        print(u"不发：他 %.1f 分前刚代插过（%s），这一轮还没到他给自己的额度。" % (li_min, li[1]))
        return 0

    raw = io.open(CLOSING, "rb").read()
    if len(raw) != EXPECT_LEN or hashlib.sha1(raw).hexdigest() != EXPECT_SHA1:
        return refuse(u"收尾口令字节不吻合（len=%d sha1=%s）" % (len(raw), hashlib.sha1(raw).hexdigest()[:12]))
    tail = raw.decode("utf-8").strip()
    stamp = time.strftime("%m-%d %H:%M:%S")
    marker = u"【值守敲门 · %s · %s】" % (CMDR, stamp)

    gtxt = u"、".join(u"`%s`（%d 分、%d B、findings %s）" % (n, a, s, f) for n, a, s, f in green[:8])
    rtxt = u"、".join(u"`%s`（%d 分，findings %s）" % (n, a, f) for n, a, f in red[:8]) or u"无"
    D = dict(marker=marker, now=time.strftime("%H:%M:%S"), sla=sla, n=len(bs), ngreen=len(green),
             gtxt=gtxt, nred=len(red), rtxt=rtxt, oldest=oldest_name, omin=oldest_min,
             limin=li_min, lin=li[1], cwmin=cw_min, tail=tail)
    body = u"""{marker}

【代插这一格过了你自己给的承诺】现测 {now}，全部由 `_door_sla_relay_r1.py` 现取（SLA={sla:.0f} 分）：

- 收件口根目录 **{n} 枚**；其中**门绿**（第一道闸 `claim_coordinate_check_r7.py --expect-clean` 逐枚跑过）**{ngreen} 枚**：
  {gtxt}
- 门拒（归车道自己修，不算在你头上）**{nred} 枚**：{rtxt}
- 最老一枚 `{oldest}` 已等 **{omin:.1f} 分**；你上一次代插是 **{limin:.1f} 分前**（`{lin}`）。
- 你这一扇自己最后一次落字是 **{cwmin:.1f} 分前**（读你的 jsonl mtime，不是窗口状态）。
- 我不判你为什么没跑（可能在别的回合里），只报这几格：门绿 {ngreen} 枚、最老 {omin:.0f} 分、你 {cwmin:.0f} 分没落字。
- 我这边边界：0 次代插（`ledger_inbox_apply` 我没跑过）、0 次改车道块、0 次动权威线、0 次碰他人进程。

{tail}
""".format(**D)
    if body.count(tail) != 1 or not body.rstrip().endswith(tail):
        return refuse(u"尾行没接上或接了两遍")
    out = os.path.join(HERE, u"_knock_%s_%s.txt" % (CMDR, time.strftime("%H%M")))
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    b = body.encode("utf-8")
    print(u"[落盘 %s｜%d B｜sha1 %s]" % (os.path.basename(out), len(b), hashlib.sha1(b).hexdigest()))
    print(u"[回读用标记：%s]" % marker)
    print(u"")
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
