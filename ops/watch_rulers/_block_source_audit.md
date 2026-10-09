## commander 执行令（第六条）@2026-09-22T19:10+08 —— **我漏读了一条**：ORD-0210 源审计早在总线 `5775258233`（18:58）就完成了，结论 `CHANGES_REQUIRED`；三处窄修已派 F；ORD-0222 的验收形状按仲裁改两处

### ① 先认我自己的漏读（这是本块最重要的一句）

仲裁在**总线 `5775258233` @18:58:01** 就给出了 ORD-0210 的源审计逐项 verdict，而我在 19:00–19:07 那几轮里**没有读到它**（我读的是 #67 的回复 `5775164855`，没往下拉一条）。它 19:05 那条里那句"**ORD-0210 源审计已经在总线 `5775258233` 完成…别让 F 误以为还在排队**"就是在提醒我。
⇒ **我的巡逻有盲区**：`bus_new.py` 只取最后一页 + 一页，两条挨着发布时我会漏掉中间那条。**处置**：本轮起每次巡逻把 `--tail` 去掉（取最后两页），并在账本记账时把"我读到的最大 id"写下来，便于自查。

### ② ORD-0210 源审计结论（照录，不加工）

```text
ORD-0210 runtime receipt/classification = ACCEPTED-EVIDENCE
ORD-0210 triple-scope classifier         = ACCEPTED      ← (SHA,nodeid,shape) 定域，缺任一键回 UNCLASSIFIED
ORD-0210 target-node exit isolation      = ACCEPTED      ← whole-file/multi-node 一律 NOT_OBSERVED
ORD-0210 no-relaxation diff              = ACCEPTED      ← 无 sleep/retry/降并发/放宽断言
ORD-0210 closure semantics               = RED           ← 见 C 之前的 3)
ORD-0210 freshness enforcement           = RED           ← C1
ORD-0210 protected-db guard              = RED           ← C2
ORD-0210 IMPLEMENTATION MECHANISM         = CHANGES_REQUIRED
```
它的原话：**"不是推翻 F 的工作。核心尺子已经对了，剩下三处都是能窄修的『最后 10%』。"**

**三处 blocker（我落成 F 的续单要求，不另开 ORD 号，写在 ORD-0210 的 status 上）**：

1. **closure 语义漏了反向要求**：`closure_allowed` 现在只要 `STREAK_MET + rounds>=10 + clause6_declared + independence_declared` 就变 True ⇒ **没有 reverse mutation 也能 CLOSED**，直接违背 15:58 冻结。要加独立 guard：`reverse_mutation_required=true` 且 `reverse_mutation_result in {KILLED, STREAK_BROKEN}`；未交反向证据时 10/10 绿最多 `STREAK_GREEN`。
2. **freshness 在 acceptance 模式没被真咬住**：`_run_once()` 量了 `path_did_not_exist_before_this_run=True`、`_instrument_problems()` 也查，但 **acceptance 的 `test_1a` 没调用 `_instrument_problems()`**；`streak_verdict()` 只检查 `initial_row_counts` 字段**存在**。⇒ 10 个不同但**预先存在**的库只要全绿仍可能 `STREAK_MET(10)`。要把 freshness 变成共享 predicate 的机械 check。
3. **用户库防护大小写敏感**：`_assert_not_user_db()` 对 `_live.db/_preview.db` 是字符串精确比较，而 **Windows 文件系统大小写不敏感** ⇒ `_LIVE.DB` 能绕过。要 `casefold()/normcase()`，最好对 resolved 绝对路径再拒一次。

**外加一条 scope 修正**：`gate-acceptance-streak.yaml` 的 `applies_to` 把 **g5 也列进"并发/时序门"** 了——g5 是稳定功能红，不是 timing-flip；可借 runner 做重复观测，但**不能因此变成 closure 对象**。请标 `measurement-only` 或移出。

### ③ `EXTERNALLY_READABLE_EVIDENCE`：规则 ACCEPTED，但**发布器本身还没签 SAFE-DEFAULT**

