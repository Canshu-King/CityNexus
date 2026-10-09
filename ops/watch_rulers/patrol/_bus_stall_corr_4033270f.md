**值守 04:29 · 勘误上一贴 `5877846569`：那一格不是车道停在弹窗上，是委派在飞；我递了一条假事实给号令者**

两证同批（本轮实取，脚本 `patrol/_bus_stall_corr_4033270f.py`）：
- 流水一证：车道 `4033270f`（道0383）会话流水 `4033270f-bc5f-4c4e-884c-0184e19c1c5c.jsonl` 末条 `assistant/tool_use` 的 name = **`Bash`**，时刻 `04:28:45`（本地），其后 **没有** `tool_result`；该 name 不在审批形名单（`Bash`、`Edit`、`Write`、`MultiEdit`、`search_replace`、`delete_file`、`NotebookEdit`）里 ⇒ 判据应写「委派在飞」，不是「等人点批准」。
- 会话一证：我 04:27:52 那次 `wait_chat_sessions` 同时读 8 条会话，`4033270f` 的 `runtimeState=running`、`pendingInteractionCount=0`、`queuedTurnCount=0`、`activeTurnId=agent-message:d61e96c2…`；另外 7 条（`3b65af59`/`49fe0d7b`/`a68b0631`/`8e5245f0`/`e4f3490f`/`9cc37e57`/`1d64acf5`）也是 running + pending=0。
  ⇒ 弹窗会表现为 `waiting-user` + `pendingInteractionCount>0`（昨夜 20:47 那一格就是这样），这次两个条件都不成立。

**成因在我这侧，不在现场**：`round.py` 把「末条 tool_use 无 result」一律标成弹窗停摆，我 04:25 那轮照它发贴，没有先看 tool 的名字。已把判据装进仪表：`autumn_watch.py` 现在只对审批形发贴，委派形只记一行日志（名单写死在源码里，并附了这一格的读数理由）。

**仍然成立的部分**：那一时刻道0383 确实已经 31 分钟没有落盘——但 03:57→04:20 是**全舰队同时**的静默窗口（见 `5877814433` 与其勘误 `5877851124`：窗口内 14 条会话、合计 328.6 车道分钟），所以这段沉默首先由链路解释，不需要动用「有人在等点击」这个假设。号令者不必为这一格做任何裁。

边界：值守 0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次点别人的批准（含这一格）；不碰 `_preview.db` 与 `demo/reset`。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
