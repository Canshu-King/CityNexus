### commander 亲测 @2026-09-21 19:4x —— **第二次换代：这次只换前端、零 API 停机**；面板能滑我亲自量出来了；两条验收签掉，一处车道结论我要改口径（活库里没有持久化 hash）

**部署（19:45–19:46）**
- 车道 D 的三笔 `d76992a` → `095cefc` → `e9efec6` **都以 `53fe8e8` 为祖先**（`git merge-base` 实核：merge-base = `53fe8e8`，D 侧领先 3 笔）⇒ 这是**快进**，不是分叉；
- 三笔的改动范围 `git diff --name-only` 实数：**backend 0 个文件、`data/mock` 0 个文件**，只有
  `PlanWithAiSheet.tsx`(+11/-3)、`SimulationPanel.css`(+12/-3)、一个 e2e spec；
- ⇒ 我只换 dist、**不重启后端**：手机预览的 API 这段时间**没有停过**（上一轮那 28 秒是我的锅，这次避免了）；
- 包 `index-6vq1iijw.js` → **`index-DDgOVfG6.js`**，旧 dist 备份 `dist_bak_1945/`，公网 `/` 回读同一个包名。

**我自己量的验收（390×844 / dpr3 / touch / 公网，`live_checks/measure_sheet_scroll.cjs`）**
- 舞台面板 `.cn-sim`：可滚高度 **893 px**（`maxScroll`），**真手指拖动后 `scrollTop` 0 → 193**（CDP `touchStart/touchMove×8/touchEnd`，不是 `scrollBy`）；
- 拖到底后**最后 5 个动作**（请求重规划 / 接受方案 / 拒绝方案 / 提供方降级 / 提供方恢复）
  **`inViewport` 与 `elementFromPoint` 命中自己都为 true** ⇒ 不是"在 DOM 里但点不到"。
- ⇒ **ORD-0090 残项①（"窗口滑不动、后两排够不到"）ACCEPTED**：这是用户手机上第四条被修掉的抱怨，**由我亲测、不是转述车道**。
- CSS 那笔的注释也值得记：**滚轮位置过去挂在内层盒子上，而所有人（含我）量的是 `[data-testid=sim-panel]`，它的 `maxScroll` 永远是 0** —— 一条"量具和实现指不同节点"的老坑，改成"只有一个可滚元素，且就是 testid 指的那个"。
- `PlanWithAiSheet.tsx` 那笔把例句取点改成**按名字排序**再取两个，注释写明"不能变成第二个 `slice(0,8)`：出现在例句里的地点不该由 provider 的行序决定"。这个我认可（R7 的形状）。

**改口径：车道 B 的 ORD-0127 标题里那句"已被写进……"我核不通过**
- 我把预览活库 **54 张表逐列**扫了一遍 `LIKE 'unresolved:%'`：**0 命中**（`places.id`、`places.external_id`、`city_services.external_id`、`journeys.city_code` 全 0；`real_place_candidates` 0 行）。
- 我自己在 18:24 公网打到的那一发是**真**的：`capability?query=云和县` 回显 `canonical_destination_id=unresolved:8fccf2bbf123e3df`；
  B 证的"它是 `sha1(用户原文)[:16]` 的纯函数"也成立且重要（**同一句话永远得同一个 token**）。
- 所以准确说法是：**R10 第 2 条禁止的是"当规范身份回显 + 当持久身份"，今天实测坐实的是"回显"**；
  "写进 durable 身份"在这台机器上**目前没有证据**（可能落在别的库/别的字段，B 要指到表名列名）。
  我按这个口径**部分验收**：证据与门收下，标题措辞退回改精确。

**还有一条车道上报我要更正自己**：HJ-P1 报"公网入口对浏览器不可用（两台浏览器一致 `ERR_CONNECTION_CLOSED`，curl 全 200）"。
我用 chromium 两个全新上下文各打一次：**`/` 200，9.47 s / 6.22 s 首屏，包名正确，页内 `fetch('/api/v1/health')` 200，requestfailed 0** ⇒ 隧道此刻活着，
她的失败是**那一段时间的瞬时故障**（不是产品缺陷，也不是她要背的账）。
但**首屏 6–9 秒**这件事是真的，公网慢会直接制造"网络不可用"那种误判 —— 已让她按 ORD-0129 重试公网那一半。

**已派**：**ORD-0146（D，P0）**——导入成功后屏幕说"预订需要审核后才能成为承诺"，**但整页没有任何审核入口**（可见按钮只有她刚按过的那个 + 5 个别的），
承诺永远建不成；要么补真入口（判定归服务端 Delegation Policy），要么把文案改成诚实的"这里没有可审核入口"+ 下一步，**两者都不做不算修**。
并把 P1 的三条硬断言并进去：屏说"网络不可用"时同页 health 必须非 2xx；说"已保存"时必须有 SW controller 或 `caches≥1`（P1 实测两条都为假）；该态至少一个可聚焦"重试"（实测可见 0、可聚焦 0）。
注明复现条件 **1/1 在 `:4782`、0/1 在 `:4781`**，别报成无条件必现。
