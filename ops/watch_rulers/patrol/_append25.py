import io
txt = r"""
- 值守拍 06:48 +08（42d1a6fa）**S1 那一发候选判为"不敲"，并顺手废掉一个我本来会误用的字段**。
  - 06:43:50 `pending_check` 报 `WAKE_CANDIDATE S1(8e094dec) idle=19.7m`。我去读现场：她最后一条是 `[tool_use Bash]`（长命令期间会话本来就不落盘），而 `list_chat_sessions` 给她 `runtimeState=running`、`updatedAt` 折到本机时间 06:45:08 ⇒ **她在跑，不是停**。不敲。
  - **但同一次比对暴露出 `updatedAt` 不能用**：号令者 `494abfd7` 在 02:41 与 06:46 两次列会话里 `updatedAt` 是**同一个值** `1790363961274`，而他的 JSONL 从 153.2 MB 涨到 157.7 MB、mtime 06:45:41；更要命的是那个冻结值折出来是 **03:19**，比 02:41 那次观测还晚 38 分钟 ⇒ 这个字段既能滞后也能"超前"，**不能当新鲜度**。判活只用 JSONL mtime；`runtimeState` 只用来决定"这一发发消息安不安全"（`cold/ready` 安全，`running` 可能挂住调用方）。已写进记忆。
  - 06:47 车队：`idle>20min` 3 条（F 等回话、HJ-P3 等验收、S4 交完 `S4-ast-taint_0632.md` 后落回 cold）；D/B/号令者/S1/S2/S3/E 在写。`quota_dead=0/6`。收件箱 3 枚待发，最久 `d-e345b9d6_0605.md` 38.3 分钟 —— 但 D 自己在跑（idle 0.0m），没被挡住，按口径不发帖。
  - 巡检批 `b1yd7wjo9` 到 08:20。
"""
with io.open("PATROL_LOG.md","a",encoding="utf-8",newline="\n") as f: f.write(txt)
print("ok")
