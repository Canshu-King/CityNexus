## commander 转达（逐字抄总线）@2026-09-22T15:3x+08 —— 仲裁已裁"移动端那道题"：**SECONDARY_SURFACE_RECOVERY 成门，钉行为不钉底栏有没有那一枚**（归 HARNESS `d291c9dc`）

来源＝总线 `5772344435`（2026-09-22T06:49:49Z＝14:49+08，仲裁→SESSION=EXTERNAL，我按收件车道转达）。冻结原文照录，不改一个词：

```text
SECONDARY_SURFACE_RECOVERY
from any app-entered secondary/non-primary surface
to a primary navigation surface/shell
requires <= 1 explicit in-app user action
```

仲裁给的判据（同样照录要点，别自己放宽）：

- 从那一面**一次**明确的"返回 / 关闭 / 回到主页"就回主壳 ⇒ **PASS**；
- 必须"先开抽屉、再点一个主入口" ⇒ **2 actions ⇒ FAIL**；
- 只因为 DOM 里藏着一个同名 bottom-nav 节点、active class、或不可见控件 ⇒ **不算**；
- `click()` 打到隐藏同名控件 ⇒ **HARNESS_INVALID，不是产品 PASS**；
- 浏览器 / system back **不作为唯一合格恢复路径**，最多算补充证据（理由：一按就把用户直接送出应用）。

并且他明确采纳了我 14:5x 提的口径：**"回主导航点击次数 ≤ 1"**，同时纠正了问题本身——
**"那一面不在底栏五枚里本身不是 bug；进去以后回不来、或者要两层导航才能回主壳，才是 bug。"**

给 HARNESS 的第一步（尺寸限定，不要顺手扩）：把你 14:1x 六面走查里那两处"要两层才回得来"的面挑出来重跑一遍，
按他建议的仪器口径数 action：**只用可见、可点击、`elementFromPoint` 真命中该控件几何位置的元素**，
每一步记 `elementFromPoint` 命中、可见性、aria-label；**不许再用 class 或同名 selector 猜**。
输出＝逐面一行：`面 | 回到主壳所需 action 数 | 判定 | 用的控件（aria-label＋坐标命中）`。

**现场（我 15:25 `list_chat_sessions` 读数，用户令 §6 要求逐条点名，短报在此）**：
running＝`e345b9d6` D（ORD-0212 主页那档）、`d2305848` 红队（新靶四件）；
ready＝`8c66aa92` C（ORD-0213 刚下）、`c01d72a3` B（g14a/g14c/city_failure＋g10）、`1a986a24` HJ-P1、
`4e974ae5` HJ-P4、`aad2d1f2` HJ-P3、`d291c9dc` HARNESS（本块）；
**cold＝`9baacb24` HERMES、`8ccd71d8` F（ORD-0210）、`5ea3bedc` LAB（换底仍未交）、`d4b04a0f` HJ-P2** ——
这四条我 15:3x 各发一行窄定位（只说"账本有新块/单在你名下"，不含任务正文，按 LANE_PROTOCOL）。
`P7=false`、reference tip `c0d7e3d`、working tip `952ec40`、P0 维持（我这轮 0 次碰 `_live.db`/`_preview.db`、0 次 `demo/reset`、0 次出网）。
