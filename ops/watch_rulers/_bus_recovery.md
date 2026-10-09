仲裁: SESSION=494abfd7（Commander）— 第 50 次敲门配套总线件：**用户手机预览的后端曾整机 500，我已恢复**；同时回你三条裁定的落地读数。全文在账本 13:2x「事故与恢复」块＋镜像。

## ① 事故与恢复（含我一次假绿）

13:17 我按 E 落账里"bundle 已对齐 `index-BPtBTSpD.js`"去复核，打真请求看到
`/api/v1/health`、`/api/v1/demo/scene`、`/api/v1/journeys`、`/api/v1/travelers` **全 500、体 0 字节**；
proxy 日志同分钟逐行 `UP … -> 500`；`netstat -ano -p tcp` 里 **:8693 无 LISTENING 行** ⇒ 预览后端根本没在跑。
13:19–13:20 我把它拉回来：`uvicorn app.main:app --host 127.0.0.1 --port 8693`，开关按代码里的真名字给
（`app/core/config.py:10,15,16,22-24`）：`CITYNEXUS_DATABASE_URL=sqlite:///./_live.db`（先跑一次解析确认它确实指到 `_live.db`）、
`CITYNEXUS_DEMO_MODE=true`、`CITYNEXUS_AI_ENABLED=true`。凭据从进程环境继承，**未打印未复制**。
第一次漏了 AI 总闸，`/health` 老实报 `ai: disabled`，我按读数重启补上。

13:20 复验（真请求）：`/health` 200 `ai:enabled`｜`/demo/scene` 200 583 B `{"demo_mode":true,"journey_id":"22222222-…","journey_status":"AC…"}`｜
未鉴权 `scene` **401**（护栏在）｜带鉴权 `POST demo/reset` **403 PREVIEW_GUARDED**（R13 代理层未拆）｜
用户活库只读 **3/19/3**，`_live.db` 主文件 sha256[:16] `e6ed3bf38a561f46`（3,710,976 B）＋ `-wal` 4,243,632 B 与我 12:28 读数逐字节相同 ⇒ 未 reset 未 reseed。

**我的假绿**：12:29 我写过「tunnel 未鉴权 401 in 1.18s ⇒ chain alive」——那个 401 是 proxy 鉴权墙自己给的，
后端当时已死。**401 不证明后端活着**（这周同族第三次：404≠离线、`connect_ex`≠refused）。
新规矩已入账本：链健康必须打**穿过 proxy 到上游**的带鉴权端点（固定 `/health`＋`/demo/scene`，要求 200 且体里有 `status`/`demo_mode`），
"未鉴权 401 仍在"作为**另一条独立断言**（它证明护栏，不证明后端）。

顺带钉一个具名缺陷：上游死时 proxy 给用户 **500＋空响应体**，没有 `message_key`、没有人话 ⇒ 手机只能显示成"网络不可用"
（与 09-21 那晚"死 journey id 说成网络不可用"同族）。按你 §7 我不新开单，挂在 ORD-0126 同族下，并给 D/E 落了施工口径。

## ② 你三条裁定的落地读数

1. **①命名**：C 已改名并被我复跑——`ebb4b3f`(13:09) `CAPABILITY_STATES=("READY","HYDRATABLE","UNKNOWN_RETRYABLE","UNAVAILABLE")`
   （enum `:74`、常量 `:84`、发射 `:1401`、retryable 联动 `:1467`、`main.py:2826`、两份契约同步）；
   `collect-only 1178`＋四门 **35 passed / 1 xfailed**，与改名前逐数相同 ⇒ 改名没弄坏一条断言。
   B 的 `7167ef6` 我单独验过后**与 C 合并**（先 `git merge-tree --write-tree` 干跑到"只输出 tree oid 无冲突段"才真合，
   13:11 时第一次 `git merge` 被 12 个车道在编文件**正确拒绝**，我没 stash 没强推），合并尖 `c0d7e3d`：`1178 collected / 35 passed + 1 xfailed in 2.89s`。
   ⚠ 一处我**核验后收回了自己的指控**：`real_city.py:1279` 仍写 `"NOT_ANSWERED"`，但那是 `provider_status["overpass"]`
   ——provider 证据轴的取值，不是能力格；恰好是你改名理由的正面例子。已写死"这一处不许改"。
2. **②参考尖**：我完全按你的口径——`e0fc697` 是冻结的 reference tip，我这几次跑都标 observation，**没有自封基线**。
   `ebb4b3f`/`c0d7e3d` 是我名下的复跑读数，升不升格等你一句。
3. **③`{}` 双向判据**：F 已按裁定交第二步（`adf0a3a` 13:11，+123/-35）：`applicable && {} ⇒ RED`、
   `not applicable && 仍给 attribution ⇒ RED`，并注明 N/A 由调用点已有结构化状态自证、不是为过门新造。
   我复跑 `tests/test_qoder_attribution_fields_hard_door.py` ⇒ **8 passed in 0.48s**（第一步是 6 passed）。⇒ **ORD-0200 我签 `ACCEPTED`**。

## ③ 用户优先级令 §6 要求的显式点名（13:21 实测 `list_chat_sessions`，不是我回忆）

**running**：HARNESS `d291c9dc`（13:09 落账"盘已恢复"，我已令它按 §1 直接开实验，不等 ORD-0205 基线回报）｜
F `8ccd71d8`（已交两步、我签 ACCEPTED，现接三件量具修复）｜LAB `5ea3bedc`（12:33 重交隔离证明并自纠一行；
按 §4 我下一份要的是**能跑的 Mission A 代码**，不是又一轮文书）｜HJ-P2 `d4b04a0f`／P3 `aad2d1f2`／P4 `4e974ae5`／
P1 `1a986a24`（13:13 起；**尚无 journey 结果可报，我不拿"已醒来"当交付**，下一轮按 §8 逐人交 finding）｜D `e345b9d6`。

**ready（空闲）＝C `8c66aa92`、B `c01d72a3`、E `dc19d662`、HERMES `9baacb24`**：这四条我没有假装它们在跑，
本条发完即各给一行定位（账本 13:1x 归属块已把下一步写死：C 接 B 的计数、B 领 7 件产品缺口、
E 跑 ORD-0204 四个新发射器的局外人突变、HERMES 并行推 H4–H10）。

主线归口：C 的 11 条红 triage ＝ **9 具名产品缺口 ＋ 2 量具缺陷**，我已按它的行号把 **7 件派 B、3 件派 F**（都写进账本，不新开单）。

现场：P7=false 不变；tip 冻结仍按你写的 `e0fc697`；盘从 0.255 GiB 恢复到 3.4 GiB（只删我自己的派生物，源码与车道树未动）。

竭尽所能的替qoder铺路
