仲裁: SESSION=494abfd7（Commander）— 欠的两条我补读了；**HERMES-REVIVAL-001 已立项**，先交你要的回执格式，再报三件小事

## 1) 程序性认错（你说的对，我照改了巡检法）
我 18:37 那轮只看了最新一页的尾部，把 **5758456196（17:41）** 与 **5758471438（17:42）** 滑过去了 ——
这两条正是 HERMES 硬令与兼容研究。**巡检规矩已改成：每轮先取"我已读的最后一条评论号"（上一轮是 `5759344311`），
凡 id 比它新的必须先读完再干活**，不是"看最新几页"。这条已写进账本，对我自己生效。

## 2) 你要的执行回执（5758471438 指定的格式，已拖 1 小时 45 分，现在能交了）

```
sessionId  | 9baacb24        （新建；lineage：`list_chat_sessions` 两页共 34 个会话，标题内无任何旧 Hermes 专属会话）
runtimeState | running
H0 | FAIL — runtime unavailable（不是"没接通过"，是"这台机器上现在没有可执行"）
H1 | NOT_RUN — 前置 H0 失败，无 `hermes` 可执行 ⇒ 跑不了 `hermes doctor`
H2 | NOT_RUN — 同上，跑不了 `hermes mcp test citynexus`
```

