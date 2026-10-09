### SESSION=494abfd7 · ORD-0169 **签收**（我自建 `8ee64ae` 的包、构建产物与车道报的 bundle 名一致，再在部署后的手机上量了归因）@00:0x

`STATUS: ORD-0169-ACCEPTED-AND-DEPLOYED | 我从 `git archive 8ee64ae` 自建：`npm run build` → **`✓ built in 13.06 s`**、产物 **`index-BkEHAbFb.js`** ⇒ **与 D 自报的 bundle 名逐字符相同**（同一 commit 两条独立构建可复现，这本身就是它交付真实性的旁证）| 部署：`_qoder_preview_20260920/dist`，换包前备份 **`dist_bak_0006`** |`

#### ① 代码级先核（不读结论读实现）
- 新建 `frontend/src/lib/failureAttribution.ts`（11,981 B）；证据优先级写成 **服务端 code → HTTP status → transport 异常**，
  而 `navigator.onLine` 在文件里**只出现在注释里**，理由也写了：*"true on a captive portal and true while a backend is dead"* ⇒ **仲裁 ③ 点我的那个错，它在设计上就避开了**。
- 消费者确实共读同一对象：`copyFor(...)`（屏幕文案）、`role=alert` 视图、`recordAttribution(...)` 三处调用点、`recovery.action` 决定按钮；
  旧的 `journeyGone / loadFailure / unreachable` 三个各写各话的状态被**合并成一个**（替换脚本 `rewrite-failure-views.py` 留在 review 里）。

#### ② 部署后在手机上量到的（390×844，死 id `ca0f1ed1…` 播种 → 重新加载）
| 读数 | 结果 |
|---|---|
| 屏幕 | 含「**这台服务器上没有这一趟行程了**」；**不含**「网络不可用」 |
| DOM 归因 | `<section data-testid="failure-view">` 上 **五个属性全在**：`data-attribution-reason="JOURNEY_NOT_FOUND"`、`data-evidence-kind`、`data-http-status`、`data-source-layer`、`data-recovery-action` |
| telemetry | `{reason:JOURNEY_NOT_FOUND, evidence_kind:HTTP_RESPONSE, http_status:404, source_layer:RESOURCE_STATE, retryable:false, recovery_action:choose-journey, message_key:failure.journeyNotFound}` |
| 上下文 | `context:"shell.boot.cleared:citynexus.v8.journey_id"` + `localStorage` 该键 = **null**（**清完不再撞 404**） |
| 出口 | 可聚焦按钮「选一趟行程」与「重试」都在屏上 |
⇒ R14-S/P 的"一个分类、四个消费者、生产可事后发现"这一条，**在用户此刻使用的入口上是实测成立的**。

#### ③ 我自己差点又造一次"能力普查错误"——先核再指控
我第一遍探测用的属性名是 `data-attribution-evidence-kind / -http-status / -source-layer / -recovery-action`，读回来**全是 null**，
差点被我写成"只落了 reason，其余四项没上屏"。实际命名是 **`data-evidence-kind` / `data-http-status` / `data-source-layer` / `data-recovery-action`**（少一个 `attribution-` 前缀）。
⇒ 我把 `getAttributeNames()` 打出来才看清 ⇒ **又一次：我的探针命名假设 ≠ 现场事实**。今晚同一类错第四次（前三次：`onLine` 主证、匿名 401 当护栏消失、CSS transform 当没平移）。
⇒ 全线口径我再加一句自己先守：**报"缺 X"之前，必须先把容器真实的键/字段名打印出来对照**，别拿预期的名字去要证据。

#### ④ 对账与遗留
- D 自报的门禁：`tsc` exit 0、生产链 **40 passed / 0 failed / 0 skipped**（`run_spec --list` 收集 40/8 files），突变 `killJ4` **KILLED**、`killJ2` 重钉锚点后 KILLED、`killJ3` **SURVIVED**（原因：Dexie 0 行使缓存视图到不了 ⇒ 归 ORD-0178，不算已解决）；我这边未复跑它的 e2e 链 ⇒ 这两项按 `ACCEPTED-code-and-live-verified / lane-reported-suite-not-re-executed` 记，不假称全跑。
- D 前一块里说"你说的 `index-BVbc7LUF.js` 在我能读的两棵树里都不存在"——解释：那是**我 21:29 自建的包**，只存在于 `_qoder_preview_20260920/dist`（发布目录，不是任何工作树）；现在这版已被 `index-BkEHAbFb.js` 取代，且**含**它的 0146/0126/0164/0169 全部码。它的"真机复验需要先重建"提醒是对的，我已经照做。
- **`manifest.webmanifest → 401` 仍未定**：我在 `:4782` 本机量到（含 D 也复述"既不能证实也不能否证"），**隧道侧无人量过** ⇒ 保持"未确认"，不立单。

status: ORD-0169 签收并部署（自建包名与车道一致；归因四消费者+telemetry+自愈全部实测在屏）；我自己差点用错属性名误报，已改为"先打印键名再指控"；D 的 e2e 链未复跑如实标注
evidence: `live_checks/build_r14.log`、`dist_swap_0006.log`、本轮 Playwright 两次 evaluate 原样读数（bundle、五个 data-* 键名、telemetry JSON、stored_id=null、按钮文案）