仲裁原话：当前 `publish_evidence.py` 接受任意 `local_file` 直接 PUT，**没有机械拒绝 `.env` / `*.db` / sqlite / key / cookie 这类禁载物**；既然第五条令要求所有车道默认用它，**发布器必须 fail-closed，而不是靠人记得别把用户库端上 GitHub**。
**最小硬化（我已认领，这是工具活不是产品活）**：① basename/suffix denylist（`.env*`、`*.db`、`*.sqlite*`、`*.pem`、`*.key`、`.p12`、`.pfx`、明显 token/cookie/credential 文件）；② 字节以 `SQLite format 3\0` 开头直接拒；③ `repo_path` 只许 `evidence/**` 与受控 `live_checks/**`，拒 `..`；④ 继续只打印 blob sha、不打印 credential。
**它只签了 `READABLE / BYTE-PROOF-OK`** —— 我把这条当作"发布器当前不可作为默认动作"的正式状态，硬化完再请它复签。

### ④ ORD-0222 的验收形状按它改两处（我原稿写错了两点）

**改 1：全屏 `innerText` 扫描不能当法官。** 它的原话：**"我们刚刚已经因为 `.v8-sr-only` 被 `innerText` 混进来撤过一次假结论。不能一边把这个量具判有罪，一边下一张单又让它当法官。"** ⇒ 拆成两层门：
```text
VISUAL_TEXT_SCAN     : only traveller-visible rendered text
                       exclude .v8-sr-only / aria-hidden / display:none / visibility:hidden / zero-render
                       scan zh-CN screen for raw internal tokens
ACCESSIBLE_TEXT_SCAN : 单独跑，raw internal enums 也不得泄进读屏输出
```
**改 2：`Check in`/`Overnight` 不许硬塞进 mode/anchor 两张表。** 它在这份 exact source 里查过：`Check in` **0 个 literal hit**；`Overnight` 只有一处与"零晚住宿"说明有关、**不在 day-card 渲染路径**。⇒ 要求 D **先交一张并排收据**（`selected.days` 原始 payload vs 实际可见的日卡文本），定位真正的数据→文案边界后再修；**禁止为了让扫描变绿，把这两个词硬加进映射表**。

**它另外补了三条我漏掉的（都进 ORD-0222，不另开单）**：
- **`:3203` `t("live.eta", { mode: nextLeg?.mode ?? mode })`** —— 又一个 Commander 没列进四点的潜在 raw-mode 入口；
- **`:3242` / `:3299` 的 `min · … min walk`** 在中文 locale 下仍是英文，与 `3240/3297` 同行同组件 ⇒ 建议**同一 diff 收掉**，免得得到"很讲究的半汉化界面"；
- **两张映射表的 fallback 风险**：未知值现在 fallback 成 `key.replace("_"," ").toLowerCase()`，中文 UI 遇到新 enum 仍会泄英文 ⇒ 建议中文 fail closed 成「未识别的出行方式 / 未识别的行程锚点」，英文再做 humanized。

**修正后的最小验收（照录它的六条）**：
```text
1. 2677 / 2678 / 3240 / 3297 全部不再裸印；
2. 核 3203 live.eta 是否消费 raw mode；
3. Check in / Overnight 先定位真实 source，不准乱塞 mapping；
4. zh-CN VISUAL_TEXT_SCAN 无 raw enums / mixed fixed-English on these touched rows；
5. ACCESSIBLE_TEXT_SCAN 单独跑；
6. 把 2677 改回 raw day.mode => visual gate RED；
7. 未知 mode/anchor synthetic value => zh UI 不泄内部 token。
```
它最后一句：**"这张单不用扩成『大一统本地化项目』，只把这几个已经被两轮人眼和源码证实的漏口一次收干净。"**

### ⑤ 现场

working tip 已推进到 **`b41b4cc`（19:02，D 交 ORD-0221：向导提示的逐面 before/after 读数 + 杀测收据加 `bytes_changed`）**；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
