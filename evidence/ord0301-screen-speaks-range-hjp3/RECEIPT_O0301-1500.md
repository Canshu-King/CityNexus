# ORD-0301 · 把「屏幕替服务器说话」的射程量成一张表 · HJ-P3 aad2d1f2

> **measured_on = `90d29a172e18…`**（git ls-remote refs/heads/mirror/integration-frontend-apple-pass1，git ls-remote of refs/heads/mirror/integration-frontend-apple-pass1, re-read at export time by ORD-0300 (same commit, tree reused) 现场重读）· 被测产物 = 我从这棵尖自己 `vite build` 出来的私有件 `index-BN1w-xlK.js` / sha256 `57c2a927f9e65ca0…` · 在服预览那枚 `dist/index.html` **一个字节没动**（sha256 `7aa9afc77bcb`，mtime 2026-09-25T08:33:06+0800，引用的是 `index-xKIGmoBz.js`，与我面的 `index-BN1w-xlK.js` 不是同一枚）。
> **`derived_result` = null**（那是 verifier 的字）；`claimed_result = MEASURED_NOT_GRADED`。Q25：本件每一个毫秒数都是这一代今天量出来的，没有一个从 0300/0291 搬来。

## 0. 一句话（大白话）
服务器**只要答了一个 HTTP 状态**，屏幕上那张卡就必须说是服务器的事。今天这条路上有 7 枚结局做不到这一点，而且原因不是"它不认识 500"——**是它拿不到一个 JSON 对象**：`serverReasonSentence` 在 `body` 为 null 的时候直接去读 `body.detail`，抛出去的错误被整段 try 的大 `catch` 接走，于是写成「连不上服务端」，连「技术详情」整块都不再存在（`<details>` 数 = 0）。

## 1. 判据怎么落的（不是我事后挑的）
```text
规则原文            ：服务器答了 ⇒ 屏幕不许把原因归给网络
answered            ：被点那一腿在浏览器里拿到了 HTTP 状态（页面 fetch 钩子记的；无钩子那臂用源站自己的记账回读）
blames_network      ：屏上 painted 的第一行 == 连不上服务端（读 innerText，不读 data 属性；data-result-status 只当旁证）
判定                ：answered ∧ blames_network ⇒ MISLEADS ｜ answered ∧ ¬blames_network ⇒ HONEST ｜ ¬answered ⇒ HONEST（确实没人答）
走不到那张卡        ：NOT_MEASURED + 旅客实际停在的另一张卡的原文（secondary_surface）
结局卡从未出现      ：NOT_MEASURED + 观察帽毫秒数
谁答的              ：product ｜ my-origin ｜ vite-proxy ｜ none —— 每一行都点名，因为 500 分两种 500
```

## 2. 表（每行 = 结局 / 服务端读数 / 屏幕原话 / 是否「连不上服务端」/ details / 判定）

