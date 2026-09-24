# ORD-0263 闭单格 · 盘上落地代 `c79e2b4f`：七格 ALL_GREEN，尺跑前跑后同一枚字节

**一句话：你 ff-only 落地并换代的那一枚（`assets/index-ChOTTCvB.js`），我用自己那枚 v3 在盘上产物上重跑整张七格表，
`derived_result: ALL_GREEN`，闭单三条件逐条成立；尺 21,703 B / `e9a4188f63e27bbbf8bfed35adfd554b9e8641d9`
跑前跑后回验相同 ⇒ 我没有动判据。**

## 1. 闭单三条件逐条对表（条件来自 5800456557 之后你落的合同）

| 条件 | 我这一格的证据 | 位置 |
| --- | --- | --- |
| ① 前四格不回归 | S1+V1+V1_vacuity+V2+V3+V4 全 GREEN，且与重启前那一遍**逐字一致**（`cross_pass_agreement` 四格皆 true） | capture `cross_pass_agreement`；verdict 前六臂 |
| ② V5 三形 GREEN | `green=3 red=0`，200+HTML / 200+空体 / 200+非 JSON 各自绿 | `verdict…json` 的 `V5_origin_invalid_response` |
| ③ 原始 capture 里**逐形**能读到非 catch-all 的专用 reason | 三形都渲染 `attribution_reason=ORIGIN_INVALID_RESPONSE`、`evidence_kind=HTTP_RESPONSE`、`http_status=200`、`source_layer=RUNTIME`；`any_shape_landing_UNKNOWN_FAILURE = []` | capture `S5_invalid_response.shapes[*].screen_columns` 与 `close_conditions_from_the_commanders_contract` |

逐字自限（合同要求原样出现在闭单文字里）：

```text
UNKNOWN_FAILURE prohibition = contractually satisfied by direct landed-generation observations; v3 has no
dedicated UNKNOWN_FAILURE mutation killer; verifier coverage debt transferred to instrument maintenance.
```

## 2. 七格读数（08:32–08:42，全新 origin `:4418`，重启后的第二遍）

| 格 | 源状态（我换的进程） | 屏上（渲染文字＋展开「归因详情」） | 判定 |
| --- | --- | --- | --- |
| S1 | 真 uvicorn `:8411` | 13/13 发 `/api/v1/*` 全 200；`早上好 · Demo之旅 · 今天 还没有安排`；网络词 0；快照 1 行 | GREEN |
| S2 源答 500 | `:8411` 无监听 → 代理 500（0.039s / 0.002s） | 「服务器 | 服务暂时不可用 | 服务器刚才答了你，但它自己报错了（HTTP 500）…这台设备上还留着你已保存的行程…」`SERVER_ERROR / HTTP_RESPONSE / 500 / RUNTIME` | GREEN |
| S3 静默超时 | `origin_hang_no_close fully-silent`（不答**也不关**） | 「没有回音 | 等了 12 秒，这台服务器一个字也没回答…」`NETWORK_UNAVAILABLE / HEALTH_PROBE / none / TRANSPORT`；experience **12 010 ms**、health **4 016 ms** 皆 status 0 | GREEN |
| S4 读不回话而 `/health` 答 500 | `answered-health`（health 500 json，读挂不关） | 与 S2 同句，但列成 `SERVER_ERROR / HEALTH_PROBE / 500`；experience **12 009 ms status 0** 后 health 5 ms 500 | GREEN |
| S5 200+HTML | `origin_answers_junk_200 html`：200 `text/html` **1,200 B** | 「服务器答了 200，可带回来的不是这一屏能用的数据」`ORIGIN_INVALID_RESPONSE / HTTP_RESPONSE / 200 / RUNTIME / content_type=text/html` | GREEN |
| S5 200+空体 | 200 `application/json` **0 B** | 同句，`content_type=application/json` | GREEN |
| S5 200+非 JSON | 200 `text/plain` **33 B** | 同句，`content_type=text/plain` | GREEN |

三形都同时**交出本地快照**（`cached_copy_present=true` 与 IndexedDB 实读 **1 行**相符、门「看已保存的只读副本 · 重试」在），
网络词 0，无骨架。按 Q9 的正交切法，我只判这列的 **pre-click 事实完整性**；点进去之后披露的是不是那份对象，
属 0273 的 post-click 格，我没有代它签字。

## 3. 蓝屏这件事对结论的影响，我按两段处理

02:2x–02:3x 的蓝屏把我的面和三份仪器进程一起带走了。我**没有**把重启前后的读数混成一张表：

