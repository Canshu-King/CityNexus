### 🇬🇧 e345b9d6（SESSION=e345b9d6）ORD-0246 + ORD-0247 交付：拒绝第二击挪到 React 提交**之前**（同步 ref，`disabled={busy}` 不当门），「高级：结构化数据」命中框 **15px ⇒ 44px** @2026-09-23 13:2x+08 → **`dc690d7`**（产品＋门）+ **`027d65e`**（只改我自己的仪器）

#### ① ORD-0246：同 tick 两击 ⇒ 1 POST / 1 行（真链路量的，不是打桩）

**他的读数我先复现，再修**：aad2d1f2 报"同 tick 两击 ⇒ 2 POST / 2 行、`b.disabled` 三段全 false"。我的仪器在**修好之后**仍量到 `buttonDisabled = {before:false, during:false, after:false}`（两下同步 click 前后），也就是**渲染态从头到尾没变过**——门不可能在那儿。把门删掉那一臂（`killG1`）当场量到 `posts=2`、新行 2 条 ⇒ 缺陷在这台机器上确实存在，不是我引用别人的结论。

```text
改动（frontend/src/features/planning/PlanWithAiSheet.tsx）：
  :335  const runningRef = useRef(false);
  :442  if (runningRef.current) return;      ← 长度门之后、每一个 await 与 setState 之前
  :443  runningRef.current = true;
  :660  runningRef.current = false;          ← 放进既有的 finally
拒绝是**静默**的：第一次请求正在跑，屏幕上已经有"规划中…"，第二下不该制造一个新任务，也不该制造一个错误。
```
三格读数（`CITYNEXUS_AI_ENABLED=false` 的权威一次性栈，写只落我自己的 `_run<id>.db`，**agent/commands 不打桩**）：
```text
ord0246-1  同 tick 两击      posts=1，journey_missions 由服务器自己的 GET /agent-feed 数出 +1 行，
                             新行 facts.mission_id 唯一且非空（3cca2348-d303-4cdb-8f83-e822d411a862 那一类）
ord0246-2  两下正常单击各 +1  ← 证明门是**一次性的**，不会把按钮变成死控件（sticky 门会）
ord0246-3  被拒那一下不伤人    结果态不在 CANCELLED / CANCELLED_AFTER_SEND / NETWORK，也没画 danger
行数的"落定"不是看 DOM 出现结果块就算完：settledMissions() 要求计数连续三次 400 ms 不变。
```
**v1 → v2 我自己修的是归属**：v1 的 `ord0246-2` 也以同 tick 两击开头 ⇒ `killG1` 一次红两格、`ord0246-1` 没有独占杀手。改成两下正常单击之后：`killG1 ⇒ {1}`、`killG2 ⇒ {2}` 各自独占。
**还有一格我不粉饰**：`ord0246-3` 的 `exclusiveKiller` 是 `[]`。它的杀手 `killG3` 是"在门里顺手 `abortRef.current?.abort()`"——abort 发生在 POST 发出**之前**，所以那一臂连"1 POST"都不成立，必然同时红 `ord0246-1`。这不是归属没做干净，是**"用中止来拒绝"这个做法本身会同时破坏两件事**；`ord0246-2` 在三个臂下都按预期存活。要不要为 3 另造一个只红它一格的臂，请裁定（我能想到的窄写法只有"被拒时 setResult 一个错误态"，而那会被第一次 run 的完成覆盖掉 ⇒ 量不出来）。

**顺手量到、但单子没要求我修的（具名残余，交你裁）**：
```text
RESIDUAL_FAST_RUN_DOUBLE_TAP
本栈一次 run 在 ~108 ms 内落定（gate-readings.runLatencyMs），浏览器生成的 dblclick 间隔是 60 ms ⇒
一次真·双击仍可能创建 2 次 run（实测 realDoubleTapRows=2，那一格 posts 从 2 涨到 4）。
同步重入门管的是"上一次还没办完"，管不到"上一次已经办完"。要盖住它需要**合并窗口**或**每命令幂等键**
（Idempotency-Key 在 replan accept 那条已有先例）。我没有偷偷加窗口：那会拒掉合法请求，是产品决定。
这一格我只在门里量了数、写进证据，**没有**为它写断言——断言今天能过只因为这台机器慢，那种绿我不签。
```

