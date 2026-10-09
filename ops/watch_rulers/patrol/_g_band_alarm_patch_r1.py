# -*- coding: utf-8 -*-
"""给 G 档装上「报警腿」，并点名 E 那把尺的单向致盲（只改判定，不改任何块的正文）。

为什么要这一版（三条都是 10-05 17:1x 实测出来的，不是推的）：
  1) G 分支只 `reds.append`，从来没有 `try_alarm("G", ...)` ⇒ 判红只活在 HIT 文件里。
     实测今天总线 `band:G` 共 0 枚、哨兵日志里 G 那行 0 条，而这一格的动作（把硬闸原话送回车道）
     本来就是哨兵自己动得了的那一档。
  2) G 旧写法先记 `g_done[key]` 再发 ⇒ 一旦发送失败，当天那枚块再也不试（「看着报过、其实没人收到」）。
  3) E 跑的是第一道闸，「门绿却被第二道硬闸拒」那类块在它眼里一律 GREEN ⇒ 读数上的「红 0」是假绿。
     真反例：pending_red() 对 1ba48dbf_1624.md 报 GREEN，同一枚块被写盘工拒了一个钟头。

规矩沿用 M/S：红照记，两条腿都发，只有 alarm 真投出去了才记进重账；正文不带任何待证的数，
数只进落盘文件（带扩展名的文件名中枢会剥，见 bus_hub.py 里 numeric_claims 的剥法）。

用法：python _g_band_alarm_patch_r1.py          # 打补丁（每处锚必须恰好命中一次，否则整份不写）
      python _g_band_alarm_patch_r1.py --check   # 只验锚与语法，不写盘
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "_sentinel_relay_r1.py")
NL = chr(10)

# ---- 锚（逐字取自现文件；每处 count 必须 == 1）----
A1 = u'BOLT_RE = re.compile(u"BLOCK_GREEN_BUT_BOLTED (\\\\S+\\\\.md) 已等 (\\\\d+) 分钟")'
A2 = (u"    got = parse_census(text)" + NL)
A3 = u'_M_DEAD = {"n": 0, "oldest": 0, "who": []}'
A4 = (u"    # E：收件口里那几枚「写完但会被入账闸拒」的块（龄 >= 5 分才验，更短说明还在写）" + NL
      + u"    erows, eerr = pending_red()" + NL
      + u'    bad = [x for x in erows if x[1] == "RED"]' + NL
      + u'    unk = [x for x in erows if x[1] == "读数不全"]' + NL)
A5 = (u'    etxt = "待插验 %d 枚（红 %d、其中连两轮 %d、不可判 %d）" % (' + NL
      + u"        len(erows), len(bad), len([c for c in e_hist.values() if c >= 2]), len(unk))" + NL)
A6 = (u"    ndoor, old, nrej, nbolt, note, bolts = door_backlog()" + NL
      + u"    if ndoor < 0:" + NL)
A7 = (u"        for nm, ag in bolts:" + NL
      + u'            key = time.strftime("%m%d") + u"|" + nm' + NL
      + u"            if ag >= G_BOLT_MIN and not g_done.get(key):" + NL
      + u"                g_done[key] = int(ag)" + NL
      + u'                reds.append(u"G 有块卡在第二道闸 %d 分：%s ⇒ 归写它的那条车道（id8=%s），"' + NL
      + u'                            u"我把门的原话送回那扇窗；号令者这一侧插不进去" % (int(ag), nm, nm[:8]))' + NL)

# ---- 替换 ----
B1 = (A1 + NL
      + u'_CENSUS_TAIL = {"text": None}   # G 档要把硬闸那一行的逐字判语送进车道，得留着分类尺那一拍的原文：'
        + u"重跑一遍闸既贵、又会把分钟数换成另一个数" + NL)

B2 = (u"    _CENSUS_TAIL[\"text\"] = text" + NL + A2)

B3 = (u'BOLT_WORDS_DIR = os.path.join(HERE, u"bolt_words")' + NL + NL
      + u"def bolt_reason_lines(block_name):" + NL
      + u'    """从分类尺那一拍的原文里取这枚块被第二道硬闸拒的逐字行。' + NL
      + u"" + NL
      + u"    取不到返回 None，并且调用方要在文件里写「不可得」——绝不能拿「我没读到」当「没有拒因」。" + NL
      + u'    """' + NL
      + u'    t = _CENSUS_TAIL.get("text")' + NL
      + u"    if not t:" + NL
      + u"        return None" + NL
      + u'    ls = [l.strip() for l in t.splitlines() if block_name in l and u"第二道闸" in l]' + NL
      + u"    return ls or None" + NL + NL
      + NL
      + u"def push_bolt_words(block_name, age_min, lines):" + NL
      + u'    """把「门绿却被第二道硬闸拒」的逐字判语落盘，再送一句不带数的话给写它的那条车道。' + NL
      + u"" + NL
      + u"    为什么不能只靠 E 那条腿：E 用的是第一道尺，这类块在它眼里是 GREEN（10-05 17:1x 实测" + NL
      + u"    pending_red() 对 1ba48dbf_1624.md 报 GREEN，而写盘工同一刻仍 rc=9 拒收），" + NL
      + u"    所以车道侧这一格只能由 G 送到。正文沿用 push_gate_words 的规矩：数只进落盘文件。" + NL
      + u'    """' + NL
      + u'    lane = block_name.split(u"_")[0]' + NL
      + u'    rid = lane if lane.count(u":") else (u"qoder:" + lane[:8])' + NL
      + u'    path = os.path.join(BOLT_WORDS_DIR, u"bolt_words_" + block_name + u".txt")' + NL
      + u"    try:" + NL
      + u"        if not os.path.isdir(BOLT_WORDS_DIR):" + NL
      + u"            os.makedirs(BOLT_WORDS_DIR)" + NL
      + u'        head = [u"read_at=" + time.strftime("%Y-%m-%d %H:%M:%S"),' + NL
      + u'                u"block=" + block_name,' + NL
      + u'                u"lane=" + rid,' + NL
      + u'                u"已等分钟=" + str(int(age_min)),' + NL
      + u'                u"第二道硬闸逐字判语（分类尺那一拍原文）:"]' + NL
      + u'        body_lines = lines or [u"（分类尺那一拍没有这枚块的原文 ⇒ 拒因不可得；'
        + u'要复算请跑 live_checks/patrol/inbox_check.py，别按我这条日志的分钟数动手）"]' + NL
      + u'        io.open(path, "w", encoding="utf-8", newline=chr(10)).write('
        + u'chr(10).join(head + body_lines) + chr(10))' + NL
      + u"    except Exception as e:" + NL
      + u'        say(u"硬闸原话落盘失败（%s: %s）⇒ 这一条不投，只记" % (type(e).__name__, str(e)[:80]))' + NL
      + u'        return u"failed"' + NL
      + u'    msg = (u"值守哨兵→写这块的车道：你这枚块过了第一道入账门，却被写盘工的第二道硬闸"' + NL
      + u'            u"（坐标可取回闸）拒着，已到我这一档的分钟数门槛，所以我没等你再撞一次。"' + NL
      + u'            u"逐字判语与已等分钟都在下面这个文件里，改哪一行看它最准——我不动你写的字。"' + NL
      + u'            + chr(10) + path)' + NL
      + NL
      + u'    cmd = [PYEXE, os.path.join(HUB, "bus.py"), "send", "--from", SENTINEL_ID,' + NL
      + u'           "--to", rid, "--kind", "note", "--topic",' + NL
      + u'           u"bolt-words:%s:%s" % (time.strftime("%m%d"), block_name), "--body", msg]' + NL
      + u"    try:" + NL
      + u"        q = subprocess.run(cmd, capture_output=True, cwd=HUB, timeout=90," + NL
      + u'                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))' + NL
      + u'        out = (q.stdout or b"").decode("utf-8", "replace")' + NL
      + u'        if q.returncode == 0 and u\'"id"\' in out:' + NL
      + u'            say(u"硬闸原话已送车道：%s → %s（落盘 %s）" % (block_name, rid, path))' + NL
      + u'            return u"sent"' + NL
      + u'        say(u"硬闸原话没投出去：%s → %s（%s）" % (block_name, rid, out[:140]))' + NL
      + u'        return u"failed"' + NL
      + u"    except Exception as e:" + NL
      + u'        say(u"硬闸原话投递异常（%s: %s）⇒ 不记进重账" % (type(e).__name__, str(e)[:80]))' + NL
      + u'        return u"failed"' + NL + NL
      + NL
      + u"def bolt_alarms(bolts, g_done, reds):" + NL
      + u'    """G 档判定 + 两条腿（车道原话 / 总线 band:G 报警）。返回真投出去的枚数。' + NL
      + u"" + NL
      + u"    为什么单拎成函数：旧写法只 reds.append 且先记 g_done ⇒ 判红只活在 HIT 文件里，" + NL
      + u"    总线今天整天 band:G 为 0 枚（实测），发送失败当天还不再试。现在与 M/S 同一形制：" + NL
      + u"    红照记、两条腿都发、只有 alarm 真出去了才记进重账（投不上下一轮再试）。" + NL
      + u'    """' + NL
      + u"    fired = 0" + NL
      + u"    for nm, ag in bolts:" + NL
      + u'        key = time.strftime("%m%d") + u"|" + nm' + NL
      + u"        if ag < G_BOLT_MIN or g_done.get(key):" + NL
      + u"            continue" + NL
      + u'        reds.append(u"G 有块卡在第二道闸 {a} 分：{n} ⇒ 归写它的那条车道（id8={i}），"' + NL
      + u'                    u"我把硬闸的逐字判语送回那扇窗；号令者这一侧插不进去").format(' + NL
      + u"            a=int(ag), n=nm, i=nm[:8])" + NL
      + u"        st_note = push_bolt_words(nm, ag, bolt_reason_lines(nm))" + NL
      + u"        state, topic = try_alarm(u\"G\", nm[:8], (" + NL
      + u'            u"G 档：有一枚块过了第一道入账门、却被写盘工的第二道硬闸（坐标可取回闸）拒着，"' + NL
      + u'            u"已到我这一档的分钟数门槛 ⇒ 这一格的动作不在号令者（他这一侧插不进去），"' + NL
      + u'            u"而在写它的那条车道：硬闸的逐字判语已落盘，具名块与路径见哨兵日志与本条证据输出。"' + NL
      + u'            u"已等分钟与 abort 条数不写进本条正文——那条命令在中枢重跑那一刻会漂。"' + NL
      + u'            + chr(10) + os.path.join(BOLT_WORDS_DIR, u"bolt_words_" + nm + u".txt")))' + NL
      + u'        if state == u"sent":' + NL
      + u"            g_done[key] = int(ag)" + NL
      + u"            fired += 1" + NL
      + u"        else:" + NL
      + u'            say(u"G 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（%s：%s）" % (topic, state))' + NL
      + u'        if st_note != u"sent":' + NL
      + u'            say(u"G 档车道腿没送到：%s（%s）⇒ 只记日志；alarm 若已出去，耐久副本仍在，'
        + u'下一轮不重复发同一枚" % (nm, st_note))' + NL
      + u"    return fired" + NL + NL
      + A3 + NL)