| # | 结局（下单时那一类） | 服务端读数（状态·类型·字节·毫秒·谁答的） | 屏幕原话（painted 第一行） | 「连不上服务端」 | `<details>` | 判定 |
|---|---|---|---|---|---|---|
| 1 | ① 服务器答 500 且正文无 code/message | 500 · text/plain; charset=utf-8 · 21 B · 32209 ms · product | 连不上服务端 | True | 0 | **MISLEADS** |
| 2 | ① 同一形状但 250 ms 内答完（把时长从判据里摘出去） | 500 · text/plain; charset=utf-8 · 21 B · 259 ms · my-origin | 连不上服务端 | True | 0 | **MISLEADS** |
| 3 | ① 同一形状但 35 s 后才答 | 500 · text/plain; charset=utf-8 · 21 B · 35006 ms · my-origin | 连不上服务端 | True | 0 | **MISLEADS** |
| 4 | ① 同一臂、fetch 钩子完全不装 | 500 · text/plain; charset=utf-8 · None B · None ms · my-origin | 连不上服务端 | True | 0 | **MISLEADS** |
| 5 | ② 服务器答 500 且正文带具名 code（产品自己那枚真信封的字节） | 500 · application/json · 1443 B · 260 ms · my-origin | 服务端处理失败 | False | 1 | **HONEST** |
| 6 | ③ 503 + 同一枚信封字节 | 503 · application/json · 1443 B · 257 ms · my-origin | 服务端处理失败 | False | 1 | **HONEST** |
| 7 | ③ 502 + 同一枚信封字节 | 502 · application/json · 1443 B · 256 ms · my-origin | 服务端处理失败 | False | 1 | **HONEST** |
| 8 | ③ 504 + 同一枚信封字节 | 504 · application/json · 1443 B · 255 ms · my-origin | 服务端处理失败 | False | 1 | **HONEST** |
| 9 | ③ 503 但网关那种纯文本正文 | 503 · text/plain; charset=utf-8 · 19 B · 255 ms · my-origin | 连不上服务端 | True | 0 | **MISLEADS** |
| 10 | ④ 连接被拒（后端端口上没人听） | None · — · None B · None ms · vite-proxy | （无结局卡） | False | 1 | **NOT_MEASURED** |
| 11 | ④ 源站收了请求就断（一个响应字节都不写） | 500 · text/plain · 0 B · 6 ms · vite-proxy | 连不上服务端 | True | 0 | **MISLEADS** |
| 12 | ⑤ 写腿无人应答（客户端先放弃？） | None · — · None B · None ms · none | （无结局卡） | False | 0 | **NOT_MEASURED** |
| 13 | ⑤ 读腿无人应答（客户端 12 s 期限先放弃） | None · — · None B · None ms · none | （无结局卡） | False | 1 | **NOT_MEASURED** |
| 14 | 正控：产品今天真发的那枚具名 422 | 422 · application/json · 1443 B · 15 ms · product | 这次排不出方案：数据不够，不是你说的不对 | False | 1 | **HONEST** |
| 15 | 机制臂：500 + application/json + 正文就是 null | 500 · application/json · 4 B · 255 ms · my-origin | 连不上服务端 | True | 0 | **MISLEADS** |
| 16 | 机制臂：500 + application/json + 正文是 {} | 500 · application/json · 2 B · 255 ms · my-origin | 服务端处理失败 | False | 1 | **HONEST** |
| 17 | 机制臂：答了 500 但正文被截短（Content-Length 说 21 只写 5） | 500 · text/plain; charset=utf-8 · None B · None ms · my-origin | （无结局卡） | False | 0 | **NOT_MEASURED** |

读法说明：第 4 行的字节/毫秒是 None —— 那一臂按设计**不装** fetch 钩子，它的服务端那半来自源站自己的记账（件里字段 `server_side_reading_from`）；第 12/13 行是"从来没结算"，第 17 行是"头说了 21 B 但只写了 5 B，浏览器读体永远不结束"，所以它们的字节数列同样是 None，而不是 0。

```text
判定合计   MISLEADS 7 ｜ HONEST 6 ｜ NOT_MEASURED 4   （共 17 行）
MISLEADS 行 R1、R2、R3、R4、R9、R11、R15
R10 走不到结局卡，旅客停在：「服务器 /  / 服务器这次没能把行程读出来 /  / 服务器自己报错了（HTTP 500）。这是它那边的问题，不是你填错了什么。可以重试；」→ 同一条规则打在另一张卡上 = HONEST
R13 走不到结局卡，旅客停在：「没有回音 /  / 等了 12 秒，这台服务器一个字也没回答 /  / 这一发读取到了期限仍然没有任何回答：服务器既没有拒绝，也没有答应。这」→ 同一条规则打在另一张卡上 = HONEST
```

