#### aad2d1f2 HJ-P3 · **ORD-0257 真机验收：`dc690d7` 的 ORD-0246 / ORD-0247** @2026-09-23 13:3x–14:3x —— 两件**都判得出"是这笔修复改的"**（双向齐全）；但**"按行数判"这把尺今晚单独用会漏判**；另：HEAD 已到 `0fd3cc7`，类级 44px 我顺手量了

**读数分母（`built_from` 是这单的第一命门）**
- 新代：`built_from = export(027d65ed381fbb4bfb81a07a7ae20a9f293454e1)`。做法 `git archive <sha> | tar -x` → `D:/moodle/_hjp3_ord0257_0923/snap_new/` → 依赖用 **`cp -al` 硬链接**接进来（**不是 junction**，删链接不会顺走真依赖）→ `vite build`。产物 **`index-DJEINrOl.js` 1,236,190 B，`sha256[:16] 80a8ca1afb915cfd`**；导出树里 `runningRef` 命中 **4** 次。
- 反例代：`built_from = export(f5a6b9a)` 同法重建 → **`index-CrAwWm5f.js` 1,234,802 B，`sha256[:16] 9fd89456daf12bca`** —— **与 canary 发布代的名字/字节/哈希三者全同** ⇒ 我的控制组就是你在跑的那一代，且构建可复现。
  ⚠ 自报一次仪器事故：我第一次 `cp -al` 打在**已存在**的 `node_modules` 上，嵌出 `node_modules/node_modules`，同 SHA 竟构建出 `index-DXuis0ST.js`（+4,191 B）。**该产物与指向它的 `:8475` 已作废停用**，上行的哈希是修好后重测的。
- 我的端口：`:8474`=新代、`:8476`=反例代、`:8477`=HEAD；全部代理到我自己的 `:8424`（后端代码 `53fe8e8`、库 = 我的副本 `_lane_aad2d1f2_livecopy.sqlite3`）。归属双向证明：`…/journeys/cc5e67c4…`（只在我库）=**200**，`…/d1bdc755…`（不在）=**404**。
- shape：Playwright 自建 `hasTouch` context，390×844 / `deviceScaleFactor 3` / `zh-CN`，每一下先 `scrollIntoViewIfNeeded` 再用 `elementFromPoint` 证明命中，然后 `page.touchscreen.tap()`。
- 未碰：`:4781 / :4782 / :8693 / :4185 / :8713`、`_live.db`、`_preview.db`；无 `demo/reset`；无 mock；权威树 0 写入（只 `git archive` 读）。时钟 `date` 实测 14:31:14（本机 +08）；库内时间全为 UTC(Z)。

---

##### ① ORD-0246 同刻双击「生成计划」：**第二击现在发不出去**（4/4 枪），反例在发布代上复现 2 发
同一支脚本（同 tick 内 `b.click(); b.click()`，不发 await；POST 用**页外 request 监听器**数，挂在点击之前；当场读 `disabled`）：

| 代 | 枪 | journey（打前 `agent_runs`） | POST | 新 `agent_runs` 行 | `disabled` 三读 |
| --- | --- | --- | --- | --- | --- |
| 新 `DJEINrOl` | 1 | `ae79fbf1`（0） | **1** | 1 行 `afdcb3ab` | false/false/false |
| 新 | 2、3 | `ae79fbf1` | **1、1** | 累计 2 行 | — |
| 新 | 4 | `51929591`（5） | **1** | **+1 行** `a8579c9e` 06:29:41→06:30:26 | false/false/false |
| 反例 `CrAwWm5f` | 1 | `e168580c`（0） | **2** | 1 行 + **1 发 HTTP 500** | false/false/false |
| 反例 | 2 | `94669bae`（**0**） | **2** | **1 行** `a5fd1824` 06:29:14→06:29:41（+3 `plan_versions`） | false/false/false |

- **⇒ 修复有效**：新代 4/4 枪只发 1 个请求；发布代 2/2 枪各发 2 个。两边 `disabled` **三读全 false**（渲染还没提交）⇒ 拦住第二击的是**同步门**：在 `dc690d7` 与 `027d65e` 上都是同一文件 `frontend/src/features/planning/PlanWithAiSheet.tsx:442` `if (runningRef.current) return;` + `:443` `runningRef.current = true;`（`submit()` 起于 `:435`，在 `finally` `:660` 复位），**不是**渲染态的 `disabled={busy}`（现 `:886`）—— 与我 12:5x 给的机理一致，也和这笔 commit 的注释一致。（先写成 `:435 那枚门` 是把函数起始行当成了门的行号，这条更正同时改文件与账本。）
- **⚠ 一条判据警告（要进 ORD-0246 的验收词）**：**只看"新建行数"今晚分不开两代** —— 反例组两发里只有一发成行，另一发撞成 **HTTP 500**（`plan/generate` 撞车），所以我量到的是「反例 2 POST→1 行」对「新代 1 POST→1 行」。我手上同时有反例**能**出 2 行的旧证据（今天 02:52:24.216 `c0ecf668` 与 02:52:47.896 `18ccecf4`，同 journey `51929591` 两行、相差 23.6 s）⇒ 旧行为本身**二态不稳定**（多一行 / 或撞 500）。**建议判据改成三列同看：POST 数 + 新增 `agent_runs` 行数 + 非 2xx 数**，只签行数会漏判。
- 模型腿今晚仍是 6/6 `FAILED_EXTERNAL`（同一把待吊销泄露 key，只记名/长 35/前 12 位 `4cab…`）⇒ 所有 `plan_versions` 增量都来自兜底重排，**不能**当"AI 成功"用。

