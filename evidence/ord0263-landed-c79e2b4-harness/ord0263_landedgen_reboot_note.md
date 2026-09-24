# ORD-0263 盘上落地代 · 重启中断记录（segment 1）

机器在 02:2x–02:3x 蓝屏并重启（用户在另一会话查蓝屏）。我那一格的重跑被拦腰切断：面 `:4417`、后端与三种仪器
进程全部消失，重启后 netstat 上我自己的端口 `4411-4417 / 8411` 全空（用户链 `:4781/:4782/:8693` 当时也没在听）。
这一份文件存在的理由只有一个：**把被切断的那一段的原始工件先外读，别让它们在对话里孤存。**

## 1. 重启前已经拿到的（同一台面、同一枚 bundle `index-ChOTTCvB.js`）

| 格 | 屏上标题与归因列（逐字） | 旁证 |
| --- | --- | --- |
| S1 2xx | `还没休息 · Demo之旅 · 今天 还没有安排`；16 发 `/api/v1/*` 全 200；网络词 0；`snapshot_rows=1` | 面收据 `ord0263_close_surface_receipt.json` |
| S2 源答 500 | 「服务器 | 服务暂时不可用 | 服务器刚才答了你，但它自己报错了（HTTP 500）…」`reason=SERVER_ERROR evidence_kind=HTTP_RESPONSE http_status=500 source_layer=RUNTIME cached_copy_present=true`；experience 计时 4 ms status 500 | curl health 500 text/plain 0.030s |
| S4 读不回话而 health 答 500 | 与 S2 同句，但列成 `evidence_kind=HEALTH_PROBE http_status=500`；experience 计时 **12 008 ms status 0**、health 6 ms 500 | `ord0263_origin_state_answered_health.log`：`age_s 12.01 outcome abandoned_by_client`，final state `closed_by_instrument: 0` |
| S3 静默 | 「没有回音 | 等了 12 秒，这台服务器一个字也没回答…」；experience **12 003 ms**、health **4 017 ms** 皆 status 0 | `ord0263_origin_state_fully_silent.log`：12.0 s 与 4.01 s 两次 `abandoned_by_client`，`closed_by_instrument: 0` |
| S5 200+HTML | 「服务器答了 200，可带回来的不是这一屏能用的数据」；`reason=ORIGIN_INVALID_RESPONSE evidence_kind=HTTP_RESPONSE http_status=200 source_layer=RUNTIME content_type=text/html; charset=utf-8 cached_copy_present=true` | `ord0263_junk_html.log`：answered 200 `text/html` 1,200 B |

**没来得及测的**：S5 的另两形（200+空体、200+非 JSON）。

## 2. 我采用的处置（不是把两段混成一张表）

重启后另起一个干净台面（新端口、新 origin，避免旧 SW 与旧快照串味），**把七格整张表重跑一遍**，
然后把"重启前那一遍"与"重启后这一遍"并排交：

* 两遍一致 ⇒ 蓝屏不影响结论，且这是一次天然的重复观测；
* 两遍不一致 ⇒ 以更晚、条件更完整的那遍为准，并把差异具名报出来，不取平均也不各说各话。

重启前的这些数字**不并入**重启后的 capture 文件；它们只作为本记录的对照。

## 3. 尺的状态（这一段还没跑判据）

`tools/ord0263_verifier_v3.py` 21,703 B / git-blob `e9a4188f63e27bbbf8bfed35adfd554b9e8641d9`，
与号令里那枚一致；本轮**不改尺、不出 v4**（仲裁 5800456557 已裁），缺的那枚 UNKNOWN_FAILURE mutation killer
按 `verifier coverage debt` 记，闭单文字里我会逐字带上包工头给的那句自限。

## 4. 纪律回读

克隆 `compat/ord0254` = `6a39c527f2aa3b16e73dfd122c34d6e6be7102df`，`git status --porcelain` **0 行**
（tracked 与 untracked 都是 0，无 stash）⇒ 蓝屏没有吞掉任何未提交的代码；盘上根 `D:/moodle/_qoder_preview_20260920/dist`
全程只读；`demo/reset` 0 次；`_live.db` / `_preview.db` 未打开；凭据未打印；本轮新路径
`evidence/ord0263-landed-c79e2b4-harness/` 另名，不覆盖任何已发布路径。
