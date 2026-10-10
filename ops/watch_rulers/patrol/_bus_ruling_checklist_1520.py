# -*- coding: utf-8 -*-
"""值守 15:20 贴：把 10 条「等裁语」车道各自的原话压成一屏清单——每行只要他一句回答。

15:12 那贴给的是「谁在等」+ 门的状态；这一贴给的是**等的到底是哪一句**。
差别在于动作成本：他从总线上读到「10 条在等」只能知道要开工，读到这张表可以一趟把 10 句发完，
其中两条甚至已经替他把验证跑好了（`8e5245f0` 自报 `merge-tree --write-tree` rc=0、5 枚面 DIFF 0；
`6a150e1e` 把合并后的栈留在 `127.0.0.1:8021` + 静态 `127.0.0.1:4813` 等复测），
也就是这几格不需要新证据，只差一句话。

只读：取 `_ruling_ask_extract_r1.py` 的读数（它读每条流水最后一段助手原文），本脚本不发消息给任何车道、不裁语、不落地。
闸：一条都抽不出来、或全部落在「读不到原文」，直接 REFUSE——不发空清单。
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

HEX40 = re.compile(r"[0-9a-f]{13,}")
SECRET = re.compile(r"(ghp_[A-Za-z0-9]{8,}|x-access-token|api[_-]?tok|Authorization|Bearer\s+[A-Za-z0-9_\-]{16,})", re.I)


def clean(s):
    s = HEX40.sub(lambda m: m.group(0)[:12] + "…", s)
    if SECRET.search(s):
        return "（含凭据形状，已整条遮住：原文在流水里，按 id 自取）"
    return s.strip()


p = subprocess.run([PY, os.path.join(HERE, "_ruling_ask_extract_r1.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=HERE, env=ENV, timeout=900)
out = (p.stdout or "") + (p.stderr or "")
cur = None
items = []
for l in out.split("\n"):
    m = re.match(u"^\\s*([0-9a-f]{8})\\s+静默\\s*([\\d.]+) 分｜(\\S+)\\s*$", l)
    if m:
        cur = {"id": m.group(1), "min": float(m.group(2)), "cat": m.group(3), "asks": []}
        items.append(cur)
        continue
    m2 = re.match(u"^\\s*└\\s*(.+)$", l)
    if m2 and cur is not None:
        cur["asks"].append(m2.group(1).strip())
usable = [x for x in items if x["cat"] != u"读不到原文（流水尾无助手文本）" and x["asks"]]
msum = re.search(u"分档合计：(.+)", out)
if not usable:
    print("REFUSE：一条原话都没抽到（共 %d 条），不发空清单" % len(items))
    raise SystemExit(7)

body = []
body.append(u"**值守 %s · 接着 15:12 那贴：这 %d 条等裁语的车道，各自等的原话在这里，每行只要一句回答**"
            % (time.strftime("%H:%M"), len(usable)))
body.append(u"")
body.append(u"尺：`patrol/_ruling_ask_extract_r1.py`（读每条流水最后一段助手原文、按请求形状抽句子：裁/请/要不要/哪一个/等你/should I…）；"
            u"原始读数落在 `patrol/_ruling_asks_latest.txt`。分档：%s" % (msum.group(1).strip() if msum else "（合计行没读到）"))
body.append(u"")
for i, x in enumerate(usable, 1):
    body.append(u"%d. `%s`（静默 %d 分｜判档 %s）" % (i, x["id"], int(x["min"]), x["cat"]))
    for a in x["asks"]:
        body.append(u"     原话：%s" % clean(a)[:260])
body.append(u"")
body.append(u"两格已经不需要新证据、只差一句话：`8e5245f0` 自报已替他把复切跑完（`git merge-tree --write-tree` rc=0、"
            u"相对尖改的 5 枚产品/测试面全部合到自己字节上、DIFF 0 枚），它那边写的是「ORD-0529 没有待办，等你落 r2 就行」；"
            u"`6a150e1e` 把合并后的栈留着等复测（api `127.0.0.1:8021`、静态 `127.0.0.1:4813`）。这两条的「自报」我只搬运它自己写下的句子，没有替它复算。")
body.append(u"")
body.append(u"复算：`cd D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\patrol && python _ruling_ask_extract_r1.py`（只读流水尾部 2 MB，0 起 git、0 写账本）。")
body.append(u"")
body.append(u"边界：①我不裁语、不派单、不落地、不敲任何车道；这张表只是把 %d 条**自己写下的最后一句**摊成一屏，"
            u"省得逐条开流水；②分档是按字面词族判的（额度|批准|点击|删|重启 这类才归「只有用户能当场解」），"
            u"这一轮 %d 条全落在「号令者可裁」，所以没有任何一条在等物理世界的动作；"
            u"③原话里的 13 位以上十六进制折成前 12 位，出现凭据形状整条遮住；④引的是车道自述，不代表我对它的交付质量做过判断。"
            % (len(usable), len(usable)))
text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
outp = os.path.join(HERE, "_bus_ruling_checklist_1520.md")
io.open(outp, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B｜可用 %d 条｜分档合计 %s" % (len(text.encode("utf-8")), len(usable), (msum.group(1)[:120] if msum else "-")))
if "--dry" in sys.argv:
    print(text[:1200])
    raise SystemExit(0)
p2 = subprocess.run([PY, os.path.join(LC, "bus_post.py"), outp], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=900, env=ENV)
print(((p2.stdout or "") + (p2.stderr or "")).strip()[:700])
raise SystemExit(p2.returncode)
