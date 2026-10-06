import io
txt = r"""
- 值守拍 21:25 +08（42d1a6fa）**换上 sqlite 仪表，判据从"像不像在动"改成"有没有新回合"**。
  - 新工具 `codex_watch.py`（只读 `mode=ro`）：每条任务给 `最后一回合 status / 起于 / 止于 / 距今分钟 / 墙型`。判停口径 = **没有 inProgress 且超过 12 分钟没有新回合起**；`usageLimitExceeded` 标"额度墙(不自愈)"、`serverOverloaded` 标"容量墙(自愈)"。`watch_loop.py` 每 5 分钟把 `codex_watch + beat` 各一拍追加进 `watch_loop.log`，出现停摆就打 `ACTION_NEEDED`。
  - 21:23:18 基线：MissionA `inProgress`（21:17:55 起，真在写 `r77_search_identity.sqlite-wal`）；Harness `failed 21:19:04→21:19:20` 容量墙；连那条每 2 分钟自愈的心跳也在 21:22:09→21:23:14 吃了同一枚容量墙 ⇒ 21:19 之后上游容量又紧了，但**三条都在自愈窗口内，不需要敲**（敲了就是往正在重排的线程里塞字）。
  - Qoder 同拍：包工头 0.3m / D 0.0m / B 0.0m / HJ-P3 2.1m 在写；F 35m、E 10.6m 都是**交完单等验收**（F 交 ORD-0315、E 交 ORD-0314 派生 + A2 修形），按规矩不催。
  - 总线 20:08→21:22 十五条，包工头没有一处等我：Q61 已到（"不要再换手机代" ⇒ ORD-0310 记 LANDED/NOT-YET-DEPLOYED 是裁定不是漏部署；`:8000` 保持 NOT AVAILABLE 是**决定**）；他自己核出 B 的 ORD-0302 r2 与 D 的 ORD-0310 在 `PlanWithAiSheet.tsx` 有一枚真冲突（三方 blob 都点名了），并已让 B re-cut 到现读尖、自己不下场解冲突。**唯一等用户的是"两枚 key 在两层各换一次"**，这条仲裁排在优先级④、只能用户做，我已在他 21:22 那帖里读到，不需要我重复催。
"""
with io.open("PATROL_LOG.md","a",encoding="utf-8",newline="\n") as f: f.write(txt)
print("ok")
