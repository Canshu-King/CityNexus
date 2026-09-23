### 🇬🇧 e345b9d6（SESSION=e345b9d6）ORD-0250 + ORD-0251 + ORD-0247（加宽）交付：被拒的那一下要留下人话、界面不再回显服务器词汇、≥44px 从"点名控件"改成整类 `<summary>` @2026-09-23 15:0x+08 → **`0fd3cc7`**（产品＋门）+ **`2d10937`**（我自己看过的截图 + 补的那把臂）

#### ① ORD-0250：空需求点「开始规划」不再静默

先复现再修：commander 的收据 `evidence/ord0242/commander_partial_walk_0923.json`（blob `a4740e8ce844dfdc`）我读了，那句"后端日志里那一次没有 POST"我按同一形状自己量了一遍——**把解释拿掉那一臂（`killM1`）当场红**，红消息就是"the press was refused with no word on screen"，所以缺陷在这台机器上是真的存在，不是我引用别人的结论。

```text
改动（frontend/src/features/planning/PlanWithAiSheet.tsx）：
  :29   const REQUEST_MIN_LENGTH = 8;          ← 以前这个 8 只写在 submit() 里，屏幕上没有任何地方说它存在
  :442  if (command.length < REQUEST_MIN_LENGTH) { setRequestTooShort(true); return; }   ← 拒绝照旧，但留下原因
  :712  <p data-testid="plan-ai-empty-request" role="status">还差你自己的一句话：…</p>     ← 画在输入框与动作条之间
  :895  disabled={busy} + aria-disabled={短于门槛}   ← 走 ORD-0066（甲）那条已收下的形状：不能走也要可聚焦、可读到原因
```
读数（390×844、真触摸 context、我自己的权威一次性栈）：
```text
placeholder 确实是那句示例（"用你自己的话说：这趟想怎么玩、想吃什么、哪儿一定要去。"）——这就是"看起来像能点"的来源
点完之后 textarea 的 value 仍然是 ""            ⇒ 我没有替用户填任何东西（单子的禁令我当断言写了）
提示句逐字符 == 门里另存的那份中文（不 import 产品常量）；两层扫描（画出来的 / 可被读出来的）都含它
中心 elementFromPoint 命中的就是这个提示块自己；inViewport=true；不在 .v8-sr-only 里
posts=0                                          ⇒ 不发请求这条没变，变的是它现在会说话
边界：7 个字符拒（posts 仍 0）/ 8 个字符收（posts=1）——夹具自己带自证 expect(TEXT.length).toBe(MIN-1)
可达性：aria-disabled="true"、focus() 后 activeElement 就是它、computed opacity 0.45（看起来就走不动）
```
**我走的验收分支**：单子写"要么禁用+屏上说出还差什么，要么点击后给具名提示"——我走**第二条**（按下之后具名提示），因为第一条会让每次打开面板都挂着一句唠叨；不自动填占位文字。若你要的是第一条，说一声我改，判据不用重写。

**我自己看过的截图**：`review/evidence/ui-overnight/ord0250-hint-run145946.png`（390×844）。看到的：提示块在输入框下面、橙色左边框、字能读；同时看到它下面还有一块同样橙边的"这台服务没有接入 AI 模型：现在提交不会真的由 AI 规划…"——**两块警告叠在一起，视觉上互相抢**，不是缺陷也不是我这次要改的东西，记一笔给你/设计裁。

#### ② ORD-0251：不再回显服务器词汇，"不知道"不再是负数

定位（改之前就量到的通路）：`PushCapabilityCard.tsx:51` 就是 `<strong>{config?.capability}</strong>`，值来自 `main.py:4228` 的 `push_capability()`（`backend/app/integrations/push.py:18-25`，今天一共三档：`RECORD_ONLY` / `DEPENDENCY_MISSING` / `WEB_PUSH_CONFIGURED`）。`data-plan-count` 只有一处（`PlanWithAiSheet.tsx:814`），全仓 e2e **0 处**读它——所以"被门消费"这半句我按事实收窄成：**它是一个给门用的属性，而我把哨兵数字写在上面**。

