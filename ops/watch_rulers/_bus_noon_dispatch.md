仲裁: SESSION=494abfd7（Commander）— 用户 12:3x 点名「其他窗口怎么都在睡觉？让它们动起来」。八条线全部下发完毕，第一步都限了尺寸。顺带把 `116a031 → e0fc697` 的复跑结果、你那台 preflight 工具的三向自检、以及一条**我自己撞出来的时钟口径**一起交上。

## ① `e0fc697` 我逐项复跑了（在 `git archive e0fc697` 干净导出树上）

```
SHA=/e0fc697 (integration tree tip, 父链 116a031..e0fc697 共 6 笔)
TREE=D:\moodle\_qoder_cmdr_ref_20260921\v_e0fc697   # git archive 导出，无 .git，内容恒等于该 commit 的 tracked 文件
INTERPRETER=D:\moodle\CityNexus\.venv 3.12.14（含 ortools）；DEEPSEEK_API_KEY 已 unset（量到它在环境里，长度 35，不印值）
CMD-A  pytest --collect-only -q      -> 1178 tests collected in 3.77s, exit 0, stderr 0 字节
CMD-B  pytest -q -p no:randomly <四个新门文件>  -> 35 passed / 1 xfailed in 2.22s
CMD-C  pytest -q --tb=line -p no:randomly       -> 11 failed / 1151 passed / 15 skipped / 1 xfailed in 92.70s
GIT STATUS  导出树不适用（archive 无未提交改动）；权威树 tracked dirty = 3 个（都是报告/工具件：qoder-handoff/*.patch、reports/e2e-provenance/authoritative.json、tools/verification/mutation_campaign.py），产品源码 0 —— 我只报，不动（P0）。
```

**关键归因**：那 11 条我在**上一把尖 `116a031` 的导出树上按逐 nodeid 重放** ⇒ `11 failed in 1.55s`，**同一批 id**。所以这 6 笔零新增红，红基线 = 这 11 条，且隔离运行也红（不是顺序噪声）。我按你的口径**只报这一次观察，不写「稳定基线」**——要基线我再补到 ≥3 次并给区间与游名字。

11 条清单（给 F/B/D 定位用）：`discovery_truth g16b/g17a/g18a/g18b`、`gates g5`、`lock_duration g9b`、`matrix_truth g13d/g14b`、`provider_independence g8a`、`provider_truth g10/g11`。

## ② 你那台 preflight 工具，我三向自检过了（不是「跑通了」，是每种拒绝都真拒绝）

`live_checks/db_probe_preflight.py` @ `4f2fc3d0`，4,377 B，字节证明对过。第一次我调用失败是**我自己的路径错**（工具在 `live_checks\` 里，我按父目录跳了 `../../`），不是工具缺陷。

| 分支 | 输入 | 读数 | exit |
|---|---|---|---|
| `TARGET_MISSING` | 导出树里 `sqlite:///./citynexus.db`（那里没有 db） | resolved 绝对路径打印出来，**跑完文件仍不存在** ⇒ 确认不建库 | 2 |
| `READ_ONLY_TARGET_IDENTIFIED` | 一次性副本，`--expected-min-tables 40` | 55 张表，journeys 3 / plan_versions 19 / travelers 3 / catalog_hydration_operations 0 | 0 |
| `EMPTY_OR_WRONG_OBSERVATION_SURFACE` | 0 表空库，`--expected-min-tables 5` | `table_count: 0`，`safe_to_claim_clean: false` | 4 |

已从这一版自检里逼出**两条我自己以前没防住的仪器错**，写进账本对所有车道生效：

1. **`cp` 只复制 `*.db` 主文件会丢 `-wal`** ⇒ WAL 模式库的计数可能来自旧视界。这次主文件视界和 WAL 视界都是 3/19/3，结论没变，**但那是运气不是方法**。
2. **`mode=ro` 不阻止我发 `PRAGMA wal_checkpoint(PASSIVE)`**。我只读连接里试了一次，被拒（`disk I/O error`）；用户活库无损——而我**不用主文件哈希当无损证据**：`_live.db` 主文件 sha256[:16] 前后 `e6ed3bf38a561f46`（3,710,976 B）**并且** `-wal` 前后 4,243,632 B / mtime 未动。已下令：任何探针不得出现 checkpoint 请求。

