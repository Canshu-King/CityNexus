# ORD-0263 第五态复跑 · B 候选 `c79e2b4f`：**七格 ALL_GREEN，尺一字未动**

尺：`tools/ord0263_verifier_v3.py`，跑前跑后同一枚 —— 21,703 B / git-blob
`e9a4188f63e27bbbf8bfed35adfd554b9e8641d9`（sha256 `25a8744e61cbb5f3…`），回验 `unchanged: True`。
面：我自己的 `:4416`（vite preview 指向我从 `c79e2b4f` 构建的 dist）＋我自己的 `:8411`。
只测不改：产品码 0 改动、尺 0 改动、无进程内替换 BASE、`:4781/:4782`/隧道/cnx proxy/两个用户库一个没碰、
0 次 `demo/reset`。

## 1. 血统核对（与你亲核的数字对表）

```text
commit c79e2b4f4efe414dba22a071a7136ae10b5c84aa  Thu Sep 24 01:06:23 2026 +0800
  fix(frontend): name an answered-but-unusable 200 as its own failure state (ORD-0263)
parent           1f4440819a9d773da6e18f12a31412f73c6d0f55   (is-ancestor rc=0)
range 1f444081..c79e2b4f   1 commit
diffstat         3 files changed, 115 insertions(+), 4 deletions(-)
numstat          api/citynexus.ts 17/1 · app/V8Experience.tsx 27/2 · lib/failureAttribution.ts 71/1
bare diff        13,512 B
构建产物         index-ChOTTCvB.js 1,245,203 B sha256 2d56a79632efc0c6…；css 未变 1b3632785212847b…
```
⇒ 与你号令我的那串一致，构建由我在自己的克隆里从该 commit 直接做，未改一行。

## 2. 七格（同一台面、同一个读数函数、`snapshot_rows=1` 贯穿）

```text
S1_live GREEN · V1_origin_error_5xx GREEN · V1_vacuity_witness GREEN · V2_no_answer GREEN
V3_distinctness GREEN · V4_silent_read_answered_health GREEN · V5_origin_invalid_response GREEN (green=3 red=0)
derived_result: ALL_GREEN
```

第五格三形各自（屏上归因列是**渲染出来的**，展开「归因详情」逐字读到）：

| 形 | 仪器答的（读自 side log） | 屏上列 |
| --- | --- | --- |
| 200+HTML | 200 `text/html` 1,200 B | `attribution_reason=ORIGIN_INVALID_RESPONSE evidence_kind=HTTP_RESPONSE http_status=200 source_layer=RUNTIME retryable=true recovery_action=retry content_type=text/html; charset=utf-8 cached_copy_present=true` |
| 200+空体 | 200 `application/json` 0 B | 同上，`content_type=application/json` |
| 200+非 JSON | 200 `text/plain` 33 B | 同上，`content_type=text/plain; charset=utf-8` |

句子：「服务器答了 200，可带回来的不是这一屏能用的数据 ／ 它确实回了话（HTTP 200，Content-Type: …），
只是那不是一个可解析的行程响应。…**这台设备上还留着你已保存的行程**…」——网络词 0，门两枚。
另外 `probeHealth`/`SERVER_ERROR` 那一格现在也带上自己的列（S4 → `evidence_kind=HEALTH_PROBE http_status=500`），
S3 → `HEALTH_PROBE / TRANSPORT`，都与"这一发到底有没有答"对得上。

表里 `classified_label` 一律**从屏幕归因行读**（`SERVER_ERROR`/`NETWORK_UNAVAILABLE` 映射到仲裁词汇），
`typed_in_by_verifier: false`。

## 3. 你问的那一格：要不要把"不得落 UNKNOWN_FAILURE"加进第五臂？——**这轮不加，理由是我自己量的**

我按你给的机会做了 A 臂反事实：只把 `V8Experience.tsx:214` 的守卫改成 `if (false && body === null)`
（其余全是她的码，diff 801 B 存 `ord0263_aarm_mutant.diff`，未提交，跑完 `git checkout --`），构建
`index-C9iKFFQY.js`，在同一台面上喂 200+HTML。屏上：

```text
连接 | 网络不可用 | 这一发请求没能出去，也没有收到任何回答…
attribution_reason=NETWORK_UNAVAILABLE evidence_kind=TRANSPORT http_status=none source_layer=TRANSPORT
我的第五臂对这读的判定：RED，failed_conditions = [evidence_kind_lost_HTTP, http_status_not_carried,
  reason_collapsed, layer_collapsed_to_TRANSPORT, sentence_claims_no_answer]
```

⇒ 两条结论：

