## commander 转达 @2026-09-23T03:29+08 —— 仲裁 `5782636042`：**真机门工程前置冻结为 `MET(field-measured)`、不再要求任何技术改动**；**ORD-0238 必须分三层真值且禁止硬映 enum**；B 的证据面被它独立签了

### ① `REAL_PHONE_GATE`：工程侧到此为止

它照我 03:22 的读数确认：注册的生产 SW 是 `/v10-sw.js`，其 precache 与 `/` 当前引用**同代**（`index-DtQ86lsQ.js` / `index-cWMF3pBW.css`），而 `/sw.js` 不带 hashed index 资产、不是生产注册件 ⇒ **"手机刷新仍被旧 SW 喂旧 bundle"这条路径被收窄掉**。据此它冻结：
```text
REAL_PHONE_GATE.tech_preconditions = MET(field-measured)
REAL_PHONE_GATE.user_action         = PENDING
asset cleanup                       = 0 delete
```
**外审口径补一句（它自己提的）**：它在 `commander/control` 还没找到一份**专门钉 `/v10-sw.js` precache 内容**的可读收据 ⇒ 这条 SW-specific 结论它**先记 `field-measured`，不冒充 `EXTERNAL_AUDITED`**；**不要求重跑**，只要把现有读数脱敏发布成一张很小的 `real_phone_gate_preflight.json`；**它不阻塞用户现在刷新**。
⇒ **我已生成并发布**：`evidence/deploy/real_phone_gate_preflight.json`（blob **`4b07d036e2f83666`**，2,806 B）——含四点链、`/v10-sw.js` 与 `/sw.js` 的字节数与 precache、index 的 sha16/字节、三代保留包、以及 `verdict` 三行（`tech_preconditions=MET(field-measured)` / `user_action=PENDING` / `asset_cleanup=0 delete`）与用户动作四要素；**文件内不含任何凭据**（显式写明）。
**用户真机那一下仍按旧规矩**：页面能正常进入 ＋ 同一时间窗服务器命中 current hashed entry ＋ 至少一条正常业务 GET 2xx ＋ 无白屏/无旧代症状 ⇒ **这条证据出现才开 CURRENT+PREVIOUS 的清理闸门**。

### ② `ORD-0238`：它拒绝"把字段塞进 preferences 就算修好"，要求**分三层真值**

它独立查了当前可读的后端契约：
```text
PUT /travelers/{id}/preferences   已存在（PreferenceInput = category/key/value/weight）
JourneyCreate.planning_mode enum  = balanced | budget | explore | strict_schedule
JourneyTrialSetup.pace enum       = relaxed | balanced | packed
```
⇒ **两个 enum 不是同一词表**；它原话：**禁止把 `relaxed/packed` 随手映成 planning_mode 再宣称"节奏接上了"——那只是把丢数据 bug 变成语义猜测 bug**。
**拆两半**：**(a) 兴趣**（词表对得上 ⇒ 接上已有的 `PUT /travelers/{id}/preferences`）；**(b) 节奏**（先只定位：两个词表各自定义在文件:行号、`pace` 现在是否存在任何请求体或表列、服务端有没有可承接字段；没有 ⇒ 明写"需要后端字段"，我拆单）。
**总验收（压轴）**：**不是"把字段存起来"这么简单，必须把"用户说了什么 / 系统保存了什么 / 系统真的按什么规划"三层真值分开钉死** ⇒ 三格任一格没读数，不许写"已修"。已原样转 D。

### ③ 它独立签了 B 的证据面（复算了我的数）

```text
13 nodes × each 10 rounds × each 10 GREEN / 0 RED
all_met / all_fresh / all_shapes_verified / no_duplicate_db_paths
主突变收据 15 臂 killed ＋ severity dependency M7a/M7b 2 臂 killed ⇒ 合计 17
nodes_without_a_killing_arm = []

B 318a034 evidence surface = ACCEPTED
13-node streak            = ACCEPTED-EVIDENCE
17-arm mutation coverage  = ACCEPTED-EVIDENCE
product patch surface     = ACCEPTED-CODE-SURFACE
```
它明说：**这仍基于 local SHA + published blobs，不等于主线已 merge/green**（exact-tree 纪律不变）。⇒ 它确认我报的"17 臂"不是虚数，而是 **15＋2 两份收据合计**。

### ④ TEMP 清理：政策确认生效，**不再追加 GC 动作**

它认同 1,183 目录/770.7 MB → 52/73.1 MB、`>6h=0` 说明**"生产者自清"比跨 lane 大扫除靠谱**；我按"SHA 可重出"具名删 8 棵、10 棵证据不足不动，也符合政策。
**它明确加了一条禁制**：D 盘仍 `USER_ATTENTION_REQUIRED`，**不要因为 TEMP 缩水成功就顺手清 `node_modules` 或未知用户目录** ⇒ 与我先前"按用户清盘规矩保留 `node_modules`"的决定一致，现在这条有仲裁背书。

### ⑤ C / ORD-0224：顺序被它钉死

```text
发布六步已有证据 -> 加 G3_XPROC_LOSER_READBACK -> 10/10 fresh cross-process
-> Y3 杀一次跨进程门 -> 才 FINAL CLOSED
在此之前不动 provider-work 强修
```

### ⑥ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（**0 删除**）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；`AI_CREDENTIAL_EPOCH = COMPROMISED_UNROTATED`。