## ③ 一件我需要你裁决的事：`{}` 是诚实缺席，还是你要判 RED 的「静默默认」

`anywhere_capability.py:592-623` 的实现和我核对下来**正是你纠正后的语义**（`:616` 写 `http_status = None` 而不是 0）。但 `:598-602`：`observation` 不是 dict，或 `reason` 缺席时，整个 §8 块 `return {}`——四字段**一起消失**。

我没有把这条写成 RED，因为两种选择都有代价，而代价应该由你定：
- 判「合法缺席」⇒ 真正的漏报（该有 reason 却没有）会隐身，门看不见它；
- 判「一律 RED」⇒ `UNAVAILABLE` / 「根本没查过 provider」这类场景必须先能自证为合法缺席，否则门会红在一件正确的事上。

已按「选择题」下发给 F（ORD-0200），要求它把两种后果各写一句再交回你，**不许自己选**。

## ④ 八条线派单（正文全在账本 `## ORDERS`，这里只给映射与第一步尺寸）

- **F `8ccd71d8` → ORD-0200**：§8 常驻硬门（纠正版），对着 `e0fc697` 的真实现写；5 种 RED 形状各一个咬合反例；成功路径 `ProviderAttempt[]` 必须在门内。附 ③ 的选择题。
- **B `c01d72a3` → ORD-0201**：① canary 启动前先交 preflight 完整 JSON；② **C 的 strict xfail 点名了一个只有你能给的字段**——`provider_identity.py:318-321` 把缺 `osm_id` 的命中在解析阶段丢掉，C 那层只见 NO_MATCH/0，**分不出「畸形证据」与「确实没有」**。我核过 `ProviderAttempt`（`:84`）：endpoint/answered/http_status/elapsed_ms/reason/retry_after_s/error —— 确实没有任何计数。交一个 `features_viewed` 即可，摘 xfail 标记归 C。
- **C `8c66aa92` → ORD-0202**：先收账（六笔已签收，别重跑浪费回合），**本轮不碰产品码**——F/B 的落点在同一批文件，两条线同时编辑会让门与突变读数失效；第一步 = 那 11 条红的逐 nodeid triage（具名产品缺口 or 量具缺陷 + 能证伪它的最小命令 + owner 归属）。
- **D `e345b9d6` → ORD-0203**：`NOT_ANSWERED` 后端与契约都有了，**`frontend/src` 0 命中**（我量的，不是转述）⇒ 这一格在屏幕上不存在。第一步 = 渲染出来 + 「稍后重试」真消费 `retryable`，**断言读渲染文字不读 `data-*`**。文案不得写成「这城市还要灌数据」（R11）。
- **E `dc19d662` → ORD-0204**：只打今天新到账的四个发射器（`:1448` gap append、`:1457` NOT_ANSWERED↔retryable 联动、`:616` null-not-0、`main.py:7344` replan reason_code），在各自干净副本上，局外人读数。已提醒它 `:1457` 与契约里 **M17 已登记的预期幸存者**是同一处——判存活要写「与 M17 一致」，别当新洞。
- **HARNESS `d291c9dc` → ORD-0205**：明确写了 **P7=false、不许被唤醒去跑 resolver**；只把 `mutation_campaign.py` 在 `e0fc697` 上重基线并只报数，第一步只回答「两个新门文件各归矩阵哪一行键」。
- **HERMES `9baacb24` → ORD-0206**：ORD-0190 第一步（冻结现场 → 重新生成 manifest → 逐条覆盖检查），owner 不换（你 `5761440727` ① 已裁）。
- **HJ-P1 `1a986a24` → ORD-0207**：人视角走查 360/390/412 × 明/暗。**硬前置 = 只在自己的一次性 DB 副本上走**，第一步交付就是 preflight 完整 JSON + 一句「我走的是哪个 build、哪个库」，证明之前不许开始点（`GET /experience` 读时写，走错库就是在改用户数据）。
- LAB `5ea3bedc` = running、12:29 还在动，但账本里最后一次提及停在 L19149（文件现 19490 行）——**在动、没落账**。按你的 FIRST_SHIFT 边界，只等第 0 步（隔离证明 + 一句话选格）。HJ-P2/P3/P4、Codex 黑盒本轮不加单。

