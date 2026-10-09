## commander 规则 + 派单 @2026-09-22T19:48+08 —— HJ-P1 交出一条**影响所有车道的仪器陷阱**（`scrollIntoView({behavior:"smooth"})` 在本机移动模拟里从不推进）；它的 ③ 改判我接受

### ① 新常驻规则：门不许把"动画滚动"当被测对象

HJ-P1 用**同一元素、同一时刻、两种 behavior** 做判别实验：

```text
被拦后 2.5 s：scrollY=0， #trial-required-hint y=1221（视口 844，doc scrollHeight 1493，无内层滚动容器）
手动 instant：el.scrollIntoView({block:"center"})                     -> scrollY 0 → 650（5 次采样全 650）inView=true
手动 smooth ：scrollTo(0,0) 后 el.scrollIntoView({block:"center", behavior:"smooth"})
                                                                      -> 6 次采样（每 200 ms）**全 0**
```
⇒ **元素能滚、文档能滚，只有"平滑滚动"在本机的 Playwright/CDP 移动模拟里从不推进。**
它的原话我落成规则：**"任何断言『被拦后解释进入视口』的门，如果用 smooth 且用 `scrollY`/`inViewport` 断言，会在产品正确的情况下红，或者更糟——在 CI 里靠时序侥幸绿。门要么把 behavior 定成瞬时，要么按『节点存在＋文档可滚』断言，别把动画当被测对象。"**
**我已在源码上核实这条规则的落点**：`JourneyTrialSetup.tsx:449` 确为 `hint.scrollIntoView({ block: "center", behavior: "smooth" })`（`dfdc5d5` 上），`:1175` / `:1199` 两处调用。

### ② HJ-P1 的 ③ 改判我接受（它自撤了"产品根本不滚动"）

它的源码旁证：被拦后 `#trial-next-reason` 拿到了句子 ⇒ 同一 `if (blockedNow)` 块里的 `speak()` 执行了，`revealReason()` 在下一行也执行了。
⇒ **正确判定不是"仍在"、也不是"已修"，而是：修法已落码，其效果在它仪器内不可观测，需要一次真机（或非移动模拟的有头）读数才能定。** 它**不给 ③ 签任何格**——这个克制我认可。
**它给 D 的稳健性意见我转成要求**（不是缺陷，是可测性）：把"被拦的唯一解释"寄托在一次动画滚动上很脆弱 ⇒ **建议改 `behavior:"auto"`（瞬时）或把提示渲染进 sticky 动作条上方**，两种都能让门用几何断言稳定咬住。

### ③ ② 那一格：它这轮把事实切得更准（我照记）

```text
被拦后：#trial-required-hint（role=status，可见）y=1221「还需要填写：总预算」
       #trial-next-reason（v8-sr-only, aria-live=polite）「还需要填写：总预算」
改成 420 后：可见提示节点 **消失**（按值重算的可见侧是对的）
             #trial-next-reason 文本 **仍是**「还需要填写：总预算」← live region 没跟着清
源码守卫 :1105 {spokenKey === missingKey ? spokenReason : ""}，missingKey 来自 :563 missingNow.map(...)
```
⇒ **同一时刻可见侧已重算、读屏侧未重算**，复现 **3/3**，分类 `HUMAN_ACCESSIBILITY` 不变。它**不猜原因**、只给节点 id 让 D 下断点——这个分寸对。
**它请求的发布**：`evidence/hjp1_0223/` ＝ 本块文本 ＋ ② 段的可复放脚本。**我来发**（它只读）。

### ④ 现场

working tip `dfdc5d5`（19:37）；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
