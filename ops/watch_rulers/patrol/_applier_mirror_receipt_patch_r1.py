# -*- coding: utf-8 -*-
"""让代插腿把镜像那一步的回执转印出来，并把"没有回执"本身判红。

现状（01:0x 实测）：`ledger_inbox_apply_r2.py` 第 182 行会串镜像腿并打印 `mirror rc=…`，
但 `_inbox_applier_r2.py` 只从子进程输出里抽 INSERTED／REFUSED／tally 三类行，
镜像那行被丢掉 ⇒ 值守日志里 `grep -c "mirror rc="` 现读为 0。
更糟的是它替我回给号令者一句"镜像腿由 applier 自己推"——那是我当时拿不出证据的话。

修法两条：
① 抽镜像相关行（mirror rc／BYTE_LEVEL_CONFIRMED／PROVEN／REMOTE_LEDGER_READ_FAILED／Bad credentials／ABORT）
   逐行转印进日志；
② 插了块却没有镜像回执 ⇒ 记一条红并走 hub_alarm（P 档），
   因为"看不见结果"不等于"成功"；给号令者的通报也改成有证据的说法。
"""
import ast
import io
import sys

P = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_inbox_applier_r2.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:44]))
        return
    s = s.replace(old, new, 1)


rep(u'''                tal = [l for l in out.split(NL) if l.startswith("tally")]''',
    u'''                tal = [l for l in out.split(NL) if l.startswith("tally")]
                # 镜像那一步以前被这里丢掉了：日志里 grep "mirror rc=" 恒为 0，
                # 于是"插进去了"被当成"也推上去了"——看不见结果不等于成功。
                MIR_W = (u"mirror rc=", u"BYTE_LEVEL_CONFIRMED", u"PROVEN", u"REMOTE_LEDGER_READ_FAILED",
                         u"Bad credentials", u"ABORT:")
                mir = [l for l in out.split(NL) if any(w in l for w in MIR_W)]''')

rep(u'''                if ins:
                    ti = dict((os.path.basename(f), t) for f, t in keep)
                    verify_landed([(x, ti.get(x) or block_head(os.path.join(IBOX, x))) for x in ins])
                    tell_cmdr(ins, u"已插入；镜像腿由 applier 自己推；插前命中为零、插后逐枚核对见本日志",
                              tally_line)''',
    u'''                if ins:
                    ti = dict((os.path.basename(f), t) for f, t in keep)
                    verify_landed([(x, ti.get(x) or block_head(os.path.join(IBOX, x))) for x in ins])
                    if mir:
                        for l in mir[-3:]:
                            say(u"镜像回执：%s" % l[:150])
                        good = any((u"BYTE_LEVEL_CONFIRMED" in l) or (u"PROVEN" in l) for l in mir)
                        note = (u"镜像回执已转印进本日志（%s）"
                                % (u"含 BYTE_LEVEL_CONFIRMED/PROVEN" if good else u"结论不是成功，见日志原文"))
                    else:
                        note = u"注意：这一拍插了 %d 块，但 applier 输出里没有镜像那一步的任何回执" % len(ins)
                        say(u"镜像回执：无 ⇒ 不能当它推成功了（%s）" % note)
                        hub_alarm(u"P", u"mirror", u"P 档：代插腿插了 %d 块却拿不到镜像回执，"
                                u"账本本地已进、远端不可证；出处是本腿日志尾行与 "
                                u"live_checks/merge_ledger_then_mirror_r2.py 的 mirror rc 那行" % len(ins))
                    tell_cmdr(ins, note + u"；插前命中为零、插后逐枚核对见本日志", tally_line)''')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：%d 条没落上，未改动" % len(miss))
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"镜像回执转印已装｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
