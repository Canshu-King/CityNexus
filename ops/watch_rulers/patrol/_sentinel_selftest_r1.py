# -*- coding: utf-8 -*-
"""`_sentinel_relay_r1.py` 的红/绿对照自测（合成读数，绝不碰流水、真收件口与总线）。

为什么要有它：哨兵一晚上大多数轮次是绿，而「绿」既可能是真的没人被弃单，也可能是三把尺都失明。
自己定过规矩：自己消失的红≠修好。所以三把尺各造红、各造绿，还要验「单拍在写 0 不许误响」。

用法：PYTHONIOENCODING=utf-8 python _sentinel_selftest_r1.py    （全对退 0；任一不符退 1）
边界：这里替换的是 S.run（取数那一步），判定本体 pass_once 用的是生产那份代码，不是副本。
"""
import io
import os
import glob
import json
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import _sentinel_relay_r1 as S
REAL_DOOR = S.door_backlog     # judge() 会把 S.door_backlog 换成桩；真日志那一眼必须用没被换掉的原函数
REAL_MID = S.mid_stalled       # 同上：直测真函数那几行要用没被 judge() 换掉的那一把
REAL_HUBALARM = S.hub_alarm    # alarm 腿那两条断言量的是真函数的 argv，不是 judge 的记录桩
# 投递总闸在 import 处就关掉：这份自测喂的全是合成读数，任何一条真投出去都是污染正式总线
# （10-05 17:31 就污染过一次：正式账本多出一条 bolt-words:1005:e766b154_0119.md）。
S.SEND["allow"] = False
BUS_JSONL = u"D:/moodle/agent_bus/bus.jsonl"
INBOX_ROOT = r"D:\moodle\_qoder_ledger_inbox"
BW = os.path.join(HERE, u"bolt_words")
GW = os.path.join(HERE, u"gate_words")
START = time.time()


def real_block_names():
    """真收件口里现在或今天进过的块名。正式哨兵每十几分钟就会为**真块**发一条原话，
    所以判"自测污染"只能数"块名根本不在收件口"的那些——按字节数或目录是否变过一刀切，
    会把线上正常的投递读成我的污点（那是单向致盲的反面：咬错人）。
    """
    nm = set()
    for d, pat in ((INBOX_ROOT, u"*.md"), (os.path.join(INBOX_ROOT, u"_processed"), u"*.inserted_*")):
        try:
            for f in glob.glob(os.path.join(d, pat)):
                b = os.path.basename(f)
                if time.strftime("%m%d") in b or os.path.getmtime(f) > START - 86400:
                    nm.add(b.split(u".inserted_")[0])
        except Exception:
            pass
    return nm


def polluted():
    """自测开跑之后，正式账本里由我发出的、块名不在真收件口的 bolt/gate 投递。

    取不到账（账本读不动）一律报出来，不许当干净。
    """
    names = real_block_names()
    bad, err = [], u""
    try:
        rows = [json.loads(l) for l in io.open(BUS_JSONL, encoding="utf-8") if l.strip()]
    except Exception as e:
        return [u"账本读不到:" + type(e).__name__], err
    for m in rows:
        t = str(m.get("topic", u""))
        if (t.startswith((u"bolt-words:", u"gate-words:"))
                and float(m.get("ts", 0)) >= START
                and str(m.get("from", u"")) == u"qoder:42d1a6fa"):
            if t.rsplit(u":", 1)[-1] not in names:
                bad.append(t)
    for d, pre in ((BW, u"bolt_words_"), (GW, u"gate_words_")):
        try:
            ls = os.listdir(d)
        except Exception:
            continue
        for f in ls:
            if not f.startswith(pre):
                continue
            blk = f[len(pre):].replace(u".txt", u"")
            if blk not in names and os.path.getmtime(os.path.join(d, f)) >= START:
                bad.append(os.path.join(d, f))
    return bad, err

S.say = lambda *a, **k: None   # 自测不许往生产日志写行（04:46 那三行 band:I:1003:abcd1234 就是这么污染进去的）


