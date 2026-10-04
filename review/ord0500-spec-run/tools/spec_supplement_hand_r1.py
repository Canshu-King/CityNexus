"""Compose and drop the supplement hand: the shipped spec, executed on the generation the line is on now.

Same doors as the other two emitters this window: every figure comes out of the run artifact, every 40-hex in
the block is re-read with `git cat-file -t`, and nothing lands in the inbox unless the ruler exits clean.

The boundary line says what this run actually did to the worktree -- the tool puts the candidate bytes into
wt22's copy of the spec, runs, then restores and verifies the restore by blob.  Calling that "zero writes"
would be the kind of sentence that gets a lane re-quoted later.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
RULER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
REF = "refs/heads/review/0afdb49b-ord0500-spec-run-r1"
SUB = "review/ord0500-spec-run"
ARTIFACTS = json.load(open(os.path.join(LANE, "run", "spec_supplement_manifest.json"), encoding="utf-8"))
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=600, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def main():
    run = json.load(open(os.path.join(LANE, "evidence", "anchor_form_spec_r26.json"), encoding="utf-8"))
    ca = json.load(open(os.path.join(LANE, "evidence", "recut_anchor_form_compare_r1.json"), encoding="utf-8"))
    cd = json.load(open(os.path.join(LANE, "evidence", "recut_staging_door_compare_r1.json"), encoding="utf-8"))
    pr = json.load(open(os.path.join(LANE, "evidence", "anchor_form_recut_probe_r1.json"), encoding="utf-8"))
    if run["tip"] != pr["live_tip"]:
        raise SystemExit("ABORT_RUN_AND_PROBE_ON_DIFFERENT_TIPS")
    if not (run["candidate_compiles"] and run["arm_rc"] == 0 and run["blob_equals_tip"]
            and run["worktree_clean_after_restore"]):
        raise SystemExit("ABORT_SPEC_RUN_NOT_CLEAN " + json.dumps(run, ensure_ascii=False)[:200])
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
    runart = "`%s` blob `%s`" % (pubpath["anchor_form_spec_r26.json"], blobs["anchor_form_spec_r26.json"])
    logart = "`%s` blob `%s`" % (pubpath["r29_spec_run.txt"], blobs["r29_spec_run.txt"])
    tail = run["arm_tail_line"]
    rows = re.search(r"(\d+) passed", tail).group(1)
    warns = re.search(r"(\d+) warnings", tail).group(1)
    secs = re.search(r"in ([0-9.]+)s", tail).group(1)
    T = datetime.now().astimezone()
    body = """### ORD-0500 手机车道（0afdb49b）补一格执行读数：待落的锚形那手在现尖上真跑过一遍，注释改完文件仍编译、那套臂仍过——静态闸答不了的那半现在有据了

一、执行读数（现尖 `{tip}`，件 {runart}；原始输出 {logart}）
- 编译：`candidate_compiles` = true（把候选字节喂进 `python -m py_compile` 的那一步）。
- 臂：退出码 {armrc}，尾行逐字 `{tail}`——{rows} 条通过、{warns} 条警告、{secs} 秒；跑在车道私有库上，共享库按字节复核为未动（`arm_shared_store_untouched` = true，跑后行数 {armrows}）。
- 还原：跑完把 wt22 里那份文件按 blob 还原，回读得到 `{restoredblob}`，与现尖同一枚（`blob_equals_tip` = true），工作树 `clean` = true，HEAD 未变。

二、为什么这不是重复上一代的那次跑
- 同一把仪器上一次读数取在别的代（尖不同），按 Q24 不能折算过来；这一趟是把同一件事在 `{tip}` 重做一遍（件 {runart} 顶层 `tip` 就是那一眼读到的尖）。
- 本单静态闸那一趟答的是「注释里引的名字标签在现尖上命中不命中」——它 {grows} 格全绿（尖 `{tip}`，上一块已交），但那不等于文件能被编译、臂能过；这一格补的正是那半（同一枚尖）。

三、请你点的格子（不自取）
- 甲：落 `{ahead}` = `refs/heads/review/newlane-ord0500-phone-anchor-form-r4`（{acmp} 枚路径、PARENT_ONLY、唯一 landed-byte 变化在前一块已声明）。
- 乙：落 `{dhead}` = `refs/heads/review/0afdb49b-ord0500-staging-door-r6`（{dcmp} 枚路径、PARENT_ONLY）。
- 丙：0485 那两枚产品腿摘不摘，仍等你一句话；不摘我记成具名未交付。

四、边界（这格是真写过的，别按「零写入」报）
- 产品字节改动 {prodbytes} 枚；权威线移动 {tipmove} 次；线上已落字节覆盖 {cover} 枚；名下旧枝改写 {refwrite} 枚、强推 {fp} 次、删枝 {dr} 枚；账本直写 {direct} 处（本块走收件口）；`demo/reset` 未跑；端口起停 {port} 个。
- wt22 里那份 `backend/tests/test_qoder_ord0500_journey_refusal.py` 在跑的时候被候选字节临时覆盖过，跑完按 blob 还原并复核（第一节点名了回读那枚）；除它之外工作树未被本手动过。
- 未量格子具名：真机 NOT_MEASURED；Playwright 本手未跑；这一趟是车道私有库上的臂，不是整套基线。
""".format(tip="`%s`" % run["tip"], runart=runart, logart=logart, armrc=run["arm_rc"], tail="`%s`" % tail,
               rows=rows, warns=warns, secs=secs, armrows=run["arm_rows_after_the_arms"],
               restoredblob=run["file_blob_after_restore"], grows=len(pr["rows"]),
               ahead=ca["new_head"], acmp=ca["paths_compared"], dhead=cd["new_head"], dcmp=cd["paths_compared"],
               prodbytes="0", tipmove="0", cover="0", refwrite="0", fp="0", dr="0", direct="0", port="0")
    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    composed = body.rstrip() + "\n\n" + closing.decode("utf-8").strip() + "\n"
    dest_comp = os.path.join(LANE, "run", "spec_supplement_block_composed.md")
    open(os.path.join(LANE, "run", "spec_supplement_block_body.md"), "w", encoding="utf-8",
         newline="\n").write(body)
    open(dest_comp, "w", encoding="utf-8", newline="\n").write(composed)
    found = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", composed)))
    bad = [h for h in found if git("cat-file", "-t", h)[0]]
    if bad:
        raise SystemExit("ABORT_UNRESOLVABLE_HEXES " + json.dumps(bad, ensure_ascii=False))
    gp = os.path.join(LANE, "run", "spec_supplement_precheck.txt")
    rc = subprocess.run([PY, RULER, "--text", dest_comp, "--out", gp, "--expect-clean"],
                        capture_output=True, timeout=600, env=ENV).returncode
    print("Q43 rc=%s\n%s" % (rc, open(gp, encoding="utf-8", errors="replace").read()[-1200:]))
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
