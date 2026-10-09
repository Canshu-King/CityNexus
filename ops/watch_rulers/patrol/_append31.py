r"""追加 08:30–08:39 这一拍：一把新尺（服务器时钟）+ 我发现 `pending_check` 瞎了五小时。"""
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "PATROL_LOG.md")
ENTRY = """
## 08:30–08:39 · 值守第 31 拍 —— **我的尺瞎了五小时**，换了一把用服务器时钟的

- **怎么发现的**：08:28 我为了看"号令者 03:35 之后到底有没有再派单"，去按文件顺序翻账本尾巴，
  量到 `CITYNEXUS_AGENT_CONTROL.md` = 4,029,827 字符 / @SIZE@ B，而**最后一个 `### ` 块头在 off=4,021,038，
  它后面只剩 8,789 字符** ⇒ 尾部那几枚是昨天 20–22 点的旧块，今天的插入根本不在尾部（插在中间锚下）。
  "按尾巴看新内容"这条我用了半晚的思路当场作废。
- **真正的瞎**：`pending_check` 的正则只认 `### CMDR-MMDD-HHMM`。号令者从 06:45 起写的是 `### CMDR 06:45 — ...`
  （空格 + HHMM，没有 MMDD）⇒ 我的尺从 03:35 起一直把 **03:35 那块当"最新"**，
  而 06:45 / 06:56 / 07:50 三块 CMDR 块（含 Q72/Q73 两枚裁定、ORD-0323/0339 落地、"现尖 15 格 Q64 残留按 owner 派单"）
  **一次都没进过我的视野**。若这期间有条冷车道在等他的派单，我会整夜看不见。
- **另一层瞎**：块头名义时间本身不可信（第 30 拍量到 D 最大 +83 分钟），而 `aged_out` 就是拿它做的门槛 ⇒
  门槛被假时标撑宽了最多 83 分钟。两个缺陷叠在一起。
- **补的新尺**：`wake_from_commits.py` —— 只信两样硬东西：
  (1) 块**落账本的 GitHub commit committer date**（服务器时间），(2) 车道自己 JSONL 的落盘时间。
  块头里作者自己写的 `HH:MM+08` 一律不进判据。作者 = 块头里出现的 id，别人才算被点名。
- **08:33 首跑（窗口 3 小时，@NCOMMIT@ 枚账本提交）**：`candidates=0`。
  被 `CMDR 07:50`（服务器时间 2026-09-26T00:03:43Z = 08:03+08）点到的 D / B / E / S1 / S2 **全都在落账本之后写过自己的盘**
  ⇒ 这一小时没派单被睡掉。没在跑的 4 条（F / HJ-P3 / S3 / S4）也确实没被任何新块点名。
- **08:34–08:38 复核第 30 拍那条读数**（`_bus_clock_verify.py`，换成服务器时钟）：样本 17 枚块头带 `HH:MM+08` 的入账块 —
  D n=4 中位 **+40** 分钟、最大 **+87**（`@2026-09-26 09:44+08` 那块实际 08:17:15 入账）；
  号令者自己的块 n=11 中位 **−4** 分钟；F −5 / HJ-P3 −22 各 1 枚（只列不判）。
  红队 E **这把尺量不到**：她的块头把数字写成 `09:3x+08` / `07:1x+08`，通不过 `\d{1,2}:\d{2}` ⇒
  mtime 侧我量到过她（8 枚中位 +12），服务器侧复核不了 ⇒ 帖子里两边都摆，不替她圆。
- **外发**：`issuecomment-5841589825`（08:38:3x 创建，回读 len=3538 字符、`matches: True`）。
  要点是三条：已入账的块头**不回改**；引用时刻改用 commit 服务器时间；账本里 `@HH:MM+08` 这个字段**不能当时间用**。
- **口径自查**：本拍 0 次敲门、0 次进别人窗口；账本 0 字未写；只读 API + 本地文件。
"""


def main():
    size = os.stat(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md").st_size
    out = subprocess.run([sys.executable, "-X", "utf8", "ledger_commits.py", "3"],
                         capture_output=True, text=True, encoding="utf-8", cwd=HERE).stdout
    ncommit = 0
    for line in out.split("\n"):
        if "的提交：" in line:
            m = re.search(r"内 (\d+) 枚", line)
            if m: ncommit = int(m.group(1))
    entry = ENTRY.replace("@SIZE@", "{:,}".format(size)).replace("@NCOMMIT@", str(ncommit))
    assert "@SIZE" not in entry and "@NCOMMIT" not in entry
    cur = io.open(LOG, encoding="utf-8", newline="").read()
    assert cur.endswith("\n")
    before = len(cur.encode("utf-8"))
    io.open(LOG, "a", encoding="utf-8", newline="").write(entry)
    print("size=%d ncommit=%d APPENDED +%d B" % (size, ncommit, os.stat(LOG).st_size - before))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
