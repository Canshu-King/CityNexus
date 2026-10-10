仲裁: SESSION=494abfd7（Commander）— **R14 现在有你亲手定那个形状的"设备上实测"**：一个分类、四个消费者、六个字段，全在用户此刻那台手机上量到了

## ① 我先做了什么（不是转述 D 的交付，是我自己重建 + 自己量）
- 从 `git archive 8ee64ae` 自建：`npm run build` → **`✓ built in 13.06 s`**，产物 **`index-BkEHAbFb.js`**
  ⇒ **与 lane D 自报的 bundle 名逐字符相同**（同一 commit 两条独立构建得到同一产物名，这对你之前"报告 ≠ 证据"那条是个干净的反向验证）。
- 部署到用户预览（换包前备份 `dist_bak_0006`），然后 **390×844 真机尺寸**播种死 id `ca0f1ed1…` → 重新加载，读到的原样值：

| 你 §3/§8 要求的 | 我量到的 |
|---|---|
| 屏幕不得借别层文案 | 含「这台服务器上没有这一趟行程了」，**不含**「网络不可用」 |
| 分类只有一个来源 | `<section data-testid="failure-view">` 上 **五个属性齐**：`data-attribution-reason=JOURNEY_NOT_FOUND`、`data-evidence-kind`、`data-http-status`、`data-source-layer`、`data-recovery-action` |
| 生产可事后发现 | telemetry：`{reason:JOURNEY_NOT_FOUND, evidence_kind:HTTP_RESPONSE, http_status:404, source_layer:RESOURCE_STATE, retryable:false, recovery_action:choose-journey, message_key:failure.journeyNotFound}` |
| 消费者共读同一对象 | `copyFor()` / `role=alert` / `recordAttribution()`（3 个调用点）/ 恢复按钮全部读同一 `Attribution`；旧的三个各写各话的状态已合并 |
| 自愈 | `context:"shell.boot.cleared:citynexus.v8.journey_id"` + `localStorage` 该键 = **null**（刷新不再撞 404）；屏上有「选一趟行程」「重试」可聚焦 |

⇒ 代码级我也核了你 ③ 关心的那个坑：`failureAttribution.ts` 里 **`navigator.onLine` 只出现在注释**，理由写的是 *"true on a captive portal and true while a backend is dead"* ⇒ 优先级是 **服务端 code → HTTP status → transport**，浏览器感觉不参与判别。

## ② 我自己差点制造一次"假缺陷"，值得进你那本 policy
第一遍我用**猜的**属性名去探测（`data-attribution-evidence-kind` 等），读回来**四个都是 null**，差一步我就写"只落了 reason，其余没上屏"。
实际命名是 `data-evidence-kind / data-http-status / data-source-layer / data-recovery-action`（少一个 `attribution-` 前缀）。我把 `getAttributeNames()` 打出来才看清。
⇒ **今晚同类第四次**（`onLine` 当主证 / 匿名 401 当"护栏没了" / CSS transform 当"没平移" / 这次属性名）。共同形状都一样：**拿预期的名字去要证据，而不是先把现场键名打印出来**。
⇒ 建议（要就写、不要就算了）：在 `test_execution_truth_policy.md` 加一句
**"Negative claims require the field/identifier inventory that was actually read, printed."**
——即任何"没有 X"的结论，必须附上"我读了哪些键/字段名"的清单，而不是我只查了我以为该存在的那个名字。

## ③ 签收口径我留了两处诚实缺口（不给自己圆满）
- D 的 e2e 生产链（`40 passed / 0 failed`、`tsc` exit 0、`killJ4` KILLED）**我没有复跑** ⇒ 账本记 `ACCEPTED-code-and-live-verified / lane-reported-suite-not-re-executed`；
- `killJ3` 仍 **SURVIVED**，原因与 ORD-0178 同一条：Dexie 实测 0 行、`caches=[]`，缓存视图今天根本到不了 ⇒ **这不是文案问题，是存储层没落地**，我不因为"门绿了"就记它解决。

## ④ 现场
tip `8ee64ae`；预览前端 `index-BkEHAbFb.js`（后端 `:8693` 未动、`:4782` 护栏 403 ENFORCED 本轮再量、用户 journeys=3 / plan_versions=19 / travelers=3 未变）；
账本已镜像 `11ed7bb4f678`（字节级相等，1,937,019 B）；基线成对 **17 / 13**；ORD-0125 仍 `NOT-STARTED`；ORD-0184 已按你 ① 的分工派给 F。
下一条我推 C 的 ORD-0167 与小县城端到端（那是你 #4 主线的第一个真闭环），有结果就报。

竭尽所能的替qoder铺路
