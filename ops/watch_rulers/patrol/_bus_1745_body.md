**值守 17:41:25 · 最老的那格待裁我量成代码事实了：ORD-0458 甲/乙/丙（挂 21779 那块，从 09-29 12:27 到现在）· 我只摆每条路撞上什么，不替你选**

对象是权威尖 `be0ffee216c7d24e48652427d290da848a9195cf`（`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` 现读；下面每行都出自 `git show <尖>:<路径>`，不碰工作树、不碰任何人的枝、0 写）。

一、工单说的那枚「已有的 pretrip 面板」在尖上确实存在，全套就 4 枚文件：
  - `frontend/e2e/qoder-ord0384-pretrip-checklist.spec.ts`
  - `frontend/src/features/checklist/PretripChecklistPanel.tsx`
  - `frontend/src/features/checklist/pretripChecklist.css`
  - `frontend/src/lib/pretripChecklist.ts`

二、这枚面板**自带一条已经落地的设计断言**（`frontend/src/lib/pretripChecklist.ts` 头注释，逐字）：
  8: * today. The order was re-scoped on that measurement: an item may appear only if the contract names its
  17: * It stores nothing and writes nothing. Completion is not a checkbox: the item disappears when the
  18: * server stops saying so, which is why there is no "mark done" control.
它的 e2e 也这么写（`frontend/e2e/qoder-ord0384-pretrip-checklist.spec.ts` 头）：
  11: *       and it returns -- completion is a projection of the field, not a checkbox;
⇒ 也就是说：屏上「勾选」这件事现在**不是**一个控件；清单只有两条，且每条都必须能被契约点名（锚 :1393 :1923，钉在契约 blob `177f3ad34f4198e87f9d8353b10d9724a816c55d`）。

三、契约面实测：`contracts/openapi.yaml` 里字面 "checklist" 现共 **0 处**；`backend/app` 的 grep：命令 `git grep -c -i checklist <尖> -- backend/app` 回 rc=1、输出 0 行，即这个字面在 backend/app 里没有行可打印——我不把它写成「没有该能力」，只写「词面没有」。
⇒ 三条路各撞上的东西，按现测：
- **甲**（只视图态、面板明写"本次不保存"）：0 新对象 0 写路由，与二里那条断言不冲突；但如果"勾选"要做成可点控件，就直接撞 spec 那句「not a checkbox」——**改 spec 那句就是改 ORD-0384 已交付的判据**，那需要你具名放行，车道不能自己改断言换绿。
- **乙**（真持久化勾选与备注）：契约面现在这个字面是 0 处，要新增字段与写路由、同笔进 `contracts/openapi.yaml` 与 `frontend/src/generated/api.ts`，并且二的断言要整个翻面（它明写 stores nothing and writes nothing）。
- **丙**（挂到已有对象）：dt 原句在下面逐字给，要挂哪一枚已有对象由你定；我不猜归属。

四、dt 那格请裁的原文（账本第 21779 行；甲/乙/丙逐行拼回，**丙那句在账本里跨了行、拼接后仍短一截**，全文按行号自取）：
> ### 车道 dt（会话 be19052c）ORD-0435 欠件补交：修后屏读两臂（并认我上一版是假双臂）+ ORD-0452 报名 + ORD-0458 前提冲突请裁（2026-09-29 12:27 +08） / **六、ORD-0458 有一处前提冲突，请裁，我不擅自选**。工单写"接在已有的 pretrip 面板上，不新建对象"， / 三条路请挑：**甲** 只做屏上粒度——勾选态与完成计数为本次会话视图，面板上明确写"本次不保存"， / 0 新对象 0 写路由（守"不新建对象"，但"勾选"不跨设备）；**乙** 给清单开字段与写路由（勾选与备注真持久化， / 但违"不新建对象"，且要同笔进契约与 `frontend/src/generated/api.ts`）；**丙** 把勾选态挂到已有的 / 我推荐 **甲 + 具名声明**，因为 0435 刚教过：客户端状态一旦看起来像已保存，就是红线本身。

五、这条为什么值得先裁：dt 名下 ORD-0435 已落地、ORD-0452 我已 11:54 量成代码面事实（总线 `5903722590`），剩这一格把她整条钉住 **29.2 小时**（块头自报 09-29 12:27 到现在，我按那时刻算的）。我这边不催、也不替她改口径；裁语归你。

六、可重跑（只读）：
- `git -C D:/moodle/CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`
- `git -C D:/moodle/CityNexus show be0ffee216c7d24e48652427d290da848a9195cf:frontend/src/lib/pretripChecklist.ts`
- `git -C D:/moodle/CityNexus show be0ffee216c7d24e48652427d290da848a9195cf:contracts/openapi.yaml | grep -ic checklist`

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
