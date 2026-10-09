# -*- coding: utf-8 -*-
"""值守 13:16 贴：现成的落地顺序表（谁与谁改同一枚文件且结果不同）。"""
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

p = subprocess.run([PY, os.path.join(HERE, "_landing_plan_r1.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=1200,
                   env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
out = ((p.stdout or "") + (p.stderr or "")).split("\n")
tip = [x for x in out if x.startswith("现尖")]
cand = [x.strip() for x in out if "自报改动" in x]
pairs = [x.strip() for x in out if "×" in x]
free = [x.strip() for x in out if x.startswith("与谁都不同改的枝")]
fam = [x.strip() for x in out if x.startswith(("最终候选", "剔除", "同族只取", "!! 块里自报"))]

body = []
body.append(u"**值守 %s · 现成的落地顺序表：8 枚候选里 6 对互斥，另有 3 枚与谁都不撞——先落这三枚最省**"
            % time.strftime("%H:%M"))
body.append(u"")
body.append(u"- %s" % (tip[0][:150] if tip else "现尖读数不全"))
for x in fam:
    body.append(u"- %s" % x[:220])
body.append(u"")
body.append(u"候选（枝名 / 远端头 / 该枝自报改动的文件数）：")
for x in cand:
    body.append(u"- %s" % x[:170])
body.append(u"")
body.append(u"互斥对（同一跳两枚都复切，后落那枚按判据必 ABORT）：")
for x in pairs:
    body.append(u"- %s" % x[:230])
body.append(u"")
for x in free:
    body.append(u"- %s" % x[:220])
body.append(u"")
body.append(u"我从这张表里能给的只有顺序，不替你决定落谁：**撞得最多的是 `frontend/src/app/v8PanelRegistry.tsx`（4 枚都改）与后端契约那一族（`backend/app/main.py` / `contracts/openapi.yaml` / `backend/app/schemas.py`，3 枚都改）**。"
            u"最省的做法是先落那 3 枚谁都不撞的（含 N3 的 ORD-0440 后半与 S4 的 0406 配方件），再挑一枚 registry 的落，其余两枚让车道按新尖重交——"
            u"顺序你定，我只把谁撞谁数出来。")
body.append(u"")
body.append(u"尺与自曝：`patrol/_landing_plan_r1.py`（只读：块里枝名+申报头 → 远端 `ls-remote` 逐字回读 → 同族取最新一代 → 「同族已有代次在线上」的族整族剔除 → 两两比 `ls-tree` blob）。"
            u"这把尺第一版有两处我自己造的红，都已修：① 同一族的旧代（例如 0437 的 `-r3`/`-r5`/`-r6`、0436 的 `-r3`）被各列成一枚候选，读起来像 9 枚要落，其实每族只有最新那一代是活的；"
            u"② 远端头不在本地对象库时会被误判成「未落地」，现在先 `fetch` 再判，取不到对象就明说不算读数。"
            u"表里那句「merge-tree 干净 / 互斥」全是**我的只读预测**，门的实判归你那一跑。")
body.append(u"")
body.append(u"边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准、0 次改动 cron。")

text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
out_path = os.path.join(HERE, "_bus_landing_plan_1316.md")
io.open(out_path, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B；候选 %d；互斥 %d；独立 %d" % (os.path.getsize(out_path), len(cand), len(pairs), len(free)))
if "--dry" in sys.argv:
    print(text[:800])
    raise SystemExit(0)
q = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_path], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=900)
print(((q.stdout or "") + (q.stderr or "")).strip()[:600])
raise SystemExit(q.returncode)
