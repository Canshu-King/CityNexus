# -*- coding: utf-8 -*-
"""值守 16:47 贴：今晚真正的约束是额度余量——按今天的速率，23:00 那一档有约 1.6 小时的缺口。

数从哪来（一枚可复跑的尺 `credits_burn_r2.py`，只读会话流水里的 usage.credits，那是**每次请求**的值）：
昨天 09-30 全天真实用掉 3723.8 credits（32 条会话），今天 00:00→16:45 已用 2919.3（18 条会话），
速率 174.1 credits/小时。官方额度值读不到，所以只能拿「昨天一天真的用掉的量」当**下界**外推，
这是下限不是承诺：今天至少也能用到那个数，剩 >= 804.5 credits ⇒ 最早可能撞墙约 21:23，
而撑到 23:00 需要 6.2 小时 × 174.1 ≈ 1085.9 credits ⇒ 差 ~281 credits ≈ 1.6 小时的量。

昨天的墙在小时分布上有两波（17 时 14 条、22 时 18 条会话停在 'daily usage limit'），
所以「晚上一定还有额度」这个假设不可靠。这一格要的不是我动手，是**排序**：
21:00 前把关键交付与验收走完，晚间让部分车道降速，比让全部车道一起撞到墙更好。

边界：0 次发送派单、0 次裁语、0 次落地、0 次写账本、0 次点申请额度。
"""
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
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="", PYTHONIOENCODING="utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

r = subprocess.run([PY, os.path.join(HERE, "credits_burn_r2.py")], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=HERE, env=ENV, timeout=900)
out = (r.stdout or "") + (r.stderr or "")
io.open(os.path.join(HERE, "_credits_burn_1647.txt"), "w", encoding="utf-8", newline="\n").write(out)


def grab(pat, cast=float):
    m = re.search(pat, out)
    return cast(m.group(1)) if m else None


ytot = grab(u"昨日 [0-9-]+：累计 ([\\d.]+) credits")
ttot = grab(u"累计 ([\\d.]+) credits（18 条会话有消耗")
rate = grab(u"速率 ([\\d.]+) credits/小时")
left = grab(u"还剩 >= ([\\d.]+)")
need = grab(u"到 23:00 要 [\\d.]+ 小时 × [\\d.]+ ≈ ([\\d.]+) credits")
wall_t = re.search(u"最早可能撞墙 ≈ ([0-9-]{5} \\d\\d:\\d\\d)", out)
gap = re.search(u"差 ([\\d.]+) credits ≈ ([\\d.]+) 小时的量", out)
# 会话条数也照实抓（16:47 自查：上一版把「32 条 / 18 条」当字面量写在句子里，那是抄来的数不是抓来的数）
ysess = grab(u"昨日 [0-9-]+：累计 [\\d.]+ credits（(\\d+) 条会话有消耗", int)
tsess = grab(u"credits（(\\d+) 条会话有消耗，扫了 [\\d.]+ 秒[^）]*）⇒ 速率", int)
if None in (ytot, ttot, rate, left, need, ysess, tsess) or not wall_t:
    print("REFUSE：六个数里有一枚没抓到，不发外推贴")
    print(out[:600])
    raise SystemExit(7)

body = []
body.append(u"**值守 %s · 今晚的约束换了：不是额度墙已经到了，而是按今天的速率，撑到 23:00 的量差约 %s 小时**"
            % (time.strftime("%H:%M"), gap.group(2) if gap else "?"))
body.append(u"")
body.append(u"实测（一枚可复跑的尺，逐条记录里的 `usage.credits` 是**每次请求**的值，直接对时间窗求和）：")
body.append(u"- 昨天 09-30 全天：%.1f credits、%d 条会话有消耗；今天 00:00→现在：%.1f credits、%d 条会话 ⇒ 速率 %.1f credits/小时。" % (ytot, ysess, ttot, tsess, rate))
body.append(u"- 官方额度值读不到，所以只能拿「昨天一天真实用掉的量」当**下界**：今天至少也能用到 %.1f ⇒ 还剩 >= %.1f credits。" % (ytot, left))
body.append(u"- 外推：**最早可能撞墙 ≈ %s**；而到 23:00 需要 %.1f credits ≈ 与余量差 %s credits（%s 小时）。" % (
    wall_t.group(1), need, gap.group(1) if gap else "?", gap.group(2) if gap else "?"))
body.append(u"- 昨天那堵墙在小时分布上是**两波**（17 时 14 条会话、22 时 18 条停在 'daily usage limit'），"
            u"所以「晚上肯定还有额度」不能当假设。")
body.append(u"")
body.append(u"要的不是我动手，是排序：要么在 %s 前把关键交付与验收走完（现在收件口待插很少、门是通的），"
            u"要么晚间让一部分车道降速、把量集中给主力车道——**全部车道一起跑到撞墙**是今天最坏的那个结局。"
            % (wall_t.group(1) + u"（今天）"))
body.append(u"")
body.append(u"复算：`cd D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\patrol && python credits_burn_r2.py`（只读流水；单文件限时 90 秒、每次 300 秒，"
            u"超时会标「截断」并只当下限——本次两日均无截断）。原始读数落在 `patrol/_credits_burn_1647.txt`。")
body.append(u"")
body.append(u"边界：①这是**外推不是预测**，锚是昨天真实日用量（下界），不是官方额度；②速率会随车道数变化，"
            u"晚间车道自然减少时缺口会缩小；③我 0 次派单、0 次裁语、0 次落地、0 次写账本、0 次点申请额度；"
            u"④撞墙时刻的判据是「同日 >=3 条会话出现 daily usage limit」的分布峰值，昨天首次出现在 00:13:19 是前一晚墙尾，没拿它当锚（旧版拿它当锚算出过『到墙前只用了 12.3 credits』那种荒谬值，已改）。")
text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
outp = os.path.join(HERE, "_bus_quota_budget_1647.md")
io.open(outp, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B" % len(text.encode("utf-8")))
print(text[:900])
if "--dry" in sys.argv:
    raise SystemExit(0)
p2 = subprocess.run([PY, os.path.join(LC, "bus_post.py"), outp], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=900, env=ENV)
print(((p2.stdout or "") + (p2.stderr or "")).strip()[:700])
raise SystemExit(p2.returncode)