```text
状态句：三档各有一句人话 + 一句"这对你意味着什么"；不认识的档 ⇒ 明说"说不准推送能不能用"，
        既不回显原词，也不降级成"只记录，不发推送"（后者是 K2 专门要红的那条）
原始值只留在 data-capability（门与工单还能说清服务器说过什么，人读不到）
data-plan-count：知道就写数字，不知道就写 "unknown"；内部 -1 保留（它确实是"无法归因"的真状态）
顺手修的同族一格：读失败时状态句原本永远挂着"检查中"（config 为 null 的兜底），现在分得出"还在读"与"读不到"
```
读数：
```text
RECORD_ONLY ⇒ 状态行 "只记录，不发推送"、解释行逐字符 == 门里那份；两层扫描都不含 "RECORD_ONLY"；data-capability 仍是 RECORD_ONLY
自造标签 A_SERVER_STATUS_NOMINATED_BY_NOBODY_HERE ⇒ 状态行是"说不准推送能不能用"，两层都不含它，且没有冒充已知档
BASELINE_UNAVAILABLE 那一格（把 /plans 基线读做成 500 真走到这条分支）⇒ data-plan-count="unknown"、屏上文字不含 "-1"、posts=1、planReads=2
截图：review/evidence/ui-overnight/ord0251-push-card-run145962.png —— 我看到的是"通知 / 只记录，不发推送 / 服务器没有配置推送密钥… / 启用 Web Push"
```
**我看到但没改的（请你开单，我不在收单中途扩自己写域）**：状态已经说"只记录，不发推送"的时候，下面那颗「启用 Web Push」仍然长得像可用（`enable()` 在 `:26` 会立刻回一句 `push.noKey`）。这是 ORD-0250 同族的"点了没用还说得像能用"，改它需要自己的判据与臂。

#### ③ ORD-0247（加宽）：整类 `<summary>`，不是被点名的那一个

```text
根因：styles.css:274 那条移动层 ≥44px 规则枚举的是控件类名，<summary> 从来不在名单里 ⇒ 两块屏各自短一截
修法：styles.css 一条元素级规则（仍在 @media (max-width:680px) 内）
      @media (max-width: 680px) { summary { min-height: var(--cn-touch-min); line-height: var(--cn-touch-min); } }
      另给 flex 排版的 .v9-evidence-summary 单退 line-height（min-height 保留）——它自己两列对齐，line-height 会撑歪
      不用 display:flex：那会让 Chrome 丢掉原生 disclosure 三角（读数里 marker 从 disclosure-closed 变 open 才说明它还在）
门不再点名：它遍历 hub/bookings/me/trips + AI 面板，把每个渲染出来的 <summary> 量一遍，并要求清单里必须真含
           被上报的那两处（否则"扫了个空"也能绿——这条是 W3 专门要红的）
扫出来的第三个（谁都没报过）：/v8/me 的「高级详情」——修前它和另两个一样短，修后 356×44
      移动清单：counted 3 / underFloor 0 / surfaces = /v8/bookings, /v8/me, plan-ai-sheet（gate-mobile-summary-inventory.json）
      桌面：所有 summary 的 computed min-height 不再是 44px（gate-desktop-summary-inventory.json）⇒ Amendment F-2 的紧凑密度没被撑坏
```

#### ④ 矩阵：十臂，跑在交付后的字节上（tag v3；v1/v2 的差别在下面自报）

```text
KILLED    killM1-refusal-goes-silent-again                     owner=ord0250-1    红集[ord0250-1] 存活[ord0250-2,ord0250-3] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (15.6s)
KILLED    killM2-length-floor-lowered-to-one                   owner=ord0250-2    红集[ord0250-2] 存活[ord0250-1,ord0250-3] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (14.5s)
KILLED    killM3-control-stops-saying-it-cannot-advance        owner=ord0250-3    红集[ord0250-3] 存活[ord0250-1,ord0250-2] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (14.4s)
KILLED    killK1-server-label-echoed-again                     owner=ord0251-1    红集[ord0251-1,ord0251-2] 存活[ord0251-3] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (12.5s)
KILLED    killK1b-state-stops-saying-what-it-means             owner=ord0251-1    红集[ord0251-1] 存活[ord0251-2,ord0251-3] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (12.3s)
KILLED    killK2-unknown-label-wears-a-known-sentence          owner=ord0251-2    红集[ord0251-2] 存活[ord0251-1,ord0251-3] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (12.7s)
KILLED    killK3-not-knowable-sentinel-back-on-data            owner=ord0251-3    红集[ord0251-3] 存活[ord0251-1,ord0251-2] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (12.1s)
KILLED    killW2-touch-floor-re-narrowed-to-one-class          owner=ord0247w-1   红集[ord0247w-1] 存活[ord0247w-2,ord0247w-3] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (26.4s)
KILLED    killW3-reported-disclosure-leaves-the-sweep          owner=ord0247w-2   红集[ord0247w-2] 存活[ord0247w-1,ord0247w-3] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (27.8s)
KILLED    killW4-touch-floor-moved-out-of-the-mobile-layer     owner=ord0247w-3   红集[ord0247w-3] 存活[ord0247w-1,ord0247w-2] anchor_hits=1 bytes_changed=True restored_exact=True 基线=4 passed (32.4s)
```
合计 **10/10 KILLED**；`treeUnchangedByThisRun=True`；`invalidStackArms=[]`；镜像附带红：无
独占杀手：`{"ord0250-1": ["killM1-refusal-goes-silent-again"], "ord0250-2": ["killM2-length-floor-lowered-to-one"], "ord0250-3": ["killM3-control-stops-saying-it-cannot-advance"], "ord0251-1": ["killK1b-state-stops-saying-what-it-means"], "ord0251-2": ["killK2-unknown-label-wears-a-known-sentence"], "ord0251-3": ["killK3-not-knowable-sentinel-back-on-data"], "ord0247w-1": ["killW2-touch-floor-re-narrowed-to-one-class"], "ord0247w-2": ["killW3-reported-disclosure-leaves-the-sweep"], "ord0247w-3": ["killW4-touch-floor-moved-out-of-the-mobile-layer"]}`
没有杀手格的节点：`[]`
运行形状：whole owner spec file per arm (3 nodes + the real-seed setup project = 4 passes when green); the same mutant is then played against another lane-critical spec as the collateral mirror；跑在 tag `v3`，时刻 2026-09-23T14:49:57+0800，文件 sha256 前后一致：PlanWithAiSheet.tsx=6d66978e79…, PushCapabilityCard.tsx=31543da5c4…, styles.css=a7b0d981b8…

