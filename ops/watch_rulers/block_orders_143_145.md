- id: ORD-0143
  to: 6af4cf53
  priority: high
  if_head: 53fe8e8
  order: |
    旧账（我这边挂了一整天的 #13）：**发布包必须对齐当前 HEAD**。今天权威 tip 从 `1874a41` 一路走到 **`53fe8e8`**，
    中间新增了不少**新模块文件**（`backend/app/anywhere_capability.py`、`catalog_hydration_operations.py`、
    `integrations/discovery/{real_city,photon}.py`、`integrations/mobility/runtime.py`、
    以及一批 `backend/tests/test_qoder_anywhere_*.py` / `test_qoder_beijing_catalogue.py` 等）。
    发布包是**逐文件手工同步**的，历史上出现过"代码 import 了新模块但包里没有那个文件"整包起不来的事，所以这次要求：
    ① **从 git 重新生成**（`git archive 53fe8e8` 或按清单从**干净副本**导出，不许从工作区脏树拷），
      导出前后各报一次文件数与总字节；
    ② **可导入性自证**：在解包出的**独立目录**里，用 `D:/moodle/CityNexus/.venv/Scripts/python.exe`（3.12.14）
      跑 `import app.main` + `pytest --collect-only -q`，**任何 `ModuleNotFoundError` 都算包不完整**，
      必须把缺的文件名列出来并补进包；
    ③ **起一次真服务**（自有端口 `:8530-:8539`，自有空库）：`GET /api/v1/health` 200 + `GET /api/v1/places?city_code=CN-BEIJING` 数量 = 8
      （北京目录今天已进 `data/mock/places.json`，包里没有它 = 手机上的老问题重演）；
    ④ 报 **包 sha ↔ 权威 sha 的对应表**（`PACKAGE-MANIFEST.json` 里那套），并写明"未 push、未动权威树"。
    禁令：不碰 `:4781/:4782/:8693` 与 `_live.db`；不动 `_qoder_integration_20260919` 与 `CityNexus\**`；
    不对 github.com 用 git fetch/clone/push；包里**不得含任何凭据**（`.env`、token、key 或其前缀）。
  status: DISPATCHED@2026-09-21T19:3x+08 by 494abfd7

- id: ORD-0144
  to: 5ea3bedc
  priority: high
  if_head: 53fe8e8
  order: |
    **只读审计**，产出 ANYWHERE 任务书 DoD 第 10 条所要求的证据：
    **"LLM 不能凭空造出持久化的物理地点"** —— 这条现在只有断言、没有全量地图，你来补。
    以 `53fe8e8` 为准，逐项列表回答（每项都要 `文件:行` 与"我读到的代码"级证据，不接受推测）：
    ① 今天所有**模型输出可以到达的写路径**（`agent/commands`、mission、`semantic_compiler`、`responses`、
      以及 `main.py` 里六条 hermes 路由与任何 planning/replan 入口）；
    ② 每条路径上**校验发生在哪一行**：是不是把模型给的 `place_id` 与**服务端目录**求交？交集为空时是拒绝、还是静默降级？
      （已知事实：前端 `PlanWithAiSheet.tsx:555-566` 现在**不再发 `place_ids`**，只发 `{candidate_count: 3}` ⇒ 旧的"前端自己截 8 个"这条面已关；
      我要的是**服务端还剩哪些门**。）
    ③ 明确回答：**模型能否凭空调入 `places` / `city_services` 的新增？** 若能，给出最小复现路径（不要真跑写实验，纸面推演 + 指出代码位置即可）；
    ④ 与 **R10** 对齐检查：有没有哪条路径会把 `unresolved:<hash>` 或用户原文当 canonical city_code **写进库**；
    ⑤ 给出一张"AI 写路径 × 门控 × 缺哪条门"的表，我会拿它决定给 C 派不派新单。
    禁令：只读；不改 `backend/**`、不改 `frontend/src/**`、不新建测试文件（要证形状就写进报告）；
    不碰 `:4781/:4782/:8693` 与 `_live.db`；不对 github.com 用 git 网络操作；报告里不得出现任何 key。
  status: DISPATCHED@2026-09-21T19:3x+08 by 494abfd7

- id: ORD-0145
  to: 848847ed
  priority: medium
  if_head: 53fe8e8
  order: |
    你的 `SIMULATION_REUSE_MAP`（ORD-0050）是照 `65e184d` 时代量的，**tip 已经到 `53fe8e8`**，
    而这几小时面板真的改了行为：`1b74040` 让舞台**向服务器问"现在能订什么 / 这是哪个提案"**、
    ORD-0132 又指出「推进当前活动：到达」与状态机要 `EN_ROUTE` 不同步。请**用你原来的办法**重跑一遍：
    ① **运行时自证路由**（405/404 判别，不靠 grep）：在自有端口的后端上把你那张表里的路由逐条打一遍，
      报"命中 / 405（存在但方法不对）/ 404（真没有路由）"三档分母；
    ② 表里每条注明**在 `53fe8e8` 上是否仍成立**（成立 / 已变 / 失效），变更处给 `文件:行`；
    ③ 单独回答一个问题：**面板现在这 8 个动作里，有没有哪个动作的"可点状态"是前端自己猜的**
      （而不是服务器投影给的）——今天 HJ-P4/C 都撞上"按钮说到达、服务器要 EN_ROUTE"这一族，
      这就是我要的"猜"的定义；
    ④ 全程 **GET/HEAD 优先**，不写业务数据；若要 POST 自证，只打你自己库、自己 journey。
    禁令：不动 `CityNexus\**` 与 `_qoder_integration_20260919\**`；不碰 `:4781/:4782/:8693` 与 `_live.db`；
    不按/不触发 `demo/reset`（它无范围删 52 张表）；端口自开自登记；不对 github.com 用 git 网络操作。
  status: DISPATCHED@2026-09-21T19:3x+08 by 494abfd7