##### ② ORD-0247 `<summary>` 命中盒：**被点名的那颗修好了，且反例复现你的原数字**；但落地代只修了一类里的一颗

| 屏 / 控件 | 新代 `DJEINrOl`（=027d65e） | 反例 `CrAwWm5f`（=发布代） | HEAD `Dx_HBGr5`（=0fd3cc7） |
| --- | --- | --- | --- |
| `/v8/bookings` **「高级：结构化数据」** `.v8-advanced > summary` | **311×44**（computed `min-height:44px; line-height:44px`） | **311×14**（`min-height:0px`）← 与你 11:39 的数字逐位相同 | **311×44** |
| 向导 **「看支持的目的地」** | 91×**30** | 91×**30** | 91×**44**（但 computed `min-height` 仍是 30px —— 是类级 `line-height:44px` 把盒抬起来的） |
| 向导 **「高级设置」** | 349×**16**，中心点命中 `DIV`（**不是它自己**） | 349×**16** | 349×**44**，中心点命中的是 **`BUTTON`**（同名按钮压在 disclosure 上） |
| AI 面板 **「技术详情」** | 331×25（`min-height:0px`） | 未测（同一构建代，我 12:5x 在别的包上测到过 25 高） | 未测 |

- CSS 层证据（不靠猜）：落地代构建里**只有** `@media (max-width:680px){ .v8-advanced > summary { min-height:var(--cn-touch-min); line-height:var(--cn-touch-min) } }`；`--cn-touch-min = 44px`。你 12:3x 加宽的 `summary{…}` + `.v9-evidence-summary{line-height:normal}` **当时不在 027d65e 里，只在工作树脏改动里** —— 到 HEAD `0fd3cc7` 已作为类级规则落地（实测上表第 3 列）。
- ⇒ **验收口径要分开签**：`dc690d7` 把**被点名的那颗**从 14px 抬到 44px（PASS）；`0fd3cc7` 才做到**整类**（向导两颗从 30/16 → 44/44）。
- ⚠ 但**「`elementFromPoint` 必须命中该控件本身」这条在向导上仍不成立**：HEAD 下「高级设置」的中心点命中的是同名 **BUTTON**，不是 `<summary>`。这不是尺寸问题，是**两个同标签控件叠在一起**。ORD-0247 若按"命中自身"签，这颗还是红的；我按实测报，不替你放宽。（顺带更正我自己：ORD-0242 块里我写的"技术详情 316×25"是抄你的数字，本轮同仪器实测 331×25 —— 以后宽度类尺寸我只写自己量的。）
- 两张带 run id 的截图：`ORD0257-A-1352_new_bookings_advanced_summary.png`（44px）、`ORD0257-A-1352_control_bookings_advanced_summary.png`（14px），236,257 / 237,108 B。

##### ③ 你问的那条决定：**权威线脏着 ⇒ 现在不能给用户换代**，而且原因要指准
- 构建开始时实测 `git status --porcelain -- frontend` = **`M frontend/src/styles.css`**（唯一脏文件），而它正是 `dc690d7` 改的两个文件之一；全树脏度实测 **361 条**（`git status --porcelain | wc -l`；其中 `frontend` 只有 1 条，其余是 `raw/`、`reports/`、`review/*.diff` 等证据/审阅产物）。⇒ 从工作树 `vite build` 会把**未提交的加宽**混进"已验收的 027d65e"，代次与被审 SHA 对不齐 ⇒ **不换**。
- 省你一步的好消息：我按导出重建**能逐字节复现发布代**（见上），所以换代风险不在"构建不可复现"，只在"工作树脏"。
- 时间线提醒：我量到 14:1x 时 tip 已从 `027d65e` 走到 **`0fd3cc7`（13:58，带 ORD-0250/0251/0247 类级加宽）** ⇒ 若你要签的是"手机上看得见的这一代"，`027d65e` 的收据只覆盖到被点名那颗；类级那半要按 `0fd3cc7` 签（我上表第 3 列就是它的实测）。

**收据文件**：`commander/control → evidence/ord0257/`（`ORD0257_RECEIPT.md` + `receipt.json` + 2 张带 run id 的截图 + `MANIFEST.txt` 记 40 位 blob，逐件本地 `hash-object` 与远端回读双向核）。
**我的现场与处置**：lane `:8424`、`:8464` 与本轮新增 `:8474/:8476/:8477` 均我自有进程；`_hjp3_ord0257_0923/{snap_new,snap_old2,snap_head}` 是三份导出树（硬链接指向 `frontend/node_modules`；**清理时先删链接本身，别对着链接 `rm -rf`**）；被污染的 `snap_old` 与 `:8475` 已停用未删（等你点名再收）；两个副本库照旧 RETAINED。

