# 待派单队列（用户不在电脑前，凡是需要他点确认的动作都落在这里，不做静默替代）

## Q1 · 给 n3（49fe0d7b）· ORD-0384 再 rebase 一次
- 现状：`review/N3-ord0384-pretrip-checklist` 最新头 `0e1aaf36182247c43429ff424b31a562f9b545ad`（16:28）
- 我的尺实测：`frontend/src/app/V8Experience.tsx` 合不出车道自己的字节 ⇒ 按 Q72 退回车道 rebase，我不手搓合并
- 权威尖逐字：`1f8d7061f9edd66652c198db983722cdd237f2b7`
- 尖从 8fddeb76 之后又动了 5 笔（0391 第 2 步 / 0382 r4 / 0390 / run-strip e2e），0390 也动了 `V8Experience.tsx`，所以是你那几行挂载代码要重排，不是范围变大

## Q2 · 给 0383 车道（4033270f）· ORD-0383 切片 1 再 rebase + 一条 schema 前置问题
- 现状：`review/ORD-0383-slice1-deleted-at` 头 `c57bd95bf42c01dc84ed207d797a7fa75dda80aa`（16:24）
- 我的尺实测：`backend/app/main.py` 与 `contracts/openapi.yaml` 两格合不出车道自己的字节 ⇒ 退回 rebase（0389 刚落了 `X-Demo-Reset-Token`，两份文件都被它动过）
- 权威尖逐字：`1f8d7061f9edd66652c198db983722cdd237f2b7`
- 落地前我要一个读数（不用改代码就能答）：`journeys.deleted_at` 这列在**已存在的 SQLite 库**上是怎么出现的？共享预览库 `D:/moodle/_qoder_preview_20260920/_preview.db` 不是新建的，`create_all` 不会给旧表加列。请给我：①迁移语句或启动期的 `ALTER TABLE` 具名位置（`path:line`），②在没有该列的库上起新后端时，读列表那条 SQL 的实际状态码与错误原文，③你验过的那枚库的路径与 `PRAGMA table_info(journeys)` 的原始列名清单。答完这三格我就能同时判"落"与"换"。

## Q3 · 环境（不是车道的事，等用户回来）
- 手机面 hop4 断：本机 `getaddrinfo failed` 解析不了 trycloudflare 隧道域名，且 7892 / 7897 / 9097 三个口全无人监听（Clash/mihomo 未运行）。
- 部署尺因此拒绝切换， served 前端仍停在 `cf0ed0b531681181642a30120a1b41f2bf681a40`；新构建 `_build_1f8d706`（`index-BuFUA540.js`）只在私有导出里验过字节。
- 需要用户做的二选一：把 Clash/mihomo 起回来（隧道就能重连/换新地址），或允许我把手机直接连到本机 `:4781` 的局域网地址。在此之前，今天落地的 5 张里用户能在手机上看到的只有后端那半条（`:8693` 已换新树，且 `demo/reset` 的令牌门我已亲测拒得下来、场景字节未变）。
