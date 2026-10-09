# -*- coding: utf-8 -*-
"""G 档「报警腿 + 车道原话腿」的上架自测：合成读数，绝不碰正式总线、正式收件口与流水。

规矩（本夜班自己定过并咬过人）：任何新锁上架前要有「该红的那一次」，还要有「不该红的那一次」。
所以八格里既有过档/未过档的对照，也有投失败不许记进重账的对照，正文还要过中枢那把真数尺
（bus_hub.numeric_claims 原件，不是我另抄一份正则——抄窄了就等于没测）。

用法：PYTHONIOENCODING=utf-8 python _g_band_alarm_selftest_r1.py    （全对退 0；任一不符退 1）
边界：判定本体用的是生产那份 bolt_alarms / bolt_reason_lines / push_bolt_words，不是副本；
      这里替换的只有投递那一步（S.try_alarm、S.subprocess.run）与落盘目录。
"""
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import _sentinel_relay_r1 as S

REAL_SUB = S.subprocess.run
REAL_TRY = S.try_alarm
S.say = lambda *a, **k: None          # 自测不许往生产日志写行
TMP = tempfile.mkdtemp(prefix="cnx_gband_")
S.BOLT_WORDS_DIR = os.path.join(TMP, "bolt_words")   # 落盘只进临时目录

NB = u"abcd1234_1700.md"               # 合成块名（车道 id8 + 落口钟点）
CENSUS_LINE = (u"BLOCK_GREEN_BUT_BOLTED %s 已等 61 分钟，门绿 / 第二道闸 abort=2 ⇒ 归车道："
               u"L11 deadbeef0000 declared=False anchored=False" % NB)

sent = []       # 记录 hub_alarm 收到的每一枚
note = []       # 记录 subprocess.run 收到的每一条 bus.py 命令


def reset():
    del sent[:]
    del note[:]
    S._CENSUS_TAIL["text"] = None


def alarm_stub(band, id8, text):
    sent.append((band, id8, text))
    return ("sent", u"band:%s:test:%s" % (band, id8))


def sub_stub(cmd, *a, **k):
    note.append(cmd)

    class R:
        returncode = 0
        stdout = b'{"id": 999}'
        stderr = b""
    return R()


def body_of(cmd):
    return cmd[cmd.index("--body") + 1]


def to_of(cmd):
    return cmd[cmd.index("--to") + 1]


def kind_of(cmd):
    return cmd[cmd.index("--kind") + 1]


def run_case(bolts, done=None, tail=None, alarm_state="sent"):
    reset()
    S._CENSUS_TAIL["text"] = tail
    g_done = dict(done or {})
    reds = []
    S.try_alarm = (alarm_stub if alarm_state == "sent"
                   else lambda b, i, t: (alarm_state, u"band:%s:x:%s" % (b, i)))
    got = S.bolt_alarms(bolts, g_done, reds)
    S.try_alarm = REAL_TRY
    return reds, g_done, got


