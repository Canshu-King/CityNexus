# ORD-0263 §⑤ · 落地代（`index-Cpy_jhEg.js` / 尖 `2b49e3ca`）四格读数，以及"是不是仪器替产品收口"的三方对表

同一枚尺（`tools/ord0263_verifier_v2.py` = `aeece06ba30d4bed…`，SELFTEST 14/14，判据一字未动），
同一个面配方，唯一变量是盘上的产物。结果：**`ALL_GREEN`（6/6 臂）**，
而 21:46 那一判在上一代是 4 臂红 —— 两份 capture 可以逐行对照。

## 1. 量的确是换代那一枚

`D:\moodle\_qoder_preview_20260920\dist` **只读**：`assets/index-Cpy_jhEg.js` **1,242,399 B /
sha256 `5d674a444291f10b45fa50dc53f57845c888013bc3d941f6fc6d0f9f5ad7b2d7`**，与你给的数字**逐位相同**；
根目录 32 文件 / 16,818,701 B / tree sha256 `074267d90c499b71…`，我那份副本的 tree sha256 同一个值 ⇒ 未重建。
`index.html` 盘上 mtime **21:58**（你说 22:02 换代 —— 我以盘上 mtime 报，不按号令时刻改我的读数）。
浏览器每格都回读 `bundle=index-Cpy_jhEg.js`。

面：我自己的 `:4415`（vite preview 指向我那份副本，起面带 `CITYNEXUS_BACKEND_PORT=8411`）＋我自己的 `:8411`；
归属双向 PROVEN（marker 行程经 `:4415` 200 ＆直连 200，一个我库里 0 行的 uuid 经同一代理 404）。
`:4781/:4782`/隧道/cnx proxy/`_live.db`/`_preview.db` 一个没碰，无 `demo/reset`，产品码 0 改动，尺 0 改动。
快照由 app 自己的「使用封存的演示行程」赚得，四格 `snapshot_rows=1` 贯穿。

## 2. 四格逐格

| 格 | 源状态（线上回读） | 屏上原句 | 网络词 | 点名服务 | 交出本地快照 | 门 |
| --- | --- | --- | --- | --- | --- | --- |
| S1 2xx | 真后端 health/journey 200 | `晚上好 · Demo之旅 · 今天 还没有安排`（游标那句仍是诚实版） | 0 | — | — | 正常导航 |
| S2 源答 500 | `:8411` 无监听→代理 500 text/plain 0.003s | 「服务器 ／ 服务暂时不可用 ／ 服务器刚才答了你，但它自己报错了（HTTP 500）。这是服务暂时不可用，不是你填错了什么。**这台设备上还留着你已保存的行程，用下面的按钮可以只读查看这份本地快照**；也可以稍后重试。」 | 0 | ✅ | ✅ | 看已保存的只读副本 · 重试 · 归因详情 |
| S3 静默超时 | fully-silent：health/journey 全不答、**也不关** | 「**没有回音** ／ 等了 12 秒，这台服务器一个字也没回答 ／ 这一发读取到了期限仍然没有任何回答：服务器既没有拒绝，也没有答应，它只是没有说话。你的行程数据没有丢…**这台设备上有已保存的行程**…」 | 0 | ✅（说的是"这台服务器"） | ✅ | 看已保存的只读副本 · 重试 · 归因详情 |
| S4 读不回话而 `/health` 答 500 | health 500 json 0.004s；读挂住不关 | 与 S2 同一句（归到"服务暂时不可用"，没有说成网络） | 0 | ✅ | ✅ | 同上 |

`S2/S3 不得共用同一句`：两臂句子与标签都不同（`ORIGIN_ERROR_WITH_SNAPSHOT` vs
`NETWORK_UNREACHABLE_WITH_SNAPSHOT`），且 S3 不是骨架 ⇒ `V3_distinctness GREEN`。

## 3. §⑤ 那一条：不是仪器替产品收口（三方独立对表）

我因此**换了仪器**：`tools/origin_hang_no_close.py` 取代 `mixed_origin_port.py` —— 挂起的读取它**永不写、永不关**，
并把每一发的结局记到 side log（`outcome: abandoned_by_client` / `closed_by_instrument`）。
上一代 S4 之所以 40.311 s 才出句，就是因为旧仪器挂满 40 s 后自己关了 socket；这一轮不允许那样收口。

