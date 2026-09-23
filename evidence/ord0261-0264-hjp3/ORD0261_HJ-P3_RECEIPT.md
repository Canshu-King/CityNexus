### 🔬 aad2d1f2 (SESSION=aad2d1f2) P3 · **ORD-0261/0264 候选字节手机人路径复验（只测不修）** @2026-09-23T18:1x–18:3x+08

**结论一句话**：仲裁 §1 那六条 **SCROLL_REACHABLE_AND_TAPPABLE** 在候选字节上 **6/6 通过**，76px/移动层 212px 的底部让位**没有造出新的滚动/导航陷阱**（最大滚动处 16 个可交互控件 0 遮挡、滚动可逆、尾部空白 32px 与发布代一样）。⇒ 建议这一格记 **CANDIDATE_HUMAN_PATH_OK**。**但有一条要给 F/D 的门前置**：候选修的那半件里「高级设置中心被 sticky `下一步` 抢走命中」在我这个内容状态**不复现**（发布代 5 个 scrollTop 全 false），我复现到的是另外半件「滚动到底也点不到/只剩 33px 余量」。

**候选身份链（三重，不是我认文件名）**
1. 四件从 `commander/control:evidence/ord0261-0264-candidate/` 独立回读，git blob sha1 与你给的号**逐位相等**：patch `0de748338e103bb70da3c0a5f4f3fcb664c9a499`(17,285 B)、改件清单 `3cdfe4023befa924…`、lineage `443262303f1a7780…`、gate-receipts `e41c68b740d50cbe…`。
2. 那份 patch 与本机 `_qoder_integration_20260919`、`_qoder_cmdr_gate_20260921` 两棵树的 `git diff dea8410 6daceb1` **逐字节相等**（17,285 B）。
3. `git archive dea8410` + `git apply` 后的 5 个改件，与 `git archive 6daceb1` 逐件相等（**5/5，换行归一后**；不归一不等的原因是我的 `git apply` 按全局 autocrlf 写出了 CRLF，已弃用那棵树，改用 `6daceb1` 导出构建）。
- 构建：`snap_6daceb1/frontend` `npm run build` **exit=0** → **`index-D76m_cky.js` 1,238,834 B sha256 `270377c83471a5a1…`** + **`index-I45CQek8.css` 183,897 B sha256 `1b3632785212847b…`**；serve 字节 == 磁盘字节；`:8478` 的 index 只引这两件，`:8474` 发布代仍只引 `index-DJEINrOl.js`/`index-COUUKhbU.css` ⇒ **候选没混进发布代**。
- 后端 = 我的 `:8424`（`_qoder_cmdr_gate_20260921` @ `53fe8e8…`，porcelain 0）+ 我的副本库；归属双向证明：只在我库里的那枚 journey → **200**，外来 id → **404**。
- **仪器坑先报**：`vite preview` 的 `/api` 代理端口取自 `CITYNEXUS_BACKEND_PORT`，默认 **8000**；我第一次没带这个变量起，`/api/v1/health` 直接 500 —— 那台是别人的。**没读数就从错后端上产生**，重起 `:8478` 后才有上面那两条归属证明。

**六条契约的实测（390×844、hasTouch、dpr 3、zh-CN，全新 context 无 journey ⇒ 进向导 step 1）**
| 契约条 | 读数 |
|---|---|
| 留在 step 1，不用切步 | `.trial-steps` 文案前后都是「1目的地与时间2人数…」；开合钮本身就在 step 1 区块内 ✓ |
| 普通滚动可 bring into usable viewport | **1 次真触摸滑动**（`Input.dispatchTouchEvent` start 620 → moves 560/500/440/380/330/300 → end）scrollTop **0 → 583**，开合钮 y **957 → 374** ✓ |
| 可见后中心不被 sticky CTA/其它元素遮挡 | 中心 (195,534)；sticky 条带 628–708；`centerInsideBar=false`；再扫 6 个 scrollTop（400/500/560/620/700/721）中心 717…396，**全都在 viewport 内且从未进条带** ✓ |
| `elementFromPoint(center)` 落在开合钮 | 命中 `BUTTON.trial-back-link`「高级设置」，`closest([data-testid])` = 自身 ✓；栈 = 开合钮 → `DIV.v8-card trial-card` → `SECTION.v8-page cn-onboarding` |
| 真点按能开 | `p.touchscreen.tap(195,534)` → `.trial-advanced` `open` **false→true**；`.trial-supported` 仍 false（没被顺手展开）✓ |
| 滚动/点开过程中草稿保留 | 目的地输入框「北京」：填充后 → 真滑动后 → 真点开后 **三读全在**；页面没重挂载 ✓ |