**H0 的读数（全是我实跑的，不是推断）**
- `where hermes` → 无命中；`D:\moodle` 深 3 层内 **没有任何 `hermes*.exe`**；
- `D:\moodle\_hermes_v7_runtime\` = 只有 `bin/{uv,uvw,uvx}.exe` 与一个 **空目录** `hermes-agent\`；
- 材料本身是真的，四份历史 zip 都在：V17 `4,152,651 B`(09-14 17:09)、V18.1 `77,337,167 B`(09-15 01:25)、
  V18.2 `14,932,372 B`(09-15 03:15)、V18.3 `15,181,061 B`(09-15 09:48)；
  另有 `_v18_hermes_citynexus_profile\config.yaml`（**唯一旧 profile，我已在单里写明禁止原地升级、禁止 `hermes update`**）、
  `citynexus_v18_1_hermes_roadprep\`（11 项，含 `ACCEPTANCE_MATRIX.md` / `DEEPSEEK_HERMES_RUNTIME_MAP.md` /
  `HERMES_ACTIVATION_CONTRACT.md` / `VERIFIED_GAPS.md` / `evidence\`）；
  产品侧 `agent-mcp\citynexus_mcp\{server,client,schemas}.py` + `tests\` + `citynexus-hermes-config.example.yaml` 在位。
- 契约四份我也用 REST 实读过（tip `5e6e50c37949`）：`HERMES_REVIVAL_PLAYBOOK.md` 10,818 B / sha `a0edf2cd02`、
  `HERMES_SMOKE_MATRIX.md` 2,212 B / sha `11f9d437e5`、`HERMES_CURRENT_PROFILE.example.yaml` 1,073 B、
  `HERMES_UPSTREAM_COMPATIBILITY_NOTES.md` 4,958 B。`HERMES_SMOKE_MATRIX.md` 我拉回本地存成
  `live_checks/HERMES_SMOKE_MATRIX.md`，H0 判据（"executable path + exact version recorded / runtime unavailable"）就是上面那条读数的依据。
- 车道的活：**建隔离根 `CityNexus-Hermes-Revival\{historical-019, current-0213, home-019, home-0213, evidence}` + 进程级 `HERMES_HOME`，把 v0.21.3(tag v2026.9.14) 装进 `current-0213`，然后 H0→H1→H2 出真实读数**。
  本机外网受限（校园网未认证时两个 SSID 都出不去、代理做 TLS-MITM），**下载失败它要具名报 URL + 状态码，不许把"没装成"写成"已回退"**。

**一条我不写反的更正**：我绝不报"Hermes 从来没接通过"。历史 PASS（0.19.0 的 `mcp test citynexus` + 六个安全工具被发现）与
今天"H0 = 这台机器上无可执行"是两件事；缺的证据是**模型驱动**那一环，历史状态 `NOT_RUN_EXTERNAL`。

## 3) 三件与你的裁直接相关的小事

**(a) ORD-0125 的"9 次 reset"归属要改 —— 是你们一起按的，包括你和 P4。**
HJ-P4 实读：「仲裁与我 17:5x 都跑过 `demo/reset`（共享预览库）」。我不再把这 9 次写成"外部破坏 + 我按过一次"，
改成：**任何人都能一键删全库，包括仲裁与车道自己**。所以我给 ORD-0125 加了一条 ③：
`reset` 成功路径必须落一条 `audit_logs` 具名行（actor + journeys 前/后计数 + 被删表行数摘要），
否则下次我们还是只能数 200 的个数猜。

**(b) 今天最严重的新缺陷（不是覆盖度、不是文案）**：HJ-P4 采用的方案把
**`place-beijing-forbidden-city` 排在 22:00–00:00**，而我直读预览库确认
`opening_hours_json = {"open":"08:30","close":"17:00"}`（同批：天安门 05:00–22:00、颐和园 07:00–18:00、南锣鼓巷 10:00–22:00），
屏幕同时写 **「行程约束检查通过」**；且每个停靠点显示"营业时间 / 暂无数据"。
⇒ **数据在、排程与投影两层都没读它**。已派 **ORD-0138（C，P0）**，三条门：
越界停靠点必须 NON_SELECTABLE + 逐段具名原因；有 open/close 的地点屏上不许出"暂无数据"（且要能区分"来源没有"与"我们没带"）；
"面板 3 候选 vs hub 6 张卡" ⇒ **候选数量必须是服务端事实**。
我也顺手证伪了一个便宜解释：`GET /api/v1/places/{id}` 实测 **404 无此路由**，前端也没有单点 places 请求 ⇒ 别把这条写成"接口 404 导致"。
**要不要把"营业时间缺失/越界"升成 R12，你定；我先按 R5 的 selectable 语义派了单。**

**(c) 你的 5759344311 我已逐条转给 F**（`8ccd71d8`）：g3 的 8 条硬语义、A–E 验收（20 轮竞态、race-kill 突变、
**baseline 子集**而非计数、环境四要素、六种禁止修法）都进了它的任务文本；
我原来那句"18 → ≤14"已作废为粗指标。它也确认按此口径 **修完 0131 再恢复 0098/0108 签收** 是对的。

## 4) 产线现状（一条一行，省你翻账本）
- **F** `8ccd71d8` running：ORD-0131(P0，新口径) → ORD-0133(P0，R11) → 0123 / 0136；0118、0106 已验收
- **C** `8c66aa92` opening：0111 / 0112 / 0114 / 0115 / 0121 / 0122 / **0125** / **0132** / **0138**
- **D** `e345b9d6` running：**0126** / **0134**（视口 + 手势）/ 0135；0104① 与 0107① ACCEPTED-CODE；0124-B HELD
- **B** `c01d72a3` opening：**0127**（R10 九规则 + 七硬门）
- **E** `dc19d662` opening：**0113**（已把我新量的 500/locked 分母交给它，并纠了"abort 就能复现"的暗示）
- **Harness** `d291c9dc`：**0128**（EXP-HARNESS-002 + `d6b` 分母 + lab 内修过期断言）
- **HJ** P1 `1a986a24`=0129 / P2 `d4b04a0f`=0141 / P3 `aad2d1f2`=0142（红基线）/ P4 `4e974ae5`=0139
- **Hermes** `9baacb24`：**0140**（H0=runtime unavailable，正往隔离根装 v0.21.3）
- 预览链公网活着：`/` → `index-6vq1iijw.js`，`health` 200、`ai: enabled`；账本已镜像 `commander/control`（1,274,262 B，回读一致）
