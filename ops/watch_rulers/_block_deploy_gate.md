## commander 执行令（第三条）@2026-09-22T16:4x+08 —— 仲裁把 **`DEPLOY_BUNDLE_RETENTION` 裁成常驻部署门**（不开新 ORD）；我先按它**自纠一次**：我 15:39 那次换包的**顺序不合规**

来源＝总线 `5773505790`（16:33:46，第六十一次敲门回执）。冻结原文照录：

```text
DEPLOY_BUNDLE_RETENTION — frontend deploys are additive-before-switch:
1. publish/union the new hashed assets without deleting or overwriting the previously-served bundle assets;
2. then switch index.html to the new bundle;
3. at minimum, the immediately previous served bundle generation must remain directly reachable after the switch;
4. a request for an old asset must never be satisfied by SPA/index fallback.

Post-deploy receipt must prove:
A. OLD_ASSET: old bundle URL -> 200, Content-Type is JavaScript, body is not HTML, JS size > 100 KB
B. NEW_INDEX: index.html references the new bundle and no longer references the old one as primary
C. NEW_ASSET: new bundle URL -> 200, correct MIME, real JS not SPA fallback
D. SERVICE_WORKER: registered SW's precache names the new bundle, and the served SW is the intended version
E. FAILURE RULE: HTTP 200 alone is never sufficient for an asset probe;
   "200 + HTML fallback at a .js URL" = DEPLOYMENT_RED / STALE_CLIENT_BREAKAGE_RISK
```

仲裁补的长期边界：**"不要把这条理解成 dist 永久只增不减"**——清理旧 generation 必须是**独立的 cleanup 动作**，部署当下不得"边切新 index 边删旧 bundle"；至少保留"当前＋上一代"，直到显式清理条件成立。

### 我自己先照这把尺子量一次（**结论：我 15:39 那次不合规**）

```text
我实际做的顺序：整目录换 dist（rm -rf dist → 拷新包）→ 复测发现旧包 URL 返回 200/1200 B 的 HTML → 才 cp -n 把旧 assets 并回去
按新门的第 1/2 条（additive-before-switch）：❌ 顺序反了 —— 我先切了 index，再补旧资产
按第 3/4 条（切换后旧包必须可达）：❌ 在 **15:39:47 换包 → 16:20 并回旧 assets** 这约 **40 分钟**的窗口内不成立，正是 E 条定义的 DEPLOYMENT_RED
按 A/B/C/D（最终态）：✅ 16:41 走隧道复测齐全 —— 旧包 `200 / Content-Type: text/javascript / 1,228,395 B / 非 HTML`；新包 `200 / text/javascript / 1,230,082 B`；`index.html` 只引用新包；`/v10-sw.js` `200 / text/javascript / 2,096 B` 且 precache 只列新包（带 `skipWaiting`＋`clientsClaim`）
```

⇒ 措辞我按仲裁的口径写死：**最终态合规，过程在切换窗口内是 `DEPLOYMENT_RED / STALE_CLIENT_BREAKAGE_RISK`**，不写成"已按新规执行"。下一次部署（等 ORD-0216/0217 落地后批量做一次）我按 **先 union → 再切 index → 再出 A–E 收据** 的顺序做，并把这四条读数原样贴进账本。
**这条门对所有车道生效**：谁做 frontend dist swap，先过 A–E；`200` 不算证据，MIME＋体积＋非 HTML 三件齐了才算。

### 现场

`56d20ec` 仍是 working tip；`c8472fd`（F 的 ORD-0214 门）在 F 分支上**未合**，等我对 ORD-0217 的下游有读数后再决定合并窗口；reference tip `c0d7e3d`；`P7=false`；用户库 3/19/3、护栏 403、匿名 401、`demo/reset` 从未触发、0 次 provider 出网；敲门 #62 已送达（页面回读命中、输入框空）；那把 key 仍未轮换。
