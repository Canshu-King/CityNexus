# -*- coding: utf-8 -*-
"""把「自测不许往正式总线投递」这条规矩装进投递腿本身，并在老自测里加锁＋负对照。

起因（现读，不是推的）：10-05 17:31:33 我跑 `_sentinel_selftest_r1.py`（为量改动有没有回归），
那份自测喂的是**合成**分类读数；我新加的 G 投递腿不认得"合成"，于是真往正式总线投了一条
`bolt-words:1005:e766b154_0119.md` 给那条车道，正文说它有一枚块被硬闸拒着——那枚块不是它交的。
正式账本现读多这一条，正式 bolt_words/ 多出几份合成文件。我已经另发一条更正给那扇窗（作废那句、
别按它动手），这里补的是规矩：**挡板装在写的那个工具里，不靠每一条测试自己记得换桩**。

改三处：
  ① `_sentinel_relay_r1.py` 加总闸 `SEND={"allow":True}`；hub_alarm / push_gate_words / push_bolt_words
     三条投递腿开头就查它，关掉时 hub_alarm 退 ("blocked", topic)、两条车道腿退 u"blocked"——
     退 blocked 而不是退 sent，调用方就不会把它记进重账（否则"被挡了"会读成"已送达"）。
  ② 老自测在 import 处把闸关掉，跑完比对正式 bus.jsonl 字节数与 bolt_words/、gate_words/ 名单
     ——这条是结构锁：以后任何一条腿在自测里真发出去，格子就报红。
  ③ 负对照：把闸开回去、拿记录桩接住 argv ⇒ 两条车道腿必须真去投递（证明②那格是被挡住的，
     不是腿本身断了）。落盘指到临时目录，正式目录一个文件都不许多。

用法：python _selftest_send_guard_patch_r1.py [--check]
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SENT = os.path.join(HERE, "_sentinel_relay_r1.py")
SELF = os.path.join(HERE, "_sentinel_selftest_r1.py")
NL = chr(10)


def R(path, pairs):
    src = io.open(path, encoding="utf-8").read()
    for i, (a, b) in enumerate(pairs, 1):
        n = src.count(a)
        if n != 1:
            print(u"%s 锚 %d 命中 %d 次（必须 1）⇒ 整份不写盘：%r" % (os.path.basename(path), i, n, a[:60]))
            return None
    for a, b in pairs:
        src = src.replace(a, b, 1)
    try:
        ast.parse(src)
    except SyntaxError as e:
        print(u"%s 改完语法不过：%s（行 %s）⇒ 不写盘" % (os.path.basename(path), e.msg, e.lineno))
        return None
    return src


# ---------- ① 哨兵：总闸 + 三条投递腿 ----------
S_A1 = u'HUB_ON = os.environ.get("SR_HUB_OFF", "0") != "1"'
S_B1 = (S_A1 + NL
        + u'# 投递总闸：三条外发腿（hub_alarm / push_gate_words / push_bolt_words）唯一的开关。'
        + u"生产默认开＝照发。" + NL
        + u'# 10-05 17:31 的教训：自测喂的是合成分类读数，我新加的 G 投递腿把它当成现网，'
        + u"真往正式总线投了一条给一条没交过那枚块的车道。" + NL
        + u'# 所以规矩装在写的那个工具里：自测把这里关掉即可，不靠每条测试自己记得换桩。' + NL
        + u'SEND = {"allow": True}')

S_A2 = (u'    topic = u"band:%s:%s:%s" % (band, time.strftime("%m%d"), id8)' + NL
        + u"    q = quiet_hit(id8)")
S_B2 = (u'    topic = u"band:%s:%s:%s" % (band, time.strftime("%m%d"), id8)' + NL
        + u'    if not SEND["allow"]:' + NL
        + u'        say(u"自测挡板（SEND=off）：%s 这枚不投——这一拍喂的是合成读数，不许写正式总线" % topic)' + NL
        + u'        return ("blocked", topic)' + NL
        + u"    q = quiet_hit(id8)")

S_A3 = (u'    lane = block_name.split(u"_")[0]' + NL
        + u'    rid = lane if lane.count(u":") else (u"qoder:" + lane[:8])' + NL
        + u"    try:" + NL
        + u"        if not os.path.isdir(GATE_WORDS_DIR):")
S_B3 = (u'    lane = block_name.split(u"_")[0]' + NL
        + u'    rid = lane if lane.count(u":") else (u"qoder:" + lane[:8])' + NL
        + u'    if not SEND["allow"]:' + NL
        + u'        say(u"自测挡板（SEND=off）：%s 的门原话不落盘也不投" % block_name)' + NL
        + u'        return u"blocked"' + NL
        + u"    try:" + NL
        + u"        if not os.path.isdir(GATE_WORDS_DIR):")

S_A4 = (u'    lane = block_name.split(u"_")[0]' + NL
        + u'    rid = lane if lane.count(u":") else (u"qoder:" + lane[:8])' + NL
        + u'    path = os.path.join(BOLT_WORDS_DIR, u"bolt_words_" + block_name + u".txt")')
S_B4 = (u'    lane = block_name.split(u"_")[0]' + NL
        + u'    rid = lane if lane.count(u":") else (u"qoder:" + lane[:8])' + NL
        + u'    if not SEND["allow"]:' + NL
        + u'        say(u"自测挡板（SEND=off）：%s 的硬闸原话不落盘也不投" % block_name)' + NL
        + u'        return u"blocked"' + NL
        + u'    path = os.path.join(BOLT_WORDS_DIR, u"bolt_words_" + block_name + u".txt")')

# ---------- ②③ 老自测：关闸 + 结构锁 + 负对照 ----------
T_A1 = u"import sys" + NL + u"import time"
T_B1 = (u"import glob" + NL + u"import json" + NL + u"import sys" + NL
        + u"import tempfile" + NL + u"import time")

T_A2 = u'REAL_HUBALARM = S.hub_alarm    # alarm 腿那两条断言量的是真函数的 argv，不是 judge 的记录桩'
T_B2 = (T_A2 + NL
        + u'# 投递总闸在 import 处就关掉：这份自测喂的全是合成读数，任何一条真投出去都是污染正式总线' + NL
        + u'# （10-05 17:31 就污染过一次：正式账本多出一条 bolt-words:1005:e766b154_0119.md）。' + NL
        + u'S.SEND["allow"] = False' + NL
        + u'BUS_JSONL = u"D:/moodle/agent_bus/bus.jsonl"' + NL
        + u'INBOX_ROOT = r"D:\moodle\_qoder_ledger_inbox"' + NL
        + u'BW = os.path.join(HERE, u"bolt_words")' + NL
        + u'GW = os.path.join(HERE, u"gate_words")' + NL
        + u'START = time.time()' + NL
        + NL
        + NL
        + u'def real_block_names():' + NL
        + u'    """真收件口里现在或今天进过的块名。正式哨兵每十几分钟就会为**真块**发一条原话，' + NL
        + u'    所以判"自测污染"只能数"块名根本不在收件口"的那些——按字节数或目录是否变过一刀切，' + NL
        + u'    会把线上正常的投递读成我的污点（那是单向致盲的反面：咬错人）。' + NL
        + u'    """' + NL
        + u'    nm = set()' + NL
        + u'    for d, pat in ((INBOX_ROOT, u"*.md"), (os.path.join(INBOX_ROOT, u"_processed"), u"*.inserted_*")):' + NL
        + u'        try:' + NL
        + u'            for f in glob.glob(os.path.join(d, pat)):' + NL
        + u'                b = os.path.basename(f)' + NL
        + u'                if time.strftime("%m%d") in b or os.path.getmtime(f) > START - 86400:' + NL
        + u'                    nm.add(b.split(u".inserted_")[0])' + NL
        + u'        except Exception:' + NL
        + u'            pass' + NL
        + u'    return nm' + NL
        + NL
        + NL
        + u'def polluted():' + NL
        + u'    """自测开跑之后，正式账本里由我发出的、块名不在真收件口的 bolt/gate 投递。' + NL
        + u'' + NL
        + u'    取不到账（账本读不动）一律报出来，不许当干净。' + NL
        + u'    """' + NL
        + u'    names = real_block_names()' + NL
        + u'    bad, err = [], u""' + NL
        + u'    try:' + NL
        + u'        rows = [json.loads(l) for l in io.open(BUS_JSONL, encoding="utf-8") if l.strip()]' + NL
        + u'    except Exception as e:' + NL
        + u'        return [u"账本读不到:" + type(e).__name__], err' + NL
        + u'    for m in rows:' + NL
        + u'        t = str(m.get("topic", u""))' + NL
        + u'        if (t.startswith((u"bolt-words:", u"gate-words:"))' + NL
        + u'                and float(m.get("ts", 0)) >= START' + NL
        + u'                and str(m.get("from", u"")) == u"qoder:42d1a6fa"):' + NL
        + u'            if t.rsplit(u":", 1)[-1] not in names:' + NL
        + u'                bad.append(t)' + NL
        + u'    for d, pre in ((BW, u"bolt_words_"), (GW, u"gate_words_")):' + NL
        + u'        try:' + NL
        + u'            ls = os.listdir(d)' + NL
        + u'        except Exception:' + NL
        + u'            continue' + NL
        + u'        for f in ls:' + NL
        + u'            if not f.startswith(pre):' + NL
        + u'                continue' + NL
        + u'            blk = f[len(pre):].replace(u".txt", u"")' + NL
        + u'            if blk not in names and os.path.getmtime(os.path.join(d, f)) >= START:' + NL
        + u'                bad.append(os.path.join(d, f))' + NL
        + u'    return bad, err' + NL)

