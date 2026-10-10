# -*- coding: utf-8 -*-
"""把号令者 02:45「敲醒派单 · 十二车道各具名一手」与 03:16 裁语块里**逐字属于某扇车道**的那一行，
编成一记可发的敲门件（尾行由 _knock_lane_r1.py 从 CLOSING_LINE.txt 逐字接上）。

为什么要它：04:00 号令者在账本里明写「10 条车道仍静默中，等 02:45 派单块与 03:16 裁语被它们读到」——
车道不轮询总线，话就躺在两处地方没人读。传话只能按收件人 id 逐字相同那一行来，
所以这里做的是「按 id 切片 + 机读成对」，不是把整块复述给十扇窗（复述会串单）。

边界：只读账本、只在本目录写敲门件，不动账本、不动权威线、不代插。
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = u"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
PYEXE = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 8ac89982 与 0afdb49b 不在此列：04:59:39 那一眼（_why_stopped_r1.py 25）它们还在写，
# 静默尺不敲在写的窗——敲了就是把话丢给一个正握着键盘的人。
LANES = u"6a150e1e 82f55d8a 1ba48dbf cff87c64 5a53846b 6a773af1 e766b154 2d2d7428 da46954a 1d64acf5".split()
BLOCKS = (u"### CMDR 02:45", u"### CMDR 03:16")
# 04:00 号令者块里点名「还欠哪一手」的那一格（逐字抄，不猜）
WAIT_LINE = u"### CMDR 04:00"


def block(text, head):
    i = text.find(head)
    if i < 0:
        return u""
    j = text.find(u"\n### ", i + 5)
    return text[i:j if j > 0 else len(text)]


def lane_lines(blk, lane):
    out = []
    for ln in blk.split(u"\n"):
        if lane in ln and re.search(u"`%s`" % lane, ln):
            out.append(ln.strip())
    return out


def main():
    text = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    blks = [block(text, h) for h in BLOCKS]
    names = [h.split(u"\n")[0] for h in blks if h.strip()]
    print(u"取到块 %d 枚：%s" % (len(blks), u" ｜ ".join(x[:26] for x in names)))
    wait = block(text, WAIT_LINE)
    m = re.search(u"三、等谁[^\n]*", wait)
    wail = m.group(0) if m else u""
    made = []
    for lane in LANES:
        parts = []
        for b in blks:
            for ln in lane_lines(b, lane):
                parts.append(ln)
        if not parts:
            print(u"%s｜名册里这扇在这两块里没有逐字点名的行 ⇒ 不编敲门件（不替它猜单）" % lane)
            continue
        body = [u"【传话 · 号令者 02:45 具名派单（+03:16 裁语）——你停在这两格之前，没读到】",
                u"依据：账本 `### CMDR 02:45 敲醒派单 · 十二车道各具名一手`；`### CMDR 04:00` 第三节逐字写着"
                u"『10 条车道仍静默中，等 02:45 派单块与 03:16 裁语被它们读到』。"
                u"我不是号令者：不派单、不裁语，只把**逐字写在你 id 名下那一行**搬来。",
                u""]
        for p in parts:
            body.append(u"你名下那一行（逐字）：" if p is parts[0] else u"")
            body.append(u"  · " + p)
        body.append(u"")
        # 尖一律从账本现取，不手打（手打的号出事过：0afdb49b 04:26 那块就是）
        tip18 = re.search(u"权威尖[^`\n]{0,6}`([0-9a-f]{40})`", block(text, u"### CMDR 04:18"))
        tip45 = re.search(u"权威尖[^`\n]{0,6}`([0-9a-f]{40})`", blks[0])
        if tip18 and tip45:
            body.append(u"代次提醒（不是我量的，逐字取自账本）：`### CMDR 04:18 换代` 写权威尖 = "
                        u"`%s`；02:45 那块里的尖 `%s` 是它写块那一刻的现读。"
                        % (tip18.group(1), tip45.group(1)))
            body.append(u"动手前请自己 `git ls-remote` 复核，别在我这句转述上建候选。")
        else:
            body.append(u"代次提醒：两块里的尖我这次没能从账本逐字取出（正则没命中），"
                        u"所以这里不写任何尖号——请自己 `git ls-remote` 现读取代次。")
        if wail and lane in wail:
            body.append(u"")
            body.append(u"另：04:00 块第三节逐字提到你这一扇 —— " + wail)
        body.append(u"")
        body.append(u"取回与回话（工地 BB 机，本机 127.0.0.1:4799，不通网也能用）：")
        body.append(u"  python D:/moodle/agent_bus/bus.py read --agent qoder:%s --all" % lane)
        body.append(u"细则 D:/moodle/agent_bus/PROTOCOL.md；05:0x 起「数字要带出处」这条已不再只看证据输出的头 400 字节。")
        body.append(u"交件走收件口 `D:/moodle/_qoder_ledger_inbox/%s_<HHMM>.md`（首行 `### `，"
                    u"过 `claim_coordinate_check_r7.py --text … --expect-clean` 报 Q43_GATE_GREEN）；"
                    u"账本由号令者代插，别自己写 CITYNEXUS_AGENT_CONTROL.md。" % lane)
        bp = os.path.join(HERE, "_relay_body_%s.txt" % lane)
        io.open(bp, "w", encoding="utf-8", newline="\n").write(u"\n".join(body))
        r = subprocess.run([PYEXE, os.path.join(HERE, "_knock_lane_r1.py"), lane, bp],
                           capture_output=True)
        o = (r.stdout or b"").decode("utf-8", "replace")
        fn = re.search(u"\[落盘 ([^｜]+)｜", o)
        mk = re.search(u"【值守敲门 · [^】]+】", o)
        print(u"%s｜%d 行逐字引文｜退 %d｜%s" % (lane, len(parts), r.returncode,
                                            fn.group(1) if fn else u"没落盘：" + o[:120]))
        if r.returncode == 0:
            made.append((lane, os.path.join(HERE, fn.group(1)), mk.group(0) if mk else u""))
    print(u"编成 %d 记（共 %d 扇在册）" % (len(made), len(LANES)))
    io.open(os.path.join(HERE, "_relay_0245_manifest.txt"), "w", encoding="utf-8", newline="\n").write(
        u"\n".join(u"%s\t%s\t%s" % m for m in made))
    return 0


if __name__ == "__main__":
    sys.exit(main())
