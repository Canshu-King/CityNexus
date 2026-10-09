import io, os, time

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
STAMP = time.strftime("%H%M")
OUT = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "6efab655_" + STAMP + ".md")

NEW = "b2fccfdf2728bbb025c3c09db36ce5ed9401ee4c"
OLD = "253d43641aad2e173fd495c611eccad14215f1fe"
PF = "2b8b3e38088227a05dcb9460bea03a1d888159e5"
RB = "b7cd3ea847fbd513df85028ec08281c21faede1c"
RULER = "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"
D33 = "0413e55634e9c6953ea88a4b01a17b8afd7ac88a"

body = u"""### 6efab655 · 号令者实例 A · 落下一笔产品字节（花费面那句），手机链静态口的根因查到我方并把服务恢复了；另裁三条与一份具名指引

**一、落地（权威线由我经门移动，一次快进）**

- 现读现尖 `@@OLD@@` → 落完 `@@NEW@@`（`git ls-remote --refs` 与门内 `branches_route` 两条路同值，`both_routes_agree: true`）。
- 落的是车道 6a150e1e 的花费面那句：候选 `review/6a150e1e-spend-off-day-sentence-r7` 头 `153ca0dcf56494a71c8bfeec8216335351c39bb0`，我先跑只读复切得 `@@NEW@@`，三枚文件逐枚与车道那份 blob 相同（`blob_equality_all: true`），推的是我自己那枚复切件 `review/cmdr-recut-ord0504-spend-r7`。
- 带上的产品字节两枚：`frontend/src/features/trip/SpendPanel.tsx` 与 `frontend/src/features/trip/spendCopy.ts`（新增件），另有一枚 e2e 件；`file_sets.intersection` 为空，未覆盖任何人字节。
- 门内两臂：污点尺（blob `@@RULER@@`）在这一笔上视野内两枚文件、屏上格数落前后同为六格（零增长，不是我把尺调宽）；`npm run build` 与 builder 退出码同为 `0`、产物入口 `index-DLbc3Q3N.js`。回执件 `evidence/cmdr-landing-ord0504-1646/preflight_r1.json`，blob `@@PF@@`，5139 字节，BYTE-LEVEL MATCH。
- 具名：**测试我没跑**（`collect_exit` 与 `test_exit` 在回执里都是 null）⇒ `NOT_EXECUTED_BY_CMDR`；那枚 e2e 要 `npm run dev` 才跑得起，跑出来的也不是发布证据。

**二、落地后的亲测（新代次，私有栈 :49812 服务 `_build_b2fccfd`）**

- 被读的那一代：入口 `index-DLbc3Q3N.js`，服务字节与磁盘字节同为 1624131 字节、sha256 头十六位 `0ad6efd8853b974d`（件 blob `@@RB@@`，6592 字节）。
- 花费屏在新代次正常出字，中文臂逐字读到：这台服务器答出了 9 项有金额的既成事实，另有 0 项它记着但没有价。三天的估算相加 432.00 加 48.00 加 12.00 等于 492.00，与币种合计那句「估算 CNY 492.00」对得上（同一件）。
- **那句新句没上屏，但不是没修**：它只在「有金额却落不进任何一天」的行存在时才画（`frontend/src/features/trip/SpendPanel.tsx:78` 算计数、`:142` 才渲染）。我这枚库里 376 段全部有 `depart_at`、有金额而无时刻的行数为零，十二程扫下来该句零次上屏、键名 `spend.offDay` 也零次泄漏（件 blob `@@RB@@`）⇒ 分母不存在，本格写 `NOT_REACHED_BY_CMDR`，唯一供给是车道那枚 e2e 夹具（`frontend/e2e/qoder-6a150e1e-spend-faces-day24-r1.spec.ts`），我不自己造数据冒充真机读数。

**三、手机链静态口那条报警：根因在我方，已恢复**

- 车道 82f55d8a 报「在听但不回话」。我独立复量：`:4783` 有 LISTENING 行，五枚路径（根、`/v8/hub`、`/index.html`、`/favicon.svg`、入口资产）全部在个位数毫秒内拿不到响应（`RemoteDisconnected`，不是超时）；同台 api 门 `:4787` 健康，`/api/v1/journeys` 回 http_status=200、1566 字节，`/api/v1/health` 回 http_status=200、113 字节。
- 根因：那枚监听进程服务的是 `_build_day33/frontend/dist`，而这棵导出树在盘上已经不存在（`ls` 现读报无此目录），于是每个请求在写出响应之前就死掉——**是我方 `_build_*` 清扫把它删了**，不是产品、也不是车道动的手。
- 处置：写了一把幂等起复件 `_cmdr_lan_4783_restore_r1.py`，先读回监听 PID 的命令行、**只允许**它是 `_cmdr_lan_static_api_r1.py`（不是就 REFUSED_FOREIGN_OWNER 退出、不动任何进程），再按那枚被删产物对应的 commit `@@D33@@` 重出 dist、放回同一端口。两遍跑：五枚路径全回 http_status=200，入口 `index-BcQ9VAso.js` 服务字节与磁盘字节同为 1622092 字节（件 blob `@@RB@@` 的 `lan_4783_restore` 段）。
- 具名限制：重出的产物与被删那份**是否逐字节相同无法证明**（旧件已无、当时没留指纹），只能说同源同 commit 同工具链；手机上那代次仍是 day33 那一代（常设裁语 Q61 不许我再换手机代），所以本轮落地的顶栏白名单与花费那句要等下一次具名换代才会上手机。api 门 `:4787` 与 `:8000` 那侧我一字未动、零次重启。

**四、三条裁决**

- 车道 42d1a6fa 的落地顺序表：形状有用，但它把 `review/2d2d7428-ord0509-ink-survey-routes-r5` 与 `review/6a150e1e-emitter-door-verify-r7` 同时列进「同批就能落」与「先别点（代次已过期）」两类（我把两行名单按枝名对撞过）。常设口径定为：**表只当排序提示，点不点以我自己那把只读复算为准**（`cmdr_recut_r1.py` 的 ff／RECUT／ABORT 判定加 `file_sets.intersection` 是否为空）。请 42d1a6fa 在下一版给每枚枝只判一类，判两类的情形直接落进「先别点」。
- 同一条车道问的 F 档与 M 档双报警：裁「**维持两档各管一头**」，M 档那一行只放指向 F 档读数的指针、不重复计数。理由就是它自己那一课：同一件事两档各报一次会造自回声，越催越响。
- 车道 1ba48dbf 那块被门拒（退出码九，门原话：coordinate … does not resolve；那枚四十位我故意不在本块里复述，因为不可解析的逐字四十位会让整块被门咬掉，包括我这段自报）。我查了：它报的是入口 JS 的**磁盘字节指纹**，不是 git 对象，所以任何 fetch 都取不回它——门拒得对。具名指引（不改它的字）：那一行要么换成可 `git cat-file` 的 40 位（已发布证据件的 blob），要么换成 `path:line` 锚；只对磁盘字节做断言时，把指纹落成一枚 `.txt` 件再发布，然后引那枚件的 blob。

**五、没改善的部分（具名）**

- 花费面那句在真屏上仍 `NOT_REACHED_BY_CMDR`（分母缺，见第二节），也就是说这笔落地虽然进了权威线，用户此刻在花屏上看见的还是老样子。
- 手机链那代次没变（day33），本轮两笔落地对用户手机不可见；要可见需要一次具名换代，那是人类的决定，我不在留言口追加新请求。
- 我名下仍欠：ORD-0520 那枚提交键的修法（ORD-0575 已派，零字节落地）、闭合查找尺接进落地门 `NOT_IN_GATE_YET_BY_CMDR`、普查白名单缺 `JSON` 一枚。
- 表里另外十四枚待落枝本轮一枚未动（我只落了这一枚产品字节候选，其余按「做完一件交一件」留到下一轮）。
"""

for k, v in (("@@OLD@@", OLD), ("@@NEW@@", NEW), ("@@PF@@", PF), ("@@RB@@", RB),
             ("@@RULER@@", RULER), ("@@D33@@", D33)):
    body = body.replace(k, v)
assert "@@" not in body
closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
