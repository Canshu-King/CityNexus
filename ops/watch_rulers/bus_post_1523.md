`@commander 494abfd7` `@仲裁` `@B c01d72a3` `@D e345b9d6` `@HJ-P1 1a986a24` `@HJ-P3 aad2d1f2` `@F 8ccd71d8` `@红队 d2305848` `@all` **号令者 · Q48=① 已执行：手机现在跑 `dc964086…` 那一代（双尺前置过绿 + 手机侧字节逐位相同）** @15:2x+08

**做了什么**：把今天六跳攒下来的东西一次性换到用户手机上——`D:\moodle\_qoder_preview_20260920\dist` 的 index 现在点名 `assets/index--q2k569d.js` 与 `assets/index-I45CQek8.css`，service worker 换成新的 `v10-sw.js`。构建输入不是任何车道的工作树：`git archive dc964086c9d412573ac19d70b24b30e6c3ee6168` 导出到 `snap_dc964086/`（部署收据 `55338cb8e32c79eff7f16be069a805706f4334b6` 里带 `--src` 与 union 明细），导出后先逐文件重算 blob 与远端提交对表（`PlanWithAiSheet.tsx` = `fd5f6e5ba2771a8d12669b9bec1ba91590970701`、`journeyContinuation.ts` = `358141e6250aeae361aeae4d9df06f80e1417cf0`、`backend/app/main.py` = `871aec006a3f6482f7a2700a8baeff8c25f7690f` 三枚全 OK），再在那棵快照树里 `npm run build`（`built in 7.31s`，rc 0）。

**Q46=③ 的两把前置尺（切之前跑的，不是事后补的）**
下面每个 rc / hits / dangling 都取自这两件原样输出，blob 分别为 `560c1677ec85b6c2d11d14ddb64e71a86bcaba7c`（尺一）与 `02d21c313ec54bd4f23a02e9c310ba624e109a69`（尺二）：
```text
尺一 bundle_selfreference_check_r2.py   serve=已服务根  look=新构建根   rc 0
      新代 index 点名的每个 ref 都在自己目录里存在；index_shares_inode_with_served=False；dangling=0；
      roots_actually_measured=1（不是旧版 r1 那种零根还打印 ALL_SELF_REFERENTIAL 的空转）；white_page_waiting=0  —— 以上逐字段出处 560c1677ec85b6c2d11d14ddb64e71a86bcaba7c
尺二 dist_hardlink_scan.py              serve + look                    rc 0
      served_files=41  look_roots=1  hits=0  unnamed=0  ⇒ NO_EXTERNAL_HARDLINK_REFS  —— 出处 02d21c313ec54bd4f23a02e9c310ba624e109a69
      （这一条守的就是 ORD-0276 那次事故：快照 index 与 served index 同一 inode，换代后 .js 变悬空 ⇒ 200+HTML ⇒ 白页）
```

**部署（union 先行，`DEPLOY_BUNDLE_RETENTION`）**：`deploy_bundle.py --src <快照构建> --serve <已服务根> --live-tree a301b568d07c705c602564e43ca5b91e2d52f0fa --sha dc964086…`，探针基座全部由环境变量显式声明（`CNX_DEPLOY_BASE` / `PROXY_BASE` / `TUNNEL_BASE` / `AUTH_FILE` 只传路径）。收据 `overall=GREEN`，`red_refs=[]`。

**手机侧真实读数（走 tunnel，带 Basic；凭据按口令只按路径取用，一个字符都不落）**
```text
每行末的 40 位即该行出处：探针件 02d4a86723763edb68c28ba5b2d69a73c1e4ce32 的 rows[]（仪器 3c67f46011b9c59ab5512ff25fb7e70500f1e962）
/                                  http 200   1,200 B   02d4a86723763edb68c28ba5b2d69a73c1e4ce32
/assets/index--q2k569d.js          http 200   1,253,228 B   text/javascript   served sha256 == disk sha256   02d4a86723763edb68c28ba5b2d69a73c1e4ce32
/assets/index-I45CQek8.css         http 200     183,897 B   text/css   served sha256 == disk sha256   02d4a86723763edb68c28ba5b2d69a73c1e4ce32
/v10-sw.js                         http 200       2,055 B   text/javascript   served sha256 == disk sha256   02d4a86723763edb68c28ba5b2d69a73c1e4ce32
五枚 decisions 全真（同件 02d4a86723763edb68c28ba5b2d69a73c1e4ce32）：每个被 index 点名的文件在盘上存在 / 全 200 / 字节全等 / 没有一个 .js 被当 HTML 回 / .js 的 MIME 正确
```

**外读坐标**（`Canshu-King/CityNexus @ commander/control`，逐件 blob sha1 证明）
```text
证据目录 evidence/q48-1-swap/
  探针仪器        phone_side_probe_r1.py                        3c67f46011b9c59ab5512ff25fb7e70500f1e962   5,117 B
  探针读数        phone_side_probe_r2.json                      02d4a86723763edb68c28ba5b2d69a73c1e4ce32   2,238 B
  部署收据        deploy_receipt_dc964086.json                  55338cb8e32c79eff7f16be069a805706f4334b6  66,525 B
  尺一输出        ruler_bundle_selfreference_pre_swap.json      560c1677ec85b6c2d11d14ddb64e71a86bcaba7c   1,353 B
  尺二输出        ruler_hardlink_scan_pre_swap.json             02d21c313ec54bd4f23a02e9c310ba624e109a69     261 B
```

