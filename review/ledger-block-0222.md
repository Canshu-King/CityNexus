### 🪞 e345b9d6（SESSION=e345b9d6）ORD-0222 交付：裸枚举的**四条路径**全部关掉，门从"盯一个节点"改成"整屏两层扫"；②按仲裁要求先交并排收据再动，活动标题不塞 mapping @2026-09-22 20:1x +08 → 提交 **`f7ce8ff`**

**报数六要素**：树 `D:/moodle/_qoder_integration_20260919`（有 .git）；`git log -1` = **`f7ce8ff 2026-09-22 20:10 +0800 fix(frontend): close the raw-enum leak on every path, and scan the screen instead of one node (ORD-0222)`**（其父 `dfdc5d5`＝ORD-0220 ①②③）；`git status --short -- frontend` 空；解释器 Node/Playwright ＋ `D:/moodle/CityNexus/.venv/Scripts/python.exe` = 3.12.14；命令 `python review/run_spec.py "e2e/qoder-raw-enums-never-reach-the-traveller.spec.ts" 4574|4576|4580 --config playwright.prod-gate.config.ts` → 收集 **6 节点**（1 real-seed ＋ 5 门），执行 **exit 0 / 6 passed**（`run-run078896.log`；加第 5 个节点前那把 5/5 `run-run078759.log`）；`tsc --noEmit -p tsconfig.check.json` **exit 0** 四次（`tsc-0222a/b/c/d.txt`）；回归链读数见文末。

**你的四个坐标我逐条复核为真**（`git show 25165d9` 之后在当前树里重读）：`:2677 {day.mode}`、`:2678 t("hub.anchor",{type: day.anchor})`、`:3240 <b>{fact.mode}</b>`、`:3297 <b>{fact.mode}</b>` 四处都确实裸印，`:2768-2769` 是唯一已修的。**⇒ 我 ORD-0208 ④ 那句"日卡不再裸印"是半屏真话**，HJ-P1 两次读数不是旧包，是另一条渲染路径。这条我收下，不辩解。

**改了什么（都是"内容不动、形式归位"）**：
1. 日卡第二路径 `<small>`：`modeLabel(day.mode, zh)` ＋ `t("hub.anchor", { type: anchorLabel(day.anchor, zh) })`——**模板留着，参数换成已翻好的词**（你给的两种合法形状里的第二种）；
2. `:3203 live.eta`（仲裁补的第四个入口）确实消费 raw mode ⇒ `modeLabel(nextLeg?.mode ?? mode, zh)`；
3. `:3240`/`:3297` 两条路线行 ⇒ `modeLabel(fact.mode, …)`；同行 `min · … min walk` 是硬编码英文 ⇒ 新增 `live.routeDuration`（zh「{duration} 分钟 · 步行 {walking} 分钟」）；
4. 同一把尺顺手量到的另两处中英混排（不扩到别家组件，只收同屏同行）：`:3202 {n} min slack` → `live.slack`、Studio `{n} min` → `studio.walkingMinutes`；
5. 未知值 fail closed（仲裁③）：`modeLabel` 未知 ⇒ zh「未识别的出行方式」，`anchorLabel` 未知 ⇒ zh「未识别」（**这里我先量后改**：第一版写「未识别的行程锚点」，而日卡模板本身带"锚点"，实测渲染成「未识别的行程锚点**锚点**」，`run-run078539` 之后我改成短词，门里现在钉「不得出现 锚点锚点」）；英文仍 humanize，且把 `replace("_"," ")` 只换第一个下划线的老 bug 改成 `replaceAll`。

**门 `e2e/qoder-raw-enums-never-reach-the-traveller.spec.ts`（6 节点）按仲裁 A 拆成两层，谁也不当法官兼被告**：
- `ord0222-1` **VISUAL_TEXT_SCAN**：TreeWalker 逐文本节点，按该节点自己的 `getBoundingClientRect()` ＋ computed `display/visibility/opacity` 判"看得见"，排除 `.v8-sr-only`、`aria-hidden`、零盒；扫 **hub/live/map/studio** 四屏；断言 ① 13 个内部枚举 token 一个都不许出现（`ARRIVAL/DEPARTURE/STAY/CHECK_IN/CHECK_OUT/ANCHOR/TRANSIT/BICYCLE/RIDE_HAIL/WALK/AUTO` ＋两个合成值）② 本单碰过的 5 类行里**不许出现任何 ≥3 字母的拉丁词**（"mixed fixed-English on these touched rows"按字面钉，不是只查枚举表）③ **防空转**：每屏渲染文本节点数 >20，且该屏该出现的行必须真看到过（`seen` 计数为 0 就报红——这条当场抓到 `.v8-route-row` 藏在 `<details>` 里没展开 ⇒ 扫描器现在先展开所有 disclosure，读数 `run-run078539.log`：`{"live ETA row":1,"live leave-by slack":1,"route-evidence row":0}`）。
- `ord0222-2` **ACCESSIBLE_TEXT_SCAN**：单独一遍，可见文本 ＋ `.v8-sr-only` ＋ `aria-label/title/alt`，同样排除 `aria-hidden`/未渲染；断言枚举 token 为 0。⇒ 读屏路径不再被"看不见"豁免。
- `ord0222-3` 合成未知值（`SCOOTER_SHARE`/`PICK_UP_POINT`）⇒ 中文必须说「未识别的出行方式 / 未识别锚点」，且屏上不得出现 `SCOOTER`/`PICK UP`。
- `ord0222-5` 深色同一批屏再扫一遍（你要的"明暗各看一眼"）。
- `ord0222-4` **并排收据**（仲裁 B）：`options[].days[]` 原始字段 vs 日卡实际可见文本，逐项落在哪个字段。

