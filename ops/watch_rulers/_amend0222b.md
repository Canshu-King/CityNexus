  note@494abfd7@2026-09-22T19:49+08: HJ-P1 19:46 实测追加两条硬要求（我已在源码上核实）：
  ① **`revealReason()` 用了 `behavior:"smooth"`**（`frontend/src/features/setup/JourneyTrialSetup.tsx:449`，调用点 `:1175`/`:1199`，在 `dfdc5d5` 上）。
     实测：同一元素 instant 能滚（scrollY 0→650，5 次采样一致），而 smooth **6 次采样（每 200ms）全 0** ⇒
     **smooth 滚动在本机 Playwright/CDP 移动模拟里从不推进**。改 `behavior:"auto"`（瞬时）或把提示渲染进 sticky 动作条上方。
     ⚠ 这是**影响所有车道**的仪器规则：任何"被拦后解释进入视口"的门若用 smooth + `scrollY`/`inViewport` 断言，
     会在产品正确时红、或在 CI 里靠时序侥幸绿。门不许把动画当被测对象。
  ② **读屏 live region 仍未按值重算**：改成 420 后可见 `#trial-required-hint` 已消失，但 `#trial-next-reason`（`v8-sr-only`, `aria-live=polite`）
     仍写着「还需要填写：总预算」；复现 **3/3**。源码守卫 `:1105 {spokenKey === missingKey ? spokenReason : ""}`、
     `missingKey` 来自 `:563 missingNow.map(f=>f.target).join("|")`。HJ-P1 只交事实、不猜原因（可能比 60ms 定时器与状态更新的次序），
     节点 id 已给全，D 可直接下断点。分类 `HUMAN_ACCESSIBILITY` 不变。
