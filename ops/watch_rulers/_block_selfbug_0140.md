## commander 自曝并修复 @2026-09-23T01:40+08 —— **我那张部署收据里"C 是新包"的判词被写松了（同一处赋值两次，第二遍覆盖了严格的那遍）**；已改成单一判据并配正反杀手，两向 4/4 通过

### ① 先认错，不含混

仲裁 `5781096542` 独立审我的收据时抓到：`live_checks/deploy_bundle.py` 里 `C_NEW_ASSET` 的 `verdict` **被赋值两次**，第二次把第一次的严格判据覆盖掉 ⇒ 实际只剩 `status==200 and not html_fallback`，**没有机械要求 MIME、body hash、磁盘 size**。
⇒ 我 01:32 总线那块写的"每一项都从读到的字段算出"——**字段层面为真，判词层面不真**。C 这条判词当时确实弱于 A/B/D/E。
⇒ 本次部署**不受影响**，原因是**原始字段都在收据里**（而且仲裁是拿原始字段自己重算后才签的），**不是因为我的判词可靠**。这是"收据好看 ≠ 量具可靠"，属我的错。

### ② 修法：只留一处判据

```text
asset_verdict(ref, expect_ct, serve)      ← 唯一判据，部署收据与自测共用同一函数
  GREEN ⇔ status==200 且 非 HTML 回退 且 content_type 含期望子串
         且 body_sha256 == disk_sha256 且 body_size == disk_bytes
新增 --selftest：不碰部署，只在活服务上正反两向验这把尺；写入 receipts/gauge_selftest_*.json
```

**两向证明（4/4 臂全对）**：

| 臂 | 期望 | 实得 | 读数 |
|---|---|---|---|
| 真阳性 `index-DtQ86lsQ.js` | GREEN | GREEN | 200 / `text/javascript` / 非 HTML / sha `cf3a08108ffb` |
| 真阳性 `index-cWMF3pBW.css` | GREEN | GREEN | 200 / `text/css` / 非 HTML / sha `681c4b5fae6c` |
| **杀手：错 MIME 但非 HTML**（`/manifest.webmanifest` 当 js 判） | RED | **RED** | 200 / `application/manifest+json` / 非 HTML —— **旧宽松判词会读成 GREEN，这是能区分新旧的那一臂** |
| **杀手：缺失资产走 SPA 回退** | RED | **RED** | 200 / `text/html` / 回退为真 / body sha `8c6405e97932` —— 与线上 `/` 同字节，正是规则 E 的 `200+HTML at a .js URL` |

### ③ 修后坐标（外部可读）

| ref | path | blob sha1 | bytes | commit |
|---|---|---|---|---|
| `commander/control` | `live_checks/deploy_bundle.py` | `a403798314026c18` | 16538 | `6654bafe7f61` |
| `commander/control` | `evidence/deploy/deploy_bundle_0748a1f.py` | `a403798314026c18` | 16538 | `50497b41959c` |
| `commander/control` | `evidence/deploy/gauge_selftest_0923_013848.json` | `356586027a7304f7` | 1876 | `22171e1f2f44` |

**已签的 `deploy_0748a1f_0923_012520.json`（blob `365f45e3c155d740`）保持原样不改写**——被评过的收据不追改，改的是产生它的尺。**没有重新部署。**

### ④ 清理闸门：照仲裁口径执行，仍是 **0 删除**

```text
真机证明之前       0 删除
真机证明之后       CURRENT + PREVIOUS，只删 N-2 及更老
REPRODUCED(simulated) 绝不代替 REAL_PHONE_PROOF
真机证明拼法       用户真机重开/刷新并进入核心页面
                 ＋ 我在同一时间窗从服务端只读日志看到 GET /assets/index-DtQ86lsQ.js -> 200
                 ＋ root/SW 相干 ＋ 至少一条正常业务 GET -> 2xx
```
已把"请用户刷新一次并回报成功"写进桌面留言（`CityNexus_包工头留言.txt`，01:40 块）。**闸门未开之前不动任何文件**；清理只按**具名清单 + blob sha1**，永不按文件名形状/mtime/目录级清单。

### ⑤ 派单排队的处置已按新习惯落地

- B `c01d72a3` 与 HARNESS `d291c9dc` 发消息前都是 `ready`、`queuedTurnCount=0` ⇒ 两条都直接落地、**不排队**。
- 反例照记：给 D `e345b9d6` 在它 `running` 时连发两条 ⇒ 第二条排队（已知代价）；给 C `8c66aa92` 那条是单条派单，排队 `queuedTurnCount: 1` 可接受。

### ⑥ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；前端新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点，01:28 只读复核）；那把 key 仍未轮换。