**②的收据与结论（不塞 mapping）**：

```text
raw  days[0] = {label:"Friday · 09 Oct", date:"2026-10-09", anchor:"ARRIVAL", mode:"TRANSIT",
               activities:["Arrival","Check in · Haihe Riverside Hotel","Overnight · Haihe Riverside Hotel"]}
可见 第 1 天 | 星期五 | Arrival · Check in · Haihe Riverside Hotel · Overnight · … | 公交地铁 抵达锚点
sourceOf: Check in -> activities[1]（2/3 天里各 1 处）  Overnight -> activities[2]
```

⇒ 「Check in」「Overnight」**不在任何枚举表里**，它们是**计划投影写进 `activities[]` 的展示字符串**（同屏还有 `Arrival`、`Check out`、`Five Great Avenues`、`Tianjin Museum` 同性质）；`Friday` 来自 `days[].label`。分界线我这样划：**形式（星期、出行方式、锚点角色、分钟单位）由前端按 locale 渲染 ⇒ 已修**——星期现在从同一行的 `days[].date`（ISO）用 `Intl` 本地化，`label` 只作没有日期时的兜底；**内容（活动标题）由服务器写 ⇒ 不在前端改写**，按仲裁"不准乱塞 mapping"交回计划投影（建议：投影按 journey locale 出标题，或出稳定的 `type` 让前端映射，两者都归后端决定）。**因此我明确不签"整屏无英文"**：zh 屏上现在仍有服务器写的英文活动标题，我的门只钉"内部枚举"与"我碰过的行"，这一格没修好就是没修好。

**突变（第 4 件）**：`killAA1-day-card-row-prints-the-raw-mode`——`V8Experience.tsx` 那一行改回 `{day.mode}`，`anchor_hits=1`、`on_disk=True`、`anchor_bytes=80`、`bytes_changed=−15`、跑完 `restored OK` ⇒ `ord0222-1` **KILLED**，变红原文 `/v8/hub renders internal enum tokens to the traveller: ["TRANSIT","A…`。

**回归与两条翻红门的归因（我做了反向对照，没有口头甩给别人）**：同一份九文件链形制、同一 SHA `f7ce8ff`——第一把 **49 passed / 2 failed**（`run-run079055.log`：`sim-window-scrolls-under-a-finger` 滑到 783/806px；`ord0087-booked-commitment-is-on-the-wallet-screen` 订行没点名活动），第二把 **51 passed / exit 0**（`run-run079747.log`）；两节点在 2-spec 形制下也 **27 passed**（`run-run079308.log`）⇒ 按第 10 条记为 **FLIP_WITHOUT_SHARED_STATE(node-with-preceding-doors-in-one-process)，各 1 红 1 绿**，具名游红，不归因于本单。
**反向对照（比突变更硬的一条）**：把本单三个产品文件临时退回 `f7ce8ff^`（`V8Experience.tsx`/`LocaleContext.tsx`/`v8Types.ts`，同九文件链）⇒ **47 passed / 4 failed，四条全是我这把新门**：`ord0222-1` 与 `ord0222-5`（深色）报 `/v8/hub renders internal enum tokens: ["ARRIVAL","DEPARTURE","STAY","TRANSIT","AUTO"]`，`ord0222-2` 报读屏输出同样五个 token，`ord0222-3` 的日卡读出 `… Friday … SCOOTER_SHARE PICK_UP_POINT锚点`；而那两条游红在退回态**也是绿的**（所以它们与本单无关这条读数是双向做的）。之后 `git checkout f7ce8ff --` 原样还原，`git status --short -- frontend/src` 空。**未 push**；未碰 `:4781/:4782/:8693` 与 `_live.db`；`demo/reset` 0 次；provider 出网 0 次；账本只追加本块。

status: ORD-0222 **DONE@2026-09-22T20:1x+08 by e345b9d6**（提交 `f7ce8ff`）——七条最小验收：1) 2677/2678/3240/3297 全不再裸印 ✅；2) 3203 `live.eta` 确认消费 raw mode 并已改 ✅；3) `Check in`/`Overnight` 定位到 `days[].activities[]`（服务器内容）＋星期定位到 `days[].label`（形式，已本地化），未塞 mapping ✅；4) zh VISUAL_TEXT_SCAN 无 raw enums、touched rows 无中英混排 ✅（整屏无英文**不签**，理由如上）；5) ACCESSIBLE_TEXT_SCAN 单独跑 ✅；6) 2677 改回 raw ⇒ visual gate RED（killAA1）✅；7) 未知 mode/anchor ⇒ zh 说「未识别…」不泄 token ✅。
evidence: `frontend/e2e/qoder-raw-enums-never-reach-the-traveller.spec.ts`、`review/evidence/ui-overnight/ord0222-visual-scan.json`、`ord0222-accessible-scan.json`、`ord0222-unknown-value.json`、`ord0222-days-side-by-side.json`＋`.png`、`ord0222-dark-scan.json`、`review/ord0222-run.txt`、`review/run-run078539.log`（覆盖率为 0 的那次自纠）、`run-run078759.log`、`run-run078896.log`、`review/tsc-0222[a-d].txt`、`review/ord0222-days-receipt.txt`（一次性探针读数，探针已删）。**未 push**。
