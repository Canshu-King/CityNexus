## commander 亲测＋部署 @2026-09-22T15:4x+08 —— **用户手机上那行废话已经换掉了**（bundle 换包，0 后端重启）；ORD-0209 行为级正证 0 POST；ORD-0212 我做到哪一格、没做到哪一格

### ① 部署（用户 15:00 指令的那一格，别再等到明天）

```text
线上旧包  assets/index-CnfHH2K_.js   （今天 02:10 构建，HJ-P1 15:10 的"改前"基线用的就是它）
线上新包  assets/index-BCF4ptyk.js   （`56d20ec` 构建，`npx vite build` 于 integration 树，frontend/ 当时 0 脏文件）
备份      D:\moodle\_qoder_preview_20260920\dist_bak_1538   （10 文件，回滚＝把 dist 换回去）
后端      未动：`53fe8e8..56d20ec` 差 **29 个 backend 文件** ⇒ 按"差集碰后端才重启"的规矩，:8693 仍钉 `53fe8e8`，0 秒中断
回读      http://127.0.0.1:4782/ 200 且 index.html 内 bundle 名＝新包；隧道 `/` 200 且同名
```

### ② ORD-0209 的行为级正证（我自己当用户走的那一遍，不在用户库上做点击实验）

canary 收据（按 canary 三件套写明）：

| 项 | 值 |
|---|---|
| SHA（前端） | `56d20ec`（构建产物 `index-BCF4ptyk.js`） |
| SHA（后端码） | `53fe8e8`（与线上同一个 `_qoder_cmdr_gate_20260921` 树，只读） |
| 端口 | 静态 `:4184` ＋ 后端 `:8694`（都是我先 `netstat` 确认空闲才占的，不碰 `:4781/:4782/:8693`） |
| DB 副本 | `live_checks\canary_56d20ec.db`，用 `sqlite3.Connection.backup()` 从 `_live.db` 取（**不是文件拷贝**），取后回验 journeys/travelers/plan_versions＝3/3/19 |
| 清理计划 | 验完停 `:8694`/`:4184` 两进程，副本库与 `canary_dist/` 留在 `live_checks/` 下作证据，**不动** `_live.db` 一个字节 |

390×844 实测：按钮 `使用封存的天津演示` 可见、`[20, 696, 335×44]`、`elementFromPoint` 命中自身（`BUTTON.trial-back-link`）；点击后 **10 条请求全部 GET、POST＝0**，其中第一条业务请求就是
`GET /api/v1/journeys/22222222-2222-4222-8222-222222222222/experience` ⇒ **入口真的去寻址封存行程**；落点 `/v8/hub`，屏上「Demo之旅 · 1 位旅行者 · 1 天」，**没有** `每人每天约` 行；canary 库前后 journeys/travelers/plan_versions 仍 **3/3/19**（⇒ 没有偷建行程）。
对照 HJ-P1 15:10 的"改前"基线（1 击 ⇒ `201 POST /travelers` ＋ `201 POST /journeys` ＋ `200 POST …/stay-options/generate`，落屏"城市探索"）——这一格的行为差异是**肉眼级**的，不只是提交说明。
**没做到的一格我写清楚**：`tight` 档的"仍在主页"我只读到 D 的代码与它新加的 210 行三档 e2e（`review/add-ord0212-mutant.py` 反例、`review/redirect-ord0064-gate.py` 把旧门改指确认屏＝我单里要的"别删覆盖"），**运行时我没有构造出 tight 场景** ⇒ 这一格 `ACCEPTED-CODE`，不是 `REPRODUCED`。手机真机那一格也没签：旧 service worker 可能仍给一次旧界面，**重开一次**即可；这条我按"未验证到真机"记。

### ③ 给 D / HARNESS 的一条验收形状（HJ-P1 15:10 的陷阱，我实时也证实了）

点一次之后按钮随跳页消失 ⇒ **"同一页上连点三次 ⇒ 0 POST" 的门会天然通过**。正确形状：**三次独立的"重进向导 → 点入口"循环**，每轮各自断言 `POST /travelers == 0 && POST /journeys == 0` 且落点是封存行程。我这遍只做了 1 轮（`postCount=0` 的那次），所以我不签"三次连点 0 新建"这一格——请 D 或 HARNESS 按三轮形状补，我用读数并排引用。

### ④ 现场

working tip `56d20ec`；reference tip `c0d7e3d`（仲裁冻结未动）；`P7=false`；15:35 巡逻：匿名 `scene` **401**、鉴权 `POST /demo/reset` **403 PREVIEW_GUARDED**、用户库 3/19/3、places `CN-BEIJING 8 / CNX-DEMO 8`；我 15:45 换包后复查用户库仍 **3/3/19** 与 15:35 同数 ⇒ **无行增删**。本轮 0 次 `demo/reset`、0 次 provider 出网、0 次写 `_live.db`（只读计数除外）。ORD-0211／g3 那 14 个进程读数在上一块（15:2x），ORD-0213 已在其下的 `- id:` 条目里。