T_A3 = u"    live = REAL_DOOR()"
T_B3 = (u'    # 结构锁：自测全程不许往正式总线/正式落盘目录写任何一条合成投递' + NL
        + u'    _bad = polluted()[0]' + NL
        + u'    res.append(check(u"自测不许往正式总线投递（闸装在投递腿里，不靠每条测试记得换桩）",' + NL
        + u'                     u"；".join(_bad) if _bad else u"干净",' + NL
        + u'                     u"干净"))' + NL
        + u'    res.append(check(u"闸关掉时两条车道腿都退 blocked（不许退成静默成功）",' + NL
        + u'                     str([S.push_bolt_words(u"selftestx.md", 61, [u"L1 fake"]),' + NL
        + u'                          S.push_gate_words(u"selftestx.md", u"fake", 2)]),' + NL
        + u'                     u"[\'blocked\', \'blocked\']"))' + NL
        + u'    # 负对照：闸开回去、拿记录桩接 argv ⇒ 两条腿必须真去投递，' + NL
        + u'    # 否则上面那格就是假绿（腿本身断了也会显示"没投递"）。落盘指临时目录，正式目录不动。' + NL
        + u'    _tmp = tempfile.mkdtemp(prefix="cnx_negctl_")' + NL
        + u'    _bwd, _gwd = S.BOLT_WORDS_DIR, S.GATE_WORDS_DIR' + NL
        + u'    S.BOLT_WORDS_DIR, S.GATE_WORDS_DIR = _tmp, _tmp' + NL
        + u'    _S2.subprocess = _Fake()' + NL
        + u'    S.SEND["allow"] = True' + NL
        + u'    try:' + NL
        + u'        _neg = [S.push_bolt_words(u"negctl99ab_1731.md", 61, [u"L1 fake"]),' + NL
        + u'              S.push_gate_words(u"negctl99ab_1731.md", u"fake", 2)]' + NL
        + u'        _cmd2 = " ".join(_cap.get("cmd", []))' + NL
        + u'    finally:' + NL
        + u'        S.SEND["allow"] = False' + NL
        + u'        _S2.subprocess = _realrun' + NL
        + u'        S.BOLT_WORDS_DIR, S.GATE_WORDS_DIR = _bwd, _gwd' + NL
        + u'    res.append(check(u"负对照：闸开回去两条腿都真投递、且点名发给写它的那扇窗",' + NL
        + u'                     str(_neg == [u"sent", u"sent"] and u"qoder:negctl99ab" in _cmd2), "True"))' + NL
        + u'    res.append(check(u"负对照之后仍没一条合成投递落进正式账本或正式落盘目录",' + NL
        + u'                     u"；".join(polluted()[0]) or u"干净", u"干净"))' + NL
        + u'    import shutil as _sh' + NL
        + u'    _sh.rmtree(_tmp, ignore_errors=True)' + NL
        + T_A3)

PAIRS_SENT = [(S_A1, S_B1), (S_A2, S_B2), (S_A3, S_B3), (S_A4, S_B4)]
PAIRS_SELF = [(T_A1, T_B1), (T_A2, T_B2), (T_A3, T_B3)]



def main():
    new_sent = R(SENT, PAIRS_SENT)
    new_self = R(SELF, PAIRS_SELF)
    if new_sent is None or new_self is None:
        return 1
    if "--check" in sys.argv:
        print(u"两份文件各锚全命中一次、改后语法都过（--check，未写盘）")
        return 0
    io.open(SENT, "w", encoding="utf-8", newline=NL).write(new_sent)
    io.open(SELF, "w", encoding="utf-8", newline=NL).write(new_self)
    print(u"已打补丁：哨兵三条投递腿认总闸；老自测关闸＋三条锁＋负对照")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