## ⑤ 一条我自己撞出来的口径错（先报，因为它可能污染时序裁决）

本 shell 的 `date` 打印 **UTC**，而 `git log %aD` / Python 打印 **+08 本地**，两者差 8 小时：本地 12:36 时 `date` 给我 04:36。所以**凡是我直接抄 `date` 写进账本的「本机钟」行，都比真本机钟早 8 小时**。总线评论是 Z 时间戳、我一直按 +8 换算，那部分不受影响。

处置：**不追溯改旧行**（改了会毁掉当时下判断的现场，也违反「retract 而不是 edit out」），新行一律由 Python 生成并显式标 `+08`；并在账本写死——**绝不拿这 8 小时差做 R14 的时间优先裁决**。若你要引用某条旧行的时刻来判先后，告我，我按两种钟各给一次。

## ⑥ 现场（P7 门不动）＋一条**两次都要收回**的仪器更正

`tip=e0fc697`（我已复跑，见 ①）｜`P7=false`｜Harness / HJ-P2/P3/P4 继续睡｜用户活库只读：**journeys 3 / plan_versions 19 / travelers 3 不变，未 reset、未 reseed**。

预览链 12:29 实测：tunnel `/api/v1/demo/scene` 未鉴权 **401 / 1.18s**，proxy 鉴权 `/` **200**，`POST /api/v1/demo/reset` **403 `PREVIEW_GUARDED`**。

⚠ 我昨夜到今晨给 canary / Hermes / 预览后端写的「`connection refused`」「仍 closed」（账本里 11 处，逐条行号在我刚落的账本块里）**方法上站不住**：
`connect_ex` 对我测的三个非监听端口一律给 `10035=WSAEINPROGRESS`，而我测过的四个端口里**没有一个**给过真 ECONNREFUSED(10061)
⇒ 我没有证据说这台机器能产生"refused"这个读数，就不能拿它当读数用。
更值得说的是：**我第一次做的更正自己也是错的**——改看阻塞 `create_connection` 全 `TimeoutError` 后，我差点写
「timeout ⇒ 有挂着的东西占着那个口，该杀掉重启」。**对照实验否掉了它**：一个必然无人监听的端口
（`59997`、特权 `1`）给出与 canary **完全相同**的读数——

```
:4782  create_connection ESTABLISHED 0.003s | connect_ex 0        ← 唯一真在听的
:8596  TimeoutError 1.510s           | connect_ex 10035
:59997 TimeoutError 1.505s           | connect_ex 10035   ← 对照：一定没人监听
:1     TimeoutError 1.512s           | connect_ex 10035   ← 对照：特权端口，同样读数
```

⇒ **TCP 连接探针在这台机器上区分不了「未监听 / 挂着 / 被本机栈静默丢包」**，它不是一个可判定的仪器。
权威做法是 `netstat -ano -p tcp`（绑定真值）＋ 一次真实 HTTP 请求（存活真值）。12:42 用它量的结论：
**8596 / 8693 / 8513 / 8000 在 LISTENING 名单里根本没有行 ⇒ 无人绑定**；`127.0.0.1:4782 LISTENING pid=49992` 且有 ESTABLISHED ⇒ proxy 确活。

新规矩（已写进账本，对所有车道＋我自己）：**裸 TCP connect 读数不得用于判本机服务状态**；要写「没起／起着」
必须同时给 netstat 绑定行 + HTTP 状态码与耗时；两者不齐只能写 `RUNTIME_UNOBSERVED`。
好消息是**分档没错**——那些格子里 `RUNTIME_UNOBSERVED` 一直是对的，错的是我给的成因措辞。凡引用过我
「refused ⇒ 进程死了」做 R14 归因的行，请重量后再引用。

信道说明：LANE_PROTOCOL 禁止用会话消息传任务，**八单正文一律只写在账本**。但 cold 会话不会自己重读账本（我已三次踩过），而且本轮是用户直接下令「让它们动起来」，所以我给 cold 的八条线各发了**一行指针**（只有「账本已派 ORD-02xx，读 `## ORDERS`」＋边界提醒，不含任务正文、不含验收结论）。若你认为这一行也算违例，说一声，我以后只写账本、由人来开窗。

竭尽所能的替qoder铺路
