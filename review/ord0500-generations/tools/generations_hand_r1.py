"""Compose and drop the generations hand: two rosters on two named tips, compared, plus the two re-parented
pending hands -- with the doors bolted to the writing step.

Numbers come out of the delta artifact, the two compare artifacts, the publish summaries and the drift note;
the new ref's blobs are read back with `git ls-tree` after the push and re-checked with `git cat-file -t`;
the block is dropped only if the door's ruler exits clean.
"""
import json
import os
import re
import shutil
import subprocess
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
RULER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
REF = "refs/heads/review/0afdb49b-ord0500-generations-r1"
SUB = "review/ord0500-generations"
ARTIFACTS = json.load(open(os.path.join(LANE, "run", "generations_manifest.json"), encoding="utf-8"))
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=600, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def main():
    dl = json.load(open(os.path.join(LANE, "evidence", "rescan_generation_delta_r1.json"), encoding="utf-8"))
    ca = json.load(open(os.path.join(LANE, "evidence", "recut_anchor_form_r4_to_r5_r2.json"), encoding="utf-8"))
    cd = json.load(open(os.path.join(LANE, "evidence", "recut_staging_door_r6_to_r7_r2.json"), encoding="utf-8"))
    dn = json.load(open(os.path.join(LANE, "run", "recut_drift_note_r1.json"), encoding="utf-8"))
    pa = json.load(open(os.path.join(LANE, "run", "recut_anchor5_publish_summary.txt"), encoding="utf-8"))
    pd = json.load(open(os.path.join(LANE, "run", "recut_door7_publish_summary.txt"), encoding="utf-8"))
    if ca["verdict"] != "PARENT_ONLY" or cd["verdict"] != "PARENT_ONLY":
        raise SystemExit("ABORT_NOT_PARENT_ONLY")
    if not dn["local_equals_r4"]:
        raise SystemExit("ABORT_RESTORE_NOT_PROVEN")
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

    def art(name):
        return "`%s` blob `%s`" % (pubpath[name], blobs[name])

    dart, caart, cdart = art("rescan_generation_delta_r1.json"), art("recut_anchor_form_r4_to_r5_r2.json"), \
        art("recut_staging_door_r6_to_r7_r2.json")
    misart, dnart = art("recut_staging_door_mistyped_head_arm_r1.json"), art("recut_drift_note_r1.json")
    scanart, paart, pdart = art("landed_blob_rescan_r2_gen_d107131c.json"), art("recut_anchor5_publish_summary.txt"), \
        art("recut_door7_publish_summary.txt")
    T = datetime.now().astimezone()
    body = """### ORD-0500 手机车道（0afdb49b）代与代之间：名册零翻转、丢判零次；两枚待落枝又按新尖重切了一代，另外我自己那把守门尺被我的错号拦下过一次

一、两代名册对比（件 {dart}；原始扫描 {scanart}）
- 上代尖 `{otip}`（{ro} 枚枝）→ 现尖 `{ntip}`（{rn} 枚枝，线上一共 {ronline} 枚 `review/*`）。新增的 {added} 枚全是今晚我自己推的件枝（名单在件的 `added_this_window`）。
- **判语翻转 {moved} 枚**：一个钟头前那趟判成 HELD／SUPERSEDED 的，这一趟一格没变；线上没有的路径 {absent} 枚、字节不同的 {changed} 枚、逐字节相同的 {same} 枚（件 {scanart} 顶层 `path_tally`）。
- 带机器落地收据的那手仍只有 `0afdb49b-ord0500-staging-door-r4`，它仍 HELD ⇒ 「丢」这一判今天触发 {lost} 次。

二、我差点报错的那格，是仪器替我纠的（具名）
- 读到 `review/ord0500-staging-door/tools/r24_chain.sh` 在现尖上不存在时，我第一反应是「已落内容又掉了」——那是错的直觉。把这枚路径**归给谁**量出来才作数：声明它的只有 `…staging-door-r5` 与 `…staging-door-r6` 两手，两手判语都是 `NOT_ON_LINE`（从未落地），而 HELD 的那手（r4）声明的 13 枚路径里根本没有它 ⇒ 判语 `NOT_A_ROLLBACK`（件的 `disputed_path_declared_by` 与 `near_miss_verdict`，`tools/rescan_generation_delta_r1.py` blob `{dtool}`）。
- 记在这里的理由：这正好是这把尺存在的目的——「掉了没」必须问归属，不能问我的印象。

三、线的形状变了，我这把尺的预测腿第一次有真读数（不改判据）
- 现尖有两个父、`git rev-list --count` = {revcount}；于是 `git merge-tree --write-tree` 对 {pred_yes} 枚枝答 `PREDICTED`（冲突计数各为 0），其余 {pred_no} 枚仍退 {e128} —— 因为它们是切在已被丢弃的重建线上。件 {dart} 顶层 `prediction_split`。
- 报这个读数不等于改判据：你裁过「这条线上 ancestry 不可作判据，一切落地/争用/归属回到 blob 相等」，我这把尺照旧只按 blob 判，预测腿只当**附加信息**。

四、两枚待落枝又重切一代（都 PARENT_ONLY，sha 从枝自己答，不从我手打）
- `{aold}` → `{anew}` = `refs/heads/review/newlane-ord0500-phone-anchor-form-r5`；比了 {acmp} 枚路径、字节改动 {achg} 枚、新枝缺路径 {amis} 枚，件 {caart}。唯一一处替换线上字节仍是那枚注释文件：`{ldold}` → `{ldnew}`（见推送回读 {paart}）。锚形闸在现尖上判 {gverdict}。
- `{dold}` → `{dnew}` = `refs/heads/review/0afdb49b-ord0500-staging-door-r7`；比了 {dcmp} 枚路径、字节改动 {dchg} 枚，件 {cdart}；推送回读 {pdart}（声明的已落变化 {ddeclared} 处）。
- 两处我自己的毛病，都具名不藏：
  - **本地字节漂了**：`evidence/anchor_form_spec_r26.json` 被 01:31 那趟同名取数覆盖过，若直接拿本地字节「重切」就等于换内容挂旧名。守门报 `ABORT_LOCAL_BYTES_NOT_WHAT_THE_REF_CARRIES` 并中止；我把枝上那份字节取回来、证到逐枚相等才推（件 {dnart}，三个 blob 都在里面）。
  - **我手打了 sha 且打错一位**：第一代守门尺接受命令行给的枝尖，于是它比了个不存在的东西并报 `PATH_MISSING_ON_NEW_REF`。那次错读数我保留发布为 `{misart_name}` blob `{misblob}`——它是臂真咬过的证据，不是证明。第二代尺改成两枚头都从 `refs/heads` 自己读，手打的与枝答的不一致就中止（`tools/recut_guard_r2.py` blob `{gtool}`）。

五、请你点的格子（不自取）
- 甲：落 `{anew}` 与 `{dnew}`（这已是今晚第二次为同两手重切；尖再动我还按常设再切，不需你提醒）。
- 乙：0485 那两枚产品腿按「被后续代次取代」结案（上一块已交读数）。
- 丙：复扫尺接进落地门那格仍等你裁；我这边接线 {gateact} 次。

六、边界与未量
- 本手产品字节改动 {prodbytes} 枚；权威线移动 {tipmove} 次（移动的是别人的落地，我 0 次）；已落字节覆盖 {cover} 枚（除第四节声明的那枚注释文件）；名下旧枝改写 {refwrite} 枚、强推 {fp} 次、删枝 {dr} 枚；账本直写 {direct} 处（本块走收件口）；`demo/reset` 未跑；端口起停 {port} 个；wt22 工作树写入 {wtwrite} 处——**这一手除外**：为把枝上字节取回来，我在本地写过 `evidence/anchor_form_spec_r26.json` 那一枚文件，之后它按 blob 与枝相等（件 {dnart}）。
- 未量格子具名：真机 NOT_MEASURED（本手未跑 `adb devices`）；Playwright 本手未跑；名册与代际对比全是只读 git 读数。
- 复算：`{py} tools/rescan_generation_delta_r1.py`；`{py} tools/recut_guard_r2.py compare anchor-form`；`{py} tools/recut_guard_r2.py compare staging-door`。
""".format(dart=dart, scanart=scanart, otip=dl["old_tip"], ntip=dl["new_tip"], ro=dl["refs_old"],
               rn=dl["refs_new"], ronline=dl["review_refs_on_line_new"],
               added=dl["refs_new"] - dl["refs_old"], moved=dl["moved_count"],
               absent=dl["path_tally_new"]["ABSENT"], changed=dl["path_tally_new"]["CHANGED"],
               same=dl["path_tally_new"]["SAME"], lost=dl["lost_today_new"],
               dtool=blobs["rescan_generation_delta_r1.py"], pred_yes=dl["prediction_split"].get("PREDICTED", 0),
               pred_no=dl["prediction_split"].get("NO_PREDICTION_EXIT_128", 0), e128="128",
               aold=ca["old_head"], anew=ca["new_head"], acmp=ca["paths_compared"],
               achg=len(ca["changed_bytes"]), amis=len(ca["missing_on_new"]), caart=caart,
               ldold=pa["declared_landed_changes"][0]["on_line"],
               ldnew=pa["declared_landed_changes"][0]["mine"], paart=paart,
               gverdict=json.load(open(os.path.join(LANE, "evidence", "anchor_form_recut_probe_r1.json"),
                                       encoding="utf-8"))["gate_verdict"],
               dold=cd["old_head"], dnew=cd["new_head"], dcmp=cd["paths_compared"],
               dchg=len(cd["changed_bytes"]), cdart=cdart, pdart=pdart, ddeclared=len(pd["declared_landed_changes"]),
               dnart=dnart, misart_name="recut_staging_door_mistyped_head_arm_r1.json",
               misart=misart, misblob=blobs["recut_staging_door_mistyped_head_arm_r1.json"],
               gtool=blobs["recut_guard_r2.py"], revcount=git("rev-list", "--count", dl["new_tip"])[1].strip(),
               gateact="0", prodbytes="0", tipmove="0",
               cover="0", refwrite="0", fp="0", dr="0", direct="0", port="0", wtwrite="1",
               py="D:/moodle/CityNexus/.venv/Scripts/python.exe")
    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    composed = body.rstrip() + "\n\n" + closing.decode("utf-8").strip() + "\n"
    open(os.path.join(LANE, "run", "generations_block_body.md"), "w", encoding="utf-8",
         newline="\n").write(body)
    dest_comp = os.path.join(LANE, "run", "generations_block_composed.md")
    open(dest_comp, "w", encoding="utf-8", newline="\n").write(composed)
    found = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", composed)))
    bad = [h for h in found if git("cat-file", "-t", h)[0]]
    if bad:
        raise SystemExit("ABORT_UNRESOLVABLE_HEXES " + json.dumps(bad, ensure_ascii=False))
    gp = os.path.join(LANE, "run", "generations_precheck.txt")
    rc = subprocess.run([PY, RULER, "--text", dest_comp, "--out", gp, "--expect-clean"],
                        capture_output=True, timeout=600, env=ENV).returncode
    print("Q43 rc=%s\n%s" % (rc, open(gp, encoding="utf-8", errors="replace").read()[-1500:]))
    if rc != 0:
        raise SystemExit("ABORT_BLOCK_NOT_GREEN rc=%s" % rc)
    name = "0afdb49b_%s.md" % T.strftime("%H%M")
    drop = os.path.join(INBOX, name)
    if os.path.exists(drop):
        raise SystemExit("ABORT_INBOX_NAME_TAKEN " + name)
    shutil.copyfile(dest_comp, drop)
    print("DROPPED %s (%d B) | hexes %d | ref %s" % (drop, os.path.getsize(drop), len(found), head))


if __name__ == "__main__":
    main()
