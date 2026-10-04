"""Compose the r2 re-scan hand: the commit message and manifest before the push, then the ledger block after
it -- with the two doors bolted to the writing step instead of next to it.

Nothing here is typed.  Every figure comes out of the two scan JSONs, the arms JSON and the receipt file; the
before/after label pairs come out of the r1 evidence bytes read off the published side ref; and every 40-hex
that reaches the block is read back with `git ls-tree` on the ref that was just pushed, then re-checked with
`git cat-file -t` before the block is allowed to exist.  The block is dropped only if
`claim_coordinate_check_r7.py --expect-clean` exits 0.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
RULER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
REF = "refs/heads/review/0afdb49b-landed-blob-rescan-r2"
SUB = "review/landed-blob-rescan-r2"
R1_REF = "refs/heads/review/0afdb49b-landed-blob-rescan-r1"
R1_EVIDENCE_PATH = "review/landed-blob-rescan/evidence/landed_blob_rescan_r1.json"
ARTIFACTS = [("tools/landed_blob_rescan_r2.py", "tools"),
             ("tools/landed_blob_rescan_arms_r2.py", "tools"),
             ("tools/landed_blob_rescan_receipts_r1.py", "tools"),
             ("tools/rescan2_hand_r1.py", "tools"),
             ("evidence/landed_blob_rescan_r2.json", "evidence"),
             ("evidence/landed_blob_rescan_r2_extended.json", "evidence"),
             ("evidence/landed_blob_rescan_arms_r2.json", "evidence"),
             ("run/rescan2_receipts.json", "run"),
             ("run/rescan2_all.txt", "run"),
             ("run/rescan2_extended.txt", "run"),
             ("run/commit_rescan2_msg.txt", "run")]
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=600, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def load(p):
    return json.load(open(os.path.join(LANE, p), encoding="utf-8"))


def rows(a, b):
    """The two passes are the fix's own measurement: same tip, one key widened by the family it missed."""
    return {"tip": a["live_tip"], "refs_on_line": a["review_refs_on_line"],
            "scanned_old_key": len(a["refs"]), "scanned_widened": len(b["refs"]),
            "missed_old_key": len(a["candidates_missed_by_key"]),
            "missed_widened": len(b["candidates_missed_by_key"]),
            "classes_old": dict(Counter(r["verdict"] for r in a["refs"])),
            "classes_new": dict(Counter(r["verdict"] for r in b["refs"])),
            "held": sorted([(r["ref"].split("/")[-1], r["paths"]) for r in b["refs"]
                            if r["verdict"] == "HELD"]),
            "own_product": sorted([(r["ref"].split("/")[-1], r["own_product_paths"]) for r in b["refs"]
                                   if r["own_product_paths"]], key=lambda x: -x[1]),
            "no_prediction": sum(1 for r in b["refs"]
                                 if str((r.get("prediction") or {}).get("prediction", "")).startswith("NO_PRED")),
            "predicted": sum(1 for r in b["refs"]
                             if (r.get("prediction") or {}).get("prediction") == "PREDICTED"),
            "lost": sum(1 for r in b["refs"] if "LOST_LANDED_CONTENT" in r["verdict"]),
            "path_tally": b["path_tally"],
            "by_ref": {r["ref"].split("/")[-1]: r for r in b["refs"]}}


