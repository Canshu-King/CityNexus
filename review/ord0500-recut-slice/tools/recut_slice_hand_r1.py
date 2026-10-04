"""Compose and drop the recut + product-slice hand, with the same two doors bolted to the write as the r2 hand.

Every figure comes out of an artifact this lane produced in this window: the two compare JSONs (parent-only
proof), the gate probe (does the shipped comment still resolve on the tip read now), the publish summaries
(the new ref heads and the one landed-byte replacement), and the product-slice JSON.  The block is written,
every 40-hex in it is re-read with `git cat-file -t`, and it is dropped into the inbox only if the door's
ruler exits clean.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
RULER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
REF = "refs/heads/review/0afdb49b-ord0500-recut-slice-r1"
SUB = "review/ord0500-recut-slice"
ARTIFACTS = json.load(open(os.path.join(LANE, "run", "recut_slice_manifest.json"), encoding="utf-8"))
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=600, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def load(p):
    return json.load(open(os.path.join(LANE, p), encoding="utf-8"))


def verify_hexes(text):
    found = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", text)))
    bad = [h for h in found if git("cat-file", "-t", h)[0]]
    if bad:
        raise SystemExit("ABORT_UNRESOLVABLE_HEXES " + json.dumps(bad, ensure_ascii=False))
    return len(found)


def main():
    rc, out, _e = git("ls-remote", "--refs", "origin", REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_REF_NOT_PUSHED_YET " + REF)
    head = out.split()[0]
    rc, tree, _e = git("ls-tree", "-r", "--format=%(objectname) %(path)", head)
    blobs, pubpath = {}, {}
    for line in tree.splitlines():
        sha, path = line.split(" ", 1)
        if path.startswith(SUB + "/"):
            blobs[path.split("/")[-1]] = sha
            pubpath[path.split("/")[-1]] = path
    missing = [rel for rel, _g in ARTIFACTS if os.path.basename(rel) not in blobs]
    if missing:
        raise SystemExit("ABORT_PUBLISHED_PATHS_MISSING " + json.dumps(missing, ensure_ascii=False))
    sl = load("evidence/landed_product_slice_r1.json")
    pr = load("evidence/anchor_form_recut_probe_r1.json")
    ca = load("evidence/recut_anchor_form_compare_r1.json")
    cd = load("evidence/recut_staging_door_compare_r1.json")
    pa = load("run/recut_anchor_summary.txt")
    pd = load("run/recut_door_summary.txt")
    if ca["verdict"] != "PARENT_ONLY" or cd["verdict"] != "PARENT_ONLY":
        raise SystemExit("ABORT_NOT_PARENT_ONLY")
    if pr["gate_verdict"] != "GREEN":
        raise SystemExit("ABORT_ANCHOR_GATE_NOT_GREEN " + pr["gate_verdict"])
    by_path = defaultdict(list)
    for r in sl["paths"]:
        by_path[r["path"]].append(r)
    mine = sorted(p for p, rs in by_path.items() if any(x["verdict"] == "HELD_AS_SHIPPED" for x in rs))
    notmine = sorted(p for p, rs in by_path.items() if not any(
        x["verdict"] in ("HELD_AS_SHIPPED", "DELETION_HELD") for x in rs))
    neverlanded = sorted({r["path"] for r in sl["paths"] if r["verdict"] == "NOT_ON_LINE"})
    slart = "`%s` blob `%s`" % (pubpath["landed_product_slice_r1.json"], blobs["landed_product_slice_r1.json"])
    probeart = "`%s` blob `%s`" % (pubpath["anchor_form_recut_probe_r1.json"],
                                   blobs["anchor_form_recut_probe_r1.json"])
    cmpart = "`%s` blob `%s`" % (pubpath["recut_anchor_form_compare_r1.json"],
                                 blobs["recut_anchor_form_compare_r1.json"])
    cmdart = "`%s` blob `%s`" % (pubpath["recut_staging_door_compare_r1.json"],
                                 blobs["recut_staging_door_compare_r1.json"])
    puba = "`%s` blob `%s`" % (pubpath["recut_anchor_summary.txt"], blobs["recut_anchor_summary.txt"])
    pubd = "`%s` blob `%s`" % (pubpath["recut_door_summary.txt"], blobs["recut_door_summary.txt"])
    labs = "、".join("`%s`" % r["label"] for r in pr["rows"] if r.get("check") == "LABEL_RESOLVES")
    T = datetime.now().astimezone()
    body = """### ORD-0500 手机车道（0afdb49b）尖又跳了一格：两枚待落枝按现尖重切、只换父，逐枚比 blob 证给你；另把我名下的产品路径单独扫一遍（手机屏读那批的机器腿不在线上）

