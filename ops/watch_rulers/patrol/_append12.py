import io
txt = r"""
- 值守拍 23:15 +08（42d1a6fa）**协调链换了形状，我跟着换了一把尺：账本收件箱积压哨兵 `inbox_check.py`**。
  - 23:07 起 **LEDGER_SINGLE_WRITER_V1**（仲裁 Q63=③ 落地）：车道**不再直接写账本**，改成把块丢进 `D:\moodle\_qoder_ledger_inbox\<lane>_<HHMM>.md`（首行 `### `），由号令者跑 `ledger_inbox_apply_r1.py --apply` 代插，他自己承诺 **≤15 分钟一轮**。
  - 这条改动的副作用对值守是新的：**协调链出现了一个单点瓶颈**。号令者一旦睡着/卡住，车道的交付就永远进不了账本，而**从车道那一侧看一切正常**（它们照常落盘、照常发帖）——我原来那套"看会话有没有在写字"完全看不见这种停摆。
  - 所以新尺判据 = 根目录里存在 mtime 早于 20 分钟的 `.md` ⇒ `INBOX_BACKLOG`（已处理件会被改名成 `*.inserted_*` 移进 `_processed`，所以只数根目录，不会把已插的算成积压）。`--selftest` 三向：正控（一枚 60 分钟前的块 ⇒ 必须报）+ 两反控（只有新鲜块 ⇒ 不报；空箱 ⇒ IDLE 不报）⇒ **selftest PASS (3/3)**。
  - 23:14:20 首跑：`inbox root=0 待处理, _processed=1, 状态=IDLE`。而且**第一次往返已经被我抓到**：E 的 `e-d2305848_2345.md` 23:10 落进箱，号令者 23:13:29 代插并改名成 `…inserted_231329` ⇒ 实测延迟 3 分 29 秒，远低于他自己那 15 分钟。这条链现在是通的。
  - 挂进 `qoder_watch.py`：每轮跑一次 `inbox_check`，只在真有积压时往日志加行（空箱不加噪声）。批次改成 12 轮 × 5 分钟 = 1 小时（当前批 `b26b3jqzi` 到 00:16）。
  - 同拍读数：六条 idle 全在 5.1 分钟内（包工头 0.2 / F 0.2 / HJ-P3 0.2 / D 0.2 / B 5.1 / E 3.0）；账本远端 6,003,976 B @commit `016a5027d8`（23:14），比 22:58 的 5,993,833 只增。`pending_check` 的 `candidates=0`（E 那格已她自己醒来接上）。
"""
with io.open("PATROL_LOG.md","a",encoding="utf-8",newline="\n") as f: f.write(txt)
print("ok")
