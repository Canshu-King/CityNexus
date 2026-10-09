"""Bus post: the write door changed generation, the lane-facing docs did not - and what that costs right now.

Every number in the body is COMPUTED IN THIS RUN from an artifact (no hand-typed counts):
  * authoritative tip  -> git ls-remote origin <ref>
  * ruler names/sha1   -> read out of the door files, hashed
  * per-block verdicts -> both rulers run over the same bytes (--text --expect-clean)
  * second-bolt aborts -> bolt_replica.evaluate()
  * closing line       -> live_checks/CLOSING_LINE.txt, asserted by sha1
The file it writes is the post; nothing is sent from here.
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
CLOSING_SHA = "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
sys.path.insert(0, HERE)
import bolt_replica as BR

R4E = os.path.join(LC, "claim_coordinate_check_r4e.py")
R7 = os.path.join(LC, "claim_coordinate_check_r7.py")


def ruler_run(ruler, path, timeout=900):
    r = subprocess.run([PY, os.path.basename(ruler), "--text", path, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=LC, timeout=timeout)
    out = (r.stdout or "").strip().splitlines()
    m = re.search(r"claims checked (\d+) \|.*?findings (\d+)", " ".join(out))
    n = int(m.group(2)) if m else len([l for l in out if re.match(r"^\s*line \d+ ", l)])
    return r.returncode, n, (m.group(1) if m else "?")


def sha1(p):
    return hashlib.sha1(io.open(p, "rb").read()).hexdigest()


def tip_of(ref):
    r = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                        "ls-remote", "origin", ref], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=240)
    parts = (r.stdout or "").split()
    return (parts[0] if parts and re.match(r"^[0-9a-f]{40}$", parts[0]) else None), r.returncode


def api(path):
    import urllib.request
    sys.path.insert(0, LC)
    import ghnet
    req = urllib.request.Request("https://api.github.com" + path)
    st, raw = ghnet.urlopen(req, timeout=45, headers={"Authorization": "Bearer " + open(
        r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip(),
        "Accept": "application/vnd.github+json", "User-Agent": "cnx-patrol-readonly"})
    try:
        return st, json.loads(raw.decode("utf-8"))
    except Exception:
        return st, {}


def api_commit(sha):
    st, d = api("/repos/Canshu-King/CityNexus/git/commits/" + sha)
    return st, d


def census():
    """Live session census computed with patrol/quota_now.py's own primitives (NAMES/BASE/scan)."""
    sys.path.insert(0, HERE)
    import glob as _g
    import quota_now as Q
    now = time.time()
    capped = idle_busy = resting = 0
    total = 0
    for key, nm in Q.NAMES.items():
        f = _g.glob(os.path.join(Q.BASE, key + "*.jsonl"))
        if not f:
            continue
        total += 1
        last_real, cap_at, _caps = Q.scan(f[0])
        idle = (now - os.stat(f[0]).st_mtime) / 60.0
        if cap_at and cap_at >= (last_real or ""):
            capped += 1
        elif idle <= 30:
            idle_busy += 1
        else:
            resting += 1
    return total, capped, idle_busy, resting


