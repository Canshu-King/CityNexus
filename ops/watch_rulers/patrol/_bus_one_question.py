"""One single question for the user, replacing the two action-asks I posted earlier.

He is away, so nothing on the bus may ask him to click or approve. Both earlier notes
(`5871099076`, `5872155769`) contained "请点一下 / 请预先放行" wording. This is the single consolidated question;
the earlier posts stay as they are (corrections go as new posts, never edits).
"""
import hashlib
import io
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")


def main():
    rows = json.load(io.open(os.path.join(HERE, "prompt_stall_rows.json"), encoding="utf-8"))
    gated = rows["gated"]
    mins = round(sum(e["minutes"] for e in gated), 1)
    b = []
    b.append("**值守 %s · 今晚只留这一个问题给您，不需要您做任何点击**" % time.strftime("%H:%M"))
    b.append("")
    b.append("前面两条（`5871099076`、`5872155769`）里我写了「您醒来点一下」和「请预先放行删除」——那是要您动手的话，"
             "您不在电脑前，不该提。这两条以本贴为准，旧贴不改。")
    b.append("")
    b.append("问题只有一句：**车道在自己的临时导出目录里跑 `rm -rf`（突变测试要复制一份再删），要不要允许？**"
             "今晚这一类停摆 `%d` 次、吃掉 `%s` 分钟车道时间；解开的方式我看不见是谁做的，所以我也没法替您决定。"
             % (len(gated), mins))
    b.append("")
    b.append("答「允许」我就把这条转成给号令者的口径（它写进账本常设规矩）；答「不允许」我就照现在的做法继续——"
             "不点别人的弹窗、只把停摆量出来。没有第三种要您做的事。")
    b.append("")
    start = time.mktime(time.strptime("2026-09-28 19:00", "%Y-%m-%d %H:%M"))
    proc = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "_processed")
    allf = os.listdir(proc)
    tonight = [f for f in allf if ".inserted_" in f
               and os.path.getmtime(os.path.join(proc, f)) >= start]
    tip = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                          "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    sha = ((tip.stdout or "").split() or [""])[0]
    assert re.match(r"^[0-9a-f]{40}$", sha), "现尖没读到，不发帖"
    b.append("其余数字（本贴现算，不靠上一贴）：现尖 `%s`；`_processed` 累计 `%d` 枚，其中今晚 19:00 之后落地 `%d` 枚。"
             % (sha, len(allf), len(tonight)))
    raw = io.open(CLOSING, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留未替换占位符"
    out = os.path.join(HERE, "_bus_one_question.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write(txt)
    print("gated=%d mins=%s -> %s (%d B)" % (len(gated), mins, out, len(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