**v1 → v2 我自报的一条**：`ord0251-1` 在 v1 里没有独占杀手——把原始标签回显那一臂（K1）天生会同时红 1 与 2（"回显"既破坏已知档的措辞、也破坏"不认识的不回显"）。我没有把这条抹平，而是补了一把只被 1 观察到的臂 `killK1b-state-stops-saying-what-it-means`（状态句不再解释含义），v2 起每格都有独占杀手。**v3** 是把整个矩阵在"加了截图之后的字节"（`2d10937`）上重跑一遍——不拿旧收据签新树，这条是我上一批被点过的同一个坑。

#### ⑤ 回归、坐标、我这一轮的仪器错

```text
npx tsc -p tsconfig.check.json --noEmit ⇒ exit 0；npx tsc -p tsconfig.typecheck.json --noEmit ⇒ exit 0（review/tsc_ord0250_0251.log）
三份新 spec 各 3 个 test(，基线各 4 passed（第 4 格是 real-seed setup project）；整文件时长 15.3 s / 14.2 s / 28.3 s
臂与臂之间树按 sha256 还原；跑完之后 git status --porcelain -- frontend = 0 行 ⇒ 臂用的字节就是交付的字节
```
1. **又踩我自己记过的 trap #1**：`aria-disabled="true"` 会让 Playwright 的 `click()` 一直等到超时（我第一次 3 分钟超时）。修的是仪器（`click({force:true})` + 注释说明为什么），**没有**为了迁就门把产品改回硬 `disabled`。
2. **CJK 字数按眼看**：我写的"7 字/8 字"夹具其实是 4 与 6 个字符（一个汉字＝一个 `length` 单位），于是边界格和可达性别格一起假红。现在门里自证 `expect(TEXT.length).toBe(MIN-1)`，夹具不对时节点直接说自己"没在量东西"。
3. **桩计数 ≠ 回答已生效**：我先 `poll(pushReads() > 0)` 再读状态行，读到的是"检查中"——响应还没落到 React。改成等 `data-capability` 落地之后再判（顺带把"原始值留在属性上"从希望变成被等到的事实）。
4. **`expect.poll(...).toBe(0)` 第一拍就通过**："没发请求"这条必须先等一个真实窗口（1.5 s）再判，否则测的是"我还没开始点"。

**给 commander 的一条现场约束照守**：这批动的是 `frontend/src`，所以按你 12:1x §④ 的规矩，**这段时间不要从合流树出发布包**；要新候选请用干净导出树（`git archive 2d10937`）。我没有碰 `:4781` 正在服务的那份 dist、没有新建隧道、公网 0 写、`_live.db`/`_preview.db` 只读、未 `demo/reset`。另外我已经把 `0fd3cc7` / `2d10937` 两次动尖在账本里预告过（B 的 v5 父请直接换到 `2d10937`）。


#### ⑥ 证据面（已发布 `Canshu-King/CityNexus @ commander/control`；下面 sha1 是对本地字节用 `git hash-object` 重算的，发布回读每件都是 201/200 + BYTE-LEVEL MATCH 或 `already identical`）

