### 1a986a24 HJ-P1 ③ 回到"未修"，但我 19:46 那条"仪器不推进 smooth"是错的：真坑是**非置前标签页会冻结平滑滚动，而 `visibilityState`/`hasFocus()` 两个都骗人** @2026-09-22T19:56+08

**这一步为什么值得再改一次口**：我 19:46 说"smooth 在本仪器里从不推进，所以 ③ 无法判定"。
刚才用一个**独立可复放脚本**跑同一件事，结论反了，于是我做了同标签页的置前/非置前对照。现在两件事都清了。

#### ① 我的脚本自己推翻了我（先记账）

`_qoder_hjp1_o207_20260922/ord0223_scroll_probe.cjs`（自带第 1 步走位，全新上下文可跑，**0 次非 GET 请求**）：
```json
{ "base": "http://127.0.0.1:8752", "error": null, "onStep2": true, "nonGetRequests": 0,
  "verdict": { "refusedPressMovedPage": false, "instantScrollWorks": true,
               "smoothScrollAdvanced": true, "visibleHintRecomputedAfterFix": true,
               "liveRegionStillStaleAfterFix": true } }
```
⇒ 在独立 Chromium 里 **smooth 是能推进的**——我 19:46 的"仪器不推进"是错的。

#### ② 真正的仪器坑（同一标签页、同一节点、只差置前）

```text
非置前： 手动 smooth -> scrollY 采样 0,0,0,0,0        document.visibilityState="visible"  document.hasFocus()=true
置前后： 手动 smooth -> scrollY 采样 0,531,648,650,650  两个标志位仍然是 visible / true
```
⇒ **平滑滚动只在标签页真正置前时推进；而 `visibilityState` 与 `hasFocus()` 都不反映这件事。**
这条比"移动模拟"危险得多：任何断言动画/滚动/过渡的门，在共享浏览器里都可能因为"我的标签页不在最前"而假红，
或者反过来在绿的时候什么都没测。判据要写进门：断言前 `page.bringToFront()`，或直接测瞬时滚动/几何存在性，别测动画。

#### ③ 于是 ③ 的判定回到 **未修**，而且证据比之前任何一次都强

同一次会话里，**已经把标签页置前**（上一格刚证明此时 smooth 能推进）之后，走产品自己的路径：
```text
第 2 步 总预算=0 -> 按「下一步」被拦
scrollY / #trial-required-hint.y  8 次采样（每 300 ms）：0/1221, 0/1221, 0/1221, 0/1221, 0/1221, 0/1221, 0/1221, 0/1221
最终：scrollY=0，hint y=1221，inView=false
```
⇒ **手动 smooth 能滚、产品那条路径滚不动**，两者条件相同。所以不是仪器、不是 id 缺失（`:1043` 在）、
也不是没调用（同一 `if (blockedNow)` 块里前一行 `speak()` 的产物 `#trial-next-reason` 拿到了句子）。
**我不下结论说原因是什么**，只交一个可查的假设：`speak()` 在 60 ms 后 `setSpokenReason(text)` 触发重渲染，
可能把刚起步的平滑滚动取消了——手动调用后面没有那次状态更新，所以能滚完。
D 可以在 `revealReason()` 里把 `behavior` 换成 `"auto"`，或把滚动排到 `spokenReason` 落地之后，两种都一行可试。
分类回到 **HUMAN_BLOCKER**，复现率：本轮 1/1（置前条件），累计 **5/5**（15:04、18:07、19:02×2、本块）。

#### ④ ② 那一格不变，脚本独立复证

同一份脚本的 `visibleHintRecomputedAfterFix: true` 与 `liveRegionStillStaleAfterFix: true` 独立复现了我 19:46 的节点级读数：
可见提示按值重算是对的，`#trial-next-reason`（`aria-live="polite"`）留着已经不成立的句子。累计 **4/4**。

#### ⑤ 交给包工头发布的东西（`evidence/hjp1_0223/`）

1. 本块文本；
2. `_qoder_hjp1_o207_20260922/ord0223_scroll_probe.cjs`（**已跑通**，输出即上面那段 JSON；脚本自带安全说明：只读、不点「确认创建」、默认指向 HJ-P1 自己的栈）；
3. `_qoder_hjp1_o207_20260922/ord0223_scroll_probe.json`（同一次运行的完整分步读数）；
4. `shots/o223-app-scroll-frontmost.png`（置前条件下被拦那一屏）。
本轮 **0 次创建**（脚本与手工都只按「下一步」，`nonGetRequests=0`）。
提醒：脚本会自己起一个 headless Chromium，不碰共享 MCP 浏览器；跑之前确认 `CNX_BASE` 指向你自己的隔离栈。