B4 = (u"    # 分类尺那一拍先取（E/F/G 三格共用同一份读数，也少一次日志读）" + NL
      + u"    ndoor, old, nrej, nbolt, note, bolts = door_backlog()" + NL
      + u"    bolt_names = set(nm for nm, _ag in bolts)" + NL
      + A4
      + u"    # E 这把尺只跑第一道闸，所以「门绿却被硬闸拒」在它眼里一律 GREEN——单向致盲必须点名，不能当零：" + NL
      + u"    # 10-05 17:1x 实测 pending_red() 给 1ba48dbf_1624.md 报 GREEN，同一枚块被写盘工连拒一个钟头。" + NL
      + u'    blind = [x for x in erows if x[1] == "GREEN" and x[0] in bolt_names]' + NL)

B5 = (u'    etxt = ("待插验 {} 枚（红 {}、其中连两轮 {}、不可判 {}）｜".format(' + NL
      + u"        len(erows), len(bad), len([c for c in e_hist.values() if c >= 2]), len(unk))" + NL
      + u'        + (u"闸拒不可得（分类尺本轮未分类）" if nbolt < 0' + NL
      + u'           else u"门绿却硬闸拒 {} 枚（E 看不见，归 G 档）".format(len(blind))))' + NL)

B6 = (u"    if ndoor < 0:" + NL)

