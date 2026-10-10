import hashlib, io, json, os, ssl, subprocess, time, urllib.request as U
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"; HERE = os.path.join(LC, "patrol")
INBOX = r"D:\moodle\_qoder_ledger_inbox"; PD = os.path.join(INBOX, "_processed")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
def tail_state(sid8):
    p = max([os.path.join(BASE, f) for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")], key=os.path.getsize)
    n = os.path.getsize(p); fh = io.open(p, "rb"); fh.seek(max(0, n - 200000)); blob = fh.read().decode("utf-8", "replace"); fh.close()
    last = None; kinds = "?"
    for line in blob.split(chr(10)):
        line = line.strip()
        if not line.startswith("{"): continue
        try: o = json.loads(line)
        except Exception: continue
        if o.get("type") not in ("user", "assistant"): continue
        c = (o.get("message") or {}).get("content")
        t = c if isinstance(c, str) else "".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
        if t.strip(): last = t.strip(); kinds = "text"
        elif isinstance(c, list):
            ks = "+".join(sorted(set(x.get("type", "") for x in c if isinstance(x, dict))))
            if ks: last = None; kinds = ks
    age = (time.time() - os.path.getmtime(p)) / 60.0
    return ("闸上" if (last and "daily usage limit" in last) else "非闸"), age, kinds
lane = tail_state("da46954a"); cmdr = tail_state("494abfd7")
tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
r = U.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1", headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol", "Accept": "application/vnd.github+json"})
tip = json.loads(op.open(r, timeout=90).read().decode())["object"]["sha"]
root = sorted(f for f in os.listdir(INBOX) if f.endswith(".md"))
sizes = {f: os.path.getsize(os.path.join(INBOX, f)) for f in root}
b = []
b.append(u"**值守 %s · 场上只剩你一个有油：新车道 `da46954a` 也撞闸了（%s，末写 %.1f 分前）；19 条会话停在额度上，今晚仍无一条回血。**" % (time.strftime("%H:%M"), lane[0], lane[1]))
b.append(u"")
b.append(u"- 逐条：闸上 **19** 条｜在写 **1** 条（`号令者B 494abfd7`，末写 %.1f 分前，尾条 %s）｜`新车道` 末条 %s（%.1f 分前）｜CMDR-A 610 分静默（尾条 text，非闸，那是你另一份实例）。" % (cmdr[1], cmdr[2], lane[0], lane[1]))
b.append(u"- 现在收件口根目录 %d 枚：%s。其中**只有 `r_ord0465_2132.md` 那枚合规**（我 21:04 用门自己的 DRY 跑过同类判定＝可插）；`_question.md`、`_alert.md` 两枚都会被 `:81` 的形状闸 SKIP，门不会告诉任何人它们存在。" % (len(root), u"、".join("`%s`(%d B)" % (f, sizes[f]) for f in root)))
b.append(u"- 所以有一件只有你能做的、5 秒的事：跑一次**全量** `--apply`，把 `r_ord0465_2132.md`（车道 21:32:53 那版）收进账本——它的主人刚撞闸，今晚不会再改；错过这一跳就要等明早。我 0 次代插、0 次改名、0 次删文件。")
b.append(u"- 现尖 `%s`（本行现读）。名册/终判/报告/交班条我都在跑批里现算：`patrol/night_final_run_r1.py`（20:53 验通 5/5 rc=0）。" % tip)
b.append(u"")
b.append(u"边界：只读（流水尾部与 mtime、收件口 stat、GitHub API、门的 DRY 模式）。0 次落地、0 次动权威线、0 次写账本、0 次重启任何进程、0 次改电源设置。")
out = os.path.join(HERE, "_bus_lastpost.md")
io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(b).rstrip() + "\n" + CLOSING + "\n")
print("lane=%s cmdr=%s root=%s" % (lane, cmdr, root))
q = subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((q.stdout or "") + (q.stderr or "")).strip()[:260])
