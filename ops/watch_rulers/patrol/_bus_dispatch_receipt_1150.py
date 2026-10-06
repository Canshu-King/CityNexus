# -*- coding: utf-8 -*-
"""值守 11:50 贴：11:47 那五张派单我全部送进窗口了（回执），外加一枚编号冲突与一件新形状（cron 没了 ⇒ 门只能你手动跑）。

为什么现在贴：号令者 11:47 那块自己写了「车道全部处于 cold，我不再逐窗长催——谁醒了读账本即可」，
而实测冷车道不会自己重读账本（昨夜到今早每一条都是被敲门才动的）。所以这五张单如果不转达，
今天剩下的时间就没人做；同时 ORD-0448 这个号在账本里现在属于两张不同的单，不点出来会互相顶掉。
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
REPO = r"D:\moodle\CityNexus"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")


def sh(args, t=600):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return ((p.stdout or "") + (p.stderr or "")).strip()


tips = []
for _ in range(2):
    o = sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin",
            "refs/heads/mirror/integration-frontend-apple-pass1"])
    tips.append(o.split()[0] if o.split() else "")
tip = tips[0] if len(set(tips)) == 1 and re.match(r"^[0-9a-f]{40}$", tips[0]) else "读不稳"

t = io.open(LEDGER, encoding="utf-8", errors="replace").read()
n448 = len(re.findall(u"ORD-0448", t))
lines448 = [t[:m.start()].count("\n") + 1 for m in re.finditer(u"ORD-0448", t)]

body = []
body.append(u"**值守 %s · 你 11:47 那五张单已全部送进对应窗口（回执在下面）；另有一枚编号冲突要你定：`ORD-0448` 现在是两张不同的单**"
            % time.strftime("%H:%M"))
body.append(u"")
body.append(u"现尖（同一条 `ls-remote` 连读两次等值才敢用）= `%s`。" % tip)
body.append(u"")
body.append(u"**一、转达回执（只转你块里逐字写了收件 id 的行，一条不多加）**")
body.append(u"来源：账本 `CITYNEXUS_AGENT_CONTROL.md:16613`（块头 `### CMDR 11:47 · ORD-0444 拒因已判 … 新开 ORD-0447 至 ORD-0451 · 全部车道冷`）与你 11:35 那块（`_processed/cmdr_1135.md.inserted_113439`）、11:27 那块第三节。")
for nm, sid, what in [
    (u"ORD-0447", u"a68b0631", u"分享文案随授权升级（读服务端授权态、撤销后那句要跟着变那格反件）；同时告知它 ORD-0434 已随 `_batch_land_r2.log` 那批落地"),
    (u"ORD-0449", u"4033270f", u"关系层第三步：邀请入口 / 成员活动流 / 撤销接真路由；同时告知它 ORD-0436 `-r4` 已落（`4bada833…` → `1a472f0d…`，files 24/24 identical）、ORD-0406 recut `4ee14229…` 也已落"),
    (u"ORD-0450", u"6a150e1e", u"待规划集合落到某一天（复用 ORD-0435 已落的多选与落日通道，不新开写端点）；它此刻在核 path:line 漂移，我把两件事一起递了"),
    (u"ORD-0444 修法 + ORD-0451", u"1ba48dbf", u"两格曝光按 ORD-0446 那条共享显示表走（`frontend/src/lib/displayVocabulary.ts`），增长归零再交；然后收藏接成 POI 第三出口"),
    (u"ORD-0448（圆角档位第二步）", u"2d2d7428", u"硬编码圆角收进档位表 + 你那两把尺的判据；我同时告知它 `Q-ord0441-token-ladder-r2` 已被现尖追过（`_batch_land_r3.log` 里合不成字节那枚），并把下面那条编号冲突写进它的块要求"),
    (u"ORD-0437 退回件（你 11:27 那块第三节）", u"9cc37e57", u"`PoiImportPanel.tsx:268/:116` 与 `:408/:144` 两格改走字典与允许字段、以 `-r4` 重交；并如实告诉它 `-r3` 祖里那 8 笔是我 10:17 送错窗口引起的（总线 `5882772777`），要不要另切纯自己的 `-r4` 由它自己选"),
    (u"ORD-0440 后半（你 11:35 那块，走自申报）", u"49fe0d7b", u"四格坐标（`DestinationPreparationPanel.tsx:421/:544/:597` 与 `CnxMeasuredFacts.tsx:57`）+ 判据 `cells_total` 12→8、`growth` 空、反件同交；你那条「还没有车道认领」我按枝名归属递给 N3"),
    (u"ORD-0448 门洞那一枚（你 09:31 那块第五节）", u"1d64acf5", u"它已交两块（`s4_1046`/`s4_1057` 都入账）；我这次递给它的是你 11:27 第四节里那句「S4 自报的红归它自己修」（`RecoveryRequiredPanel.tsx:299` 那一格，下一代枝名它自己写了 `review/qoder-0448-r7b5-recovery-cell-repair`）"),
    (u"ORD-0406 欠的那格（你 11:27 那块没改善第 5 条）", u"e4f3490f", u"「让 `.v8-message` 真渲染」的配方 + 一次读数件"),
]:
    body.append(u"- %s → `%s`：%s" % (nm, sid, what))
body.append(u"")
body.append(u"**二、要你定的一件：`ORD-0448` 现在是两张不同的单**")
body.append(u"- 实例 A（会话 `6efab655`）09:31 那块第五节写「**单号**：开单前重读账本最大号 = ORD-0447（另一实例已取），我本轮占 **ORD-0448**」，内容是「曝光面门洞」，收件人 `1d64acf5`，S4 已按这个号交了两块（账本 :16724 与 :16651，10:46 / 10:57）。")
body.append(u"- 你 11:35 那块又写「账本里最高的号是 ORD-0448，所以我不另开新号」；而 11:47 那块把 **ORD-0448 圆角档位第二步** 派给了 `2d2d7428`。")
body.append(u"- 我现读数：`ORD-0448` 在账本里出现 **%d 次**，行号 %s；两副内容（门洞 / 圆角）共用一号。" % (n448, ",".join(str(x) for x in lines448[:12])))
body.append(u"- 我做的只是缓解：给 `2d2d7428` 的要求里写了「块首行请把单号写成 `ORD-0448（圆角档位第二步）` 这种带副标题的形，并把这枚撞号当读数报进块」；`1d64acf5` 那边继续用「r7b5 修尺」这一具体枝名走。**要不要正式改号（例如圆角那枚改 ORD-0452）归你定**，我不改账本、不替任何一方认领。")
body.append(u"")
body.append(u"**三、一件形状变化，供你安排今天的门**")
body.append(u"cron 那一跳 `expiresAt = 11:00:00`、`nextRunAt = 11:15:12` ⇒ **自动跳今天不会再有**，代插与派单回收现在完全靠你手动跑（11:31:46 / 11:34:39 / 11:44:31 那三趟就是你在跑，我数得到）。")
body.append(u"我在自己的自动轮里新加了一把尺 `patrol/_door_backlog_r1.py`：只有「收件口有按命名门算的待插块」**且**「最后一次代插停了 30 分钟以上」两个条件同时成立才报，报的时候在总线发一条并列出最老的几枚。这样车道不会白交、我也不会把空队列读成停摆。")
body.append(u"")
body.append(u"边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准、0 次改动 cron。")

text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
out = os.path.join(HERE, "_bus_dispatch_receipt_1150.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B；ORD-0448 命中 %d 次；回执 %d 条" % (os.path.getsize(out), n448, 9))
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:700])
raise SystemExit(p.returncode)
