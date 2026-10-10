r"""追加 09:12–09:30 两拍：F 的第二条判定不敲 + 两条车道被日额度掐死（含外发的停机通告）。"""
import io
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "PATROL_LOG.md")
ENTRY = """
## 09:12–09:30 · 值守第 33–34 拍 —— 一条真候选判成不敲，然后两条车道被账户额度掐死

- **09:12 拍**：`wake_from_commits` 报 `CMDR 09:10`（commit `7bc1b8c3`，服务器时间 09:08:36）点到 F、S2，F idle 27m。
  我把那块**逐行读了正文**（不是看块头）：里面是 ORD-0332 落地记功、Q76 裁定（折叠保持合着，**要改的是门**：
  读 span 前先点 `continuation-technical-toggle`，这条具名要件派给 D 的 ORD-0341）、ORD-0344-c 开给 S1、
  ORD-0340 被号令者的门拦下要求 S2 重切。**给 F 的只有记功，没有新单** ⇒ 判**不敲**，写进
  `wake_from_commits_state.json`（键 `7bc1b8c3|8ccd71d8`，理由随键存着）。S2 当时 idle 0m，本来就不用敲。
- **09:23 拍抓到今晚第一条真停机**：`quota_check` 报 `quota_dead=2/10` —— F `8ccd71d8` 与 S4 `1d64acf5`。
  两边都复核过才敢当真：(1) 最后一条 assistant 逐字是
  「You\\'ve reached your daily usage limit for Chat. Come back tomorrow to continue working with me.」；
  (2) 再量 20 秒，两条会话的 JSONL 字节增量都是 **+0**；(3) 两者最后落盘都在 09:23。
  ⇒ 不是"停下来等谁"，是**账户额度**，敲门无效、我也不能替她们做单。
- **停机对进度的实际影响**（现读账本，不引用谁的说法）：
  - F 的 ORD-0332 已落地（号令者 `CMDR 09:10` 那块记的，账本里 `ORD-0332` 出现 31 次、块头 5 枚），
    并且已随手机换代带上（`CMDR 09:25`：手机换到 `2d8b03b8…`，含 ORD-0332/0346/0344-b）⇒ **F 没欠单，损失是后续产能**。
  - S4 的 ORD-0346 候选 09:16:28 已入账（`_processed/S4-ast-taint_0912.md.inserted_091628`），
    但 ORD-0348（他 08:55 那块"两单"里的第二单：尺的详情面例外）在账本里**没有任何她的交付块头**（出现 5 次 / 块头 0 枚）
    ⇒ **这一单在她死掉时还开着**，今晚大概率没人交。
  - 恢复时间我**不预测**：昨夜同类掐死我量到 43~81 分钟自愈，但那句文案写的是 "Come back tomorrow" ⇒ 两种读数都摆出来。
- **外发停机通告**：`issuecomment-5841968280`（09:30:0x 创建，回读 len=1508 字符、`matches: True`），
  点名 `@commander` `@仲裁`，核心一句：**到 11:00 之前新单别派给 F / S4**。
  帖里每条数字都由 `_bus_quota_down.py` 现算（含 idle≤4 分钟的会话数与不在跑的那条）。
  发之前我修掉自己两处错话：一是"F 的活还没上手机"（`CMDR 09:25` 已经换代带上去了），
  二是"其余 8 条都在写"（S3 那时 idle 162m，不在写）——两处都是先量再改才发的。
- **09:2x 车队**：在写 7 条（号令者 / HJ-P3 / D / B / E / S1 / S2，idle ≤4m）；S3 162m（号令者明确"我还没派"）；
  F、S4 额度停机。`root` 待发 1 枚（`S1-q64sweep_0926.md`）；root 里作者自判废副本 30 枚（**不占队列**，别再当积压报）。
- 本两拍 0 次敲门、0 次进别人窗口、账本 0 字未写。
"""


def main():
    cur = io.open(LOG, encoding="utf-8", newline="").read()
    assert cur.endswith("\n")
    entry = ENTRY.replace("\\'", "'")
    before = len(cur.encode("utf-8"))
    io.open(LOG, "a", encoding="utf-8", newline="").write(entry)
    print("APPENDED +%d B (=%d -> %d)" % (os.stat(LOG).st_size - before, before, os.stat(LOG).st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
