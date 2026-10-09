# -*- coding: utf-8 -*-
u"""更新 INVITE_CODEX.txt：把"两侧没有字段能互指、值守不猜"换成真抽到的窗名。

为什么必须改（20:28 现读）：那份件现在写着"活跃 thread 与 bbfix1 没有字段能互指 ⇒
还是��人看一眼窗口才知道"。20:23 我把那座库翻了一遍——**确实没有标题列**
（表只有 thread_turns／thread_items／thread_history_projection_state／thread_realtime_items），
但身份句包在 thread_items 的头十几条里：子窗首条 userMessage 只是 "continue"，
真正的委派书是上一次 `create_thread` 的 functionCallOutput，里面有
`<source_thread_id>` 与 `You are CityNexus Codex Window R.`

⇒ 那扇窗现在有名字了。件里继续写"对不上"就是在**把已经查到的事实说成查不到**——
正是我自己那条纪律（负结论必须先列实物；"没读"和"读不到"长得一样）。

安全：只改这份**纯文本接入件**（人粘的东西），不碰 bus.py／board.py／任何腿。
自证：改完回读关键词都在；脚本自己按 Window R 这一名生成 id 建议并把名字原样带给那扇窗。
"""
import io
import os
import re
import sys

# 接入件在 agent_bus/（人粘的东西与 BB 机同目录），**不在 patrol/**——
# 我第一版把 HERE 当成它的目录，直接 FileNotFoundError（20:28 实测）。
INV = u"D:/moodle/agent_bus/INVITE_CODEX.txt"   # 现读真路径（20:29 实测：agent_bus 在 D:/moodle 下，不在 _qoder_cmdr_ref_20260921 里）

OLD_TAIL = u"""#   · 活跃 thread 现读只有 **1 枚**（01a10cd0…，近 90 分 2 轮），与 bbfix1 **没有字段能互指** ⇒
#     那个 thread 是不是另一扇新车道，仍要人看一眼窗口才知道（值守不猜：猜错＝给不相干会话装身份）。
#   · 所以：**先确认窗口是谁**；是新车道再粘下面那段，是 bbfix1 就不用动。
#   （巡检第⑦格那个"缺口多 0 枚"只说明数量对得上，不等于接上了）"""

NEW_TAIL = u"""#   · 近 90 分活跃 thread 现读 **1 枚**（01a10cd0-05e8…），窗名**抽出来了**（20:23–20:24 实测）：
#     它的首条 userMessage 只是 "continue"，身份包在上一次 `create_thread` 的 functionCallOutput 里
#     —— 父窗 `01a0c796-93d8-7621-9157-161a973cab50` 写给子窗的委派书，原文
#     「You are CityNexus Codex Window R.」
#     （那座库里**确实没有标题列**，表只有 thread_turns／thread_items／
#       thread_history_projection_state／thread_realtime_items——所以当时说"对不上"是对的，
#       只是那话说早了：身份不在标题列里，在 thread_items 的正文里。）
#   ⇒ 那扇窗叫 **CityNexus Codex Window R**，它**不是** bbfix1（bbfix1 是 10-04 19:0x 交过真 deliver
#     的另一扇，早接上了）。巡检第⑦格现在按**窗名**判缺口，报的是"缺口 1 扇：CityNexus Codex Window R"。
#   ⇒ 所以：**你就是那扇窗的话，粘下面那段**（id 建议 `codex:winR`）；
#     已经接过、或者你就是 bbfix1，就不用动。
#   抽出窗名的工具：`live_checks/patrol/_codex_window_id_r1.py`（只读，可重跑）。"""

OLD_GAPNOTE = u"""（巡检第⑦格那个"缺口多 0 枚"只说明数量对得上，不等于接上了）"""


def main():
    t = io.open(INV, encoding="utf-8", newline="").read()
    if u"CityNexus Codex Window R" in t:
        print(u"已在 ⇒ 不重复改")
        return 0
    n = t.count(OLD_TAIL)
    if n != 1:
        print(u"REFUSE：锚命中 %d 次（应为 1），未写盘" % n)
        i = t.find(u"活跃 thread 现读")
        print(u"现读那段：\n%s" % t[max(0, i - 300):i + 500])
        return 1
    new = t.replace(OLD_TAIL, NEW_TAIL, 1)
    if OLD_GAPNOTE in new:
        new = new.replace(OLD_GAPNOTE, u"", 1)
    if u"CityNexus Codex Window R" not in new:
        print(u"REFUSE：新文里没成形，未写盘")
        return 1
    bak = INV + u".bak_winR_2028"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(bak and t)
    io.open(INV, "w", encoding="utf-8", newline="").write(new)
    back = io.open(INV, encoding="utf-8", errors="replace").read()
    print(u"已写 %s（备份 %s）｜%d → %d 字节"
          % (os.path.basename(INV), os.path.basename(bak), len(t), len(back)))
    for k in (u"CityNexus Codex Window R", u"01a0c796", u"codex:winR",
              u"_codex_window_id_r1.py"):
        print(u"  回读含「%s」：%s" % (k, k in back))
    print(u"  旧那句『没有字段能互指』还在：%s（应为 False）"
          % (u"没有字段能互指**" in back))
    return 0


if __name__ == "__main__":
    sys.exit(main())