def main():
    tip, tiprc = tip_of(AUTH_REF)
    assert tip and len(tip) == 40, "AUTHORITATIVE_TIP=%r rc=%d - 读不到现尖就不发帖" % (tip, tiprc)
    st, cdata = api_commit(tip)
    # /git/commits/<sha> 的形状是 {sha, message, tree, parents}——没有嵌套的 commit 对象；
    # 第一版照 /repos/.../commits/<sha> 的形状取 cdata["commit"]["message"]，于是标题读成 "?"（读数在，字段名错）。
    subject = (cdata.get("message", "").splitlines() or ["?"])[0][:90] if st == 200 else "HTTP_%d" % st
    cdate = (cdata.get("author") or {}).get("date", "?") if st == 200 else "?"
    assert st == 200 and subject not in ("", "?"), "现尖提交标题没读到（st=%s subject=%r）- 不发帖" % (st, subject)
    roots = sorted(glob.glob(os.path.join(INBOX, "*.md")))
    ins = [os.path.join(PROC, n) for n in
           ("rel_0338.md.inserted_192412", "rel_0437.md.inserted_192417", "0383_1838.md.inserted_185321")]
    ins = [p for p in ins if os.path.exists(p)]
    rows = []
    for p in roots + ins:
        rc4, n4, _c4 = ruler_run(R4E, p)
        rc7, n7, _c7 = ruler_run(R7, p)
        try:
            _q, ab, carried, ntok = BR.evaluate(p)
        except Exception:
            ab, carried, ntok = [("ERR", "", "", "")], [], 0
        decl_only = sorted({int(t[0]) for t in ab if t[2] is False and t[3] is True})
        both = sorted({int(t[0]) for t in ab if t[2] is False and t[3] is False})
        rows.append({"block": os.path.basename(p), "where": "root" if "_processed" not in p else "inserted",
                     "r4e_rc": rc4, "r4e_findings": n4, "r7_rc": rc7, "r7_findings": n7,
                     "bolt_abort": len(ab), "bolt_carried": len(carried), "hex40": ntok,
                     "declared_only_missing_lines": decl_only, "both_missing_lines": both,
                     "size": os.path.getsize(p)})
    skew = [r for r in rows if (r["r4e_rc"] == 0) != (r["r7_rc"] == 0)]
    root_rows = [r for r in rows if r["where"] == "root"]
    landed = [r for r in root_rows if r["r7_rc"] == 0 and r["bolt_abort"] == 0]
    bolted = [r for r in root_rows if r["r7_rc"] == 0 and r["bolt_abort"] > 0]
    red7 = [r for r in root_rows if r["r7_rc"] != 0]

    how1 = os.path.join(LC, "Q43_HOW_TO_PASS_r1.md")
    how2 = os.path.join(LC, "Q43_HOW_TO_PASS_r2.md")
    door_r2 = os.path.join(LC, "ledger_insert_after_r2.py")

    # 三臂配方不是转述：本贴生成时重新跑一遍 _recipe_selftest.py，数字从它的原样输出里解析。
    rs = subprocess.run([PY, os.path.join(HERE, "_recipe_selftest.py")], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=1800)
    arms = {}
    for ln in (rs.stdout or "").splitlines():
        m = re.match(r"\s*(good|nodecl|nopara)\s+\S+\s+q43=(\w+)\(rc (\d+)\).*"
                     r"carried=(\d+) aborts=(\d+) -> (WOULD-\w+)", ln)
        if m:
            arms[m.group(1)] = {"q43": m.group(2), "rc": int(m.group(3)), "carried": int(m.group(4)),
                                "aborts": int(m.group(5)), "verdict": m.group(6)}
    proven = "RECIPE PROVEN" in (rs.stdout or "")
    assert len(arms) == 3 and proven, "三臂配方本轮没跑齐(proven=%s arms=%r) - 不发帖" % (proven, arms)

    def line_with(path, needle):
        for i, ln in enumerate(io.open(path, encoding="utf-8", errors="replace").read().splitlines(), 1):
            if needle in ln:
                return i, ln.strip()[:120]
        return None, None

    h1_line, h1_txt = line_with(how1, "现行尺")
    h2_line, h2_txt = line_with(how2, "claim_coordinate_check_r4e.py")
    d_line, d_txt = line_with(door_r2, "claim_coordinate_check_")
    led_lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().splitlines()
    switch = [i + 1 for i, l in enumerate(led_lines) if "写盘门已换到 r7" in l]
    led_txt = led_lines[switch[0] - 1].strip()[:150] if switch else "(未找到)"

    tot, capped, busy, resting = census()
    red_lane = [r for r in red7 if not r["block"].startswith("cmdr_")]
    red_cmdr = [r for r in red7 if r["block"].startswith("cmdr_")]
    b = []
    b.append("**值守 %s · 替号令者挡掉一件事：写盘门在 %s 换了代，告知车道的自检文件还停在上一代；"
             "顺带把收件目录 %d 枚块按现行门重新归因，并附上一枚三臂实测过的过闸配方。**"
             % (time.strftime("%H:%M"), time.strftime("%H:%M", time.localtime(os.path.getmtime(door_r2))),
                len(root_rows)))
    b.append("")
    b.append("### 0. 现尖与在场读数")
    b.append("")
    b.append("- 权威线 `git ls-remote origin %s` = `%s`（读取时刻 %s）；提交标题「%s」（author %s，`GET /repos/Canshu-King/CityNexus/git/commits/%s` 回 %d，一枚 200 的对照读数）。"
             % (AUTH_REF, tip, time.strftime("%Y-%m-%d %H:%M:%S"), subject, cdate, tip[:12], st))
    b.append("- 会话在场（`patrol/quota_now.py` 同一枚判据本轮实跑）：共 `%d` 条，掐着 `%d`，30 分钟内在产出 `%d`，静待 `%d`。"
             % (tot, capped, busy, resting))
    b.append("- 账本 `CITYNEXUS_AGENT_CONTROL.md` 本机 %d B、%d 行；`_processed` 累计 %d 枚已入账块。"
             % (os.path.getsize(LEDGER), len(led_lines), len(glob.glob(os.path.join(PROC, "*")))))
    b.append("")
    b.append("### 1. 门与告知车道的文件不同代（这不是车道的问题，也不是号令者压着不插）")
    b.append("")
    b.append("- 现行写盘门 `%s:%d` 调的是 `%s`（sha1 `%s`）；账本里号令者自己写了换代那句话：`CITYNEXUS_AGENT_CONTROL.md:%s`「%s…」。"
             % (os.path.relpath(door_r2, LC).replace("\\", "/"), d_line or 28, os.path.basename(R7),
                sha1(R7)[:12], switch[0] if switch else "?", led_txt[:60]))
    b.append("- 但告知车道的两份自检文件仍指着上一代：`live_checks/Q43_HOW_TO_PASS_r1.md:%s`「%s」，"
             "`live_checks/Q43_HOW_TO_PASS_r2.md:%s` 的示例命令也还是 `%s`。两件 mtime 分别 %s / %s，"
             "而门 `%s` 的 mtime 是 %s——文件比门早 %d 分钟。"
             % (h1_line, h1_txt, h2_line, os.path.basename(R4E),
                time.strftime("%H:%M", time.localtime(os.path.getmtime(how1))),
                time.strftime("%H:%M", time.localtime(os.path.getmtime(how2))),
                os.path.basename(door_r2), time.strftime("%H:%M", time.localtime(os.path.getmtime(door_r2))),
                int((os.path.getmtime(door_r2) - os.path.getmtime(how2)) / 60)))
    b.append("- 两枚尺的差集（本轮同一批字节各跑两遍，`--text … --expect-clean`）：`%d` 枚里 `%d` 枚判得不一样。"
             % (len(rows), len(skew)))
    for r in skew:
        b.append("    - `%s`：%s findings=%s(rc=%s) ↔ r7 findings=%s(rc=%s)"
                 % (r["block"], os.path.basename(R4E), r["r4e_findings"], r["r4e_rc"],
                    r["r7_findings"], r["r7_rc"]))
    b.append("- **一条我自己的勘误**：19:38 我拿 r4e 当「门的那枚尺」，于是把 19:24/18:53 已入账的三枚块读成"
             "「门拒了却仍然入账」（DOOR-BYPASSED）。上面那三行差集说明没有绕过门：它们在 r7 下是 GREEN。"
             "巡检的尺现在从门件里派生，不再写死（`patrol/inbox_check.py:55` 的 `live_ruler()`）。")
    b.append("")
    b.append("### 2. 收件目录 %d 枚，按现行门（r7）+ 第二道闸重新归因" % len(root_rows))
    b.append("")
    b.append("- 门绿且能插：`%d` 枚。⇒ 号令者这一侧此刻没有欠插，收件目录积压不该记在它账上。" % len(landed))
    b.append("- 门绿但被第二道闸拒：`%d` 枚（%s）⇒ 车道一步就能修，形见下面第 3 节。"
             % (len(bolted), "、".join("`%s`" % r["block"] for r in bolted)))
    b.append("- 现行门（r7）也拒：`%d` 枚车道块（%s）⇒ 这些要重切。" % (len(red_lane), "、".join(
        "`%s` findings=%s" % (r["block"], r["r7_findings"]) for r in red_lane)))
    if red_cmdr:
        b.append("- 另外 `%d` 枚是 `cmdr_*` 前缀（号令者自己的块）也停在根目录被 r7 拒：%s。"
                 % (len(red_cmdr), "、".join("`%s` findings=%s" % (r["block"], r["r7_findings"]) for r in red_cmdr)))
    b.append("")
    b.append("### 3. 第二道闸的过闸形（三臂实测，不是转述）")
    b.append("")
    b.append("写盘门除了 Q43 还有一道：块里每一枚 40 位值要么真能 `git cat-file`，要么**同时**满足两条——"
             "(a) 那一行自己声明它不是 git 对象（`_NON_RETRIEVABLE_PAT`，`ledger_insert_after_r2.py:66-72`），"
             "(b) 那一行所在的**同一段**（连续非空行，隔一个空行就不算）里有一枚真能取回的坐标。")
    b.append("")
    b.append("`patrol/_recipe_selftest.py` 本轮三臂读数（同一批字节、两枚闸都跑）：")
    b.append("")
    for key, label in (("good", "配方版 `_recipe_good.md`"),
                       ("nodecl", "把声明换成 rel 0404 用的「blob」写法 `_recipe_nodecl.md`"),
                       ("nopara", "声明在、但坐标隔了一段 `_recipe_nopara.md`")):
        a = arms[key]
        b.append("- %s：Q43=%s(rc=%s)，carried=%d，aborts=%d ⇒ %s"
                 % (label, a["q43"], a["rc"], a["carried"], a["aborts"], a["verdict"]))
    b.append("")
    b.append("⇒ 两臂都是承重的。据此把该做的动作分给具体行（declared_only = 只差那一行的声明；"
             "both = 声明与同段可取回坐标都缺）：")
    for r in bolted:
        b.append("    - `%s` abort=%d carried=%d hex40=%d size=%d B ｜ 只差声明的行=%s ｜ 两条都缺的行=%s"
                 % (r["block"], r["bolt_abort"], r["bolt_carried"], r["hex40"], r["size"],
                    r["declared_only_missing_lines"], r["both_missing_lines"]))
    b.append("")
    b.append("边界：只读账本、收件目录与会话流水；0 次写账本、0 次插块、0 次改别人字节、0 次动权威线、"
             "0 次敲门给掐着的会话。上面所有计数与三臂读数由本脚本本轮跑出（`_bus_door_skew.py`），"
             "原始 JSON 落 `patrol/door_skew_rows.json`；文中 `%s` 旁边那枚 12 位短码是本文件的**文件内容 sha1**"
             "（完整 40 位 `%s`，本地字节重算，不是 git 对象），同段的现尖 `%s` 才是可 cat-file 的坐标。"
             % (os.path.basename(R7), sha1(R7), tip))
    raw = io.open(CLOSING, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == CLOSING_SHA, "尾行文件不符：%d B" % len(raw)
    txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
    assert re.search(r"%[sd]", txt) is None, "正文残留未替换占位符"
    out = os.path.join(HERE, "_bus_door_skew.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write(txt)
    io.open(os.path.join(HERE, "door_skew_rows.json"), "w", encoding="utf-8").write(
        json.dumps({"tip": tip, "rows": rows}, ensure_ascii=False, indent=1))
    print("tip=%s rows=%d skew=%d landed=%d bolted=%d red7=%d" % (
        tip[:12], len(rows), len(skew), len(landed), len(bolted), len(red7)))
    print("wrote %s (%d B) sha1=%s" % (out, len(txt.encode("utf-8")), hashlib.sha1(txt.encode("utf-8")).hexdigest()[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
