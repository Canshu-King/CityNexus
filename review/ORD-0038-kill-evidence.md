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

## 逐节点结果（八杀零活）

| 变异体 | 改动形状 | 点名节点 | 红消息（原文摘录） |
| --- | --- | --- | --- |
| kill38-a-frozen-seconds | 中文渲染臂把秒数写死成 `已等待 0 秒` | `plan-ai-elapsed-ticks` | the seconds the traveller reads on screen never advanced (zh-CN copy) |
| kill38-a2-frozen-seconds-en | 英文渲染臂写死成 `waiting 0s` | `plan-ai-elapsed-ticks` | the seconds the traveller reads on screen never advanced (en copy) |
| kill38-b-everything-claims-done | 所有阶段行一律标 `done` | `plan-ai-no-fabricated-stage` | while the request is still in flight only the baseline read has really finished, but these claim done: ["baseline","request","verify"] |
| kill38-c-cancel-cannot-stop-the-post | 命令请求不带 `signal` | `plan-ai-cancel-aborts-request` | the browser never aborted the request; a cancel that only hides the sheet leaves the model running and spending money |
| kill38-d-cancel-cannot-stop-the-baseline | 基线读取不带 `signal` | `plan-ai-cancel-before-send` | nothing had been sent yet, so this must read as a clean CANCELLED, not "CANCELLED_AFTER_SEND" |
| kill38-e-refused-request-falls-through | 去掉 422/5xx 的提前具名失败 | `plan-ai-failure-not-loading` | a 422 must be reported as the refusal it is, got "NO_PLANS_PRODUCED" |
| kill38-f-unreadable-status-reads-as-ready | 预检失败分支改成"已配置" | `plan-ai-preflight-honest` | the sheet claimed a model was configured after case "never answered" |
| kill38-g-any-rows-count-as-ai-success | 去掉"mission 必须自己完成"的判定 | `plan-ai-no-synthetic-success` | a mission that reported it did not run must never be presented as AI success |

八杀零八活。产品改动（`cce00ca`）之后八个变异体**全部重跑**，pristine 指纹
`9386d47d9e9ffba3517eb4de665d80fd85af7642`，八次还原全部 `OK`。

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
八条门现在全部由"用户可见的渲染结果"驱动。

## 生产构建走查（`review/prod-refresh-walk.mjs`，证据 `evidence/ui-overnight/prod-walk.json`）

按 Mission 003 的新口径，dev 结果不算发布证据，所以这条走查跑的是 **`vite build` 产物 + `vite preview`**，
390×844，亮+暗，浏览器语言 zh-CN（用户真实默认）。每一步记的是**屏幕上实际渲染的字**：

| 步 | 实测 |
| --- | --- |
| 首访 | `#root` 有内容，标题"Demo之旅"，此时还没有 controller（注册中） |
| 二访 | `navigator.serviceWorker.controller` = `http://127.0.0.1:4199/v10-sw.js`（生产 workbox worker 接管） |
| 改构建→普通刷新 | 资源 `index-CAyaf1Ya.js` → `index-C91FKfyv.js`，注入的标记到达运行中的页面；**没有清缓存、没有硬刷、没有注销 SW** |
| AI 面板（亮/暗） | 提交前预检："这台服务没有接入 AI 模型：现在提交不会真的由 AI 规划，结果会走其它路径。" |
| 等待中 | "读取已有方案作为基线 · 已等待 0 秒" |
| 结果（修复前） | **`COMPLETED` "已生成 2 个可选方案"**，而技术详情里写着 `DeepSeek API key is not configured` |
| 结果（修复后） | `PLANS_WITHOUT_AI` "AI 没有参与这次规划（生成了 2 个备选）…不代表系统理解了你刚才那段话" |
| 360 宽 | `scrollWidth 360 / clientWidth 360`，无横向溢出 |

**这次走查抓到的缺陷不是"不好看"，是假成功**：mission 明确没跑，组件自己的兜底重排产出了行，
界面把它报成 AI 成功（绿色 ok 语气）。dev 门抓不到，因为它走不到"兜底真的产出行"这一步。
已修（`cce00ca`）并补门 `plan-ai-no-synthetic-success` + 变异体 kill38-g。

走查里 `secondsAdvanced` 为 `false` 并**不是回潮**：那次请求在第二次读数之前就返回了，
等待块已经消失，所以这一遍无法证明秒数在动 —— 这条证据由 e2e 里挂住请求的
`plan-ai-elapsed-ticks` 提供，走查不再把它算作自己的结论。

## 仍然存在的缺口

- **真实 AI 成功路径没走过。** 本车道能测的环境一律 `CITYNEXUS_AI_ENABLED=false`；
  预览实例（:8781/:4781 + `_preview.db`）是用户此刻在用的，订单不许拿它跑 e2e、也不许动它的 AI。
  门里的"模型正在工作"是 `page.route` 挂住请求**代替延迟**，不是代替结果。
  要补这一条，要么 Commander 在手机上走一遍，要么明确授权我另起一套开 AI 的实例与独立库
  （会花那把 key 的余额，我不自己决定）。
- 阶段名（基线读取 / 等待模型 / 核对新方案 / 兜底重排）是**客户端自己 await 的步骤**，
  不是后端阶段；后端阶段仍然一个都没有。界面上用一行明说了这件事。