**"让位有没有造出新陷阱"（这是令牌的正面问题）**
- `.trial-steps` 实算 `padding-bottom` = **212px** = 76 + `--cn-sim-float-clearance`（解析值 `calc(136px + 0px)`）+ safe-area 0。**补丁注释写"≈76px"，移动层真实是 212px**，引用别只写 76。
- 让位不是空付：`sim-float` 真的在（`position:fixed`、48×60 @ x330,y556）+ `sim-ball` 48×48 + dot。
- 最大滚动处：候选 `scrollTop 721 / scrollHeight 1565`；**16 个** button/input/summary 逐个中心 hit-test，**`occluded` = false 全部**（`下一步` y=652、`使用封存的演示行程` y=768 两个虽在条带里/之下，`elementFromPoint` 返回的就是它们自己）。
- 尾部空白：最低控件下缘 812，视口 844 ⇒ **32px 尾巴，与发布代同值**（发布代也是 812/32）⇒ 让位被内容吃掉，**没有多出一段滚不动也点不到的死带**。
- 可逆：一次向下滑（320→610）scrollTop **721 → 0**，没卡住。
- 一处残留（**不是新陷阱，报着**）：点开时那个位置，「离开地点」输入框下缘压进 sticky 顶 **20px**（中心仍干净、仍可点）；>680px 桌面档让位只有 76px。

**同形对照 = 发布代 `index-DJEINrOl.js`（同一个后端、同一个库、同一个内容状态）**
- 静止：开合钮 y=**1142**（补丁注释那枚是 1208，我这状态测到 1142），中心在视口外；`.trial-steps` `padding-bottom:0px`；`scrollHeight 1217`、**max 373**。
- 真滑动 1 次即到底（top 374），开合钮 y=**768**、中心 **790** ⇒ 距 844 底边只剩 54px；`scrollTop < 340` 的三个位置中心 963/904/863 **在视口外，`elementFromPoint` 直接 null = 点都点不到**；只有最后 **33px** 滚动余量里才可点。
- **没复现的一枚**：5 个 scrollTop 上 `hitIsStickyCTA` **全 false** ⇒ 我这状态没有"中心被 `下一步` 抢走命中"。若 F/D 的门以那枚为反例，请先给出可复现的内容状态（我：目的地已填「北京」、`.trial-supported` 未展开、`.trial-advanced` 未展开）；否则那扇门在自然树上不会红，红会被错归因。
- 截图（文件名带 run id `ORD0261-P3-1815`）：候选 `…_candidate_advanced_open.png` 137,089 B sha256 `4b4b383e78b278a5…`；对照 `…_published_control_wizard_bottom.png` 124,323 B sha256 `f4604937a94ac824…`。

**没做的**：不改任何产品码/样式；不碰发布代 dist 与隧道；不 `demo/reset`；不碰 `_live.db`/`_preview.db`/`:4781`/`:4782`/`:8693`；向导**没点过「下一步」**（不建行程、不落产品写）；按新令**一枚窗口都没关**，我这几只面（`:8478`×1、`:8474`×2）留在原地并具名。

**外读坐标**：`Canshu-King/CityNexus @ commander/control` → `evidence/ord0261-0264-hjp3/`（`ORD0261_HJ-P3_RECEIPT.md` 本块、`candidate_human_path_capture.json` 逐条原始读数、`artifact_identity.json` 身份与字节、两张截图），逐件独立目录列表回读 40 位 blob。候选原件我**一件没动**（`evidence/ord0261-0264-candidate/` 只读）。
