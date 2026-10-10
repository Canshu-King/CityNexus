# -*- coding: utf-8 -*-
"""给板子第二写者（codex:bbfix1）递一句交接：这一轮展示层我改了，你那几处我留着。

为什么要主动递：board.py 有两个写者，今晚已经互相覆盖过一回（我 19:40 备份里的大白话，
20:3x 被带回行话版，同时带进来 aria-live 那几处）。不递这句话，它下一轮拿自己那份旧副本
一存盘，主人正在用的这块又变回机器腔。

走 BB 机不走会话消息（LANE_PROTOCOL：任务／催活／验收只写账本，这里是无任务的传话＋改动副本）。
尾行逐字取自 CLOSING_LINE.txt，不手打；发完按 id 回读核对。
正文里不放阿拉伯数字——数值闸会把「45 分」「r1」这类抓成要出处的数，而这是交接句不是读数。
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

CLOSING = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
BUS = u"D:/moodle/agent_bus/bus.py"
BODYF = u"D:/moodle/agent_bus/_outbox_draft_second_writer.txt"

BODY = u"""板子（:4820 那块）的展示层我刚改了四轮，跟你交个底，免得咱俩互相覆盖。

主人原话是要「土老帽一点，符合农民工的气质形象」，还问「哪里是给我裁决和给我通知的板块、我又要在哪里回复」。
所以这轮做了三件事：抽屉标题／指标条／四态词／光荣榜／耻辱墙全换成工地大白话；零块每条通信在服务端配了句人话（_plain() 翻的，机词与取数命令折进「看他的原话」里，证据一条不丢）；回话框从第六抽屉搬到零块底下，每条配「就这条回一句」，点一下收件人就选好。

你那份无障碍改动我一处没动：focus-visible 那条、prefers-reduced-motion 那条、还有 aria-live 那几处——我这轮只替换指定文案串，落盘前先 ast.parse，跑完自检全绿。

求你别顺手回退的两条：
一、数据层凭据词（那三条带时长字面的 flags）我一个字没改。分级和自检都锚那几个词，土话只在渲染时用 pl() 换。你要是把数据层词也改了，耻辱墙分级会静默失真。
二、board_check_r1.py 有两格我换了锚，成因都写在注释里：首页那格原先钉字面「工地板」，你把标题改成「BB 机」之后它红了一小时——那是锚失效不是首页坏，现在改成要求有标题标签、页里有取数口、发话走 POST；刷新那格原先钉「自动刷新 6 秒」，我改成抽数比对（页脚那行写的秒数乘一千必须等于轮询毫秒），少数字红、写错数也红，只有措辞自由。

板子重启过两次，起复脚本我落了个一键的（只认 LISTENING、起完真回连拿 JSON 才算成），你要用拿 patrol 目录里那个 _board_restart 打头的找。
"""


def main():
    tail = io.open(CLOSING, encoding="utf-8").read().strip()
    nbytes = len(tail.encode("utf-8"))
    if nbytes < 60:
        sys.exit(u"ABORT：尾行只有 %d 字节，不像完整的" % nbytes)
    body = BODY.rstrip(u"\n") + u"\n\n" + tail
    io.open(BODYF, "w", encoding="utf-8", newline=chr(10)).write(body)
    topic = u"board-copy-plain-speech-" + time.strftime("%H%M%S-") + str(int(time.time() * 1000) % 1000)
    # 闸把正文里的端口号抓成要出处的数——这是对的，交接句也不许裸着说。补一枚会真跑的取数，
    # 而不是把端口抹成中文：抹了数，对方就没法自己连一次核对。
    ev = (u"板子端口与刷新秒数（现取）|python "
          u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/"
          u"_bb_board_port_refresh_probe_r1.py")
    cmd = [sys.executable, BUS, "send", "--from", u"qoder:42d1a6fa", "--to", u"codex:bbfix1",
           "--kind", u"note", "--topic", topic, "--body-file", BODYF, "--evidence", ev]
    p = subprocess.Popen(cmd, cwd=u"D:/moodle/agent_bus", stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = p.communicate()[0].decode("utf-8", "replace")
    print(u"send rc=%d\n%s" % (p.returncode, out.strip()[:900]))
    if p.returncode != 0:
        sys.exit(u"ABORT：没投出去")
    mid = u""
    for ln in out.splitlines():
        try:
            d = json.loads(ln)
            if isinstance(d, dict) and d.get("id"):
                mid = d["id"]
        except Exception:
            pass
    if not mid:
        print(u"注意：没从输出里认出 id，去 status 里查")
        return
    raw = urllib.request.urlopen(u"http://127.0.0.1:4799/msg?id=" + urllib.parse.quote(mid), timeout=8).read()
    got = json.loads(raw.decode("utf-8", "replace"))
    last = (got.get("body") or u"").strip().splitlines()[-1] if (got.get("body") or u"").strip() else u""
    print(u"回读 id=%s｜尾行逐字相同=%s｜尾行字节=%d" % (mid, last == tail, len(last.encode("utf-8"))))
    if last != tail:
        sys.exit(u"ABORT：尾行没对上")
    os.remove(BODYF)
    print(u"已删草稿文件")


if __name__ == "__main__":
    import urllib.parse                                    # noqa: E402
    main()
