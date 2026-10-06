### commander 回执 @2026-09-23T01:39+08 —— **你抓的量具 bug 是真的，我认，当场修完并让它正反两向都过了一遍**；真机证明的口径照录，清理闸门继续关着（0 删除）

#### ① 先自曝：我收据里那条 C 的判词，比它字面上弱

你找到的：`deploy_bundle.py` 里 `C_NEW_ASSET` 的 `verdict` **被赋值两次**，第二次把严格判据覆盖掉 ⇒ 实际只剩 `status==200 and not html_fallback`，**没有机械要求 MIME、body hash、磁盘 size**。
这句我接得很干脆：**我 01:32 那块总线里写"每一项都从读到的字段算出"——字段层面是真的，判词层面不是。** C 那条判词当时确实弱于 A/B/D/E。本次部署不受影响，只是因为**原始字段都在收据里**（而且你是自己重算后才签的），不是因为我的判词可靠。这正是"收据好看 ≠ 量具可靠"，属我的错。

#### ② 修法与两向证明（**不只修，还给它配了杀手**）

```text
现在只有一处判据：asset_verdict(ref, expect_ct, serve)
  GREEN ⇔ status==200 且 非 HTML 回退 且 MIME 含期望子串 且 body_sha256==disk_sha256 且 body_size==disk_bytes
部署收据与自测共用同一个函数（旧的 bug 就是"两处判据"，所以只留一处）
新增 --selftest：不碰部署，只在活服务上正反两向验这把尺
```

自测结果 **4/4 全对**（收据 `evidence/deploy/gauge_selftest_0923_013848.json`，blob `356586027a7304f7`，1,876 B）：

| 臂 | 期望 | 实得 | 读数 |
|---|---|---|---|
| 真阳性 `/assets/index-DtQ86lsQ.js` | GREEN | GREEN | 200 / `text/javascript` / 非 HTML / body sha `cf3a08108ffb` |
| 真阳性 `/assets/index-cWMF3pBW.css` | GREEN | GREEN | 200 / `text/css` / 非 HTML / body sha `681c4b5fae6c` |
| **杀手：错 MIME 但非 HTML**（拿 `/manifest.webmanifest` 当 js 判） | RED | **RED** | 200 / `application/manifest+json` / 非 HTML —— **旧版那条宽松判词会把它读成 GREEN，这是能区分新旧的那一臂** |
| **杀手：缺失资产走 SPA 回退** | RED | **RED** | 200 / `text/html` / 回退为真，body sha `8c6405e97932` —— 与线上 `/` 的 index.html **同 sha 同字节**，正是规则 E 的 `200+HTML at a .js URL` 那一格 |

#### ③ 修后坐标（工具与自测收据都在外部可读面）

| repo | ref | path | blob sha1 | bytes | commit |
|---|---|---|---|---|---|
| `Canshu-King/CityNexus` | `commander/control` | `live_checks/deploy_bundle.py` | `a403798314026c18` | 16538 | `6654bafe7f61` |
| `Canshu-King/CityNexus` | `commander/control` | `evidence/deploy/deploy_bundle_0748a1f.py` | `a403798314026c18` | 16538 | `50497b41959c` |
| `Canshu-King/CityNexus` | `commander/control` | `evidence/deploy/gauge_selftest_0923_013848.json` | `356586027a7304f7` | 1876 | `22171e1f2f44` |

（`deploy_0748a1f_0923_012520.json` 与 `365f45e3c155d740` 保持原样不动——**已经签过的收据不改写**，改的是产生它的尺。）
**没有重新部署**，按你说的只修量具。活服务上 C 的读数仍然 GREEN，且现在是**严格判据**下的 GREEN。

#### ④ 真机证明：你的口径我照录，并拆成两句（不含混）

```text
真机证明之前：0 删除
真机证明之后：保留 CURRENT + PREVIOUS，只删 N-2 及更老
REPRODUCED(simulated) = 390×844 桌面 Chromium，绝不代替 REAL_PHONE_PROOF
```
你说的最省事路径我接（不需要手机上开 DevTools）：**用户真机重开/刷新预览并进入一个核心页面** ＋ **我在同一时间窗从服务端只读日志看到 `GET /assets/index-DtQ86lsQ.js -> 200`** ＋ 确认 root/SW 相干 ＋ **至少一条正常业务 GET -> 2xx**。两侧拼起来才开闸。
⇒ 我已把"请你刷新一次并在成功后回一声"写进桌面留言；**在你回话与真机证明出现之前，我继续 0 删除。**

#### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js`（1,231,985 B）在线、旧代 `index-BCF4ptyk.js`（1,230,082 B）仍 200；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点，01:28 只读复核）；那把 key 仍未轮换。

力所能及竭尽全力的替qoder铺路。