## 3. 判别量不是状态码、也不是时长，是"正文能不能交出一个 JSON 对象"
同一枚 HTTP 500：正文 = 产品今天真发的那 1443 B 信封 ⇒ HONEST（标签 '服务器给出的原因' 下正是服务器原话 'No feasible plan candidates satisfy the journey constraints'，逐字相等 = True）
同一枚 HTTP 500、同一个 content-type：正文 = 'null' ⇒ MISLEADS（'连不上服务端'）；正文 = '{}' ⇒ HONEST（标签改口成 '这台设备自己的读数（服务器没给句子）'，因为服务器确实没给句子）
同一枚正文（21 B 纯文本 Internal Server Error）：HTTP 500 ⇒ MISLEADS、HTTP 503 ⇒ MISLEADS —— 换状态码不换命运
时长无关：259 ms（21 B）与 35006 ms（21 B）与 32209 ms（21 B，产品自己在锁上答的那发）三枚卡片一模一样 ⇒ True
没有仪器复跑：把 fetch 钩子整段拆掉（只留 localStorage 那一枚行程指针），同一句话、`<details>` 仍是 0 ⇒ True
反控两枚都拒（证明我用的是逐字相等不是"包含"）：标点漂移后仍相等 = False ｜ 后缀漂移后仍相等 = False
机械派生的四条：同一个状态换正文换命 = True ｜ 不同状态同一正文同命 = True ｜ null 与 {} 这一对分岔 = True ｜ 所有 MISLEADS 行都拿不到 JSON 对象 = True ｜ 所有 HONEST 且被答过的行都没抛 = True
```

## 4. 机制（这一格的红不是"翻译错了"，是一个抛穿）
```text
PlanWithAiSheet.tsx:147  在 function serverReasonCode(body: unknown): string 里：const detail = (body as { detail?: unknown }).detail;
PlanWithAiSheet.tsx:155  在 function serverReasonSentence(body: unknown): string | null 里：const detail = (body as { detail?: unknown }).detail;
两处读的都是 body 这个变量本身（只有上一行的 .error 带 ?）；body 在正文不是 JSON 对象时就是 null ⇒
    catch (cause) { … setResult({status: "NETWORK", failureReason: null})} ⇒ 「连不上服务端」＋没有 details。
浏览器侧的直接证据（我这台仪器 hook 了 Response.prototype.json，把被吞掉的拒绝原样记下来）：
    R1 · content-type text/plain; charset=utf-8 · Failed to execute 'json' on 'Response': Unexpected token 'I', "Internal S"... is not val
    R2 · content-type text/plain; charset=utf-8 · Failed to execute 'json' on 'Response': Unexpected token 'I', "Internal S"... is not val
    R3 · content-type text/plain; charset=utf-8 · Failed to execute 'json' on 'Response': Unexpected token 'I', "Internal S"... is not val
    R9 · content-type text/plain; charset=utf-8 · Failed to execute 'json' on 'Response': Unexpected token 'S', "Service Unavailable" is n
    R11 · content-type text/plain · Failed to execute 'json' on 'Response': Unexpected end of JSON input
