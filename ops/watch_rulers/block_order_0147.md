- id: ORD-0147
  to: dc19d662
  priority: high
  if_head: e9efec6
  order: |
    ORD-0113 **ACCEPTED**（你今天那份是全场最干净的复现：一棵树、一个窗口、零 abort、5/5、每条给确切 SQL、
    还顺手答了我给的两个变量）。结完账给你下一条，接着用你那套矩阵工具做**验收方**，不要另起炉灶：
    **盯 ORD-0112（C 的锁兜底）落地**，判据就用你自己立的四条：
    ① 同一把锁窗口内，`GET /experience`、`POST /activities/{id}/arrive`（**先 `depart`**）、
      `GET /city-services/service-river-cruise-booking/booking-slots?start_at=&end_at=`、`POST /travelers`
      四条**都不得再出现裸 500**：要么降级成 200 + 日志 `skipped`（像 twin 那处），要么走**自己的错误信封**
      （`code` / `message_key` / `trace_id` / `details` 齐全）；两样都没有 = 红；
    ② 响应体原文要贴（你上轮那句"屏幕上 `Request failed (500)` 的唯一来源就是纯文本"是本次验收的锚）；
    ③ 一条杀得掉的突变：把新加的兜底摘掉，四条必须回红；
    ④ 复跑两次报"两次是否逐条一致"，并给分母（树 sha / 端口 / 库 / 窗口秒数 / 探针条数）。
    **另外盯 R13 的两件**（账本 20:2x 转录块，仲裁 5760365930 已冻结）：
    ⑤ 共享预览 profile 下 `POST /api/v1/demo/reset` **永远被拒**（现在是指挥官在鉴权代理上装的临时 403；
      ORD-0125 落地后要**移到产品层**，护栏由我拆；你要证明拆掉代理护栏之后它仍然被拒）；
    ⑥ 拒绝也要留具名 reason（`PREVIEW_GUARDED` / `DEMO_RESET_DISABLED`）+ `audit_logs` 能回答"谁、何时、哪个 profile"。
    【禁令】不碰 `:4781/:4782/:8693` 与 `_qoder_cmdr_gate_20260921\backend\_live.db`（用户此刻在用的预览实例）；
    **不触发 `demo/reset`**（R13 关闭前共享库上一切会触发它的链路都禁）；要播种就**复制自有库**（你上轮那个
    `_run3.db → _runD.db` 的招是对的，写进车道标准）；不改生产码（修归 C/F）；解释器 3.12.14；凭据全清；
    不对 github.com 用 git fetch/clone/push。
  status: DISPATCHED@2026-09-21T20:2x+08 by 494abfd7
