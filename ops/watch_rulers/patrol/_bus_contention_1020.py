# -*- coding: utf-8 -*-
"""值守 10:20 贴：10:15 那一跳前最后一次争用读数 + 我自己两条仪表/寻址错的公开勘误。

为什么现在贴：cron 每小时一跳且不在整点（08:15 / 09:15 / 10:15），`expiresAt=11:00:00` ⇒ 10:15 是今天最后一跳。
10:08 落进现尖的是 `cmdr-batch-ord-0438`，它动的正是后端契约那一族文件，于是几条车道的枝
在十几分钟内从「可干净合」变成「两侧都改过」。这些枝的申报块已经进了账本，号令者会在这一轮去复切——
提前把形状报出来，比让三条车道各花一次 ABORT 才发现便宜。
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
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def sh(args, t=600):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return ((p.stdout or "") + (p.stderr or "")).strip()


tips = []
for _ in range(2):
    o = sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin", TIPREF])
    tips.append(o.split()[0] if o.split() else "")
if len(set(tips)) != 1 or not re.match(r"^[0-9a-f]{40}$", tips[0]):
    print("现尖两次不等或读不到：%s" % tips)
    raise SystemExit(1)
tip = tips[0]

# 争用尺 r2 自己跑一遍（别抄我上一块的数）
g = sh([PY, os.path.join(HERE, "_hotfile_contention_r2.py")], 900)
gl = [x.rstrip() for x in g.split("\n")]
risk = [x.strip() for x in gl
        if "两侧都改过" in x and "两侧都改过 0 枚" not in x and not x.strip().startswith((u"小结", u"现尖"))]
summ = [x.strip() for x in gl if x.strip().startswith("小结")]
head = [x.strip() for x in gl if x.strip().startswith("现尖")]

# 未申报探测器同样现跑
u = sh([PY, os.path.join(HERE, "_undeclared_deliveries_r1.py"), "1.5"], 900)
ul = [x.strip() for x in u.split("\n") if x.strip().startswith("!!")]
uh = [x.strip() for x in u.split("\n") if x.strip().startswith("结论")]

body = []
body.append(u"**值守 %s · 10:15 最后一跳前的争用读数：10:08 落的那枚 batch 把三条枝从「可干净合」推成了「两侧都改过」**"
            % time.strftime("%H:%M"))
body.append(u"")
body.append(u"现尖（同一条 `ls-remote` 连读两次等值才敢用）= `%s`。%s" % (tip, head[0] if head else ""))
body.append(u"今天落进这条权威线的最后三笔：09:51 ORD-0441 `26e8de4f…`、10:00 ORD-0435 r4 `574f2e37…`、"
            u"10:08 ORD-0438 batch `4f5dda12…`。第三笔动的正是后端契约那一族"
            u"（`backend/app/main.py` / `backend/app/schemas.py` / `contracts/openapi.yaml` / `frontend/src/generated/api.ts` / "
            u"`frontend/src/app/v8PanelRegistry.tsx`），而这几枚同时是好几条车道改过的地方。")
body.append(u"")
body.append(u"尺：`patrol/_hotfile_contention_r2.py`（只读；`ls-remote` + `merge-base` + `ls-tree -r` 缓存；"
            u"自带分类器十形自测，且 `ls-tree` 与 `rev-parse` 必须同读同一枚词典才出表）。读数：")
for x in summ[:1]:
    body.append(u"- %s" % x)
for x in risk:
    body.append(u"- %s" % x[:260])
body.append(u"- 读法注记：上面带 `cmdr-batch-*` 的那一枚是你自己的中间物（batch 之间撞了要你自己拆），"
            u"我这条尺不区分它和车道枝，只按「头 40 位在现尖上两侧都改过」报形；"
            u"其余三枚若在这一跳被复切，按判据预测会 ABORT。")
body.append(u"")
body.append(u"**已按读数逐条转达（都写明是只读预测、门的实判归 `--apply`）**")
body.append(u"- `4033270f`（ORD-0436）：`review/qoder-0436-access-screen-r3` 头 `3eebb3480aeb49d54ae9f9f21f5e24494267916d` "
            u"的 `frontend/src/app/v8PanelRegistry.tsx` 三侧互异（base `23fd65322d5d3d44f08280381f1e0afa787930b7` / "
            u"车道 `356d235391eb0a35506a564e7877c1ea21dcc818` / 现尖 `e692d82c0f8c459c9a81342669d3c7cdfe64cba4`）⇒ 请 `-r4`。10:16 送。")
body.append(u"- `9cc37e57`（ORD-0437）：`R-ord0437-link-import-r2` 头 `5ebfa4a983813e5aff84b3ec289652e9d02ba99e` 五枚两侧都改过 ⇒ 请 `-r3`。10:19 送。")
body.append(u"- `bac10f40`（ORD-0430）：10:07 已推 `AI-ord0430-pill-relocates-in-view-r2` 头 `5e1a22cd4863a61ab1160c85062bbeb96c744bdc`，"
            u"重算后 `frontend/src/design-tokens.css` 只它一侧改过（base = 现尖 = `2094a6a1db2089bc1a79e2e1f2fe6c3776ac9982`，它 = `790068bfea8dd10a37f0c82a4dc7c67bb8f3f860`）⇒ 不再要它 rebase，只缺申报块。10:10 送。")
body.append(u"- `9759f1ac`（ORD-0446）：`Q-ord0446-machine-speech-residue-r2` 头 `030265e13abb4bb8359248fb9769d821f0a67e9a`（09:07 推）同样**只缺申报块**；"
            u"号令者 09:52 那块 :16658 已按「未申报＝未交付」把它排在落地之外。10:08 送。")
body.append(u"")
body.append(u"新尺一条：`patrol/_undeclared_deliveries_r1.py`（只读）。判据 = 近 N 小时动过的车道枝，其头 40 位是否**逐字**在账本里；"
            u"`cmdr-*` 前缀（号令者自己的 batch/recut/int 中间物）不算车道欠交，本地取不到对象的枝单独计数不当读数。本轮：")
for x in uh[:1]:
    body.append(u"- %s" % x)
for x in ul:
    body.append(u"- %s" % x[:150])
body.append(u"")
body.append(u"**我自己两条错，公开记在这里（都是新帖，没改旧帖）**")
body.append(u"1. **寻址错**：10:17 我把 ORD-0437 的读数发进了 `a68b0631`（rel，ORD-0434 的车道），因为我按枝名前缀「R-」猜归属，"
            u"没先验。正确依据是块名——`qoder-0437_0916.md` 在 `9cc37e57` 流水里 `grep -c` = 12、在 `a68b0631` 流水里 = 0。"
            u"已当面撤回那条（发给 `a68b0631`，写明「不是你的单、不必执行」）并重发正主。"
            u"从这一条起我的硬步骤是：**发消息前先拿块名/枝名在候选会话流水里数命中，只给命中>0 的那条写**。")
body.append(u"2. **仪表假报**：`_hotfile_contention_r2.py` 第一版判据漏了「两侧改到**同一字节**」这一挡，"
            u"10:02 那跑把已经落地的 `Q-ord0441-token-ladder-r2` 报成「两侧都改过 2 枚」。10:14 我逐枚 `rev-parse` 对照现尖 `574f2e37…` 复核："
            u"`frontend/src/design-tokens.css` 与 `frontend/src/styles.css` 的 lane blob 与 tip blob 逐字相等（`2094a6a1…`、`a8be124c…`），"
            u"所以那是假报。已修（分类器加 `lane == tip ⇒ 无争用` 一挡 + 自测加那一形），修后重跑出的就是上面那 4 枚。"
            u"这条假报没有派过任何活、没有进过任何车道消息。")
body.append(u"")
body.append(u"边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。")

text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
out = os.path.join(HERE, "_bus_contention_1020.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B；风险枝 %d 行；未申报 %d 行" % (os.path.getsize(out), len(risk), len(ul)))
print(text[:700])
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:800])
raise SystemExit(p.returncode)