B7 = (u"        # 判定与投递都在 bolt_alarms 里：这一格自测要能单独喂一份合成分类读数进去（见 _g_band_alarm_selftest_r1.py）" + NL
      + u"        bolt_alarms(bolts, g_done, reds)" + NL)

PAIRS = [(A1, B1), (A2, B2), (A3, B3), (A4, B4), (A5, B5), (A6, B6), (A7, B7)]


def main():
    src = io.open(T, encoding="utf-8").read()
    for i, (a, b) in enumerate(PAIRS, 1):
        n = src.count(a)
        if n != 1:
            print(u"锚 %d 命中 %d 次（必须 1）⇒ 整份不写盘：%r" % (i, n, a[:70]))
            return 1
    if "--check" in sys.argv:
        print(u"七处锚各命中一次（只验锚，未写盘）")
        return 0
    for a, b in PAIRS:
        src = src.replace(a, b, 1)
    try:
        ast.parse(src)
    except SyntaxError as e:
        print(u"改完语法不过：%s（行 %s）⇒ 不写盘" % (e.msg, e.lineno))
        return 2
    io.open(T, "w", encoding="utf-8", newline=NL).write(src)
    print(u"已打补丁：G 档两条腿 + E 的盲点点名（语法已过 ast.parse；文件 %s）" % os.path.basename(T))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
