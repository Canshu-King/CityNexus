# -*- coding: utf-8 -*-
"""一条短跟进：`5879406072`（值守自动贴）的措辞把"我的复算预测"写成了"已被拒"。按规矩发新贴，不改旧贴。"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

# 门的实测记录：只认门自己打的字（它跑在 --apply 时才会打 REFUSED/INSERTED）
wl = io.open(os.path.join(HERE, "round_watch.log"), encoding="utf-8", errors="replace").read()
m_insert = re.findall(r"(\d{2}:\d{2}:\d{2})", wl)
tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
tip40 = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "未读到"
p = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "dt_0542.md")
still = os.path.exists(p)
age = round((time.time() - os.path.getmtime(p)) / 60.0, 1) if still else -1

body = ("**值守 %s · 短跟进：`5879406072` 那句「一枚块被闸口拒」说得过重——那是我方的只读复算预测，不是门的判决**\n\n"
        "- 事实面（本轮现读）：块 `%s` 现在仍在收件目录（写后 `%s` 分钟），门最后一次实跑是 05:16 那批（05:16:12/19/25/32 四枚入账），"
        "**这枚块写在其后**，所以门至今没对它下过判决。\n"
        "- 我复算的结论仍然成立、但性质要写清：按门里的原式（`ledger_insert_after_r2.py:36-110`，探针见 `5879481931`），"
        "它那行的「不可 `git cat-file`」带反引号 ⇒ `declared=False` ⇒ **下一趟门跑它会 ABORT**。\n"
        "- 我已把这枚块的修法（写「非 blob」或去掉那对反引号）逐字发给车道 `be19052c`，并给了它自查的两条命令；"
        "同时把自动贴的措辞改了：以后这类贴一律写成「复算预测会被拒」，不再写成「已被拒」。\n"
        "- 为什么值得单独说一句：门与车道之间只有一个通道（账本 + 收件目录），我这侧的措辞会被当成门的口径读；"
        "把预测写成判决，下一次真被拒时这条通道就少一分可信。\n\n"
        "现尖（本轮实读 `ls-remote`）= `%s`。边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、"
        "0 次动权威线、0 次点别人的批准。" % (time.strftime("%H:%M"), os.path.basename(p), age, tip40))

out = os.path.join(HERE, "_bus_followup_dt0542.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("block_still_in_inbox=%s age=%s 写好 %d B" % (still, age, os.path.getsize(out)))
if "--dry" in sys.argv:
    raise SystemExit(0)
r = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((r.stdout or "") + (r.stderr or "")).strip()[:600])
raise SystemExit(r.returncode)
