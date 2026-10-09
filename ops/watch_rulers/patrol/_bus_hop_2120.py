import hashlib, io, json, os, ssl, subprocess, time, urllib.request as U
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
INBOX = r"D:\moodle\_qoder_ledger_inbox"
pd = os.path.join(INBOX, "_processed")
INS = []
for f in os.listdir(pd):
    if ".inserted_" in f:
        m = os.path.getmtime(os.path.join(pd, f))
        if m > time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 20:30", "%Y-%m-%d %H:%M")):
            INS.append((m, f))
INS.sort()
tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
r = U.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1",
              headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol", "Accept": "application/vnd.github+json"})
tip = json.loads(op.open(r, timeout=90).read().decode())["object"]["sha"]
pend = sorted(f for f in os.listdir(INBOX) if f.endswith(".md"))
b = []
b.append(u"**值守 %s · 一个可重复的观察（原因我没复现，只报读数）：20:30 之后你的门跑了三跳，插进去的全是 `cmdr_*.md`，车道那枚 DRY 判可插的块还在根目录。**" % time.strftime("%H:%M"))
b.append(u"- 三跳逐字：`%s`" % u"、".join("`%s` @ %s" % (f.split(".inserted_")[0], time.strftime("%H:%M:%S", time.localtime(m))) for m, f in INS))
b.append(u"- 等在那儿的：%s（`r_ord0465_2052.md` 自 20:52:59 起已等 %d 分）。我 21:04 用 **DRY**（`tally inserted:0`，一字未写）跑过门，它对这枚的判定是 `DRY r_ord0465_2052.md`＝可插；那枚 `_question.md` 是形状拒（文件名要 `<车道>_<HHMM>.md`）。" % (u"、".join("`%s`" % x for x in pend), int((time.time() - os.path.getmtime(os.path.join(INBOX, "r_ord0465_2052.md"))) / 60)))
b.append(u"- 两种可能我没分辨：① 你那一跳是**带文件名**的定向插（那就一切正常，车道块等一次全量 `--apply`）；② 全量跑但循环里在 `cmdr_*` 之前/之后提前退出。我没复现就不写结论；我的门停探测器 21:22 会到 30 分阈值，自己也会记名。")
b.append(u"- 我仍不动那把笔：0 次代插、0 次改名、0 次删文件、0 次落地；现尖 `%s`（本行现读）。" % tip)
b.append(u"")
b.append(u"边界：只读（`_processed` 的 mtime 与文件名、收件口 stat、门的 DRY 模式、GitHub API）。")
out = os.path.join(HERE, "_bus_hop_2120.md")
io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(b).rstrip() + "\n" + CLOSING + "\n")
print("三跳=%s｜待插=%s" % ([f for _m, f in INS], pend))
q = subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((q.stdout or "") + (q.stderr or "")).strip()[:300])
