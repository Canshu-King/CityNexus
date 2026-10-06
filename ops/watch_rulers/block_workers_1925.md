### 19:2x 实测覆盖（**上面那张 21:1x 的表已过期，以这一块为准**；来源＝`list_chat_sessions` 的 `runtimeState` + 账本写入时间，不是回忆）

| session（前 8） | 车道 / 现在手上的单 | runtimeState（19:2x 实读） | 写域 |
|---|---|---|---|
| `494abfd7` | **Commander**：巡检、亲测、仲裁对接、台账 | running | `_qoder_recovery_20260919/**` + Workspace 的 `commander/control` |
| `8c66aa92` | **C 后端**：ORD-0111 / 0112 / 0114 / 0115 / 0121 / 0122 / **0125(P0)** / **0132(P0)** / **0138(P0)** | opening（已叫醒） | `backend/**`（权威树由 F 持有，写域按 FILE_OWNERSHIP 走） |
| `8ccd71d8` | **F 契约与门禁**：**0131(P0，仲裁已冻结 A-E 口径)** / **0133(P0，R11)** / 0123 / 0136；0118、0106 已 ACCEPTED | **running** | `contracts/**` + `backend/tests/**` |
| `e345b9d6` | **D 前端**：**0126(P0)** / **0134(P0，面板视口 + 地图手势)** / 0135；0104①、0107① 已 ACCEPTED-CODE；**0124-B port 仍 HELD** | **running** | 隔离树 `frontend/**` |
| `c01d72a3` | **B 外部数据实测**：**0127（R10 已冻结 9 规则 + 7 硬门）**；0092、0109 已 ACCEPTED | opening（已叫醒） | `live_checks/**`、只读取证 |
| `dc19d662` | **E 红队**：**ORD-0113 未交**（abort→500 的响应体原文 + traceback 行） | ready（**空闲 1h+，本轮叫醒**） | 只测不改 |
| `d291c9dc` | **Harness 线**：0119 已 ACCEPTED → **0128**（EXP-HARNESS-002 + `d6b` 分母 + 修过期断言） | opening（已叫醒） | 隔离 lab `D:\moodle\_qoder_harness_revival_20260921\**` |
| `1a986a24` | **HJ-P1 背包客**：**0129**（新包手机复验：假离线死屏 / 建承诺 404 / 北京两条路） | opening（已叫醒） | 只测不改 + 独立 profile |
| `d4b04a0f` | **HJ-P2 承诺密集型**：上一轮已交（0132 的因）→ 本轮派 **0141** | ready（**本轮叫醒**） | 只测不改 + 独立 profile |
| `aad2d1f2` | **HJ-P3  impatient 用户**：地图机制已交（0134 的因）→ 本轮派 **0142** | cold（**本轮叫醒**） | 只测不改 + 独立 profile |
| `4e974ae5` | **HJ-P4 偏好密集型**：0120 全收 → **0139**（盯 0138 三条 + P4-2/P4-8 复现卡 + P4-10 分母） | running | 只测不改 + 独立 profile |
| **`9baacb24`** | **HERMES_REVIVAL（第三条产线，新建）**：**ORD-0140** | **新建 running** | 只读 / 隔离根 `D:\moodle\CityNexus-Hermes-Revival\**` |
| `5ea3bedc` | AI Architecture Scout（旧）：AI scout reuse map 已交付，无在手单 | cold | 只读 |

**lineage 一句（按令要求记）**：`list_chat_sessions` 翻完两页共 **34** 个会话，标题内**没有任何旧 Hermes 专属会话**
⇒ 按 5758456196 §1 的"否则新建并记录 lineage"新建 **`9baacb24`**。
**车道字母以 `to:` 会话 id 为准**（我 19:1x 已认账：叙述里 C/F/B 三位字母串过）。
**全线禁令**：不碰 `:4781/:4782/:8693` 与 `_live.db`；修好前不许触发 `demo/reset`；不对 github.com 用 git 网络操作。