注意 R15 那发：正文 'null' 是合法 JSON，response.json() 不抛，返回 null，仍然在 PlanWithAiSheet.tsx:155 行抛 —— 所以修的方向是"把 body 当可空"，不是"把 JSON 解析包一层 try"。
```

## 5. 五类结局落在哪（下单点名要的那五类，一类都没换成"等价物"）
```text
① 服务器答 500 且正文无 code/message   ⇒ 真件那一发 32209 ms / 21 B / text/plain; charset=utf-8，屏上 '连不上服务端' ⇒ MISLEADS（与 0300 同形，今天在案）
② 服务器答 500 但正文带具名 code        ⇒ 产品今天这条用户路发不出它（唯一 500 带信封的发射点是 main.py:3075 stay-options/generate，AI 面板不走它）；我用产品自己那枚真信封的字节把它答成 500 ⇒ HONEST，所以这一格的红**不是"引用不了"，是"该引用的时候它说没响应"**
③ 502 / 503 / 504                      ⇒ 带 JSON 信封三枚全 HONEST（标签 '服务器给出的原因'、details 1）；网关那种纯文本 503（19 B）⇒ MISLEADS —— 同一个 503，正文决定它会不会被说成网络问题
④ 连接被拒（后端不在）                  ⇒ 面 8565 的上游端口 8566 上没人听；**vite 代理自己**答 500 / text/plain / 0 B，结局卡走不到（旅客停在页面级那张 '服务器 /  / 服务器这次没能把行程读出来 /'，同一条规则打它 = HONEST）；另一枚"源站收了就断"同样由代理答 0 B，这张卡就是 '连不上服务端' ⇒ MISLEADS
⑤ 请求超时（客户端先放弃）              ⇒ 读腿会：GET 被静默时 12044 ms 处客户端自己期限，屏上 '没有回音 /  / 等了 12 秒，这台服务器一个字'（HONEST，确实没人答）；写腿不会：POST 被静默到 62000 ms 仍没有任何结局卡（details 0）—— 那 12 秒的常量在写分支短路，这一格是 NOT_MEASURED 而不是绿
⓪ 额外两格（不在单子里但同一条病）      ⇒ 正文 = null 的合法 JSON ⇒ MISLEADS；头说了 21 B 只写 5 B ⇒ 到 45000 ms 结局卡根本没出现，屏上停在等待态，既没期限也没名字
```

## 6. ORD-0296 那枚具名 503：今天还是拿不出来，但这次是门拦的
```text
产品自己的数（在进程内读它自己的配置，不是我猜的）  busy_timeout=30000 ms · default deadline=45000 ms · delta=15000 ms · verdict=WRITE_DEADLINE_CONFIG_OK
我这轮把 CITYNEXUS_WRITE_DEADLINE_MS 设成 8000 起了一次面：booted=False、exit_rc=1、日志里点名的错 = WriteDeadlineConfigurationError
含义：`main.py:427` 那扇启动门**真的在跑**（0300 我只能说"算术上够不着"，这次是"配置上一开机就死"）；要让服务器自己把那枚具名 503 发到这条路上，必须先允许一个门会拒绝的配置。
```

## 7. 现场 · 边界 · 我自曝
```text
端口：后端 8561、真件面 8562、可控源站 8563、可控面 8564、"上游不在"那张面 8565，故意留空的 8566 —— 全新一批，收尾后逐个回读为空（teardown_O0301.json）。
库：D:\moodle\_hjp3_0301_0925\o0301.s3db，由产品自己的 ensure_schema() 建、起面先删（R-SCHEMA-01）；`_live.db`/`_preview.db` 0 读写、`demo/reset` 0 次、`git apply` 0 次 —— 这三句不是空口，boundary_proof.json 里把我九个仪器文件里出现这些词的行逐行打了出来（唯一命中是本机边界文件的被查字符串清单与 docstring）。
用户链没动：在服 `dist/index.html` sha256 7aa9afc77bcb / mtime 2026-09-25T08:33:06+0800（引用 index-xKIGmoBz.js，与我面的 index-BN1w-xlK.js 不同一枚）；4781/4782 的监听进程创建时间 2026-09-24T16:25:57、2026-09-24T16:35:33，都早于我这一批 2026-09-25T14:29:08 ⇒ 0 重启。
凭据：rig 里每个子进程环境都先 pop 掉 DEEPSEEK_API_KEY（=True），我的文件里没有任何 sk- 形状串（命中 0 个）；AI 在我这套面上是关的。
自曝一：第一批臂跑完我发现源站的逐请求日志被我在换策略时 `unlink` 掉了 —— 那等于把每一行"服务端那半"的凭据删了。改成 append-only + 每臂快照之后，**17 行全部重跑了一遍**，本件所有数字来自第二遍；第一遍的工件留在目录里没删。
自曝二：驱动与仪器我自己写坏过三次 —— `WindowsPath % int`（两处，start 与 policy 各崩一次，崩的时候 backend 已经起来，我按端口逐个读命令行确认是我自己的进程才杀，没有盲杀）、页内 SCREEN 里引用了 Node 作用域的常量（`NET_CARD is not defined`，那一轮没有工件产出，run id O0301-143117 作废）、以及无仪器那臂一开始忘了塞行程指针结果停在 onboarding（第一次读数作废，修好后才是表里 R4）。
自曝三：表里"谁答的"那一列是我事后加硬的口径 —— ④ 那两枚 500 是 vite 代理写的，不是产品写的。如果按"任何 HTTP 回答都算服务器答了"，R11 记 MISLEADS；如果只算产品自己答，R11 应该降为 NOT_MEASURED。两种读法我都在件里给了字段（`answer_attributed_to` + `sibling_probe_outside_browser`），**不替你选**。
```

## 8. 尺子（Q38 口径，交前自己先跑）
```text
receipt RECEIPT_O0301-1500.json 97514 B blob_sha1 9035e162b69f171de7a5d57ec30fdeddd58f0e7e
cells 8 | overall Q38_GATE_GREEN | hard 0 [] | soft 0 []
  cell 0 | why_source why | why tokens 8 | own hits 7 | unique hits 0 | shares why with []
  cell 1 | why_source why | why tokens 7 | own hits 7 | unique hits 0 | shares why with []
  cell 2 | why_source why | why tokens 9 | own hits 6 | unique hits 0 | shares why with []
  cell 3 | why_source why | why tokens 5 | own hits 1 | unique hits 0 | shares why with []
  cell 4 | why_source why | why tokens 4 | own hits 4 | unique hits 0 | shares why with []
  cell 5 | why_source why | why tokens 5 | own hits 5 | unique hits 0 | shares why with []
  cell 6 | why_source why | why tokens 6 | own hits 4 | unique hits 0 | shares why with []
  cell 7 | why_source why | why tokens 5 | own hits 5 | unique hits 0 | shares why with []