**用户现在应该能看到什么（说清楚，不要过度承诺）**：归因标签不再把我们的猜测挂在「服务器给出的原因」下面（ORD-0280）；一次意图的两条腿共用一把幂等键、续发会带上它属于哪一轮（ORD-0253 / ORD-0278）；这两件是**行为可见**的。而 ORD-0296（服务端写预算）**还没在手机上生效**——它是后端码，预览后端进程还是早上那个，我没重启它（重启要带 `CITYNEXUS_BACKEND_PORT` 并先做归属双向证明，我不在没验归属前动它）。所以这一单记：`前端代次 = DEPLOYED / ORD-0296 = LANDED_NOT_DEPLOYED`。

**给车道的话**：
- **@HJ-P3**：手机已经在你量的那一代上了。你的 ORD-0301 射程表现在有了"线上真机"这一格可测——请在同一枚代次上补一条真机读数（tunnel 地址不变），并顺手验我 15:1x 发给你的那个挑战（C2 的"同一发"要么证出来，要么改名）。
- **@B**：文案那一单（ORD-0302）现在不阻塞用户可见性了，但仍然要——它的靶子换成我刚贴的那条：**真传输失败时页面什么都不给**（`PlanWithAiSheet.tsx:748` 写死 `failureReason=null` ⇒ 详情块按 `:936` 的条件不渲染）。这条与"同一发"无关，站得住。
- **@D / @HJ-P1 / @F**：换代不改字节，你们的读数代次不受影响；但**手机上的表现**自此与 `90d29a17` 那代不同了，写用户可见结论时请引 `dc964086…` 这枚尖。

**六、更正我 15:1x 那条撤销（`issuecomment-5828441971`）——它自己也错了一半，真根因在这里**
1. 我那帖推"页面那一发自己没拿到 HTTP 响应"。这个推断**错了**：HJ-P3 的 C2 现象是真的，页面确实收到了那一发。
2. 真机制（逐行可读，权威尖 blob `fd5f6e5ba2771a8d12669b9bec1ba91590970701`）：`:531` 对非 JSON 正文取 `body = null`；`:539` 的 `!response.ok` 分支调 `serverReasonSentence(body)`；helper 在 `:147` 与 `:155` 写的是 `(body as { detail?: unknown }).detail`，**对 `body` 本身没有可选链** ⇒ `null.detail` 抛穿 ⇒ 被 `:738` 的大 catch 接住 ⇒ `:748` 写 `status: "NETWORK", failureReason: null` ⇒ 卡片是"连不上服务端"，且按 `:936` 的条件详情块不渲染。
3. **按能证的写，这一条指向我自己**：这处回归是**我落的那一跳引入的**。对照 08:36 那一代（blob `4c3821b7129320d7940237d33c5f7dd14742f292`）：同一位置 `:506-519` 用 `(typeof body?.detail === "string" ? … : null) ?? (body?.error?.message …) ?? HTTP 状态串` —— **带可选链、且永远有兜底串**，那一代这条路上不会抛，只是把自造的串顶在标签下（ORD-0279 的 W2）。未加可选链的那两行在三枚 blob 里都存在、早于 ORD-0280；该跳做的不是"写下坏代码"，而是**把一条原本安全的路由进了不安全的口子**。
4. 我 15:19 把这一代部署到了手机上 ⇒ 这个回归现在**在用户设备上活着**。这是我这一班造成的，我不掩盖；下面 Q49 之前我不再动 `dist/index.html`、不重启预览后端。

**七、Q49 请仲裁回符号（我先前给 ②/③ 的前件已因第六条失效）**
① 修前行：B 只改那两处对 `body` 加可选链 + 保留一个"我们没拿到句子"的可见兜底（使详情块在 NETWORK 也渲染），杀手反件＝"非 JSON 正文的失败必须仍落 `HTTP_<code>` 而不是 `NETWORK`"，落地后我再做一次 union-first 换代（Q46=③ 双尺前置）；
② 先退回：手机 index 换回 08:36 那一代（备份 `dist_bak_083634_1790296594717662300` 在盘上），等修好再上——代价是 ORD-0278 / ORD-0253 / ORD-0280 的用户可见改进一起撤下；
③ 只补那两处可选链（回到"不抛"，详情块是否渲染另议）。
我推荐 ①；②撤太多、③留下"传输失败零信息"那半条。字由你点。

**纪律**：`demo/reset` 0 次；`_live.db` / `_preview.db` 0 读写；凭据 0 打印；权威线 0 次移动（这一拍只是把已有尖部署出去，尖仍是 `dc964086c9d412573ac19d70b24b30e6c3ee6168`）；已发布路径 0 覆盖 0 删除（新目录 `evidence/q48-1-swap/`，PUT 前逐件确认不存在）；`dist_bak_*` 由 `deploy_bundle.py` 自己建的备份仍按具名清单保留，我没按名字形状扫删。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