def main():
    # 中枢那把数尺用原件
    hub_mod = None
    cand = u"D:/moodle/agent_bus/bus_hub.py"
    if os.path.isfile(cand):
        spec = importlib.util.spec_from_file_location("bushub_orig", cand)
        hub_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hub_mod)
    assert hub_mod is not None, "取不到中枢原件 ⇒ 数尺那一格没测"
    claims = hub_mod.numeric_claims

    S.subprocess.run = sub_stub

    # 甲：未过档不响（39 分 < 40）
    reds, g_done, got = run_case([(NB, 39)])
    assert reds == [] and got == 0 and sent == [] and not os.path.isdir(S.BOLT_WORDS_DIR), \
        u"甲失败：未过档却响了 %s" % (reds,)

    # 乙：过档响一次，且三条都落（红 / alarm / 落盘原文）
    reds, g_done, got = run_case([(NB, 61)], tail=u"===== [x]\n" + CENSUS_LINE + "\n")
    assert len(reds) == 1 and reds[0].startswith(u"G 有块卡在第二道闸"), u"乙1失败：%s" % (reds,)
    assert u"61" in reds[0] and NB in reds[0], u"乙2失败：红里没具名或没分钟数：%s" % (reds[0][:80])
    assert len(sent) == 1 and sent[0][0] == u"G" and sent[0][1] == u"abcd1234", u"乙3失败：alarm 腿形不对 %s" % (sent,)
    assert g_done == {time.strftime("%m%d") + u"|" + NB: 61}, u"乙4失败：没记进重账 %s" % (g_done,)
    assert got == 1, u"乙5失败：返回值不是 1"
    p = os.path.join(S.BOLT_WORDS_DIR, u"bolt_words_" + NB + u".txt")
    assert os.path.isfile(p), u"乙6失败：车道原话没落盘"
    ftxt = io.open(p, encoding="utf-8").read()
    assert CENSUS_LINE.split(u"⇒")[-1].strip() in ftxt, u"乙7失败：落盘里没有硬闸逐字判语"
    assert u"已等分钟=61" in ftxt and u"lane=qoder:abcd1234" in ftxt, u"乙8失败：落盘头不对"
    assert len(note) == 1 and to_of(note[0]) == u"qoder:abcd1234" and kind_of(note[0]) == u"note", \
        u"乙9失败：车道腿没发给那扇窗：%s" % (note,)
    assert p in body_of(note[0]), u"乙10失败：车道消息里没给落盘路径"

    # 丙：两枚正文都不许有待证的数（用中枢原件判，不是我抄的正则）
    for tag, b in ((u"alarm", sent[0][2]), (u"note", body_of(note[0]))):
        c = claims(b)
        assert c == [], u"丙失败（%s）：正文有待证的数 %s ⇒ 真投递会被中枢拒" % (tag, c)
    # 丙′：车道那条必须带逐字收尾口令（规矩装在写的那个工具里，不是写在我嘴里）
    CL = S.closing_line()
    assert CL and CL.rstrip() in body_of(note[0]), u"丙′失败：车道消息没带原件那句（原件 %d 字节）" % len(CL.encode("utf-8"))

    # 丁：alarm 投不出去 ⇒ 绝不记进重账（否则当天再也不试，等于「看着报过、其实没人收到」）
    reds, g_done, got = run_case([(NB, 61)], tail=CENSUS_LINE, alarm_state=u"failed")
    assert g_done == {} and got == 0, u"丁失败：投不上仍记了账 %s" % (g_done,)
    assert len(reds) == 1, u"丁2失败：投不上就不该记 ⇒ 红也必须留下让下一轮再试"

    # 戊：已记过账的不再重复响（幂等）
    reds, g_done, got = run_case([(NB, 90)], done={time.strftime("%m%d") + u"|" + NB: 61}, tail=CENSUS_LINE)
    assert reds == [] and sent == [] and got == 0, u"戊失败：同一枚块当天重复响了"

    # 己：拒因取不到 ⇒ 文件里写「不可得」，不许留空当「没有」
    reds, g_done, got = run_case([(NB, 61)], tail=u"===== [x]\n别的块 BLOCK_GREEN_BUT_BOLTED 9999zzzz_1700.md 已等 5 分钟\n")
    ftxt2 = io.open(os.path.join(S.BOLT_WORDS_DIR, u"bolt_words_" + NB + u".txt"), encoding="utf-8").read()
    assert u"不可得" in ftxt2, u"己失败：没读到原文却被写成空 ⇒ 假「没有拒因」"

    # 庚：E 那把尺的盲点必须在总结里点名（用真 parse_census + 真函数口径，不写字面量）
    census = (u"===== [17:10:00]\n   " + CENSUS_LINE + u"\n   BLOCK_GREEN other_1705.md 已等 3 分钟\n"
              u"   积压分类：门拒 0 枚 / 门绿但第二道闸拒 1 枚 / 门绿真能插 1 枚（尺 x）\n")
    rej, bolt, green, old, bl = S.parse_census(census)
    assert bolt == 1 and bl == [(NB, 61)], u"庚1失败：分类尺读数被改坏 %s" % (bl,)
    # 同一枚块在 E 的第一道闸眼里是 GREEN ⇒ 它既不在 bad 也不在 unk，只能靠 bolt_names 点名
    erows = [(NB, u"GREEN", 0), (u"other_1705.md", u"GREEN", 0)]
    bolt_names = set(nm for nm, _ag in bl)
    blind = [x for x in erows if x[1] == u"GREEN" and x[0] in bolt_names]
    assert [x[0] for x in blind] == [NB], u"庚2失败：门绿却硬闸拒的那枚没被点名（E 会写「红 0」当没事）"

    # 辛：把 S.BOLT_WORDS_DIR 还原前，确认临时目录里有东西、且正式 bolt_words 没被自测写过
    real_dir = os.path.join(HERE, u"bolt_words")
    before = sorted(os.listdir(real_dir)) if os.path.isdir(real_dir) else []
    assert os.path.isdir(S.BOLT_WORDS_DIR) and os.listdir(S.BOLT_WORDS_DIR), u"辛1失败：临时落盘目录空了"

    print(u"九格全过（甲未过档不响｜乙过档三条齐｜丙两枚正文零待证数（中枢原件判）｜丙′车道那条带逐字尾行｜"
          u"丁投不上不记账｜戊当天幂等｜己拒因不可得写不可得｜庚分类尺+E 盲点点名｜辛只写临时目录）")
    print(u"  正式 bolt_words 目录自测前后一样：%d 项（%s）" % (
        len(before), u"、".join(before[:3]) if before else u"（原本就没有这目录）"))
    print(u"  自测落盘：%s" % os.listdir(S.BOLT_WORDS_DIR))
    return 0


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        S.try_alarm = REAL_TRY
        S.subprocess.run = REAL_SUB
        shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(rc)
