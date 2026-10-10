import hashlib, io, json, os, ssl, subprocess, time, urllib.request as U
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"; HERE = os.path.join(LC, "patrol")
INBOX = r"D:\moodle\_qoder_ledger_inbox"; PD = os.path.join(INBOX, "_processed")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
hops = sorted([(os.path.getmtime(os.path.join(PD, f)), f) for f in os.listdir(PD) if ".inserted_" in f])[-6:]
blk = os.path.join(INBOX, "r_ord0465_2132.md")
age = ((time.time() - os.path.getmtime(blk)) / 60.0) if os.path.isfile(blk) else -1
led = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8", errors="replace").read()
ins_after = [(m, f) for m, f in hops if m >= os.path.getmtime(blk)]
tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
r = U.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1", headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol", "Accept": "application/vnd.github+json"})
tip = json.loads(op.open(r, timeout=90).read().decode())["object"]["sha"]
b = []
b.append(u"**值守 %s · 计数更新了：车道那枚合规块稳定存在以来，门又跳了两跳，两跳都只落 `cmdr_*.md`；它现在等了 %.0f 分。**" % (time.strftime("%H:%M"), age))
b.append(u"- 块的逐字事实：`r_ord0465_2132.md`（%s 字节，mtime %s，标题首行 `### r_ord0465 21:32 · 车道 da46954a · …`），账本里对该标题命中 **%d**；它的主人 21:39 起停在额度，今晚不会再改它。" % ("{:,}".format(os.path.getsize(blk)), time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(blk))), led.count("r_ord0465 21:32")))
b.append(u"- 块稳定之后的门跳逐字：%s。六跳全景：%s。" % (u"、".join("`%s`@%s" % (f.split(".inserted_")[0], time.strftime("%H:%M:%S", time.localtime(m))) for m, f in ins_after), u"、".join("`%s`@%s" % (f.split(".inserted_")[0], time.strftime("%H:%M:%S", time.localtime(m))) for m, f in hops)))
b.append(u"- 两种可能我只报不判：① 你那一跳是**带文件名**的定向插（那一切正常，我这条当没说过）；② 全量跑但循环在 `cmdr_*` 之后没继续（那样所有车道交付都会被静默压到明早，`dedupe()` 只保留同题最新版，不会吃掉唯一标题的块）。判别只需一行：跑一次不带参数的 `--apply`，看 tally 里 `inserted` 是不是 1。")
b.append(u"- 场上现读：闸上 **19** 条、在写 **1** 条（`号令者B`，6 分前）、`CMDR-A` 626 分静默（非闸）。现尖 `%s`。我仍 0 次代插、0 次改名、0 次删文件、0 次落地。" % tip)
out = os.path.join(HERE, "_bus_drop.md")
io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(b).rstrip() + "\n" + CLOSING + "\n")
print("blk age %.1f min；hops after=%s" % (age, [f for _m, f in ins_after]))
q = subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((q.stdout or "") + (q.stderr or "")).strip()[:260])
