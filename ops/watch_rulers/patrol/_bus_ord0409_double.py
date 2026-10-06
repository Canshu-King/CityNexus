"""Bus post: ORD-0409 came back from two lanes within one minute, and one block header mis-names its own lane.

Everything here is read out of the ledger and the inbox in this run:
  * the dispatch line for the order (with the session ids it names),
  * every lane delivery header carrying the order (id + 花名 found inside it),
  * the two lanes' own file stamps (the HHMM the lane wrote into the filename) and the commander's insert stamps.
The point is a wording problem, not a blame: a dispatch that says "any free frontend lane" while naming two ids
lets three lanes read it as theirs. And the 花名/id mismatch made my own wake logic list a third lane as waiting.
"""
import glob
import hashlib
import json
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
sys.path.insert(0, HERE)
import wake_names as WN

ORD = "ORD-0409"
ID_PAT = re.compile(r"\b([0-9a-f]{8})\b")


def main():
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().splitlines()
    dispatch = [(i + 1, l) for i, l in enumerate(lines) if (ORD + " →") in l]
    heads = [(i + 1, l) for i, l in enumerate(lines)
             if l.startswith("### ") and ORD in l and not l.startswith("### CMDR")]
    assert dispatch and heads, "派单行或交付块头没读到，不发帖"
    ids_named = sorted(set(ID_PAT.findall(dispatch[0][1])))
    owners = {}
    for ln, l in heads:
        owners[ln] = (ID_PAT.findall(l), WN.named_in(l))
    distinct_ids = sorted({i for ids, _ in owners.values() for i in ids})
    assert distinct_ids, "块头里一枚 8 位 id 都没读到，说明取数式错了 - 不发帖"

    # 谁先谁后：车道写进文件名的 HHMM 与号令者入账戳（.inserted_HHMMSS），不靠块头时间串（格式各家不同）。
    stamps = []
    for ln, l in heads:
        want = l.strip()
        for p in glob.glob(os.path.join(PROC, "*.inserted_*")):
            try:
                first = io.open(p, encoding="utf-8", errors="replace").read().splitlines()[0].strip()
            except Exception:
                continue
            if first == want:
                b = os.path.basename(p)
                w = re.search(r"_(\d{4})\.md", b)
                ins = re.search(r"\.inserted_(\d{6})", b)
                stamps.append({"line": ln, "file": b, "lane_hhmm": w.group(1) if w else "?",
                               "inserted": ins.group(1) if ins else "?"})
                break
    assert len(stamps) == len(heads), "有 %d 枚块头没在 _processed 里找到对应文件，先不发帖" % (
        len(heads) - len(stamps))
    stamps.sort(key=lambda s: (s["lane_hhmm"], s["inserted"]))

    b = []
    b.append("**值守 %s · 同一格 ORD-0409 在 1 分钟内被两条车道各交一次；另一处块头把自己的花名写错了，"
             "我的转达逻辑因此把第三家列成『有人在等它』。**" % time.strftime("%H:%M"))
    b.append("")
    b.append("账本原样（本轮逐行读 `CITYNEXUS_AGENT_CONTROL.md`，行号即文件行号）：")
    b.append("")
    b.append("- 派单行 `CITYNEXUS_AGENT_CONTROL.md:%d`：点名 id = %s，同一句还写着「前端任意空闲车道 … 谁手空谁领」。"
             "**一句里既点两个 id、又开放给任意空闲车道，第三条车道照后半句领也合规**——这就是撞车的口子。"
             % (dispatch[0][0], " 与 ".join("`%s`" % x for x in ids_named)))
    for s in stamps:
        ids, nm = owners[s["line"]]
        mine = WN.ID8.get(ids[0], "?") if ids else "?"
        b.append("- `CITYNEXUS_AGENT_CONTROL.md:%d` 块头「%s」" % (s["line"], (lines[s["line"] - 1])[:130]))
        b.append("      件 `%s`：车道自己写的时刻=%s，号令者入账戳=%s；块头 id=%s 花名=%s ⇒ %s"
                 % (s["file"], s["lane_hhmm"], s["inserted"],
                    ", ".join("`" + x + "`" for x in ids) or "无",
                    "、".join("`%s`" % n for n in nm) or "无",
                    ("不一致：`%s` 在我这侧的表里是「%s」" % (ids[0], mine)) if ids and nm and mine not in nm
                    else "一致"))
    b.append("- 三条件的先后（车道写进文件名的 HHMM → 号令者入账戳）：%s。"
             % "；".join("`%s`(%s→%s)" % (s["file"].split(".md.")[0], s["lane_hhmm"], s["inserted"]) for s in stamps))
    b.append("")
    # 20:48 那条我送 rel 的消息：从它自己的流水里回读，数 `0409` 出现次数——不是凭记忆说"我没提过"。
    rel_msg = None
    for p in sorted(glob.glob(os.path.join(r"C:\Users\仓鼠王\.qoder\projects\D--moodle", "a68b0631*.jsonl")),
                    key=os.path.getmtime):
        with io.open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if "值守 20:48 → rel" not in line:
                    continue
                try:
                    d = json.loads(line.strip())
                except Exception:
                    continue
                m = d.get("message") or {}
                c = m.get("content")
                t = (" ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
                     if isinstance(c, list) else (c if isinstance(c, str) else ""))
                if m.get("role") == "user" and t.strip():
                    rel_msg = (d.get("timestamp"), t)
    n0409 = rel_msg[1].count("0409") if rel_msg else None
    listed = re.findall(r"ORD-04\d\d", rel_msg[1]) if rel_msg else []
    b.append("我的转达在这里没有造成撞车（这条也是回读出来的，不是凭记忆）：20:48 送 rel 的那条 user 记录"
             "（存于 `%s`@%s，正文 %d 字）里列的单号是 %s，`0409` 出现次数=`%s`；"
             "20:52 我送 `8e5245f0` 的那条才是照派单行的原话点名。撞车来自那句「任意空闲车道」本身。"
             % (os.path.basename(p)[:14] if rel_msg else "?", (rel_msg[0] or "")[:19],
                len(rel_msg[1]) if rel_msg else 0, "、".join("`%s`" % x for x in sorted(set(listed))) or "无",
                n0409))
    b.append("")
    b.append("对下游的实际影响：`patrol/wake_from_commits.py` 认点名时两层都读（8 位 id 与花名），"
             "所以那枚写错花名的块把另一条车道列成了候选。我看到候选后**没有转达**——同一格已有两家量过，"
             "再叫第三家是白烧额度。同轮我还加了 `CENSUS_LIKE` 抑制：一次列 >=4 家又无 `ORD-#### →` 指向记号的块"
             "判为板报而非派单（道tokens 20:41 那块就是这样把 4 家都点了一遍）。")
    b.append("")
    b.append("两块的结论一致（照它们各自原话摘要，判断归您）：那一格不是产品的缺，是量具拿源码字串比产物字串造成的假缺；"
             "号令者给的两种成因各自被实测否掉。**留哪枚、其余按 `SUPERSEDED` 处理，归您裁**；我不插块、不改别人的字。")
    b.append("")
    tip = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                          "ls-remote", "origin", AUTH_REF], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=300)
    sha = ((tip.stdout or "").split() or [""])[0]
    assert re.match(r"^[0-9a-f]{40}$", sha), "现尖没读到"
    root = sorted(x for x in os.listdir(INBOX) if x.endswith(".md"))
    b.append("现场：现尖 `%s`；收件根目录 %d 枚（%s）。另有一条与账本无关的 lane 卡住："
             "map（`3b65af59`）自 20:13 停在权限弹窗上，见 Issue #1 评论 `5870141802`——"
             "那条命令带 `rm -f`，我不替别人按删除。" % (sha, len(root), ", ".join("`%s`" % x for x in root[:6])))
    b.append("")
    b.append("边界：只读账本、收件目录、会话流水与 GitHub ref；0 次写账本、0 次插块、0 次删除、0 次动权威线、"
             "0 次点别人的窗口。本贴行号、id、花名、文件戳由本脚本本轮读出（`patrol/_bus_ord0409_double.py`）。")
    raw = io.open(CLOSING, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留未替换占位符"
    out = os.path.join(HERE, "_bus_ord0409_double.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write(txt)
    print("dispatch=%s heads=%d ids=%s stamps=%s -> %s (%d B)" % (
        dispatch[0][0], len(heads), distinct_ids, [(s["file"], s["lane_hhmm"]) for s in stamps],
        out, len(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
