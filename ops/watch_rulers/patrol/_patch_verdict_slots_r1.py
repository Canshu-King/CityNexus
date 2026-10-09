# -*- coding: utf-8 -*-
u"""把「一天多档的到点取数器」接进值守栈的覆盖里（带锚点断言，落盘前 ast.parse）。

改两份：
  _night_verdict_runner_r1.py：档点除 env 外再认命令行标记 `NVR_AT=<档点>`；
                               锁按整档点、落盘件名按四位档点后缀（23:00:20 那档名字不变）。
  _watch_stack_r1.py        ：COMPONENTS 加第 9 条腿 verdict_1055；start() 带 extra env＋argv 标记；
                               alive() 支持按标记筛（同脚本两档各判各的活）。

跑法：python _patch_verdict_slots_r1.py --check   # 只看锚
      python _patch_verdict_slots_r1.py           # 动手
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, u"_night_verdict_runner_r1.py")
STK = os.path.join(HERE, u"_watch_stack_r1.py")

EDIT = []


def rep(path, old, new, n=1):
    EDIT.append((path, old, new, n))


# ——— 取数器：认 argv 档点 ————————————————————————————————
rep(RUN,
    u'RUN_AT = os.environ.get("NVR_AT", "23:00:20")       # 到这一刻就取数（留 20 秒让 23:00 的最后一拍落账）\n',
    u'# 档点：默认 23:00:20（终值单）。同一份脚本可以守几档，看护器按命令行标记 `NVR_AT=<档点>` 分档——\n'
    u'# env 在进程表里看不见，只靠 env 传档点的那条腿一旦机器重启就没人认得它是哪一档：\n'
    u'# 10-06 03:1x 实测，22:46 那次修复安装重启带走 10:55 那枚，栈起复时 COMPONENTS 只有一条 verdict，\n'
    u'# 于是只补回 23:00:20，10:55 那一档静默失踪，而本班目标写的正是"守到明天 11:00"。\n'
    u'_SLOT = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("NVR_AT=")]\n'
    u'RUN_AT = (_SLOT[0] if _SLOT else os.environ.get("NVR_AT", "23:00:20"))\n'
    u'SLOT_TAG = RUN_AT.replace(":", "")          # 锁名用整档点：230020 / 105500（沿用旧名，不新开一把）\n'
    u'ART_TAG = SLOT_TAG[:4]                     # 件名用四位档点：23:00:20 那档仍是 _2300.txt，一字不改\n')

rep(RUN,
    u'LOCK = os.path.join(HERE, "_night_verdict_runner.%s.lock"\n'
    u'                   % os.environ.get("NVR_AT", "230020").replace(":", ""))\n',
    u'LOCK = os.path.join(HERE, "_night_verdict_runner.%s.lock" % SLOT_TAG)\n')

rep(RUN, u' + u"_2300.txt", d)', u' + u"_" + ART_TAG + u".txt", d)', n=2)

# ——— 值守栈：第 9 条腿 + 按标记判活 ————————————————————————
rep(STK,
    u'    ("verdict", "_night_verdict_runner_r1.py", "_night_verdict_runner.log", "到 23:00:20 出终值单+第2格补件，出完自退"),\n',
    u'    ("verdict", "_night_verdict_runner_r1.py", "_night_verdict_runner.log", "到 23:00:20 出终值单+第2格补件，出完自退", None),\n'
    u'    # 11:00 前收尾那一档也进覆盖，否则它一死就得靠我正好醒着补（上一条注释里那次就是这么丢的）。\n'
    u'    # 两档同名脚本 ⇒ 判活必须带档点标记，不然场上只要有任一枚 verdict，另一档就被读成"已在"。\n'
    u'    ("verdict_1055", "_night_verdict_runner_r1.py", "_night_verdict_runner_early.log",\n'
    u'     u"到 %s 出收尾读数（今天 11:00 前那一档），出完自退" % os.environ.get("NVR_EARLY_AT", "10:55:00"),\n'
    u'     os.environ.get("NVR_EARLY_AT", "10:55:00")),\n')

rep(STK,
    u'def start(name, script, logfile):\n'
    u'    p = resolve(script)\n'
    u'    if not os.path.exists(p):\n'
    u'        raise RuntimeError("脚本不在：" + p)\n'
    u'    cwd = os.path.dirname(p)\n'
    u'    with io.open(os.devnull, "rb") as dn, io.open(os.path.join(LOGDIR, logfile), "a") as out:\n'
    u'        pr = subprocess.Popen([PYEXE, p], stdin=dn, stdout=out, stderr=out, cwd=cwd,\n'
    u'                              creationflags=DETACH, env=dict(os.environ, PYTHONIOENCODING="utf-8"))\n'
    u'    return pr.pid\n',
    u'def start(name, script, logfile, slot=None):\n'
    u'    p = resolve(script)\n'
    u'    if not os.path.exists(p):\n'
    u'        raise RuntimeError("脚本不在：" + p)\n'
    u'    cwd = os.path.dirname(p)\n'
    u'    # slot 非空 ⇒ 把档点当显式 argv 传（env 那份也一起给，兼容手敲的跑法）：\n'
    u'    # 这样进程表里就看得见"这一枚守的是哪一档"，判活才分得开同名脚本的两档。\n'
    u'    argv = [PYEXE, p] + ([u"NVR_AT=%s" % slot] if slot else [])\n'
    u'    with io.open(os.devnull, "rb") as dn, io.open(os.path.join(LOGDIR, logfile), "a") as out:\n'
    u'        pr = subprocess.Popen(argv, stdin=dn, stdout=out, stderr=out, cwd=cwd,\n'
    u'                              creationflags=DETACH,\n'
    u'                              env=dict(os.environ, PYTHONIOENCODING="utf-8",\n'
    u'                                       **({"NVR_AT": slot} if slot else {})))\n'
    u'    return pr.pid\n')

rep(STK,
    u'def alive(name, script, rows=None):\n'
    u'    rows = rows if rows is not None else ps_rows()\n'
    u'    hit = [(pid, cl) for pid, cl in rows if script in cl and "python" in cl.lower()]\n'
    u'    return hit\n',
    u'def alive(name, script, rows=None, slot=None):\n'
    u'    rows = rows if rows is not None else ps_rows()\n'
    u'    hit = [(pid, cl) for pid, cl in rows if script in cl and "python" in cl.lower()]\n'
    u'    if slot:\n'
    u'        # 同一份脚本守几档：只认 CommandLine 里带着本档标记的那几枚。\n'
    u'        # 不带标记的老腿（重启前手起的那些）在这儿会读成"缺"，下一拍被带标记的新腿替上；\n'
    u'        # 真 double 起不了：取数器自己有按档点的锁，锁里 pid 还活着就自退，不重写出第二枚。\n'
    u'        hit = [x for x in hit if (u"NVR_AT=%s" % slot) in x[1]]\n'
    u'    return hit\n')

rep(STK,
    u'    for name, script, logfile, note in COMPONENTS:\n',
    u'    for name, script, logfile, note, slot in COMPONENTS:\n')

rep(STK,
    u'        hit = alive(name, os.path.basename(script), rows)\n',
    u'        hit = alive(name, os.path.basename(script), rows, slot=slot)\n')

rep(STK,
    u'        pid = start(name, script, logfile)\n',
    u'        pid = start(name, script, logfile, slot)\n')


def main():
    check = "--check" in sys.argv
    texts = {}
    bad = []
    for path, old, new, n in EDIT:
        t = texts.get(path) or io.open(path, encoding=u"utf-8").read()
        got = t.count(old)
        if got != n:
            bad.append(u"%s：锚命中 %d 次，要 %d 次 ⇒ %r"
                       % (os.path.basename(path), got, n, old[:56]))
            continue
        t = t.replace(old, new)
        texts[path] = t
    if bad:
        for x in bad:
            print(u"REFUSE：" + x)
        return 1
    if check:
        print(u"--check：%d 处锚全部逐字命中（未写盘）" % len(EDIT))
        return 0
    for path, t in texts.items():
        ast.parse(t)                      # 语法不过就整批不落
    for path, t in texts.items():
        with io.open(path, u"w", encoding=u"utf-8", newline=u"\n") as f:
            f.write(t)
        print(u"已写 %s（%d 字符）" % (os.path.basename(path), len(t)))
    return 0


if __name__ == u"__main__":
    sys.exit(main())