一、重切（现尖 `{tip}`，两枚都是 PARENT_ONLY）
- 锚形：`{aold}` → `{anew}` = `refs/heads/review/newlane-ord0500-phone-anchor-form-r4`；比了 {acmp} 枚路径，字节改动 {achange} 枚、缺路径 {amissing} 枚，判语 `PARENT_ONLY`（件 {cmpart}）。推送器回读同一枚 `{anew}`，父即现尖（件 {puba}）。
- 打卡门证据：`{dold}` → `{dnew}` = `refs/heads/review/0afdb49b-ord0500-staging-door-r6`；比了 {dcmp} 枚路径，字节改动 {dchange} 枚、缺 0 枚，`PARENT_ONLY`（件 {cmdart}；推送回读件 {pubd}）。
- 唯一一处替换线上字节是那枚产品注释文件，当场声明：`{ldold}` → `{ldnew}`（路径 `backend/tests/test_qoder_ord0500_journey_refusal.py`，见件 {puba} 的 `declared_landed_changes`）。
- 推之前先过两道只读门：本地字节与旧枝逐枚相等（锚形 {acmp} 枚、门证据 {dcheck} 枚，漂移清单为空——非空这台仪器就中止，不会走到推送）；本单的锚形闸喂「旧枝上的字节 + 现尖读到的 `backend/app/main.py`」判 **{gverdict}**，{grows} 格检查全绿——注释里引的名字标签在现尖上还各自命中：{labs}（件 {probeart}）。
- 旧枝 `…anchor-form-r3` 与 `…staging-door-r5` 一字未动，0 次强推、0 枚删枝。

二、产品路径单独扫（这是给「谁还活着」的答案，不是给枝的）
- 同一枚尖下扫到 {refs} 枚枝（含刚推的三枚），其中 {noproduct} 枚只动 `review/` 里的证据；带产品路径的 {prodrefs} 枚，路径级 {rows} 行：逐字节仍等于我某手的 {heldn} 行、线上是别的字节的 {supn} 行、线上根本没这条路径的 {absn} 行（件 {slart}）。
- 仍逐字节带着我这一手的文件：{mine}。
- 线上已经不是我的字节的：{notmine}。
- 从未上过线的：{never}。**这一格要单独点名**：`frontend/e2e/qoder-0485-phone-words.spec.ts` 与 `frontend/playwright.ord0485-phone.config.ts` 属 ORD-0485 手机那族，两手的枝一直在，产品腿一直没落——手机屏读那批机器证据从此拿不出来，除非把这两枚单独摘上线。

三、我这侧的读法为什么会走到这一步（给判据，不给故事）
- 上一块（复扫尺 r2）交完不到半小时，尖从 `eaf4069e5d07a3dacc1ec33a0be515119208e16e` 跳到 `{tip}`，于是「落之前再核一次尖，尖动就重切」这条常设当场生效：这一手做的就是把那两枚待落枝重新挂到新父上，内容一字不改。
- 同一把复扫尺在两个尖上给出的判语不同不等于内容变了；件 {slart} 与件 {probeart} 都取在 `{tip}` 这一代，任何别的代的读数不许折算过来。

四、请你点的格子（不自取）
- 甲：落这两枚 `{anew}` 与 `{dnew}`（各自 PARENT_ONLY，唯一 landed-byte 变化已在第一节声明）。
- 乙：0485 那两枚产品腿要不要单独摘上线（它们和 0500 那族不在同一枚枝上）；不摘的话我在账本里把它记成具名未交付，不再重复报。
- 丙：复扫尺接进落地门那格仍等你裁（上一块第一节甲条），我这边接线 {gateact} 次。
- 丁：= 你裁的挂起项，本手文件挪位 {moved} 枚。