meaning: no shared literal and every sentence names its own readings
expectation held: Q38_GATE_GREEN
```

## 9. 代次边界（这条我必须自己先说，不等谁来问）
```text
本件 17 行的 measured_on = 90d29a172e18（下单点名那一枚）。交之前 15:06:55 我现场重读同一条路由：尖已经变成 dc964086c9d4（compare: ahead，ahead_by=10，total_commits=10，改动文件里确实有 PlanWithAiSheet.tsx）。
新尖上那两行有没有修：blob fd5f6e5ba2771a8d12669b9bec1ba91590970701（49,063 B）里 `PlanWithAiSheet.tsx:147` 与 `:155` 仍是 const detail = (body as { detail?: unknown }).detail;，`?.detail` 之类的空值守卫 = False ⇒ **源码层面这一格在新尖上仍然是同一枚洞**。
但我今天所有**运行时**读数（含毫秒、卡片文字、`<details>` 数）属于 90d29a172e18 那棵树的私有构建 `index-BN1w-xlK.js`；新尖的运行时我没跑，不替它签字，也不把上面这些数字搬过去（Q25）。要在新尖上重跑同一套 17 行，我这把 rig 现成。
```

**发布与坐标**：坐标（脚本从分支 tree 读回，非手抄）：`Canshu-King/CityNexus @ commander/control` 读回 commit 尖 `10b8bdb70ea897165c8205bc05d8bee9c7571b3f` · 其 tree `7cbf9345802048afd4f4c4f38805547a15c52a52` · `evidence/ord0301-screen-speaks-range-hjp3/` 共 96 件（合计 2,673,696 B）。外部可读探针 `GET /git/blobs/9035e162b69f171de7a5d57ec30fdeddd58f0e7e` → 重算 sha1 与 tree 上 blob id 相等 = True；与本机字节一致 = True（97,514 B）。关键件：`RECEIPT_O0301-1500.json` 97,514 B `9035e162b69f` · `boundary_proof.json` 3,943 B `5b060c3e08f6` · `q38_ruler_run1.txt` 990 B `cf464b372a7e` · `table_O0301.json` 112,469 B `db1927627aae` · `tip_moved_readback.json` 1,938 B `55246d35fb7f`。
