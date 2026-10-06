- id: ORD-0187
  to: 8c66aa92
  priority: high
  if_head: 8ee64ae
  order: |
    【我 00:2x 在**用户预览那台**上量到的两条现场，第一条是真缺陷：契约声明了 `/health`，后端只挂了 `/api/v1/health`】
    读数（`:4782`，带凭据，GET，只读）：
    ```
    /api/v1/health -> 200 {"status":"ok","database":"ok","ai":"enabled","e2e_run_id":"","e2e_database_id":""}
    /health        -> 200 <!doctype html> <html lang="en"> …        ← SPA 兜底把裸路径接走了
    ```
    而前端**生成物里确实声明了这个端点**：`frontend/src/generated/api.ts:7  "/health": { … }`。
    ⇒ 后果不是"少一个端点"，而是**探活会假绿**：任何按契约调 `/health` 的客户端拿到 **HTTP 200**，
       只是 body 是 HTML —— 状态码判断"服务活着"会通过，JSON 解析才失败；
       在 R14 的口径下这正是"**成功状态配错误载荷**"被当成成功，跟我们今晚修过的"404 折成离线"是同一类反向错误。
    要做（二选一，给理由）：
    (A) **后端补一个真 `/health`**（与 `/api/v1/health` 同源，同 body，明确不要求鉴权外的信息）；或
    (B) **把生成物/契约里的 `/health` 摘掉**，只保留 `/api/v1/health`，并让 SPA 兜底**不吞 `/api/*` 前缀**
        （现在裸 `/health` 能掉进静态兜底，说明兜底范围过宽，未来任何 API 拼错都会拿到 200+HTML）。
    我倾向 **B 为主 + 兜底收口**：`/api/**` 下未匹配的路径必须回 **具名 404 JSON**，**永远不得**回 200+HTML。
    门（三条，全要求先红后绿）：
    1. 按最终选择断言 `/health`（若存在）返回 **content-type: application/json** 且 body 与 `/api/v1/health` 同构；
    2. **`/api/v1/definitely-not-a-route` ⇒ 具名 404 JSON，不得 200+HTML**（这条是兜底收口的正身，也最容易先红）；
    3. 突变：把 SPA 兜底改回"吞一切路径" ⇒ 第 2 条必须回红。
    另：`ai: "enabled"` 我核过**边界仍然守住**——匿名 `POST /api/v1/agent/commands` 与匿名 `POST …/plans/generate` 都是 **401**（代理先拦），
    所以"公网无鉴权 AI 端点"这条**当前不成立**；但护栏**只有我的代理一层**，且线上那把 key 是可撤销前状态 ⇒
    我**不会**为省钱去关代理，也提醒 C：**不要**在这台上新增任何"免鉴权可调 AI"的路由。此项无需你动手，只需你**别扩大面**。
    禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db` 的写；禁 `demo/reset`（R13 护栏 ENFORCED）；报数六要素；突变只认原绿门变红。
  status: DISPATCHED@2026-09-22T00:3x+08 by 494abfd7（两条读数都在本块内，可复放；兜底收口是关键那条）