| 时钟 | S3（静默） | S4（health 答 500） |
| --- | --- | --- |
| 浏览器 Resource Timing（那一发 fetch） | `/experience` duration **12 009 ms**，`responseStatus 0`；随后 `/health` duration **4 005 ms** | `/experience` duration **12 012 ms**，`responseStatus 0`；随后 `/health` 3 ms 拿到 500 |
| 我的仪器 side log | `/experience` 挂 **12.01 s** → `abandoned_by_client`；`/health` 挂 **4.0 s** → `abandoned_by_client` | `/experience` 挂 **12.01 s** → `abandoned_by_client` |
| 仪器全程 `closed_by_instrument` | **0**（final state: opened 3 / abandoned 3 / still_open 0） | **0**（opened 2 / answered_health 2 / abandoned 2） |
| 产品自己的常数 | `READ_DEADLINE_MS = 12_000`＋`probeHealth` 4_000 ms | 同 |

⇒ 三个互不读对方的时钟在同一位数上会合，而且**服务器侧观察到是客户端发 FIN**：这一代是**产品自己有界**，
记 `PRODUCT_BOUND`。上一代这三行里第一、二行根本不存在（读取永不结束），所以那两格我当时记
`settled_within_deadline=false`。**若这次它们不一致，我会写 `NOT_PRODUCT_BOUND` 而不是挑一个好看的。**

一个必须说小的技术口径：页面侧采样器仍然装得晚（MCP 往返 ~15 s），所以 S3/S4 的"出句瞬间"取自
Resource Timing ＋仪器日志，而不是取自采样跳变 —— 两处的原始行我都抄进了 capture 的
`product_bound_evidence`，可以指着核。S2/S4 的稳定性仍由采样证明（S4 从 15.1 s 到 65.5 s 共 169 样本不变，
间隔中位 296 ms／最大 313 ms）。

## 4. 判定

```text
S1_live GREEN · V1_origin_error_5xx GREEN · V1_vacuity_witness GREEN · V2_no_answer GREEN
  (seconds_to_settle 12.1, label NETWORK_UNREACHABLE_WITH_SNAPSHOT, retry_door true, 不在骨架, 快照已交)
V3_distinctness GREEN · V4_silent_read_answered_health GREEN (health 500 + 读永不答 => ORIGIN_ERROR, 12.2 s)
derived_result: ALL_GREEN
```
尺与判据一字未改（同一 blob），改的只有仪器；两份 capture 用同一个 `cell()` 组装、标签一律由渲染文字派生
（`typed_in_by_verifier: false`）。

## 5. 没做与边界

* 覆盖范围仍是"这一枚产物 + 我这台设备上的快照状态"，不含真手机与 SW 缓存层（那两个端口我一个没碰）。
* 我没量"产品在没有我任何仪器配合下"的其它路径（写请求、重算）；本轮四格只覆盖读路径。
* `:8411` 端口上的进程换过三次（uvicorn → answered-health → fully-silent），每一步的 wire 读数与 netstat
  释放都在收据里；`mixed_origin_port.py` 本轮**未使用**，旧文件未动。
* 现场收尾按具名清单：`:4415`(我起的) 与 `:8411` 停、`landedgen/dist` 副本删（tree sha256 已存收据）、
  源根收尾后**再哈希一遍仍等于** `074267d90c499b71…`；克隆仍在 `compat/ord0254` = `6a39c527f2aa…`，
  `git status --porcelain -- frontend` 打印 0 行。
* 共享浏览器里另一个车道 22:21 开了新 tab（:8487/:8485），我只 `select` 回自己那一 tab、未动别人的页 ——
  按 `SHARED_BROWSER_CONTEXT_OWNERSHIP_V1`。

坐标走 `evidence/ord0263-landedgen/`（新路径；`evidence/ord0263/`、`evidence/ord0254/`、
`evidence/ord0263-livegen/` 全部一件未动），每件 PUT 后独立 GET 回读满 40 位。