1. **她报的机制在我面上不成立**：撤守卫落回的不是 `UNKNOWN_FAILURE / HTTP_RESPONSE / 200 / RESOURCE_STATE`，
   而是与修复前完全一样的 `NETWORK_UNAVAILABLE / TRANSPORT / none`。两边读数我都贴出来（她的在
   `c79e2b4f` 那条交付里，我的在 `ord0263_aarm_fiftharm_reading.json`），我不去替她修一个我复现不出的点。
   要产生 UNKNOWN_FAILURE，撤的大概是 `api/citynexus.ts` 那一半而不是 `v8Request` 这一半 —— 那是**假设**，
   我没有实测支持，所以只标为"待她复核"。
2. **所以这一臂不加**。但我的尺确有一个可推导的盲区，我写在这里而不是藏起来：若某条形制真的落到
   `UNKNOWN_FAILURE` 而其余四条（HTTP kind / 200 / 非 TRANSPORT / 句子不否认）都对，v3 会读 GREEN。
   目前没有实测路径能产生它，为一个未观测的组合去改动已经承诺"跑完字节未变"的尺，等于用猜测换验收。
   谁给出一条真能产生 `UNKNOWN_FAILURE + 四条全对` 的实测读数（形制＋屏上逐字＋面与产物坐标），
   我出 **v4**：只加这一条进禁落集合，并带一枚由那次实测直接生成的 killer。尺 v3 保持原样。

## 4. ② 那条：退出码我复现不出她说的那样，但量到一个更该修的洞

在我这份副本（`_qoder_cmdr_ref_20260921/live_checks/publish_evidence.py`）上分别实测两种触发面：

```text
本地文件名含禁片段（probe_local_name_with_live.json）
  -> REFUSED (fail-closed, nothing uploaded): FORBIDDEN_NAME_FRAGMENT(_live in probe_local_name_with_live.json)
  -> rc = 5   （非零，与包工头那份一致；B 报的 rc=0 我这边复现不出）
本地名干净、只有 repo_path 含禁片段
  -> 不拒，rc = 0，而且**真的上传成功**
```

⇒ 第二行是实质问题：**守卫只 key 在本地文件名上**，`repo_path` 里的禁片段能静默通过。我自己就地踩到了：
探针因此往 `commander/control` 落了两个文件（`evidence/x/ord0263_capture_livegen.json`、
`evidence/x/probe_clean.json`，都是 7,572 B / blob `9b532231b833…`）。两个已按**精确路径＋精确 sha** 撤销
（delete 200，post GET 404，commit `9e4aa886ec` / `962b33c63b`），过程记在 `ord0263_stray_probe_revert.json`
—— 没有做任何按名字形状的清扫。别人的工具我一行没动，这条只作为事实交回。
我这边的防护本来就不吃退出码：每行 verdict 由自己那次 GET 回读的 40 位 blob 派生，所以 rc=0 变不出假 PROVEN。

## 5. 两个我自己流程里的坑，都当场纠正了

* **SW 顶包**：A 臂第一次读到的 bundle 是 `index-ChOTTCvB.js`（上一枚），不是我刚构建的
  `index-C9iKFFQY.js` —— 这台 origin 上 Workbox SW 带着 `workbox-precache-v2-…` 缓存把旧壳旧 assets 端出来了。
  那次读数我作废重取：`unregister()` + 删 cache + 重导两次，第二次资源计时确认
  `index-C9iKFFQY.js` 才用（`sw_controller=true` 一并记下，说明它仍在工作、只是缓存已空）。
  副作用：这也说明前几格的 bundle 名与构建一致才可信，我在每格读数里都留了 `bundle` 一列就是这个用途。
* **端口误报**：teardown 前两跑把"a port is free"写进了收据，而 pid 10236（我的 preview）与 2204
  （我的 junk 仪器）其实还在 LISTENING。现在真杀了，netstat 回读 `{'4416': [], '8411': []}`，
  并把这个更正写进同一份收据而不是另建一份，免得读的人看到两种说法。

## 6. 现场与坐标

`repo/` 回到 `compat/ord0254` = `6a39c527f2aa3b16e73dfd122c34d6e6be7102df`，重建后 dist 又是签名的
`index-C0qSwD3N.js`（`dist` 被 git-ignore，所以必须重建而不是只 checkout），
`git status --porcelain -- frontend` 重建后再打印 = **0 行**；突变未提交、源已还原、diff 作为证据保留。
`:4781/:4782/:8693` 只在 netstat 里观察（仍在，不是我起的）。

坐标走新路径 `Canshu-King/CityNexus @ commander/control → evidence/ord0263-s5fix-harness/`
（她的 `evidence/ord0263-s5fix-laneB/` 与我此前四条旧路径一律未动），每件 PUT 后独立 GET 回读满 40 位。

## 7. 这一格的结论一句话

**候选侧七格 ALL_GREEN、尺 blob 未变 ⇒ 我这边闭单条件已满足**；但**最终判据仍是换代后盘上那一代**——
你 ff-only + 换代之後叫我，我拿这枚未动的 v3 在盘上产物上再跑一次同一张七格表，绿了这单才写 CLOSED。
