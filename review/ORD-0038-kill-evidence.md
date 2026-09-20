# ORD-0038 杀证据记录（AI 面板：可见进度不得伪造）

会话 `e345b9d6` · 门 `frontend/e2e/qoder-plan-ai-thinking.spec.ts` · 驱动 `review/ord0038_kill_drivers.py`
产品改动 `d47e085`，门 `c04a4d8` → `93a336b` → `6bfb2a7`。
`*.log` 被 `.gitignore:39` 排除，逐条读数记在这里；原始日志在同名 `review/kill38-*.log`（本地）。
每个变异体跑完都从 `git show HEAD:` 重新取回的 pristine 还原并校验 sha1，七次全部 `OK`。

pristine 基线 sha1：`0ff112290dcbd7d75e0fbf787d010292c19695d2`（`PlanWithAiSheet.tsx` @ `6bfb2a7`）。

## 这张门测的是什么

`POST /agent/commands` 是**同步**接口：请求发出后到答复回来之前，后端不报任何阶段。
所以门只允许断言组件自己能证明的东西 —— 真实等待秒数、真实 await 的阶段、取消是否真的中止、
失败是否与加载可分、预检读不到时是否老实说读不到。

门**不断言** `interactive`/`setInterval` 这类实现细节，也不给任何假进度打分：它派发布尔动作、读渲染结果。

## 逐节点结果（七杀零活）

| 变异体 | 改动形状 | 点名节点 | 红消息（原文摘录） |
| --- | --- | --- | --- |
| kill38-a-frozen-seconds | 中文渲染臂把秒数写死成 `已等待 0 秒` | `plan-ai-elapsed-ticks` | the seconds the traveller reads on screen never advanced (zh-CN copy) |
| kill38-a2-frozen-seconds-en | 英文渲染臂写死成 `waiting 0s` | `plan-ai-elapsed-ticks` | the seconds the traveller reads on screen never advanced (en copy) |
| kill38-b-everything-claims-done | 所有阶段行一律标 `done` | `plan-ai-no-fabricated-stage` | while the request is still in flight only the baseline read has really finished, but these claim done: ["baseline","request","verify"] |
| kill38-c-cancel-cannot-stop-the-post | 命令请求不带 `signal` | `plan-ai-cancel-aborts-request` | the browser never aborted the request; a cancel that only hides the sheet leaves the model running and spending money |
| kill38-d-cancel-cannot-stop-the-baseline | 基线读取不带 `signal` | `plan-ai-cancel-before-send` | nothing had been sent yet, so this must read as a clean CANCELLED, not "CANCELLED_AFTER_SEND" |
| kill38-e-refused-request-falls-through | 去掉 422/5xx 的提前具名失败 | `plan-ai-failure-not-loading` | a 422 must be reported as the refusal it is, got "NO_PLANS_PRODUCED" |
| kill38-f-unreadable-status-reads-as-ready | 预检失败分支改成"已配置" | `plan-ai-preflight-honest` | the sheet claimed a model was configured after case "never answered" |

`plan-ai-elapsed-ticks` 有**两个**变异体：这个节点在源码里是两条模板分支（中/英各一条），
一条变异体只能打死被执行的那条。

## 第一轮只杀掉 1/6：五条存活全是量具缺陷，已公开记录

第一轮（门 `c04a4d8`）结果 a 存活、b 杀死、c/d/e 红了但没点名、f 存活。逐条查出来都是我的门写错：

1. **读错了对象**：`plan-ai-elapsed-ticks` 轮询的是 `data-elapsed-seconds` 属性，而变异体改的是渲染文字。
   属性照走、屏幕冻在 0 秒，门照样绿。→ 改为解析用户真正看到的那行里的数字。
2. **红不带节点 id**：c/d/e 都变红了，但红在 `toBeVisible()` / `locator.click()` 的超时上，
   消息里只有"element(s) not found"。等于"有个东西没出现"，不等于"这条契约破了"。
   → 每个等待与轮询都自带 `:: <节点 id>`，并把具名语义断言排在 UI 交互之前；
   同时把变异体下的响应延迟调到 8s/6s，让"不响应取消"的产品也能产出结果，从而死在语义断言上而不是死在超时上。
3. **守卫写反**：`/is configured/` 把正确文案 "No model is **configured** here" 判成撒谎。→ 只匹配肯定句。
4. **分支不可达**：预检的 `catch` 只在 fetch **reject** 时走，`fulfill(500)` 不是 reject，
   所以"读不到却说 ready"这个变异体没有路径可暴露。→ 加 `route.abort()` 的真·传输失败用例。
5. **语言臂漏管**：a 的变异体改中文，套件默认英文跑，改的那行根本没执行。
   → 该节点中英各跑一次，驱动也各配一个变异体。

第 5 条的根因和第 1 条同类：**门量的是它以为产品会走的路径，而不是产品实际走的路径**。
七条门现在全部由"用户可见的渲染结果"驱动。

## 已知缺口（登记，不写成通过）

- **真实 AI 成功路径没有走过**。本车道能测的环境一律 `CITYNEXUS_AI_ENABLED=false`；
  预览实例（:8781/:4781 + `_preview.db`）是用户此刻在用的，订单明令不许拿它跑 e2e，也不许动它的 AI。
  所以门里的"模型正在工作"是用 `page.route` 挂住请求来**代替延迟**，不是代替结果。
  "点 AI 规划 → 真出方案"这一步要么由 Commander 在手机上走一遍，要么明确授权我另起一套开 AI 的实例与库。
- 阶段名（基线读取 / 等待模型 / 核对新方案 / 兜底重排）是**客户端自己 await 的步骤**，
  不是后端阶段；后端阶段仍然一个都没有。这一点在界面上用一行明说了。