#### ② ORD-0247：`<summary>` 的命中框（before 是我自己复测的）

定位：`V8Experience.tsx:3667` 的 `details.v8-advanced > summary`（bookings 屏「高级：结构化数据」，是结构化导入的唯一入口）。基线样式只有 `styles.css:1560` 的 cursor/字号；移动层那条 ≥44px 规则（`styles.css:274`）枚举的是控件类名，`summary` 不在名单里。

修法一行，放在移动层里（`styles.css:279`）：
```css
@media (max-width: 680px) { .v8-advanced > summary { min-height: var(--cn-touch-min); line-height: var(--cn-touch-min); } }
```
用 `line-height` 撑高而不是 `display:flex`——flex 会让 Chrome 丢掉原生 disclosure 三角（读数里 `markerListStyle` 从 `disclosure-closed` 变 `disclosure-open` 才说明它还在、还能用）。也没有挪出媒体查询（桌面紧凑密度是 Amendment F-2 的地盘）。

```text
390×844：  310×44，elementFromPoint(中心) 返回的就是这个 SUMMARY 本身（不是父 details、不是 aside），
          真触摸屏点下去 → open=true 且 marker=disclosure-open
1280×900： 321×15（桌面没被撑大）
before 复测： 把那条规则删掉那一臂当场量到 310×15 —— 单子上写的是 311×14，形状一致、差 1px 是行高/取整
三臂 3/3 KILLED 且三格各自独占杀手：H1 删规则⇒{1}；H2 pointer-events:none（几何过、手落不到它）⇒{2}；
H3 把规则挪出媒体查询⇒{3}；每次臂另跑一遍镜像（同一突变 × ORD-0246 spec）全绿，mirrorCollateral 三次都是 []
门禁值取自产品自己的 --cn-touch-min（断言它 == "44px"），不是我抄的第二份常量；
桌面那一格的 30px 是我写进门里的自由量，没有产品常量背书——这一点请记在归属里。
```

#### ③ 回归与坐标

- `npx tsc -p tsconfig.check.json --noEmit` **exit 0**、`npx tsc -p tsconfig.typecheck.json --noEmit` **exit 0**（`review/tsc_ord0246_0247.log`）。
- 两份新 spec 各 **3** 个 `test(`，基线各 `4 passed`（第 4 格是 `real-seed` setup project）；`ord0246` 全套 16.2 s / `ord0247` 13.0 s。
- 每次臂跑用的字节 == 交付字节：臂与臂之间树被守卫按 sha256 还原，跑完之后 `git status --porcelain -- frontend` = **0 行**（`dc690d7` + `027d65e` 都在 `integration/frontend-apple-pass1` 上）。
- 六臂字段：`anchor_hits=1`、`bytes_changed=True`、`restored_exact=True` 全中；`treeUnchangedByThisRun=True`；`invalidStackArms=[]`。

#### ④ 我这一轮的仪器错误（三条，都当场更正）

1. **用 Edit 往 `styles.css` 那条 575 字符长行里插规则**：我把 `cut -c1-200` 看到的前缀当成了整行 ⇒ 长行被劈开、尾巴塞进我的新行。复原后 `git diff --numstat` = **5 行新增 / 0 行删除**，原行逐字节回来了（能这么说是因为我核过 diff，不是因为我重打了一遍）。教训：长行文件不要用截断视图当锚点。
2. **两个证据键撞了发布器护栏**：我起的 `touchToken` / `mobileFloorToken` 让 `publish_evidence.py` 按 `FORBIDDEN_CONTENT(secret_pattern=ENV_SECRET_ASSIGNMENT)` fail-closed 拒了两份 patch（值其实是 CSS 长度 `44px`）。按 09-23 已定的处置：**只改名、不动判据、不削清单**（`027d65e`），并且在**改名之后的字节**上重跑三臂（tag `v2`），不拿旧收据签新树。`git show 027d65e` 整笔 diff 仍含被删掉的旧名两行 ⇒ 那一份我没有发布，改成发布 **pathspec 限定的 range patch**（`dc690d7^..027d65e`，逐单裁文件），护栏一次没被削弱。
3. **`ord0246-2` 一开始也测了同 tick 两击**（上面 ① 的 v1 归属问题）；以及行数最初用"DOM 出现结果块"当落定信号——结果块可能是**上一次** run 留下的，所以换成连续三读不变的 `settledMissions()`。

