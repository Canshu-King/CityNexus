# -*- coding: utf-8 -*-
"""一眼跑齐值守这五格，并且**取不到数就不判绿**：把人从「记得跑五条命令」里换出来。

为什么要有它：夜里真正会漏事的不是判据错，而是我漏跑某一把尺——
比如 06:2x 之前我每拍都跑「谁停了」「谁在等单」「门堵没堵」，却没跑 `wake_from_commits.py`，
而那一把恰好是唯一能发现「号令者刚落了一块、点名某扇、那扇已经静下去」的。
这一枚把五把尺按固定顺序跑完，逐格要拿到自己的读数才准打印；任何一格取不到数就在结论里显式写「不可判」。

它不做动作：只有我在读它。判出来的「要做的事」是要我下一步去敲窗/报号令者的清单。
只读：不 POST、不 ack、不敲门、不动账本、不碰任何人的进程。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PYEXE = sys.executable
PATROL = HERE
BUS = "D:/moodle/agent_bus"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHECKS = (
    ("谁停了", [PYEXE, os.path.join(PATROL, "_why_stopped_r1.py"), "25"],
     lambda o: re.search(u"名册 (\\d+) 扇.*?在写（<\\d+ 分）(\\d+) 扇", o, re.S),
     u"^(名册|停了 \\d+ 扇|该敲|额度类|分不出)"),
    ("谁在等单", [PYEXE, os.path.join(BUS, "_queued_census_r1.py")],
     lambda o: re.search(u"该敲：(.*)$", o, re.M),
     u"^(该敲|文件腿|已执行但没人 ack|没有面向车道)"),
    ("门堵没堵", [PYEXE, os.path.join(PATROL, "_door_sla_relay_r1.py")],
     lambda o: re.search(u"(不发：.*|该敲：.*|REFUSE.*)", o),
     u"^(不发|该敲|REFUSE|门)"),
    ("新块点名谁", [PYEXE, os.path.join(PATROL, "wake_from_commits.py")],
     lambda o: re.search(r"candidates=(\d+)", o),
     u"^(candidates|名册外滤掉|\\s+· )"),
    ("栈与哨兵", [PYEXE, os.path.join(PATROL, "_watch_stack_r1.py"), "--check"],
     lambda o: re.search(u"(栈完整|\\*\\*缺\\*\\*)", o),
     u"^(⇒|   动作|   缺文件|   子支)"),
    ("谁没接进来", [PYEXE, os.path.join(PATROL, "_bb_cover_r1.py")],
     lambda o: re.search(u"干活 \\d+ 扇", o),
     u"^(干活|新窗|没接进来的|在册没自证|覆盖面满|REFUSE)"),
)


def run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, cwd=PATROL, timeout=300)
        return (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    except Exception as e:
        return u"" if False else u"__FAIL__ %s: %s" % (type(e).__name__, str(e)[:120])


def main():
    print(u"_tick_r1.py 于 %s｜%d 把尺按固定顺序，取不到数就写不可判（只读，不做动作）" % (
        time.strftime("%m-%d %H:%M:%S"), len(CHECKS)))
    todo = []
    bad = 0
    for name, cmd, probe, show in CHECKS:
        o = run(cmd)
        m = probe(o) if o else None
        if o.startswith(u"__FAIL__") or m is None:
            bad += 1
            print(u"  %-9s 不可判｜%s" % (name, (o or u"（空输出）").strip().splitlines()[-1][:150] if o.strip() else u"空"))
            continue
        body = [ln.strip() for ln in o.splitlines() if ln.strip()]
        picked = [ln for ln in body if re.match(show, ln)] or body[:1]
        print(u"  %-9s ｜%s" % (name, u" ‖ ".join(p[:150] for p in picked[:4])))
        if name == u"谁停了":
            for ln in [x.strip() for x in o.splitlines()]:
                if ln.startswith(u"该敲车道本人") and not ln.endswith(u"无"):
                    todo.append((u"敲车道（卡闸/断在半路/意图句就停）", ln))
                if ln.startswith(u"该敲号令者") and not ln.endswith(u"无"):
                    todo.append((u"报号令者（等裁语）", ln))
                if ln.startswith(u"分不出") and not ln.endswith(u"无"):
                    todo.append((u"人工看尾条（尺判不了，别乱敲）", ln))
        if name == u"谁在等单":
            seg = o.splitlines()
            for ln in seg:
                if ln.startswith(u"该敲：") and not ln.startswith(u"该敲：零"):
                    todo.append((u"这扇名下有未取走的单且已静下去", ln))
        if name == u"新块点名谁":
            # 候选数 >0 就必须进「要做的事」让人读一眼正文：这一把尺分不清
            # 「块在命令这扇做一手」还是「块在叙述这扇做过什么」（06:2x 那两枚 cmdrA 块就是叙述）。
            # 早先这里按「候选」二字筛，把真候选整格滤掉了也不报错——那是最坏的一种漏：静默的漏。
            seg = [ln.strip() for ln in o.splitlines() if u"idle=" in ln and u"落账本" in ln]
            cand_n = int(re.search(r"candidates=(\d+)", o).group(1)) if re.search(r"candidates=(\d+)", o) else 0
            if cand_n:
                todo.append((u"新块点名了静下去的窗（读正文判是不是真点名，别照敲）",
                             u"；".join(s[:120] for s in seg[:3]) or u"candidates=%d 但没打出明细行" % cand_n))
        if name == u"栈与哨兵":
            if u"缺" in o:
                todo.append((u"值守栈缺支（跑一次不带 --check 的起复）", u"见本行上方输出"))
        if name == u"谁没接进来":
            hit = [ln.strip() for ln in o.splitlines()
                   if ln.strip().startswith(u"新窗") or ln.strip().startswith(u"没接进来的")]
            if hit:
                todo.append((u"推广：请这扇接进 BB 机（身份要它自己 claim，我不代注册）",
                             u"；".join(h[:150] for h in hit[:2])))
    print(u"—— 要做的事 %d 件 ——" % len(todo))
    for why, detail in todo:
        print(u"  · %s：%s" % (why, detail))
    if not todo:
        print(u"  （无：舰队全在写或交完无单、门不堵、块不点名静窗、栈齐）")
    print(u"取数失败的格：%d/%d（>0 就别把这一眼当绿）" % (bad, len(CHECKS)))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
