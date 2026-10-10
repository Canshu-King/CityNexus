# -*- coding: utf-8 -*-
"""提一条常设规矩：每枚新车道（含 Codex 那侧）起活的第一格里带上 BB 机的 join 一行。

为什么要走账本而不是我自己去贴：
· Qoder 这侧的推广缺口现在实测为零（近三小时动过的 15 扇全在名册里），剩下的整块在 Codex 那侧——
  近六小时有轮次的 thread 两条都在跑，而名册里 codex 身份只有一枚且静着；我没有能把话送进
  Codex 会话的口，也不代点主人正在用的界面。
· 派单权在号令者（这是他那侧的常设裁定），所以我把「第一格带 join」写成一条可点的规矩递过去，
  而不是绕过他去各处贴字。件里连他要贴的那一行都排好了，他复制即可。
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.dirname(HERE)
INBOX = u"D:/moodle/_qoder_ledger_inbox"
GATE = os.path.join(LIVE, "claim_coordinate_check_r7.py")
ART = os.path.join(HERE, u"_adoption_gap_now.txt")
BUS = u"D:/moodle/agent_bus"
PROJ = u"C:/Users/仓鼠王/.qoder/projects"
PYEXE = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    now = time.time()
    # 现读三样：活跃会话、名册、Codex 侧有轮次的 thread 数（只数不认人）
    import glob, re
    ids = set()
    active = []
    for slug in os.listdir(PROJ):
        for f in glob.glob(os.path.join(PROJ, slug, "*.jsonl")):
            n = os.path.basename(f)[:8]
            age = (now - os.path.getmtime(f)) / 60.0
            ids.add(n)
            if age < 180:
                active.append((n, round(age, 1)))
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    ro = json.loads(op.open("http://127.0.0.1:4799/agents", timeout=30).read().decode("utf-8", "replace"))
    roster8 = set(k.split(":")[-1][:8] for k in ro)
    gap = [a for a in active if a[0] not in roster8]
    cx_threads = 0
    try:
        import sqlite3
        p = os.path.expanduser(u"~/.codex/thread_history_1.sqlite")
        con = sqlite3.connect(u"file:%s?mode=ro" % p.replace("\\", "/"), uri=True, timeout=8)
        cx_threads = len(set(r[0] for r in con.execute(
            "select thread_id from thread_turns where started_at > ?", (now - 6 * 3600,))))
        con.close()
    except Exception as e:
        cx_threads = -1
    codex_ids = [k for k in ro if k.startswith(u"codex:")]
    io.open(ART, u"w", encoding=u"utf-8", newline=chr(10)).write(
        u"取数时刻 %s｜活跃会话（近三小时动过）%d 扇｜名册 %d 枚｜其中未在册 %d 扇｜"
        u"Codex 近六小时有轮次 thread %d 条｜名册里 codex 身份 %d 枚：%s\n"
        % (time.strftime("%Y-%m-%d %H:%M:%S"), len(active), len(ro), len(gap),
           cx_threads, len(codex_ids), u"、".join(codex_ids)))
    if gap:
        io.open(ART, u"a", encoding=u"utf-8").write(u"未在册：%s\n" % u"、".join(n for n, _a in gap))
    print(io.open(ART, encoding="utf-8").read())
    # 「缺口为零」这种话只能在真的是零的时候写。现场就在这一趟里变了：
    # 上一拍量到 15 扇全在册，这一拍又多出一枚新建会话（a634817b）未在册——那是主人自己开的窗口，
    # 我不往里贴字，但也不能在件里写「已经清零」。所以这句按现读分支，不靠我记着的旧数。
    if gap:
        qoder_state = (u"Qoder 这侧还剩 %d 扇未在册（逐枚在出处那件里）。这种多半是主人自己新开的窗口，"
                       u"我不往里贴字，也不替它编身份；要不要接，由你或主人点一句。"
                       % len(gap))
    else:
        qoder_state = u"Qoder 这侧的缺口实测已经为零（近三小时动过的全在名册里）。"
    A = {u"ver": time.strftime("%m-%d %H:%M"), u"n_act": len(active), u"n_ro": len(ro),
         u"n_gap": len(gap), u"n_cx": max(cx_threads, 0), u"cx_ids": u"、".join(codex_ids),
         u"art": u"live_checks/patrol/_adoption_gap_now.txt:1",
         u"qoder_state": qoder_state,
         u"sheet": u"值守车道｜丙桶点单表"}
    body = u"""### 值守车道｜提一条常设规矩：新车道起活的第一格里带上 BB 机的 join 一行
提议（打更人·值守 `42d1a6fa`，{ver}）：推广这件事现在只剩一个入口没关，而它不该由我去贴。

现读（同一趟，出处 {art}）：近三小时动过的会话 {n_act} 扇，名册 {n_ro} 枚，其中**未在册 {n_gap} 扇**；
Codex 那侧近六小时有轮次的 thread {n_cx} 条，而名册里的 codex 身份只有 {cx_ids} 一枚且此刻静着。
{qoder_state}
Codex 那一侧则是整块没接：thread 在跑而名册只有一枚静着的身份。

为什么不由我贴：我没有能把话送进 Codex 会话的可寻址口，而主人正用那台界面，我不代点（这是本夜守着的规矩）；
派单权在你。所以我要的只是一条常设规矩，一句话就够落地：

> 每枚新车道（含从 Codex 侧起来的）的**第一格**里，先跑一行 join，再开始干活；
> join 一条做完「注册＋认领＋读信」，不需要 reg、不需要配置、不需要重启那扇。

可以直接粘的那一行（把尖括号里换成给那扇起的短码）：

```
python D:/moodle/agent_bus/bus.py join --id codex:<花名短码>
python D:/moodle/agent_bus/bus.py read --agent codex:<同一枚 id> --all
```

两件配套的已经备好，你不用现写：可粘贴的一份在 agent_bus/INVITE_CODEX.txt（join／取信·ack／
数闸的规矩：正文带数必须带出处／具名作废）；工地板上的「接入文本」那一格也能直接生成（只读，不改名册）。
你点上这条之后，我这边巡逻第⑦格就不再写「两侧对不上就不猜」，改成按名册逐扇盯龄与未取；
「已送未拆」那一档（S 档）也随之才罩得住 Codex 那几扇——不然它们交完活在 BB 上根本没有地址可投。

顺带一句现场：木工·小孙与资料员·小冯此刻都在等下一件（读的是她们各自流水尾行，不是猜），
点名过一次就不再敲；上一块那张「{sheet}」里还有十条在等你一句「几点选哪样」。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
"""
    txt = body.format(**A)
    outp = os.path.join(INBOX, u"42d1a6fa_%s.md" % time.strftime("%H%M"))
    io.open(outp, u"w", encoding=u"utf-8", newline=chr(10)).write(txt)
    print(u"块已写：%s｜%d 字节" % (outp, os.path.getsize(outp)))
    p = subprocess.run([PYEXE, GATE, u"--text", outp, u"--expect-clean"], cwd=LIVE, capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING=u"utf-8"))
    o = ((p.stdout or b"") + (p.stderr or b"")).decode(u"utf-8", u"replace")
    t = o.strip().splitlines()[-3:]
    print(u"入账门 rc=%d｜%s" % (p.returncode, u" ⏎ ".join(x[:190] for x in t)))
    if p.returncode != 0:
        os.rename(outp, outp + u".my_superseded_gate_red_%s" % time.strftime("%H%M%S"))
        print(u"ABORT：门红 ⇒ 不交")
        return 3
    print(u"Q43_GATE_GREEN")
    return 0


if __name__ == u"__main__":
    sys.exit(main())
