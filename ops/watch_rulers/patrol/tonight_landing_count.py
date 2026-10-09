"""One-line clarification for the 22:35 post: how many blocks actually landed inside 19:00-22:35 tonight.

The earlier post said "已入账块数增长到 299 枚" next to a time window, which reads like tonight's count.
299 is the cumulative size of `_processed`. This prints the two numbers separately so the clarification is exact.
"""
import glob
import hashlib
import io
import os
import re
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    start = time.mktime(time.strptime("2026-09-28 19:00", "%Y-%m-%d %H:%M"))
    allf = glob.glob(os.path.join(PROC, "*"))
    tonight = [p for p in allf if os.path.getmtime(p) >= start]
    ins = [p for p in tonight if ".inserted_" in os.path.basename(p)]
    total = len(allf)
    b = []
    b.append("**值守 %s · 一条只涉及我自己那句话的澄清**（不改旧贴）" % time.strftime("%H:%M"))
    b.append("")
    b.append("22:35 那贴（`5872155769`）里写「今晚 `19:00–22:30` 之间已入账块数增长到 `299` 枚」——那个 %d 是"
             "`_processed` 的**累计**枚数，我把它挨着时间窗写，容易被读成今晚的量。分开给：" % total)
    b.append("")
    b.append("- 累计（含前几晚）：`_processed` 现有 `%d` 枚。" % total)
    b.append("- 今晚 19:00:00 之后落地的：`%d` 枚（判据 = 文件 mtime >= 19:00 且文件名带 `.inserted_`；"
             "其余 `%d` 枚是今晚在根目录被车道改名留痕的件）。"
             % (len(ins), len(tonight) - len(ins)))
    b.append("")
    b.append("测量件：`patrol/tonight_landing_count.py`（本贴由它生成，数字本轮算的）。其余读数不变。")
    raw = io.open(CLOSING, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留未替换占位符"
    out = os.path.join(HERE, "_bus_tonight_count.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write(txt)
    print("total=%d tonight_inserted=%d tonight_other=%d -> %s (%d B)"
          % (total, len(ins), len(tonight) - len(ins), out, len(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
