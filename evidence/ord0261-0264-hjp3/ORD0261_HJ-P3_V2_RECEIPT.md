### 🔬 aad2d1f2 (SESSION=aad2d1f2) P3 · **ORD-0261/0264 候选 v2：`e3b0b47` 上重跑那一遂（门坐标以包工头 18:3x 那条为准）** @2026-09-23T18:4x+08

**先认坐标**：我上一块用的 `443262303f1a7780`/`e41c68b740d50cbe` 确实是 **lineage + v1 门收据**（commander 上一条给串了，仲裁当场纠正）。本轮以 **`evidence/ord0261-0264-gate-v2/`** 为准：门收据 `gate-and-arms-receipt.json` = **`e088e7ca37d1da1c8dbd2391cf155d2ef8c97f05`**(2,538 B)、门本体 `gate__qoder-wizard-advanced-is-tappable.spec.ts` = **`feb0b3bd0929ee78878f0b75addbeb4fd73ab5f5`**(9,945 B)，两枚都按完整 40 位独立回读对上他给的前缀。

**"产品字节一致"我不认转述，自己证了三遍**
1. `git merge-base --is-ancestor 6daceb1 e3b0b47` = **true**，中间 3 笔全是 `test/chore`；
2. `6daceb1 → e3b0b47` 改动 9 个文件，**bundled 输入 0 处**（只有 `frontend/e2e/` 那一个 spec + `review/` 8 个新文件）；`frontend/src` **tree hash 两枚完全相同** = `389c1bd6b4fe25e13a179484ae2207ab32522e5b`；
3. 我另起一棵 `git archive e3b0b47` 导出树重新构建（exit=0），**四件产物 sha256 与 `6daceb1` 构建逐件相等**（`index-D76m_cky.js` 1,238,834 B `270377c8…`、`index-I45CQek8.css` 183,897 B `1b363278…`、`JourneyMap`/`maplibre` 也等）⇒ 同一套产品布局，**不是"他说一致所以一致"**。

**面**：`http://127.0.0.1:8479`（新端口，我的 `:8424` 后端 @ `53fe8e8`、porcelain 0、我的副本库；带 `CITYNEXUS_BACKEND_PORT=8424` 起，页面内自证归属：**我库里那枚 journey → 200，外来 uuid → 404**）。仪器：**CDP `Input.dispatchTouchEvent` 真触摸滑动 + `page.touchscreen.tap`**（D 的门用的是 `mouse.wheel`，我这两遂补的正是触摸那一半）。

**四问四答（两遂都是全新 context、无 journey ⇒ 落在 step 1）**
| 你要验的 | pass1（先填草稿） | pass2（初始态不动） |
|---|---|---|
| ① 真能自然滚到 | **1 次**滑动 scrollTop 0→706，开合钮 y 1080→374 ✓ | **1 次**滑动到 **max 623**，y 929→306 ✓；反向一次滑回 0，没卡 |
| ② 到点中心不被盖 | 中心 396，sticky 条带 628–708 ⇒ **不在条带内**；`elementFromPoint` = `BUTTON.trial-back-link` 本体 ✓ | 中心 328，同样 `centreInsideBar=false`、命中自身；栈 `BUTTON → DIV.v8-card → SECTION.v8-page`，上面没有别的东西 ✓ |
| ③ 真点得开 | `touchscreen.tap(195,396)` → `.trial-advanced` `open` **false→true**（`.trial-supported` 保持 false）✓ | 同样 false→true ✓ |
| ④ 滚 + 展开期间内容不丢 | 「天津卫」：填后 → 滑后 → 点开后 三读全在 ✓ | 在**展开后的 details 内**那 3 个输入框之 1 填「测试串」→ 反向滚到 top=0 仍在 → 收起再展开仍在 ✓ |

**顺手两枚给别人的读数**
- **可达性是状态相关的**：光填一个目的地（「天津卫」），开合钮就从 y=929 被顶到 **y=1080**（中心 1102 = 视口外、`elementFromPoint` 直接 null）。⇒ 只量"干净初态"的门会**低估**这段距离；pass2 需要滚到 **max=623**（全程余量）才进入可点区，pass1 反而在中途 706 就够了。
- **ORD-0266 我没有新分布**：向导这一遂根本不打开 AI sheet，busy 标志没在场，所以我不谎称"路过量到了"。种子读数仍在 ORD-0262 那一套里（Q 系列：Q2 于 08:55:33 发出，而 Q1 第一腿 08:55:59 才返回 ⇒ 先返回的那条把按钮放开了），坐标 `evidence/ord0262/qp_capture_ord0262.json` + `ORD0262_RECEIPT.md` §9。

**D 的两枚双臂我不判**：`K261_REMOVE_STICKY_RESERVE` / `K264_MOVE_OPENER_BACK_TO_PAGE_TAIL` 的 `KILLED` 是交付方 `claimed_result`，closure 归 verifier；我这两遂只是仲裁 §3-8 要的人路径见证。

**没做**：产品字节一个没改（只读 D 的工作树 + 我自己的导出树构建）；没点「下一步」（零产品写入）；不碰发布代 dist/隧道/`:4781`/`:4782`/`:8693`/两个用户库；不 `demo/reset`；**一枚页面/窗口都没关**，面具名：`:8478`×1（`6daceb1` 构建）、`:8479`×2（`e3b0b47` 构建）、`:8474`×2（发布代对照）。
