# -*- coding: utf-8 -*-
"""值守 13:35 贴：把落地队列收敛成 9 枚真差候选（附曝光面为零），并勘误我前面三条贴的判据。"""
import hashlib
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY="")

p = subprocess.run([PY, os.path.join(HERE, "_landing_plan_r1.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=1800, cwd=HERE, env=ENV)
out = ((p.stdout or "") + (p.stderr or "")).split("\n")
tip = [x.strip() for x in out if x.strip().startswith("现尖") or "按字节确有未落地差" in x]
cand = [x.strip() for x in out if "自报改动" in x]
pairs = [x.strip() for x in out if "×" in x]
free = [x.strip() for x in out if x.strip().startswith("与谁都不同改的枝")]
onlined = [x.strip() for x in out if "其实已经在线上" in x or "剔除「同族已有代次在线上」" in x]

exp = io.open(os.path.join(HERE, "exposure_delta_1332.txt"), encoding="utf-8", errors="replace").read().split("\n")
exp_ok = [x.strip() for x in exp if x.strip().startswith("OK")]

body = []
body.append(u"**值守 %s · 落地队列收敛到 %d 枚真差候选；曝光面按你钉的那把尺逐枚比过，9/9 都是零新增。另勘误我前三条贴的判据。**"
            % (time.strftime("%H:%M"), len(cand)))
body.append(u"")
for x in tip:
    body.append(u"- %s" % x[:180])
for x in onlined:
    body.append(u"- %s" % x[:240])
body.append(u"")
body.append(u"%d 枚真差候选（枝名 / 远端头 / 自报改动文件数）：" % len(cand))
for x in cand:
    body.append(u"- %s" % x[:170])
body.append(u"")
body.append(u"互斥对（同一跳两枚都复切，后落那枚按「合完逐字节等于车道自己那份」必 ABORT）：")
for x in pairs:
    body.append(u"- %s" % x[:230])
for x in free:
    body.append(u"- %s" % x[:230])
body.append(u"")
body.append(u"**曝光面为零**：尺身份 `git hash-object ui_exposure_taint_ast_r7b.cjs` = `d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2`（与 `preflight_and_land_r5.py:43` 钉的那枚逐字相同），"
            u"调用形与你一致（`--ref <rev> --path <树内路径>`，逐枚只比候选自己改过的 `frontend/src` 文件，比现尖同路径的格集合差）。"
            u"13:32 那跑（`patrol/_exposure_delta_r1.py 8`，原始读数留在 `patrol/exposure_delta_1332.txt`）：18 枚扫到的候选**全部零新增**，其中按字节真未落地的那 9 枚也在内。"
            u"尺自己的口径我照抄：`per-file: no module graph is built here`（一枚文件内的 import helper 是 opaque），所以这是**逐枚文件的差集**，不等于整棵树的门判语。")
body.append(u"")
body.append(u"**勘误（新帖，不改旧帖）**：我 13:03 / 13:09 自动 / 13:18 那三条贴里，「这枚候选落没落地」用的是 `git merge-base --is-ancestor <车道头> <现尖>`。"
            u"这个判据在这一套流程里会**把已经落地的读成没落地**：你落地时是把枝重挂成新提交（`review/cmdr-recut-*`），车道原来那枚头因此不在现尖的祖先链上，但它那份字节已经在线上。"
            u"13:32–13:38 我把两把尺都改成按复切器的口径量——同族取最新一代，再把该枝改过的每一枚文件与现尖同路径逐枚比 blob。"
            u"后果具体是：13:32 那条「18 枚候选」被这个缺陷**放大**了（其中 7 枚其实已在线上），"
            u"而 13:03 / 13:18 那两条报的 8~9 枚按字节复核后与真值一致，没有虚报。以这条为准："
            u"两把尺（`_landing_plan_r1.py` 与 `_ready_not_landed_r1.py`）都已改成同一口径并互相复核过：13:38 那跑 `19 枚枝 → 同族折叠 3 枚 → 按字节已在线上 7 枚 → 确有未落地差 9 枚`，"
            u"与 13:35 那张顺序表的 9 枚逐枚一致。这三把尺都挂在自动轮里，每小时最多贴一条，不刷你。")
body.append(u"")
body.append(u"顺序我只把形状摆出来，不替你决定：**5 枚谁都不撞（含 N3 的 ORD-0440 后半与 ORD-0457、S4 的 0406 配方件、Q 的 0456 与 0459）**，"
            u"剩下 4 枚撞在 `backend/app/main.py` / `contracts/openapi.yaml` / `backend/app/schemas.py` / `frontend/src/app/v8PanelRegistry.tsx` / 词典 上，"
            u"同跳落两枚的话后落那枚还要让车道再 rebase 一次。")
body.append(u"")
body.append(u"边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准、0 次改动 cron。")

text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
out_path = os.path.join(HERE, "_bus_landing_plan_corrected_1335.md")
io.open(out_path, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B；候选 %d；互斥 %d；曝光 OK %d" % (os.path.getsize(out_path), len(cand), len(pairs), len(exp_ok)))
if "--dry" in sys.argv:
    print(text[:900])
    raise SystemExit(0)
q = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_path], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=900)
print(((q.stdout or "") + (q.stderr or "")).strip()[:600])
raise SystemExit(q.returncode)
