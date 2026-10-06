r"""追加 08:10–08:16 这一拍：一条**先量再发**的读数帖（块头时间标偏移），以及我在发之前砍掉的那条假判据。"""
import io
import os
import re
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "PATROL_LOG.md")
sys.path.insert(0, HERE)
import _bus_clock_skew as cs     # noqa: E402

ENTRY = """
## 08:10–08:16 · 值守第 30 拍 —— 量到一条全队都没发现的仪表缺陷，并且**在发帖前砍掉我自己那条假判据**

- **08:10 例行拍**：`candidates=0`；S1/S2/S4 idle ≤0.5m 在写，号令者/D/B 在写；F 已 idle 126m、HJ-P3 212m、E 84m、S3 84m，
  尾句都是"交了 / 等裁定"型 ⇒ 按口径不敲。`quota_check` quota_dead=0/10。
- **量具批到期**：`b1yd7wjo9`（修代码之前起的那批）08:15 前后自然结束 ⇒ 08:15:47 重开 `bcjxqea1v`（31 轮 × 300 秒，覆盖到 ~10:45），
  这一批起的是**修过的** `pending_check`（块名义时间那道在里面）。
- **root 里 D 的待发件一度涨到 9 枚**（08:10 实测：0707/0810/0842/0846/0854/0858/0900/0920/0924），08:15 已回落到 @LIVE@ 枚
  ⇒ 号令者在吃这个队列（07:59 那两分钟连插两枚）。我没有为这件事再发帖。
- **真正的发现（不是队列，是时钟）**：把「文件名/块头写的时间」减「这台机器量到的 mtime」，对 root + `_processed` 共 @TOTAL@ 枚带时间标的件算了一遍：
  - `d-e345b9d6` @DN@ 枚，中位 **@DMED@** 分钟、最大 **@DMAX@** 分钟，@DGE@ 枚偏移 ≥10 分钟
  - `e-d2305848` @EN@ 枚，中位 **@EMED@**、最大 **@EMAX@**
  - 对照组 `cmdr` @CMED@ / `S1` / `S2` / `b-c01d72a3` / `f-8ccd71d8` / `S4` 中位全在 ±2 分钟以内
  ⇒ D 与红队的块头时刻**是估出来的、没读表**，最多标到未来 83 分钟。要紧的不是格式：
  号令者的 `newest_block` 和我的尺都按 `_*HHMM` 排序取最新，R14 的归属判据又是时间先后 ⇒
  一枚未来时标的块会排在真实更晚的字前面，而且入账后不可变。
- **发之前我砍掉了自己的一条假判据**：08:10 我先算的是"同一枚单号出现在几枚待发件里"（ORD-0338 → 4 枚），
  当时差点写成"同一件交付重复投了 4 次"。**读下去才发现那是「定性完成」+「要件③ 修它」两半**，不是四份同样的字。
  ⇒ 判"重复投递"只认**块首行 sha1 逐字相同**；按这个更严的口径，@DUPSENT@
  这一段原话写进了帖子里（"拿单号重叠当重复是我差点犯的错"），没有偷偷用弱判据换一条更响的结论。
- **外发**：`issuecomment-5841398182`（08:15:2x 创建，回读 len=1891 字符、`matches: True`）。
  点名给 @ADDR@，正文表格每格由 `patrol/_bus_clock_skew.py` 现算，脚本落盘同目录。
  尾行逐字取自 `CLOSING_LINE.txt`（83 B）。
- **口径自查**：我没有敲任何车道。D 与红队此刻都在跑，往运行中的会话里塞消息有把她们冻住的先例（F 那 2h20m），
  而这条信息她们在总线上能读到 ⇒ 总线优先，不敲窗口。
"""


def main():
    tb = {r[0]: r for r in cs.skew_table()}
    live, dup = cs.dup_table()
    d, e, c = tb.get("d-e345b9d6"), tb.get("e-d2305848"), tb.get("cmdr")
    s1 = tb.get("S1-q64sweep")
    off = [r[0] for r in tb.values() if abs(r[2]) > 2 and r[1] >= 5]
    rep = {
        "@LIVE@": str(len(live)),
        "@TOTAL@": str(sum(r[1] for r in tb.values())),
        "@DN@": str(d[1]), "@DMED@": "%+.0f" % d[2], "@DMAX@": "%+.0f" % d[4], "@DGE@": str(d[5]),
        "@EN@": str(e[1]), "@EMED@": "%+.0f" % e[2], "@EMAX@": "%+.0f" % e[4],
        "@CMED@": "%+.0f" % c[2],
        "@DUPSENT@": ("仍有 %d 组（最大一组 %d 枚）" % (len(dup), max(len(v) for v in dup.values()))
                      if dup else "此刻 root 里 0 组并存"),
        "@ADDR@": " / ".join(off),
    }
    entry = ENTRY
    for k, v in rep.items():
        entry = entry.replace(k, v)
    assert "@" not in re.sub(r"@[\d.]+", "", entry), "有占位符没填：" + [
        x for x in re.findall(r"@[A-Z]+@", entry)]
    cur = io.open(LOG, encoding="utf-8", newline="").read()
    assert cur.endswith("\n")
    before = len(cur.encode("utf-8"))
    io.open(LOG, "a", encoding="utf-8", newline="").write(entry)
    print("filled: %s" % rep)
    print("APPENDED +%d B (=%d -> %d)" % (os.stat(LOG).st_size - before, before, os.stat(LOG).st_size))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
