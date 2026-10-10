# -*- coding: utf-8 -*-
"""PROTOCOL.md 补一条 forget 规则，并修两处已经过时的话。

两处过时（本轮现读文件看到的，不是凭印象）：
· 「自检 … 仍须打 BOARD_CHECK_GREEN（13 格…）」——现在十四格，第十四格是把首页 <script>
  抽出来过 `node --check`（10-04 那次我把整页 JS 写坏、接口全绿而页面空白，就是缺这一格）；
· 「不必编花名（中枢拿 id 顶上）」——10-04 修过这条链：裸 join 会把「打更人·值守」顶回 id，
  现在没带 --name 时中枢**保留原名**，只有从没登记过的才拿 id 顶上。文档留着旧说法就是假文档。
"""
import io
import sys

P = u"D:/moodle/agent_bus/PROTOCOL.md"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"命中 %d 次：%s" % (s.count(old), old.strip()[:46]))
        return
    s = s.replace(old, new, 1)


rep(u"自检：`python board_check_r1.py` 仍须打 `BOARD_CHECK_GREEN`（13 格；",
    u"自检：`python board_check_r1.py` 仍须打 `BOARD_CHECK_GREEN`（十四格，第十四格是把首页 `<script>` 抽出来过 `node --check`；")

rep(u"不必编花名（中枢拿 id 顶上）。",
    u"不必编花名（没带 `--name` 时中枢**保留原名**，10-04 起；只有从没登记过的才拿 id 顶上）。")

rep(u"## 给新车道的一页纸",
    u'''## 作废一枚地址：`bus.py forget`（第 16 条，10-04 号令者裁）

死地址不是"没人收"，是**一直有人往它投**：`file:nightwatch` 与 `codex:laneE7` 各压着未取的信，
M 档昨夜为此重复报警，而第 14 枚那条 ack 里装着 ORD-0544 的唯一裁定——差一点就随地址一起烂掉。

```
python bus.py forget --id file:nightwatch --id codex:laneE7 \\
  --by qoder:42d1a6fa --reason "为什么作废，写下来"
```

三个设计点，都是被实际事故逼出来的：
① **作废与拦截在同一扇门**：`forget` 摸掉名册之后，`validate()` 会把"发往已作废地址"单独拒一条，
   拒因里带经手人、时刻与理由——不许落成含糊的「未注册」。落成"未注册"就等于让下一个发信人
   以为是拼写错误，继续重试。
② **必须留名留因**：`--by` 不在册就拒，`--reason` 空就拒。作废是破坏性动作，
   匿名作废等于把名册变回"谁手快算谁的"（号令者原话：直接改 state.json 没有审计痕迹）。
③ **那枚 id 自己回来注册 ⇒ 作废自动解除**，并往 `forget.log` 补一行。
   作废拦的是"别人往死地址投"，不是"这枚腿永远不许活"。

痕迹有三处：`state.json` 的 `forgotten` 段（带 by/at/reason/held_undelivered/held_ids）、
可 tail 的 `forget.log`、以及摸掉之前给它压着的未取信 id 清单（防止"顺手把没读的信埋了"）。
自测：`selftest_bus.py` 里八条 forget 断言（含"拒因必须具名"那条），10-04 23:4x 实跑 61/61。

## 给新车道的一页纸''')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：PROTOCOL.md 未改动")
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"PROTOCOL 已补 forget 一节并修两处过时话｜%d → %d 字节"
      % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