```text
evidence/ord0250/
   a4100a38ce6116e5   59,277 B  0fd3cc7__0fd3cc7.patch
   7a6cbf257854fe57      496 B  0fd3cc7__changed-files.txt
   b07a6d72cd72187d      717 B  0fd3cc7__source-and-parent.txt
   a118a88be6ac651e      944 B  MANIFEST.txt
   3d6a84da0ae1a29a    1,499 B  followup__2d10937.patch
   b14746f3623b6a54      295 B  gate-length-boundary.json
   b0d93b9c055ea958      567 B  gate-refused-press.json
   fdebbbcb80550777   26,152 B  mutation-receipts.json
   1f7949730117c29f   42,440 B  ord0250-hint-run145946.png
evidence/ord0251/
   a4100a38ce6116e5   59,277 B  0fd3cc7__0fd3cc7.patch
   7a6cbf257854fe57      496 B  0fd3cc7__changed-files.txt
   d0b845caa98173fe      717 B  0fd3cc7__source-and-parent.txt
   6140c1d31e5d94c9    1,075 B  MANIFEST.txt
   fd3753fe8bfada69    1,116 B  followup__2d10937.patch
   786ef7a7a90d056d      537 B  gate-plan-count-attribute.json
   8b69a80fa652c798      420 B  gate-push-card-reading.json
   9fc1da3be8a2c183      305 B  gate-unknown-label-reading.json
   52f6109239d77dbf   26,152 B  mutation-receipts.json
   d12c223a8c290a47   11,788 B  ord0251-push-card-run145962.png
evidence/ord0247w/
   a4100a38ce6116e5   59,277 B  0fd3cc7__0fd3cc7.patch
   7a6cbf257854fe57      496 B  0fd3cc7__changed-files.txt
   6540e6856f0ca01c      754 B  0fd3cc7__source-and-parent.txt
   8207c172a80852fc      781 B  MANIFEST.txt
   b1a31bcc31625b86      766 B  gate-desktop-summary-inventory.json
   216c6b626cd758c9      846 B  gate-mobile-summary-inventory.json
   c42508c322caa4c7   26,189 B  mutation-receipts.json
```
两次的 `INITIAL_GET_FAILED`（`RemoteDisconnected` / `_ssl.c:1007`）都是 fail-closed 没 PUT；重跑读到 `already identical` + 同一枚 sha1 ⇒ 文件本来就在分支上，不是丢了再补。
**代次自证**：矩阵 tag `v3` 跑在 `2d10937` 的字节上（`filesBefore` 三个文件 sha256 前 10 位印在上一节的运行形状里）；`0fd3cc7__0fd3cc7.patch` 是产品＋门那笔，`followup__2d10937.patch` 是只加截图/补臂那笔，两笔合起来才是这一批的交付形状。

`STATUS: ORD-0250-DONE-TEN-ARMS-ALL-KILLED-NINE-EXCLUSIVE | ORD-0251-DONE | ORD-0247-WIDENED-CLASS-SWEEP-DONE | files frontend/src/features/planning/PlanWithAiSheet.tsx, frontend/src/features/notifications/PushCapabilityCard.tsx, frontend/src/i18n/LocaleContext.tsx, frontend/src/styles.css, frontend/e2e/{qoder-empty-request-says-what-is-missing.spec.ts(新), qoder-no-internal-words-or-sentinels.spec.ts(新), qoder-every-summary-is-tappable.spec.ts(新)}, review/{ord0250_0251_0247w_kill_arms.py(新), render_arms_section.py(新), build-evidence-payload.py}；**backend/ 0 个文件** | tests tsc 两配置 exit 0 ＋ 三份 spec 各 3 节点（基线各 4 passed）＋ 十臂 10/10 KILLED、九格独占、镜像无附带红、restored_exact 十中 | blocker 无；两格交你裁：验收分支（我走"按下后给具名提示"，你要"禁用+先说还差什么"我就换）与「启用 Web Push」在只记录档仍像可用（同族，我没动） | writes 全在我自己的 `_run<id>.db`；`:4781` dist、`_live.db`/`_preview.db`、别人 spike 树一字节未动；公网 0 写；未 `demo/reset`；发布器护栏一行未削 | evidence 见下节 21 件 + 本节`

**插入收据（本脚本当场测）**：写前 `@BYTES_BEFORE@` B、纯 LF（`CRLF=@CRLF_BEFORE@`）、`sha256` 前 16 位 `@SHA_BEFORE@`（本机钟 `@NOW@`）；`## ORDERS（收件箱` 全文唯一（`count=@ANCHOR_BEFORE@`）、切点 `@CUT_BEFORE@`；我的块 `@BLOCK_BYTES@` B。写后回读：块出现 `@BLOCK_COUNT@` 次、锚点 `@ANCHOR_AFTER@` 份、**把我的区域整段拿掉是否与写前逐字节相同** = `@ROUNDTRIP@`、写后 `@BYTES_AFTER@` B / sha256 前 16 `@SHA_AFTER@` / 锚点切点回到 `@CUT_AFTER@`。文件别人在续写，所以我只对「我这一段可逆」负责。
