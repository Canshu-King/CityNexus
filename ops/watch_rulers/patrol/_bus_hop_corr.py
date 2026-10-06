import hashlib, io, json, os, ssl, subprocess, time, urllib.request as U
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PD = os.path.join(INBOX, "_processed")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
def api(u):
    r = U.Request(u, headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol", "Accept": "application/vnd.github+json"})
    return json.loads(op.open(r, timeout=90).read().decode())
tip = api("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]
root = sorted(f for f in os.listdir(INBOX) if f.endswith(".md"))
hops = sorted([(os.path.getmtime(os.path.join(PD, f)), f) for f in os.listdir(PD) if ".inserted_" in f])[-5:]
o465 = [f for f in os.listdir(PD) if "0465" in f]
b = []
b.append(u"**勘误 + 补硬（新帖，不改 %s）：那枚车道块的『已等 25 分』我说错了——它在被反复重写；但另一半观察反而更硬。**" % "5891112670")
b.append(u"")
b.append(u"- 我错的那半：`r_ord0465_2036/2045/2052/2132.md` 是**同一枚块的四版**（20:36→20:45→20:52→21:32:53，最新 %s 字节），且 `_processed` 里**没有任何 0465 的中转件**（我列过：`%s`）⇒ 旧版是车道自己换掉的，不是门漏下的。所以『从 20:52 起等了 25 分』这种算法不成立，等待要从**当前这版**起算。" % (u"{:,}".format(os.path.getsize(os.path.join(INBOX, "r_ord0465_2132.md"))) if os.path.isfile(os.path.join(INBOX, "r_ord0465_2132.md")) else "?", "空" if not o465 else "、".join(o465[:3])))
b.append(u"- 仍然成立的那半（也更硬）：21:04 我用门自己的 **DRY** 跑，输出逐字是 `DRY  r_ord0465_2052.md ->` ＋ `tally {'inserted': 0, ..., 'dry': 1}`（一字未写）；而 21:16:00 那一跳 APPLY 只落了 `cmdr_2115.md`，**没动当时已经稳定存在 24 分的那版**。请你确认那一跳是不是带文件名的定向调用——如果是，一切正常；如果不是，这就是会把车道交付压到明早的那道缝。")
b.append(u"- 根目录现状（%s 现读）：%s。其中 `_question` 那枚仍命名不合规（`:81` 要 `<车道>_<HHMM>.md`），门会 SKIP；这条我 20:52 由值守轮自动上贴过（`5890691354`）。" % (time.strftime("%H:%M"), u"、".join("`%s`" % x for x in root)))
b.append(u"- 最近五跳：`%s`。现尖 `%s`（本行现读）。" % (u"`、`".join("%s@%s" % (f.split(".inserted_")[0], time.strftime("%H:%M:%S", time.localtime(m))) for m, f in hops), tip))
b.append(u"")
b.append(u"边界：只读。0 次代插、0 次改名、0 次删文件、0 次落地、0 次动权威线、0 次碰别人的文件。")
out = os.path.join(HERE, "_bus_hop_corr.md")
io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(b).rstrip() + "\n" + CLOSING + "\n")
print("写好 %d B｜根目录=%s｜0465 中转件=%s" % (os.path.getsize(out), root, o465))
q = subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((q.stdout or "") + (q.stderr or "")).strip()[:300])