def make(a_un=0, b_pending=0, b_nq=0, writing_seq=(4,)):
    st = {"n": 0}

    def runner(script, arg=None, timeout=900):
        if script == "_unclaimed_orders_r1.py":
            return u"号令者块 1 枚\n**无人接的单 %d 张**\n" % a_un, 0
        if script == "_restart_watch_r1.py":
            return (u"在场会话（最近 720 分钟动过）17 条｜被叫醒过 15 条｜叫醒后已回话 15 条｜"
                    u"叫醒后仍未回话 %d 条｜停在额度字样且没人接 %d 条\n" % (b_pending, b_nq), 0)
        i = min(st["n"], len(writing_seq) - 1)
        st["n"] += 1
        return u"14:42:29 名册：停在额度 1｜在写 %d｜静默非闸 15\n" % writing_seq[i], 0
    return runner


def blind(script, arg=None, timeout=900):
    return u"Traceback: boom\n", 1


def judge(runner, rounds=1, tage=30.0, qn=3, erows=None, eerr="", door=(0, 0.0, 0, 0, u"按分类", []),
          waiting=[], stalled=[], idle=((u"abcd1234", 50),), why_calls=None, hub_sends=None, boot=None,
          hub_override=None):
    """waiting 默认给空列表：自测**绝不去起 `_why_stopped_r1.py`（它会逐扇读真流水）。
    传 callable 时按它替换——那样才能验「在写 > 门槛就不该去读尾条」这一格。"""
    S.run = runner
    S.tip_age_min = lambda: tage
    S.queue_depth = lambda: qn
    S.door_backlog = lambda: door
    S.pending_red = lambda: (erows if erows is not None else [("x.md", "GREEN", 0)], eerr)
    S.waiting_ruling = waiting if callable(waiting) else (lambda: waiting)
    S._WHY = {u"text": None, u"rc": None}      # J 档吃的是 I 档那一次子进程的输出，桩之间不许串味
    S.mid_stalled = stalled if callable(stalled) else (lambda: stalled)
    S.idle_ids = lambda mins, exclude=None: list(idle)   # 自测不去 listdir 真目录
    S.boot_epoch = boot if callable(boot) else (lambda: 0.0)
    S.why_run_once = lambda: (why_calls.append(1) if why_calls is not None else None) or True
    # 自测绝不许真往 BB 机投：hub_alarm 一律换成记录器（真投会真发一条 alarm 给号令者）
    def _hub(band, id8, text):
        if hub_sends is not None:
            hub_sends.append((band, id8, text))
        return ("sent", "stub")
    S.hub_alarm = _hub
    # judge() 每轮都会把 hub_alarm 换成记录器；所以想验「投不上」必须在这里再覆盖一次。
    # 早先那枚「投信失败不许改变判定」是在 judge 之前赋值的 ⇒ 它其实从没真的失败过（假绿的自测）。
    if hub_override is not None:
        S.hub_alarm = hub_override
    z = 0
    d = 0
    eh = {}
    bs = 0
    g = {}
    out = []
    for _ in range(rounds):
        reds, z, summ, d, eh, bs, g = S.pass_once(z, d, eh, bs, g)
        out.append((reds, z, summ, d, g))
    return out


def check(name, got, want):
    ok = want in got
    print("%-30s %s（期望含「%s」）" % (name, "对" if ok else "错", want))
    if not ok:
        print("   实读：" + " / ".join(got)[:260])
    return ok


