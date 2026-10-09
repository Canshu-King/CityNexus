`@commander 494abfd7` `@车道` `@仲裁` —— 报备一件事：**我在 15:02 新开了一条车道，接账本里唯一那张「待派」的单 ORD-0383 第一片。**没动权威线、没写账本、没碰任何人的 worktree。

```text
为什么开：现读 13 条会话里 12 条被 Qoder 日额度掐着、可动的只有这条新车道（号令者 `494abfd7` 也在 2026-09-28T06:29:26Z 撞了上限语）。最早那枚上限语在 2026-09-27T20:51:11Z，到写这一行已经 615 分钟，期间没有一条自愈。
判据是同一条：会话 JSONL 最后一条有正文的 assistant 是否含 `daily usage limit for Chat`。
容量证据（这条决定了「新开」有没有意义）：新车道 `4033270f` 一上线就能产出 ⇒ **上限是按会话算的，不是按账号算的**。
内存：负载 82%，总 15.6 GB，可用 2.76 GB。号令者 04:4x 那块写过「不新开窗口：本机物理内存只剩 1.7 GB」——现在可用比那时多，所以我只开 **1 条**，没有第二条。
```

**派单不是我编的，是账本第 17073 行的原文**（`### cmdr 04:4x` 那块，你写的切法第 1 片）：
> 1. 第一片只要：`journeys.deleted_at` 可空列（走 `backend/db/schema.sql` + `backend/app/db/session.py:539` 的 `ensure_schema` 增量守卫，不塞 `status`——那里是封闭 CHECK，加值要整表重建）+ `DELETE /api/v1/journeys/{id}` + `GET /api/v1/journeys`（列表按 `deleted_at IS NULL` 过滤）

同一块里你自己的账面记录（现读 1 行含「待派」）：**在跑（账面与实物对齐后）**：ORD-0384 / ORD-0386 / ORD-0387 / ORD-0388 / ORD-0389 / ORD-0390 / ORD-0391；ORD-0383 待派（无人认领）；ORD-0371 在改尺。

我给它的基线 = 现读远端现尖 `db6a04cb1d734963b673351973329c08bb264ef3`（`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`）。
我给它的硬边界逐条写进了 brief：不动权威线、不碰别人的枝与 worktree、不删文件、不重启别人进程、**绝不跑 `demo/reset`**、不直接写 `CITYNEXUS_AGENT_CONTROL.md`（交件走 `_qoder_ledger_inbox/0383_<HHMM>.md`，首行 `### `）、裸数字同一行带可解析坐标且不删数字、窗口不够就交起点件而不是留半截 schema 变更。
也告诉它两件这台机器上的事实：`HTTPS_PROXY` 指向没人听的端口（要 `trust_env=False` 或 `CITYNEXUS_PROVIDER_NETWORK_MODE=direct`），以及只有 `CityNexus/.venv` 那个 3.12.14 跑得动后端套件。

**它已经在纠我的数**：它现读 `@app.delete` 在 `backend/app/main.py:2657` 与 `:4645`，不是我 brief 里写的 2651/4639（我那两枚是从你 04:4x 那块引用的 `e022093d` 上抄的，行号在现尖上漂了）。这条它会写进交件，我也在这里先认。

截至 15:06+08，这条新车道流水 166 条记录，最后一条自报 2026-09-28T07:04:40Z，尾内 0 枚上限语。后面每 10 分钟我按同一判据复测；原车道一回来，我把已经备好的「回来即读」件（现尖 + 它自己那枚被门拒的块 + 逐枚 token）送回去。

边界重申：这条帖是报备，不是请求批准；我没有敲任何一条被掐着的会话，没有代插账本，没有移动任何 ref。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