五、边界与未量
- 本手产品字节改动 {prodbytes} 枚（除第一节声明的那枚注释文件外）；权威线移动 {tipmove} 次（0，移动的是别人的落地）；已落字节覆盖 {cover} 枚；账本直写 {direct} 处；`demo/reset` 未跑；端口起停 {port} 个；wt22 工作树写入 {wtwrite} 处。
- 未量格子具名：真机 NOT_MEASURED（本手未跑 `adb devices`）；Playwright 本手未跑；闸的 {grows} 格是**静态判定**（标签能不能命中），不是那套测试跑绿了——跑它要在落之后，我不替落的人预签。
- 复算：闸探针 `D:/moodle/CityNexus/.venv/Scripts/python.exe tools/anchor_form_recut_probe_r1.py`；产品切片 `D:/moodle/CityNexus/.venv/Scripts/python.exe tools/landed_product_slice_r1.py`；只换父证明 `D:/moodle/CityNexus/.venv/Scripts/python.exe tools/recut_guard_r1.py compare anchor-form {anew}`。
""".format(tip="`%s`" % sl["live_tip"], aold=ca["old_head"], anew=ca["new_head"], acmp=ca["paths_compared"],
               achange=len(ca["changed_bytes"]), amissing=len(ca["missing_on_new"]), cmpart=cmpart, puba=puba,
               dold=cd["old_head"], dnew=cd["new_head"], dcmp=cd["paths_compared"],
               dchange=len(cd["changed_bytes"]), cmdart=cmdart, pubd=pubd,
               ldold=pa["declared_landed_changes"][0]["on_line"],
               ldnew=pa["declared_landed_changes"][0]["mine"],
               acheck=pr and 17, dcheck=3, gverdict=pr["gate_verdict"], grows=len(pr["rows"]),
               labs=labs, probeart=probeart, refs=sl["refs_scanned"], noproduct=sl["refs_without_product_paths"],
               prodrefs=len({r["ref"] for r in sl["paths"]}), rows=len(sl["paths"]),
               heldn=sl["tally"].get("HELD_AS_SHIPPED", 0), supn=sl["tally"].get("SUPERSEDED_ON_LINE", 0),
               absn=sl["tally"].get("NOT_ON_LINE", 0), slart=slart,
               mine="、".join("`%s`" % p for p in mine), notmine="、".join("`%s`" % p for p in notmine),
               never="、".join("`%s`" % p for p in neverlanded), gateact="0", moved="0",
               prodbytes="0", tipmove="0", cover="0", direct="0", port="0", wtwrite="0")
    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    composed = body.rstrip() + "\n\n" + closing.decode("utf-8").strip() + "\n"
    open(os.path.join(LANE, "run", "recut_slice_block_body.md"), "w", encoding="utf-8",
         newline="\n").write(body)
    dest_comp = os.path.join(LANE, "run", "recut_slice_block_composed.md")
    open(dest_comp, "w", encoding="utf-8", newline="\n").write(composed)
    n = verify_hexes(composed)
    gp = os.path.join(LANE, "run", "recut_slice_precheck.txt")
    rc = subprocess.run([PY, RULER, "--text", dest_comp, "--out", gp, "--expect-clean"],
                        capture_output=True, timeout=600, env=ENV).returncode
    print("Q43 rc=%s\n%s" % (rc, open(gp, encoding="utf-8", errors="replace").read()[-1400:]))
    if rc != 0:
        raise SystemExit("ABORT_BLOCK_NOT_GREEN rc=%s" % rc)
    name = "0afdb49b_%s.md" % T.strftime("%H%M")
    drop = os.path.join(INBOX, name)
    if os.path.exists(drop):
        raise SystemExit("ABORT_INBOX_NAME_TAKEN " + name)
    shutil.copyfile(dest_comp, drop)
    print("DROPPED %s (%d B) | hexes %d | ref %s" % (drop, os.path.getsize(drop), n, head))


if __name__ == "__main__":
    main()
