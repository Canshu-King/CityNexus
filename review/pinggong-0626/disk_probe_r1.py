# -*- coding: utf-8 -*-
"""盘务那单的回读尺：把「我名下有什么、带不带 .git、注册在哪、两处盘读数、三枚枝的先人位」
一次落成读数件。全部只读：不搬、不删、不改任何人的工作树。"""
import ctypes
import datetime
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = "D:/moodle"
OUT = ROOT + "/_qoder_pinggong_0588/review/pinggong-0626/disk_and_worktree_probe.txt"
TREES = ["_qoder_pinggong_0555", "_qoder_pinggong_0555_dict", "_qoder_pinggong_0555_verify",
         "_qoder_pinggong_0555b", "_qoder_pinggong_0555c", "_qoder_pinggong_0557",
         "_qoder_pinggong_0557_dict", "_qoder_pinggong_0557_verify", "_qoder_pinggong_0558_ai",
         "_qoder_pinggong_0558_b", "_qoder_pinggong_0576", "_qoder_pinggong_0588",
         "_pinggong_scratch"]
TIP_ARG = sys.argv[1] if len(sys.argv) > 1 else None


def sh(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


# 权威尖从 GitHub 现取，不写死：写死了就会像上一版那样，枝一并尖读数就过期
TIP = TIP_ARG or sh(["git", "-C", ROOT + "/CityNexus", "ls-remote", "origin",
                     "refs/heads/mirror/integration-frontend-apple-pass1"]).stdout.split("\t")[0].strip()
if len(TIP) != 40:
    raise SystemExit("ABORT 现尖取不到：%r" % (TIP,))


rows = ["取值时刻 %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
# 两处独立量法：Windows API 与 MSYS df —— 同一件事两把尺，对不上就当场看见
for drive in ("D:\\", "E:\\"):
    free = ctypes.c_ulonglong()
    total = ctypes.c_ulonglong()
    avail = ctypes.c_ulonglong()
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(drive),
                                               ctypes.byref(free), ctypes.byref(total),
                                               ctypes.byref(avail))
    rows.append("winapi %s 可给本用户 %.1f GiB / 卷总 %.1f GiB"
                % (drive, free.value / 2.0 ** 30, total.value / 2.0 ** 30))
for line in sh(["df", "-h", "/d", "/e"]).stdout.splitlines():
    if line.startswith(("D:", "E:", "/")):
        rows.append("df %s" % line)
rows.append("")
rows.append("[一] 花名开头名下目录：共 %d 枚（含一枚无 .git 的仪表目录）" % len(TREES))
for name in TREES:
    path = os.path.join(ROOT, name)
    gitfile = os.path.join(path, ".git")
    kind, target = "无 .git", "-"
    if os.path.isdir(gitfile):
        kind, target = "目录 .git", "(独立仓)"
    elif os.path.isfile(gitfile):
        kind = "文件 .git"
        target = open(gitfile, encoding="utf-8", errors="replace").read().strip().replace("gitdir: ", "")
    stamp = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%m-%d %H:%M")
    rows.append("%-28s %-10s 目录时刻=%s 指向=%s" % (name, kind, stamp, target or "-"))

rows.append("")
rows.append("[二] 权威枝那侧 worktree 名册里，我名下几枚")
out = sh(["git", "-C", ROOT + "/_qoder_integration_20260919", "worktree", "list"]).stdout.splitlines()
mine = [l for l in out if "pinggong" in l]
rows.append("   名册总 %d 行，我名下 %d 行" % (len(out), len(mine)))
rows += ["   " + l for l in mine]

rows.append("")
rows.append("[三] CityNexus 那侧 worktree 名册里，我名下几枚")
out2 = sh(["git", "-C", ROOT + "/CityNexus", "worktree", "list"]).stdout.splitlines()
mine2 = [l for l in out2 if "pinggong" in l]
rows.append("   名册总 %d 行，我名下 %d 行" % (len(out2), len(mine2)))
rows += ["   " + l for l in mine2]

rows.append("")
rows.append("[四] 已发布枝相对现尖 %s 的「尖独有/枝独有」" % TIP[:12])
for b in ("review/pinggong-0607-r1", "review/pinggong-0610-r1", "review/pinggong-0620-r1",
            "review/pinggong-0626-r1"):
    r = sh(["git", "-C", ROOT + "/_qoder_integration_20260919", "rev-list", "--left-right",
            "--count", "%s...refs/heads/%s" % (TIP, b)])
    rows.append("   %-28s %s" % (b, (r.stdout or r.stderr).strip()))

rows.append("")
rows.append("[五] presence 那一面在最新尖上的两项现读")
listing = sh(["git", "-C", ROOT + "/_qoder_integration_20260919", "ls-tree", "--name-only",
              "%s:backend/app/execution" % TIP]).stdout.split()
rows.append("   backend/app/execution/ 现读 %d 枚：%s" % (len(listing), " ".join(sorted(listing))))
for path, needle in (("backend/app/db/models.py", "journey_member_id"),
                     ("backend/app/stay_mobility.py", "JourneyMember")):
    body = sh(["git", "-C", ROOT + "/_qoder_integration_20260919", "show", "%s:%s" % (TIP, path)]).stdout
    hits = [str(n) for n, line in enumerate(body.split("\n"), start=1) if needle in line]
    rows.append("   %s 里 %s 命中 %d 处%s" % (path, needle, len(hits),
                                            ("（行 " + ",".join(hits[:5]) + "）") if hits else ""))

with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    handle.write("\n".join(rows) + "\n")
print("\n".join(rows[:6]))
print("...共 %d 行，落 %s" % (len(rows), OUT))