#### ⑤ 证据面（已发布 `Canshu-King/CityNexus @ commander/control`，每件 201/200 + BYTE-LEVEL MATCH 或 `already identical`）

```text
evidence/ord0246/  MANIFEST ab4c5bb338904b01 · changed-files a315e22397544498 · source-and-parent ce621caaf7b3dca2
                   delivery-range__dc690d7-plus-027d65e.patch 0759565fe42085ac (25,114 B)
                   gate-readings af73952ec3032731 · mutation-receipts 59f1bf765efe70fc (v2, 8,060 B)
evidence/ord0247/  MANIFEST b977a9239f55f2c0 · changed-files a315e22397544498 · source-and-parent e12bbe937fb41a25
                   delivery-range__dc690d7-plus-027d65e.patch 3a3074fc88bae33c (20,387 B)
                   gate-readings 371c8bed3b850867 · mutation-receipts d3ccb03d3abe7767 (v2, 8,578 B)
未发布（护栏拒，我没动护栏）：dc690d7__dc690d7.patch —— 整笔 diff 含改名前两行；已用上面的 range patch 代替。
一次 `INITIAL_GET_FAILED(URLError, _ssl.c:1007)` 发生在 ord0246/MANIFEST 的第一次尝试上：fail-closed 没 PUT，重发后 200 + MATCH。
```

`STATUS: ORD-0246-DONE-THREE-ARMS-ALL-KILLED-TWO-OF-THREE-EXCLUSIVE-ONE-RESIDUAL-NAMED | ORD-0247-DONE-THREE-ARMS-ALL-KILLED-THREE-EXCLUSIVE | files frontend/src/features/planning/PlanWithAiSheet.tsx, frontend/src/styles.css, frontend/e2e/{qoder-same-tick-double-tap-plans-once.spec.ts(新), qoder-advanced-summary-is-tappable.spec.ts(新)}, review/{ord0246_kill_arms.py(新), ord0247_kill_arms.py(新), build-evidence-payload.py}；**backend/ 0 个文件** | tests tsc 两配置 exit 0 ＋ 两 spec 各 3 节点（基线各 4 passed，含 real-seed 那一格）＋ 六臂 6/6 KILLED、六次镜像全绿、anchor_hits=1/bytes_changed/restored_exact 六中 | blocker 无；两格**求裁定**已具名：`ord0246-3` 没有独占杀手（abort 必然连"1 POST"一起破坏）与 `RESIDUAL_FAST_RUN_DOUBLE_TAP`（60 ms 真双击在 ~108 ms 落定的 run 上仍会创建 2 次 run，需要合并窗口或每命令幂等键）| writes 全在我自己的 `_run<id>.db`；`:4781` 正在服务的 dist、`_live.db`/`_preview.db`、别人 spike 树一字节未动；公网 0 写；未 `demo/reset`；发布器护栏一行未削 | evidence 上列 12 件（两单各 6）＋ 本节`

**插入收据（本脚本当场测）**：写前 `@BYTES_BEFORE@` B、纯 LF（`CRLF=@CRLF_BEFORE@`）、`sha256` 前 16 位 `@SHA_BEFORE@`（本机钟 `@NOW@`）；`## ORDERS（收件箱` 全文唯一（`count=@ANCHOR_BEFORE@`）、切点 `@CUT_BEFORE@`；我的块 `@BLOCK_BYTES@` B。写后回读：块出现 `@BLOCK_COUNT@` 次、锚点 `@ANCHOR_AFTER@` 份、**把我的区域整段拿掉是否与写前逐字节相同** = `@ROUNDTRIP@`、写后 `@BYTES_AFTER@` B / sha256 前 16 `@SHA_AFTER@` / 锚点切点回到 `@CUT_AFTER@`。文件别人在续写，所以我只对「我这一段可逆」负责。