def main():
    hit = S.HIT
    if os.path.isfile(hit):
        os.remove(hit)
    res = []
    r = judge(make())
    res.append(check("全绿：不该有红因", ["绿" if not r[0][0] else "；".join(r[0][0])], "绿"))
    r = judge(make(a_un=2))
    res.append(check("红 A 无人接 2 张", "；".join(r[0][0]), "A 无人接 2 张"))
    r = judge(make(b_pending=3), rounds=2)
    res.append(check("红 B 叫醒后未回 3 条（连两轮）", "；".join(r[1][0]), "B 连 2 轮有车道没回声（未回 3"))
    r = judge(make(b_nq=2), rounds=2)
    res.append(check("红 B 额度且没人接 2 条（连两轮）", "；".join(r[1][0]), "停在额度且没人接 2）"))
    r = judge(make(writing_seq=(0,)), rounds=1)
    res.append(check("单拍在写 0 不响", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(writing_seq=(0, 0)), rounds=2)
    res.append(check("连两拍在写 0 才响", "；".join(r[1][0]), u"连续 2 拍在写 0 条"))  # 10-02 19:38 改文案：整队停摆要报「谁停了、缺的是活还是裁语」
    r = judge(blind)
    got = "；".join(r[0][0])
    res.append(check("尺取不到数算红（不是绿）", got, "尺取不到数"))
    res.append(check("三把尺都盲要报三条", str(got.count("尺取不到数")), "3"))
    # D：互等停摆（尖静止 >= 90 分 且 队列 >= 8 枚），要连三拍才响；取不到数不计红
    r = judge(make(), rounds=1, tage=95.0, qn=13)
    res.append(check("D 单拍不响（要连三拍）", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), rounds=3, tage=95.0, qn=13)
    res.append(check("D 连三拍才响", "；".join(r[2][0]), "D 互等停摆连 3 拍"))
    # 早退的资格：只有 A（无人接）与 E（会被闸拒）是我这班动得了的，其余只记不退
    res.append(check("B 红不算可落地（不该退场）", str(bool(S.actionable([u"B 连 2 轮有车道没回声"]))) , "False"))
    # 旧断言是「C 不算可落地」；19:29 全队在 0 而我没被叫醒，证明那条政策是错的，已翻向（见上面 C 那一组）
    res.append(check("C 红算可落地（整队停必须醒）", str(bool(S.actionable([u"C 整队停摆：连续 2 拍在写 0 条"]))) , "True"))
    res.append(check("D 红不算可落地", str(bool(S.actionable([u"D 互等停摆连 3 拍"]))) , "False"))
    res.append(check("F 红算可落地（门停我能敲门）", str(bool(S.actionable([u"F 门停了：待插 3 枚"]))) , "True"))
    res.append(check("H 红不算可落地", str(bool(S.actionable([u"H 尖静止 171 分"]))) , "False"))
    res.append(check("A 红要退场", str(bool(S.actionable([u"A 无人接 2 张"]))) , "True"))
    res.append(check("E 红要退场", str(bool(S.actionable([u"E 同一枚块连 2 轮都会被入账闸拒"]))) , "True"))
    # B 的宽限：单轮「未回 3 条」不叫，连两轮才叫（23:15 那回就是被单轮顶退的）
    r = judge(make(b_pending=3), rounds=1)
    res.append(check("B 单轮不叫", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(b_pending=3), rounds=2)
    res.append(check("B 连两轮才叫", "；".join(r[1][0]), "B 连 2 轮有车道没回声"))
    # H：兜底——尖静止 >=150 分且队列 >=3 就响（D 要队列 >=8，15:00-16:00 那种互等形状它不响）
    r = judge(make(), rounds=1, tage=171.0, qn=4)
    res.append(check("H 尖很久没动且还有候选要响", "；".join(r[0][0]), "H 尖静止 171 分"))
    r = judge(make(), rounds=1, tage=171.0, qn=1)
    res.append(check("H 队列只有一枚不响", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), rounds=1, tage=120.0, qn=9)
    res.append(check("H 未到 150 分不响（该由 D 连三拍管）", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), rounds=1, tage=95.0, qn=5)
    res.append(check("D 队列不足不响（读数里要带尖龄）", r[0][2], "尖 95 分没动、队列 5 枚"))
    r = judge(make(), rounds=3, tage=-1.0, qn=-1)
    res.append(check("D 取不到数不计红", "；".join(r[2][0]) if r[2][0] else "绿", "绿"))
    res.append(check("D 取不到数要在读数里写明", r[0][2], "不可得"))
    # E：入账闸预检——红要响、不可判不算绿也要写明、根目录读不到要报红
    r = judge(make(), rounds=1, erows=[("e766b154_1605.md", "RED", 5), ("a.md", "GREEN", 0)])
    res.append(check("E 单轮红只记不叫（16:30 实测：车道 4 分钟后自己改完被门收了）", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), rounds=2, erows=[("e766b154_1605.md", "RED", 5)])
    res.append(check("E 同一枚连两轮才叫", "；".join(r[1][0]), "E 同一枚块连 2 轮都会被入账闸拒：e766b154_1605.md"))
    r = judge(make(), rounds=2, erows=[("a.md", "RED", 1)])
    res.append(check("E 小结要写清连两轮几枚", r[1][2], "其中连两轮 1"))
    r = judge(make(), erows=[("a.md", "GREEN", 0)])
    res.append(check("E 全绿不该响", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), erows=[("b.md", "读数不全", -1)])
    res.append(check("E 不可判不判绿也不静默", r[0][2], "待插验 1 枚（红 0、其中连两轮 0、不可判 1）"))
    r = judge(make(), erows=[], eerr="根目录读不到")
    res.append(check("E 根目录读不到要报红", "；".join(r[0][0]), "E 根目录读不到"))
    # F：门停——分子只数「门绿真能插」那几枚（02:24 的反例：根目录 4 枚里 3 枚刚落口 3 分钟，
    # 唯一超龄的是被第二道闸拒的车道侧块，那种块敲号令者窗也没用，他插不进去）。
    r = judge(make(), door=(3, 41.0, 0, 0, u"按分类", []))
    res.append(check("F 门停要响", "；".join(r[0][0]), "F 门停了：可代插 3 枚"))
    r = judge(make(), door=(1, 21.0, 0, 0, u"按分类", []))
    res.append(check("F 只一枚且没过两倍 SLA 不算门停", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), door=(1, 45.0, 0, 0, u"按分类", []))
    res.append(check("F 一枚但龄过两倍 SLA 要响", "；".join(r[0][0]), "F 门停了：可代插 1 枚"))
    r = judge(make(), door=(4, 8.0, 0, 0, u"按分类", []))
    res.append(check("F 龄不够不算门停", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), door=(0, 0.0, 0, 1, u"按分类", []))
    res.append(check("F 回归：真能插 0 枚（4 枚根目录里 1 枚被闸拒）不许响",
                     "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), door=(-1, -1.0, -1, -1, u"分类尺读不到", []))
    res.append(check("F 读不到不能当绿", "；".join(r[0][0]), "F 收件口读不到"))
    r2 = judge(make(), door=(0, 0.0, 0, 0, u"按分类", []))
    res.append(check("F 读数要写进小结", r2[0][2], "门可插 0 枚（最老 0 分）｜门拒 0｜闸拒 0｜按分类"))
    # 分类尺本身：逐枚都从合成文本算，不碰真日志
    s1 = (u"===== [02:20:00] round\n"
          u"  BLOCK_GREEN a.md 已等 25 分钟，门绿 + 第二道闸干净\n"
          u"  BLOCK_GREEN c.md 已等 31 分钟，门绿 + 第二道闸干净\n"
          u"  BLOCK_GREEN_BUT_BOLTED b.md 已等 66 分钟，门绿 / 第二道闸 abort=1\n"
          u"  积压分类：门拒 0 枚 / 门绿但第二道闸拒 1 枚 / 门绿真能插 2 枚（尺 claim_coordinate_check_r7.py）\n"
          u"===== [02:30:00] round\n"
          u"  BLOCK_GREEN next-round.md 已等 99 分钟\n")
    g1 = S.parse_census(s1)
    res.append(check("分类尺抓到三档与龄（只数本轮，龄取最大）", str(g1[:4]), str((0, 1, 2, 31))))
    res.append(check("分类尺把闸拒那枚归车道（不当号令者的账）", str(g1[4]), str([("b.md", 66)])))
    res.append(check("分类尺不许数到下一拍", str([n for n, _a in g1[4]]), str(["b.md"])))
    res.append(check("分类尺没有分类行时返回 None（让调用方退回旧计数并标注）",
                     str(S.parse_census(u"BLOCK_GREEN a.md 已等 25 分钟\n")), "None"))
    g4 = S.parse_census(u"积压分类：门拒 2 枚 / 门绿但第二道闸拒 0 枚 / 门绿真能插 0 枚")
    res.append(check("分类尺有分类无绿块 ⇒ 龄 0", str(g4[:4]), str((2, 0, 0, 0.0))))
    # C：整队停摆——19:29 那拍全队 0 而旧版只记不叫，所以这一格现在必须能叫醒我一次；恢复了再停算新的一段。
    o5 = judge(make(writing_seq=(0, 0, 0, 5, 0, 0)), rounds=6)
    res.append(check("C 第一拍 0 不许响（单拍不算停摆）",
                     "绿" if not [x for x in o5[0][0] if x.startswith(u"C")] else "响了", "绿"))
    res.append(check("C 连续两拍 0 要响", "；".join(o5[1][0]), "C 整队停摆"))
    res.append(check("C 有退场资格（整队停我必须醒）", str(bool(S.actionable(o5[1][0]))), "True"))
    res.append(check("C 同一段第三拍只许记不许再叫", "；".join(o5[2][0]), "C·续 停摆仍在继续"))
    res.append(check("C 同一段续拍不许有退场资格", str(bool(S.actionable(o5[2][0]))), "False"))
    res.append(check("C 恢复在写那拍清账", "绿" if not [x for x in o5[3][0] if x.startswith(u"C")] else "有 C 行", "绿"))
    res.append(check("C 停了又停算新的一段，要再叫一次", "；".join(o5[5][0]), "C 整队停摆"))
    # G：块卡在第二道闸——F 修好后这类块不进 F 的分子，所以必须有一格钉住它，否则能躺一夜没人送原话
    r = judge(make(), door=(0, 0.0, 0, 1, u"按分类", [(u"e766b154_0119.md", 45)]))
    res.append(check("G 闸拒超龄要响", "；".join(r[0][0]), "G 有块卡在第二道闸 45 分：e766b154_0119.md"))
    res.append(check("G 归车道不归号令者", "；".join(r[0][0]), "号令者这一侧插不进去"))
    res.append(check("G 有退场资格（我能送原话）", str(bool(S.actionable([u"G 有块卡在第二道闸 45 分：x.md"]))), "True"))
    r = judge(make(), door=(0, 0.0, 0, 1, u"按分类", [(u"fresh.md", 12)]))
    res.append(check("G 龄不够不许响", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), rounds=2, door=(0, 0.0, 0, 1, u"按分类", [(u"same.md", 70)]))
    res.append(check("G 同一枚块整轮只报一次（第二轮不许再叫醒）",
                     "绿" if not r[1][0] else "第二轮仍响：" + "；".join(r[1][0]), "绿"))
    r = judge(make(), door=(0, 0.0, 0, 2, u"按分类", [(u"a.md", 90), (u"b.md", 50)]))
    res.append(check("G 两枚各报各的（不合并成一条）", str(len([x for x in r[0][0] if x.startswith(u"G ")])), "2"))
    # I：车道明写「等点单」超龄（10-03 新档）——动作权在号令者，所以报的是「敲他窗」，不是敲车道
    r = judge(make(), waiting=[(u"abcd1234", 50)])
    res.append(check("I 等点单超龄要响", "；".join(r[0][0]), u"I 车道 abcd1234 明写等号令者点单"))
    res.append(check("I 归号令者、不敲车道", "；".join(r[0][0]), u"该敲他窗"))
    res.append(check("I 有退场资格（我能把原话递过去）",
                     str(bool(S.actionable([u"I 车道 abcd1234 明写等号令者点单"]))), "True"))
    r = judge(make(), waiting=[(u"abcd1234", 20)])
    res.append(check("I 龄不够不许响", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), rounds=2, waiting=[(u"same8888", 70)])
    res.append(check("I 同一扇一天只报一次（第二轮不许再叫醒）",
                     "绿" if not r[1][0] else "第二轮仍响：" + "；".join(r[1][0]), "绿"))
    r = judge(make(), door=(0, 0.0, 0, 1, u"按分类", [(u"bolted.md", 60)]),
              waiting=[(u"abcd1234", 50)])
    res.append(check("I 与 G 各报各的（不互相吞）", str(len([x for x in r[0][0] if x[:2] in (u"I ", u"G ")])), "2"))
    r = judge(make(), waiting=None)
    res.append(check("I 尺取不到数要报红（不许当绿）", "；".join(r[0][0]), u"I 尺取不到数"))
    calls = {"n": 0}

    def spy():
        calls["n"] += 1
        return []
    r = judge(make(writing_seq=(9,)), waiting=spy)
    res.append(check("I 整队在写（在写 9 > 6）时不去读尾条", str(calls["n"]), "0"))
    res.append(check("I 小结要写明这一格没读", r[0][2], u"等点单：未读"))
    r = judge(make(writing_seq=(4,)), waiting=spy)
    res.append(check("I 在写 4 时确实去读了", str(calls["n"]), "1"))

    # J：车道断在半路（尾条是没回音的 tool_use）——判据来自 _stall_predicate_audit_r1.py 的实测（24 h 死尾 5 次、3 次没自复工）
    r = judge(make(), stalled=[(u"abcd1234", 50)])
    res.append(check("J 断在半路超龄要响", "；".join(r[0][0]), u"J 车道 abcd1234 断在半路"))
    res.append(check("J 叫醒归号令者、我只送话", "；".join(r[0][0]), u"该敲号令者把它叫回这一手"))
    res.append(check("J 有退场资格", str(bool(S.actionable([u"J 车道 abcd1234 断在半路已 50 分"]))), "True"))
    r = judge(make(), stalled=[(u"abcd1234", 20)])
    res.append(check("J 龄不够不许响", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    r = judge(make(), rounds=2, stalled=[(u"same9999", 70)])
    res.append(check("J 同一扇一天只报一次", "绿" if not r[1][0] else "第二轮仍响：" + "；".join(r[1][0]), "绿"))
    # 门控改了之后这一条的原话不再成立：J 现在按「有没有静默窗口」走，不看整队在写。
    # 所以这里同时验两件事：没静默窗口 ⇒ 不起子进程，且小结写明未读。
    calls0 = []
    r = judge(make(writing_seq=(9,)), idle=[], stalled=lambda: (_ for _ in ()).throw(AssertionError(u"J 不该被调用")), why_calls=calls0)
    res.append(check("J 无静默窗口且整队不低潮 ⇒ 不起子进程", str(len(calls0)), "0"))
    res.append(check("J 整队在写时不去读（与 I 同门槛）", r[0][2], u"断在半路：未读"))
    # J 的门控洞（01:5x 补）：lone 一扇断在半路、别人都在忙——旧门控（只看整队在写）永远看不见这形状
    calls2 = []
    r = judge(make(writing_seq=(11,)), idle=[(u"lon91234", 55)], stalled=[(u"lon91234", 55)], why_calls=calls2)
    res.append(check("J 整队忙但 lone 一扇静 55 分 ⇒ 仍要去看", "；".join(r[0][0]), u"J 车道 lon91234 断在半路"))
    res.append(check("J 与 I 共用一次尺输出（不起第二遍子进程）", str(len(calls2)), "1"))
    calls3 = []
    r = judge(make(writing_seq=(11,)), idle=[], stalled=[], why_calls=calls3)
    res.append(check("J 没静默窗口也不没低潮 ⇒ 一次都不该起子进程", str(len(calls3)), "0"))
    res.append(check("J 那一格要写明未读", r[0][2], u"断在半路：未读"))
    # 真函数那一遍：号令者与我自己的死尾必须剔掉（重启腰斩、上下文压缩都是良性成因），且不碰真流水
    S._WHY = {u"text": u"  abcd1234  车道   静  60 分｜判：结尾是 tool_use 无回音" + chr(10) + u"该敲车道本人（卡闸/断在半路）：494abfd7、abcd1234、42d1a6fa" + chr(10), u"rc": 0}
    res.append(check("J 把号令者与我自己从名单里剔掉", str(REAL_MID()), str([(u"abcd1234", 60)])))
    S._WHY = {u"text": None, u"rc": None}
    res.append(check("J 没 I 那次输出就报不可得（不许当绿）", str(REAL_MID()), "None"))
    # 04:07 号令者点名的那条 order：I/J 报红同一刻要往 BB 机投 alarm（topic 带日期＝幂等按天）
    hs = []
    rr0 = []
    r = judge(make(), waiting=[(u"abcd1234", 50)], hub_sends=hs)
    rr0 = list(r[0][0])
    res.append(check("I 报红时同步投一枚 BB 机 alarm", str(hs[:1]), "('I', 'abcd1234'"))
    res.append(check("同一扇去重键生效：不重复投", str(len(hs)), "1"))
    # 06:55 现形：alarm 正文写「已 53 分」，而中枢在发送那一刻重跑证据命令，输出已是 54 ⇒ 整枚被拒。
    res.append(check("alarm 正文不许带裸分钟数（数会漂，漂了就整枚被拒）", str(u"已 50 分" in hs[0][2]), "False"))
    res.append(check("红因那行仍要带上分钟数（日志给人看，不受中枢校验）", str(u"实测 50 分" in "；".join(rr0)), "True"))
    hs2 = []
    r = judge(make(), stalled=[(u"zz991234", 50)], idle=[(u"zz991234", 50)], hub_sends=hs2)
    res.append(check("J 报红时也投", str(hs2[:1]), "('J', 'zz991234'"))
    hs3 = []
    r = judge(make(), stalled=[(u"old8888", 50)], idle=[(u"old8888", 50)], hub_sends=hs3,
              boot=lambda: time.time() - 60.0)      # 假装 60 分钟前刚开机
    res.append(check("死尾早于本次开机 ⇒ 不报（重启腰斩不是停摆）", "绿" if not r[0][0] else "；".join(r[0][0]), "绿"))
    res.append(check("同上一格也不该往 BB 机投", str(len(hs3)), "0"))
    import _sentinel_relay_r1 as _S
    _real = _S.hub_alarm
    def boom(band, id8, text):
        raise AssertionError(u"投信失败")
    _S.hub_alarm = boom
    try:
        rr = judge(make(), waiting=[(u"qoder77ab", 99)], stalled=[], idle=[], hub_override=boom)
        res.append(check("投信失败不许改变判定（红还是红）", "；".join(rr[0][0]), u"I 车道 qoder77ab 明写等号令者点单"))
        # 更要紧的一格：投不上就不许记进重账，否则当天再也不试——看着报过、其实没人收到。
        res.append(check("投不上 ⇒ 不写 g_done（下一轮会重试）", str([k for k in rr[-1][4] if u"|I|" in k or u"|J|" in k]), "[]"))
    finally:
        _S.hub_alarm = _real

    _hl = [l for l in io.open(os.path.join(HERE, "_sentinel_relay_r1.py"), encoding="utf-8").read().split(chr(10))
               if l.startswith("HUB = ")]
    res.append(check("HUB 路径里没有控制字符（反斜杠+a 会变成 BEL）",
                       str([ord(c) for l in _hl for c in l if ord(c) < 9 or ord(c) in (11, 12, 14)]), "[]"))
    # alarm 腿的 evidence（04:52 探针暴露：不带就是"永远投不出去"的死腿）
    _cap = {}
    import subprocess as _sp
    _real_run = _S2.subprocess.run if False else None
    import _sentinel_relay_r1 as _S2
    _realrun = _S2.subprocess
    class _Fake:
        def run(self, cmd, **k):
            _cap["cmd"] = list(cmd)
            class R:
                returncode = 0
                stdout = b'{"id": "m_fake"}'
                stderr = b""
            return R()
    _S2.subprocess = _Fake()
    try:
        _S2.HUB_ON = True
        # 这一格量的是 hub_alarm 真拼出来的 argv，所以总闸要临时开回去——投递腿已被 _Fake 接住，
        # 出不了本进程（关掉闸 hub_alarm 会在门口就 return blocked，那两条断言就成了假红）。
        _S2.SEND["allow"] = True
        # 必须调**没被 judge() 换掉的那一把**（REAL_HUBALARM）：这里若调 _S2.hub_alarm，
        # 拿到的是 judge 的记录桩，它不拼 argv，两条断言就会假红——04:55 就是这么错了一次。
        r0 = REAL_HUBALARM("I", "abcd1234", u"I 车道 abcd1234 明写等号令者点单已 56 分")
    finally:
        _S2.SEND["allow"] = False
        _S2.subprocess = _realrun
    _cmdtxt = " ".join(_cap.get("cmd", []))
    res.append(check("alarm 投出去之前先备好取数命令作 evidence",
                     str("--evidence" in _cmdtxt and "_why_stopped_r1.py" in _cmdtxt), "True"))
    res.append(check("topic 带日期＝幂等按天",
                     str("band:I:" + __import__("time").strftime("%m%d") + ":abcd1234" in _cmdtxt), "True"))
    # 结构锁：自测全程不许往正式总线/正式落盘目录写任何一条合成投递
    _bad = polluted()[0]
    res.append(check(u"自测不许往正式总线投递（闸装在投递腿里，不靠每条测试记得换桩）",
                     u"；".join(_bad) if _bad else u"干净",
                     u"干净"))
    res.append(check(u"闸关掉时两条车道腿都退 blocked（不许退成静默成功）",
                     str([S.push_bolt_words(u"selftestx.md", 61, [u"L1 fake"]),
                          S.push_gate_words(u"selftestx.md", u"fake", 2)]),
                     u"['blocked', 'blocked']"))
    # 负对照：闸开回去、拿记录桩接 argv ⇒ 两条腿必须真去投递，
    # 否则上面那格就是假绿（腿本身断了也会显示"没投递"）。落盘指临时目录，正式目录不动。
    _tmp = tempfile.mkdtemp(prefix="cnx_negctl_")
    _bwd, _gwd = S.BOLT_WORDS_DIR, S.GATE_WORDS_DIR
    S.BOLT_WORDS_DIR, S.GATE_WORDS_DIR = _tmp, _tmp
    _S2.subprocess = _Fake()
    S.SEND["allow"] = True
    try:
        _neg = [S.push_bolt_words(u"negctl99_1731.md", 61, [u"L1 fake"]),
              S.push_gate_words(u"negctl99_1731.md", u"fake", 2)]
        _cmd2 = " ".join(_cap.get("cmd", []))
    finally:
        S.SEND["allow"] = False
        _S2.subprocess = _realrun
        S.BOLT_WORDS_DIR, S.GATE_WORDS_DIR = _bwd, _gwd
    res.append(check(u"负对照：闸开回去两条腿都真投递、且点名发给写它的那扇窗",
                     str(_neg == [u"sent", u"sent"] and u"qoder:negctl99" in _cmd2), "True"))
    res.append(check(u"负对照之后仍没一条合成投递落进正式账本或正式落盘目录",
                     u"；".join(polluted()[0]) or u"干净", u"干净"))
    import shutil as _sh
    _sh.rmtree(_tmp, ignore_errors=True)
    live = REAL_DOOR()
    print(u"现网门读数（真日志，不判定只贴数）：%s" % (live,))
    res.append(check("door_backlog 对现网也回六格（含闸拒清单）", str(len(live)), "6"))
    print("PASS %d/%d" % (sum(1 for x in res if x), len(res)))
    if not all(res):
        print("FAIL：%d 条不符" % (len(res) - sum(1 for x in res if x)))
        return 1
    print("三把尺各自报得出红、取不到数不判绿、单拍在写 0 不误响 ⇒ 哨兵的报红能力是活的。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