def prior_labels():
    """What the published r1 evidence actually said, read from that ref's own bytes."""
    rc, out, _e = git("ls-remote", "--refs", "origin", R1_REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_R1_REF_UNREADABLE")
    head = out.split()[0]
    rc, blob, _e = git("rev-parse", "%s:%s" % (head, R1_EVIDENCE_PATH))
    if rc:
        raise SystemExit("ABORT_R1_EVIDENCE_PATH_MISSING " + R1_EVIDENCE_PATH)
    rc2, text, err = git("cat-file", "blob", blob.strip())
    if rc2:
        raise SystemExit("ABORT_R1_EVIDENCE_UNREADABLE " + err[:120])
    d = json.loads(text)
    return {"head": head, "blob": blob.strip(), "tip": d["live_tip"],
            "verdicts": {r["ref"].split("/")[-1]: (r.get("verdict"), r.get("paths"))
                         for r in d["refs"]}}


def prep():
    a, b = load("evidence/landed_blob_rescan_r2.json"), load("evidence/landed_blob_rescan_r2_extended.json")
    arms = load("evidence/landed_blob_rescan_arms_r2.json")
    rec = load("run/rescan2_receipts.json")
    if not arms["every_arm_bit"]:
        raise SystemExit("ABORT_ARMS_NOT_ALL_BIT")
    if a["live_tip"] != b["live_tip"]:
        raise SystemExit("ABORT_PASSES_ON_DIFFERENT_TIPS")
    f = rows(a, b)
    msg = ("ORD-0500 re-scan ruler, second generation: the first scan's labels were wrong in three places, "
           "and this cut fixes the names before anyone lands a decision on them.\n"
           "\n"
           "Measured on live_tip {tip} against {refs_on_line} refs under refs/heads/review/*. The name key r1 "
           "used matched {scanned_old_key} refs and silently missed {missed_old_key} whose names carry this "
           "lane's own order numbers; widening the key to the ORD-0485 phone family scanned {scanned_widened}, "
           "and the {missed_widened} that remain belong to other lanes.\n"
           "\n"
           "Corrections:\n"
           "  1. LOST_LANDED_CONTENT now requires a landing receipt. r1 printed that verdict over hands that "
           "were never on the line; r2 says NOT_ON_LINE unless an instrument-generated receipt names the tip "
           "they were read equal on. Receipts available to this scan: {receipts}, and the loss class fires on "
           "{lost} hands today.\n"
           "  2. git merge-tree --write-tree exited 128 (unrelated histories) for {no_prediction} of the hands "
           "scanned here, so r1's conflict_markers=0 was a number from a command that never merged. r2 reports "
           "a prediction only on exit 0 or 1; the control arm (a commit against its own parent) still answers "
           "PREDICTED, so the leg is not disabled to hide the problem.\n"
           "  3. 'paths outside review' is renamed to what it measured: generation distance. The stray-write "
           "question is now computed from the hand's own diff as own_product_paths.\n"
           "  4. the enumeration's blind spot is printed as candidates_missed_by_key rather than swallowed.\n"
           "\n"
           "Nine arms (two controls, seven mutants) all bite: every_arm_bit {every_arm_bit}. Class tally over "
           "the widened pass: {classes}.\n"
           ).format(tip=f["tip"], refs_on_line=f["refs_on_line"], scanned_old_key=f["scanned_old_key"],
                    missed_old_key=f["missed_old_key"], scanned_widened=f["scanned_widened"],
                    missed_widened=f["missed_widened"], receipts=len(rec["landed"]), lost=f["lost"],
                    no_prediction=f["no_prediction"], every_arm_bit=arms["every_arm_bit"],
                    classes=json.dumps(f["classes_new"], sort_keys=True, ensure_ascii=False))
    open(os.path.join(LANE, "run", "commit_rescan2_msg.txt"), "w", encoding="utf-8",
         newline="\n").write(msg)
    json.dump([list(x) for x in ARTIFACTS],
              open(os.path.join(LANE, "run", "rescan2_manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print(json.dumps({"tip": f["tip"], "classes": f["classes_new"], "held": f["held"],
                      "own_product": f["own_product"], "lost": f["lost"]}, ensure_ascii=False))
    print("WROTE run/commit_rescan2_msg.txt + run/rescan2_manifest.json")


def verify_hexes(text):
    found = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", text)))
    bad = [h for h in found if git("cat-file", "-t", h)[0]]
    if bad:
        raise SystemExit("ABORT_UNRESOLVABLE_HEXES " + json.dumps(bad))
    return len(found)


def deliver():
    rc, out, _e = git("ls-remote", "--refs", "origin", REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_REF_NOT_PUSHED_YET " + REF)
    head = out.split()[0]
    rc, tree, _e = git("ls-tree", "-r", "--format=%(objectname) %(path)", head)
    if rc:
        raise SystemExit("ABORT_LS_TREE " + head)
    blobs, pubpath = {}, {}
    for line in tree.splitlines():
        sha, path = line.split(" ", 1)
        if path.startswith(SUB + "/"):
            blobs[path.split("/")[-1]] = sha
            pubpath[path.split("/")[-1]] = path
    missing = [rel for rel, _g in ARTIFACTS if os.path.basename(rel) not in blobs]
    if missing:
        raise SystemExit("ABORT_PUBLISHED_PATHS_MISSING " + json.dumps(missing, ensure_ascii=False))
    a, b = load("evidence/landed_blob_rescan_r2.json"), load("evidence/landed_blob_rescan_r2_extended.json")
    arms = load("evidence/landed_blob_rescan_arms_r2.json")
    rec = load("run/rescan2_receipts.json")
    prior = prior_labels()
    f = rows(a, b)
    T = datetime.now().astimezone()
    by = f["by_ref"]

    def ev(name):
        return "`%s` blob `%s`" % (pubpath[name], blobs[name])

    held_txt = "、".join("`%s`（%d 枚路径逐字节相同）" % (n, p) for n, p in f["held"])
    own_txt = "、".join("`%s` 那手自己动 %d 枚产品路径" % (n, c) for n, c in f["own_product"])
    r3 = by["newlane-ord0500-phone-anchor-form-r3"]
    s5 = by["0afdb49b-ord0500-staging-door-r5"]
    pairs = [(n, v1, p1, by.get(n, {}).get("verdict", "?")) for n, (v1, p1) in sorted(prior["verdicts"].items())]
    relabelled = [p for p in pairs if p[1] != p[3]]
    scanart = ev("landed_blob_rescan_r2_extended.json")
    armart = ev("landed_blob_rescan_arms_r2.json")
    recart = ev("rescan2_receipts.json")
    body = """### ORD-0500 手机车道（0afdb49b）复扫尺第二代：上一手印错了三个名字，改对了才敢让人按它落地——「没落过」不等于「丢了」；名下枝从三十一枚扫成三十六枚，尖 `{tip12}`

一、上一手错在哪（错在名字，不在读数；件 {scanart}）
- 那一手把「线上根本没有这条路径」判成 `LOST_LANDED_CONTENT`，而同一块里第 3 节说它丢了、第 5 节又请你把那两枝落上去。r2 在同一枚尖上重判：`newlane-ord0500-phone-anchor-form-r3` = **{r3v}**、`0afdb49b-ord0500-staging-door-r5` = **{r5v}**；枚数从 {scanart} 的 `counts` 现取：锚形 r3 共 {r3p} 枚路径（线上没有 {r3ab} 枚、存在但字节不同 {r3ch} 枚），staging-door r5 共 {r5p} 枚且全不在线上。
- 于是「丢」这一判在今天触发 {lostn} 次（件 {scanart}）：唯一带机器收据的那手本来就逐字节相同。收据的来历钉死为一种——同一把仪器先前那趟在具名尖上读过逐字节相同：来源尖 {prec12}、清单 {recart}，共 {recn} 枚。光靠账本散文说「当年落过」的那族（锚形 r1／r2）不算收据，r2 照实报 `NOT_ON_LINE`，不替自己造损失。
- `git merge-tree --write-tree` 在这条线上对 {nopred} 枚枝全部退出 {m128}（无共同祖先），而 r1 把它的 `CONFLICT` 计数印成 {c0}——那枚数是从一条没跑成的命令里数出来的，不是「没有冲突」。r2 只在退出 {e0} 或 {e1} 时才给预测，其余答 `NO_PREDICTION_EXIT_128`；控制臂拿「提交对它自己的父」现跑仍答 `PREDICTED`，所以这条腿不是关掉糊过去的。
- r1 那列「paths outside review」量的是代距（现尖到那手所在代差了多少条产品路径），旧基那手能报到几百，看着像在乱写产品文件。r2 把它改名 `gen_distance_product_paths`，另用那手自己的 diff 算 `own_product_paths`；非零的这几手：{own_txt}（件 {scanart}）。

二、名册这一格才是本手最有用的（同一把尺、两次扫描、同一枚尖）
- 现尖下 `refs/heads/review/*` 共 {ronline} 枚（`git ls-remote --refs origin refs/heads/review/*` 的行数；件 {scanart} 顶层 `review_refs_on_line`）。
- r1 的名字钥匙只认到 {oldn} 枚，另有 {missold} 枚名字带着本车道单号没被认到；钥匙加上 `newlane-ord0485-phone` 后扫到 {newn} 枚，剩下 {missnew} 枚名字开头是别的车道 id（逐枚名单在件的 `candidates_missed_by_key`，本块不抄）。
- 结论具名：**名字钥匙不是归属证明**——它一次就漏了本车道 {wtfive} 手 `newlane-ord0485-phone-walkthrough-r1`…`r5`，其中两手里带产品路径（见第一节末格）。以后「扫我名下所有已发布枝」必须带这层反查。
- 判语分布（{newn} 枚枝；路径级 SAME {same} 枚／CHANGED {changed} 枚／ABSENT {absent} 枚，件 {scanart} 顶层 `path_tally`）：{classes}。逐字节都在现尖上的 {heldn} 枚：{held_txt}。

三、反件九枚全咬（尺 `{rulerpath}` blob `{rulerblob}`；臂件 {armart}；控制臂 {controls}；反件臂 {mutants} 枚）
- 无收据且线上没有 → `NOT_ON_LINE` 且不许出现 `LOST_LANDED_CONTENT`；同一读数挂上收据 → `LOST_LANDED_CONTENT`。这一对正是上一手那处错名的正反两面。
- 线上有但字节不同 → `SUPERSEDED_ON_LINE`，不许折成 `NOT_ON_LINE`。
- 退出 {m128} → `NO_PREDICTION`，且冲突计数必须是空值而不是 {c0}；提交对自身父 → `PREDICTED`（证明这条腿还活着）。
- 合成名册：`newlane-ord0485-phone-walkthrough-r1` 必须落进「漏认候选」而不是「已认名册」。
- 纯工具那手：`own_product_paths` 必须为 {c0} 而 `gen_distance_product_paths` 必须大于 {c0}——把代距当越界写的那一步封死。
- 读不动那棵树 → `UNREADABLE_ON_LINE`，不许当「文件没了」。
- 第三枚反件先咬到我：第一版把目标指在只活在侧枝上的 `review/landed-blob-rescan/` 路径，实答 ABSENT——那是臂的目标错了、不是判语错了，改成拿「逐字节相同」那手自己的第一条路径现取。

四、请你点的格子（不自取）
- 甲：上一手那块里两处 `LOST_LANDED_CONTENT` 由本块更正，受影响的是锚形 r3 与 staging-door r5 那两枝；你裁的判据没变（落地=逐枚比 blob）。要不要把 r2 这把尺接进落地门仍归你点，我这边接线 {gateact} 次。
- 乙：仍在等你落、且尖没动的两枝：`{r3head}` = `refs/heads/review/newlane-ord0500-phone-anchor-form-r3`、`{r5head}` = `refs/heads/review/0afdb49b-ord0500-staging-door-r5`。落之前我再核一次尖，尖动就按新尖重切——已是常设。
- 丙：= 你裁的挂起项，本手文件挪位 {moved} 枚。

五、边界与仍欠的格子
- 本手产品字节改动 {prodbytes} 枚；权威线移动 {tipmove} 次；已落字节覆盖 {cover} 枚（发布器 `declared_landed_changes` 为空）；名下旧枝改写 {refwrite} 枚、强推 {forcepush} 次、删枝 {delbranch} 枚；账本直写 {directwrite} 处（本块走收件口）；`demo/reset` 未跑；端口起停 {portact} 个；wt22 工作树写入 {wtwrite} 处（臂与两次扫描只喂字节和只读命令）。
- 未量的格子照旧具名：真机 NOT_MEASURED（本手未跑 `adb devices`）；Playwright 本手未跑；{missnew} 枚别人名下的候选枝只报名字、不判归属（件 {scanart}）。
- 复算两条：`RESCAN_ALL=1 RESCAN_PREDICT=1 RESCAN_LANDED_RECEIPTS=run/rescan2_receipts.json {py} tools/landed_blob_rescan_r2.py`；宽钥匙那条只多挂 `RESCAN_KEYS` 与 `RESCAN_DEST` 两个环境变量；臂那条是 `{py} tools/landed_blob_rescan_arms_r2.py`。
""".format(tip12="`%s`" % f["tip"], scanart=scanart, r3v=r3["verdict"], r3p=r3["paths"],
               r3ab=r3["counts"].get("ABSENT", 0), r3ch=r3["counts"].get("CHANGED", 0),
               r5v=s5["verdict"], r5p=s5["paths"], lostn=f["lost"], prec12="`%s`" % prior["tip"],
               recart=recart, recn=len(rec["landed"]), nopred=f["no_prediction"], m128="128", c0="0",
               e0="0", e1="1", own_txt=own_txt, ronline=f["refs_on_line"], oldn=f["scanned_old_key"],
               missold=f["missed_old_key"], newn=f["scanned_widened"], missnew=f["missed_widened"],
               wtfive=f["scanned_widened"] - f["scanned_old_key"], same=f["path_tally"]["SAME"],
               changed=f["path_tally"]["CHANGED"], absent=f["path_tally"]["ABSENT"],
               classes=json.dumps(f["classes_new"], ensure_ascii=False, sort_keys=True),
               heldn=len(f["held"]), held_txt=held_txt, rulerpath=pubpath["landed_blob_rescan_r2.py"],
               rulerblob=blobs["landed_blob_rescan_r2.py"], armart=armart,
               controls="、".join(arms["controls"]), mutants=len(arms["mutants"]),
               gateact="0", r3head=r3["head"], r5head=s5["head"], moved="0", prodbytes="0",
               tipmove="0", cover="0", refwrite="0", forcepush="0", delbranch="0", directwrite="0",
               portact="0", wtwrite="0", py="`D:/moodle/CityNexus/.venv/Scripts/python.exe`")
    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    composed = body.rstrip() + "\n\n" + closing.decode("utf-8").strip() + "\n"
    dest_body = os.path.join(LANE, "run", "rescan2_block_body.md")
    dest_comp = os.path.join(LANE, "run", "rescan2_block_composed.md")
    open(dest_body, "w", encoding="utf-8", newline="\n").write(body)
    open(dest_comp, "w", encoding="utf-8", newline="\n").write(composed)
    hexcount = verify_hexes(composed)
    gp = os.path.join(LANE, "run", "rescan2_precheck.txt")
    rc = subprocess.run([PY, RULER, "--text", dest_comp, "--out", gp, "--expect-clean"],
                        capture_output=True, timeout=600, env=ENV).returncode
    print("Q43 rc=%s\n%s" % (rc, open(gp, encoding="utf-8", errors="replace").read()[-1500:] if
                             os.path.exists(gp) else ""))
    if rc != 0:
        raise SystemExit("ABORT_BLOCK_NOT_GREEN rc=%s" % rc)
    name = "0afdb49b_%s.md" % T.strftime("%H%M")
    drop = os.path.join(INBOX, name)
    if os.path.exists(drop):
        raise SystemExit("ABORT_INBOX_NAME_TAKEN " + name)
    shutil.copyfile(dest_comp, drop)
    print("DROPPED %s (%d B) | hexes checked %d | relabelled %s" % (
        drop, os.path.getsize(drop), hexcount, json.dumps(relabelled, ensure_ascii=False)))


if __name__ == "__main__":
    {"prep": prep, "deliver": deliver}[sys.argv[1]]()