* 重启前那一遍拿到 S1/S2/S3/S4/S5_html，原文记在 `ord0263_landedgen_reboot_note.md`（已外读）；
* 重启后另起干净 origin `:4418`，**整张表七格全部重跑**（含重启前没来得及测的另两形）；
* 四格可重叠的对照结果：headline、正文句、归因列**逐字相同**（capture 的 `cross_pass_agreement` 四格 true，
  `pass` 字段逐格带着）⇒ 这一格实际上拿到了一次天然的重复观测，而不是"重启前后各信一半"。

新 origin 也顺手排掉了上一轮那个坑：同一 origin 上 Workbox 会用 precache 把**旧一枚** bundle 端出来
（我当时读到 `index-ChOTTCvB` 而构建是另一枚）。这次每格读数都带 `bundle`，全部是 `index-ChOTTCvB.js`。

## 4. 盘上这一枚的身份（不是靠文件名）

`D:/moodle/_qoder_preview_20260920/dist` **只读**：`index.html` 仅引用 `assets/index-ChOTTCvB.js`
（1,245,203 B / sha256/16 `2d56a79632efc0c6`，与你在手机隧道侧量的数字对得上）；根 35 文件 / 19,122,061 B /
tree `303e189b4a0ae3a9…`，我副本 tree 同值 ⇒ 未重建。
代次标记：`v10-sw.js` 2,055 B / sha256/16 **`88a7d980b3ffcbd6`**，上一代是 `e63d7421eda34093` ⇒ **可辨**；
`manifest.webmanifest` 314 B；上一代 bundle `index-Cpy_jhEg.js` 仍在盘上可取（DEPLOY_BUNDLE_RETENTION 未被破坏）。
归属双向 PROVEN（marker 行程经 `:4418` 200 且直连 200；一个我库里 0 行的 uuid 经同一代理 404）。

## 5. 我没有做的两件（遵令）

* **没改尺、没出 v4。** 你说 Q11 已裁、合同现在生效、v3 少的那枚 mutation killer 记成 verifier coverage debt
  并转 instrument maintenance（0271-B 同一维护窗口），0263 的 CLOSED 不等它 ⇒ 我这轮一个字没碰 `v3`，
  也没顺手把 `UNKNOWN_FAILURE` 加进禁落集合。
* **Q8(b) 的运行时 A 臂三件指纹我这轮没用到**（本轮没有 mutant 读数）；下次做突变读数时我按那三件套署：
  页面实际执行的 script URL == 突变构建 / 从该 URL 读回字节 sha256 == 本地突变构建 / 受 SW 控制时证 shell 同代，
  hashed JS 可能 `revision:null` 故不强求 JS 自带 `__WB_REVISION__`。

## 6. 现场、坐标、分段交付

`demo/reset` 0 次；`_live.db` / `_preview.db` 未打开；`:4781/:4782`/隧道/cnx proxy 只在 netstat 里出现、
未发任何信号；凭据未打印。收尾：`:4418`/`:8411` 按端口具名停且 netstat 回读为空；我那份 dist 副本按具名清单删
（释放 19,125,803 B），**删完把源根再哈希一遍仍是 `303e189b4a0ae3a9…`、与面启动收据一致**；
克隆仍在 `compat/ord0254` = `6a39c527f2aa3b16e73dfd122c34d6e6be7102df`，`git status --porcelain -- frontend`
**0 行**；克隆侧也没有任何未提交改动（蓝屏后第一件事就是查这个，无未提交代码 ⇒ 没有需要抢救的 sha）。

坐标全在 `commander/control:evidence/ord0263-landed-c79e2b4-harness/`，按段外读（机器不稳，所以不攒到最后）：

```text
segment1  7 件  PROVEN  重启前原件：面收据 + 两份 never-close side log + junk_html log + 启动器 + 中断记录 + 索引
segment2  4 件  PROVEN  四格读数 jsonl（S1/S2/S4/S3）+ 增量发布器 + 索引
segment3 12 件  PROVEN  capture + verdict + 七格 readings + 暂存清单 + 重启后四份原件日志 + builder + 索引
segment4  本文件 + 收尾收据 + teardown 脚本 + 索引
```

命名纪律：与**已发布同名**的三份日志和面收据，本轮新字节一律带 `_postreboot` 后缀另发（`…_postreboot.json/.log`），
不覆盖任何已发布路径；`evidence/ord0263-landing-c79e2b4/`（你的落地收据）与其它四条我的旧路径都未动。

**这一格交回的话**：三条件成立、尺未动、两遍一致。0263 的 CLOSED 现在不再等我这边；
剩下的只是你落账与 Q11/0271-B 那条维护窗口。
