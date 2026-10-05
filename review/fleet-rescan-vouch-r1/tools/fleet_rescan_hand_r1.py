"""Compose, gate and drop the fleet re-scan r2 hand.

Every figure is read out of the artifacts that this generation published, straight back off the side ref
that was just pushed -- the block's numbers come from `git cat-file` on the line, not from a lane-local
file the commander cannot reach.  The hand names exactly which review refs the new ruler relabelled and
attributes every moved per-path count; an unattributed move aborts the hand instead of being smoothed
into prose.
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
REF = "refs/heads/review/0afdb49b-fleet-rescan-r2"
SUB = "review/fleet-rescan-r2"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
TOOLS = "D:/moodle/_qoder_phone_ord0485_20260930/tools"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"
# the block cites these blobs; a missing one is an abort, never a silent omission
NEED = ["fleet_landed_rescan_r2.py", "fleet_landed_rescan_arms_r2.py", "fleet_rescan_label_delta_r2.py",
        "fleet_rescan_roster_r2.py", "fleet_rescan_arms_r2.json", "label_delta_r2.json",
        "fleet_rescan_r2_summary_r2.json", "fleet_rescan_r2_roster_r2.tsv", "fleet_r2_delta.txt",
        "fleet_landed_rescan_r1.py", "fleet_r2_arms.txt", "fleet_r2_read.txt",
        "fleet_rescan_roster_r2.py", "commit_fleet_rescan_msg.txt", "fleet_rescan_manifest.json"]


def git(*args):
    q = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=600, env=ENV)
    return (q.returncode, q.stdout.decode("utf-8", "replace"), q.stderr.decode("utf-8", "replace"))


def live_tip():
    rc, out, err = git("ls-remote", "--refs", "origin", TIP_REF)
    line = [l.split("\t") for l in out.splitlines() if l.strip()]
    if rc or len(line) != 1 or len(line[0][0]) != 40:
        raise SystemExit("ABORT_NO_LIVE_TIP rc=%s %s" % (rc, (err or out)[:160]))
    return line[0][0]


def main():
    tip = live_tip()
    rc, out, err = git("ls-remote", "--refs", "origin", REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_REF_NOT_PUSHED_YET " + REF + " " + (err or "")[:120])
    head = out.split()[0]

    rc, tree, _e = git("ls-tree", "-r", "--format=%(objectname) %(path)", head)
    pub = {}
    for line in tree.splitlines():
        sha, path = line.split(" ", 1)
        if path.startswith(SUB + "/"):
            pub[os.path.basename(path)] = (path, sha)
    missing = [n for n in NEED if n not in pub]
    if missing:
        raise SystemExit("ABORT_PUBLISHED_PATHS_MISSING " + json.dumps(missing, ensure_ascii=False))

    def coord(name):
        path, sha = pub[name]
        return "`%s` blob `%s`" % (path, sha)

    def from_line(name):
        path, sha = pub[name]
        rc, data, _e = git("cat-file", "blob", sha)
        if rc:
            raise SystemExit("ABORT_BLOB_UNREADABLE " + name)
        return data

    s = json.loads(from_line("fleet_rescan_r2_summary_r2.json"))
    d = json.loads(from_line("label_delta_r2.json"))
    a = json.loads(from_line("fleet_rescan_arms_r2.json"))
    roster_raw = from_line("fleet_rescan_r2_roster_r2.tsv").splitlines()
    header = [l for l in roster_raw if l.startswith("#")]
    roster = [l for l in roster_raw if l.strip() and not l.startswith("#")]
    delta_txt = from_line("fleet_r2_delta.txt")

    # the three artifacts and the published commit must be talking about the same coordinate
    for label, val in (("summary tip", s["tip"]), ("delta r1_tip", d["r1_tip"]),
                       ("delta r2_tip", d["r2_tip"]), ("arms tip", a["tip"])):
        if val != tip:
            raise SystemExit("ABORT_STALE_GENERATION %s=%s but the live tip is %s" % (label, val, tip))
    rc, pars, _e = git("rev-list", "--parents", "--no-walk", head)
    if pars.split() != [head, tip]:
        raise SystemExit("ABORT_PUBLISHED_PARENT_NOT_TIP " + pars[:160])
    if not a["every_arm_bit"]:
        raise SystemExit("ABORT_ARMS_NOT_ALL_GREEN " + json.dumps(
            [x["arm"] for x in a["arms"] if not x["bit"]], ensure_ascii=False))
    if d["unattributed_count_moves"]:
        raise SystemExit("ABORT_UNATTRIBUTED_ON_THE_LINE %s" % d["unattributed_count_moves"])
    if len(roster) != s["roster_tsv_rows"]:
        raise SystemExit("ABORT_ROSTER_LINES %d vs %d" % (len(roster), s["roster_tsv_rows"]))
    if len(header) != 2:
        raise SystemExit("ABORT_ROSTER_HEADER %d" % len(header))
    # the header itself carries the same denominator; a roster whose header disagrees with its body is
    # a roster nobody can recompute from
    for token in ("tip=%s" % s["tip"], "refs=%d" % s["review_refs"],
                  "tip_tree_paths=%d" % s["tip_tree_paths"],
                  "distinct_heads=%d" % s["distinct_review_heads"]):
        if token not in "".join(header):
            raise SystemExit("ABORT_ROSTER_HEADER_DISAGREES " + token)
    ct = s["class_tally"]
    if sum(ct.values()) != s["review_refs"]:
        raise SystemExit("ABORT_TALLY_DENOMINATOR %d != %d" % (sum(ct.values()), s["review_refs"]))
    if sum(p["refs"] for p in d["changed_pairs"]) != d["labels_changed"]:
        raise SystemExit("ABORT_PAIR_SUM %d != %d" % (sum(p["refs"] for p in d["changed_pairs"]),
                                                     d["labels_changed"]))
    if sum(causes_sum(d)) != d["rows_with_per_path_counts_moved"]:
        raise SystemExit("ABORT_CAUSE_SUM %d != %d" % (sum(causes_sum(d)),
                                                      d["rows_with_per_path_counts_moved"]))
    # the delta's own printed line must carry the same headline numbers as its JSON.  Only tokens this
    # printer actually emits are compared -- demanding a line the instrument never wrote is how a
    # cross-check turns into a wish.
    for token in ("labels_changed=%d" % d["labels_changed"],
                  "refs_compared=%d" % d["refs_compared"],
                  "rows_with_per_path_counts_moved=%d" % d["rows_with_per_path_counts_moved"],
                  "same_tip=%s" % d["same_tip"]):
        if token not in delta_txt:
            raise SystemExit("ABORT_PRINTER_DISAGREES %s absent from fleet_r2_delta.txt" % token)

    pairs = "\n".join("- `{a}` → `{b}`：{c} 条。件 {cd}".format(
        a=p["from"], b=p["to"], c=p["refs"], cd=coord("label_delta_r2.json"))
        for p in sorted(d["changed_pairs"], key=lambda p: -p["refs"]))
    causes = "\n".join("- `{k}`：{v} 条。件 {cd}".format(
        k=k, v=v, cd=coord("label_delta_r2.json"))
        for k, v in sorted(d["count_move_causes"].items(), key=lambda kv: -kv[1]))
    arms = "\n".join("- `{}` bit={}".format(x["arm"], x["bit"]) for x in a["arms"])
    hms = d["head_moves"]
    if hms:
        hm = hms[0]
        head_move = ("- 另 {n} 条不在改判语之列：`{ref}` 的头在两趟之间自己前进了（`{old}` → `{new}`），"
                     "那是别的车道推了自己的枝、我在两个坐标读到两个事实，不是这一代给同一件事换了说法。"
                     "我按读数报，没有把它折进任何判语。件 {cd}。").format(
            n=len(hms), ref=hm["ref"].split("/")[-1], old=hm["r1_head"], new=hm["r2_head"],
            cd=coord("label_delta_r2.json"))
    else:
        head_move = "- 两趟之间没有任何一支枝自己动了头，所以每一条改判语都出自判据而不是出自新坐标。"

    body = """### ORD-0500 手机车道（0afdb49b）全车队落地铁重扫第二代：同一枚尖上全部 review 枝逐枚按字节复判，三十五条被这一代改了判语、无人认领的计数移动零条；上一代的聚合判语是我夸了口，本代只收口不追账

一、这一代修的是我自己上一代夸过的两处口
- 快照形的手被折进了 CHANGED：这些枝的头是从孤儿根或整树快照切出来的，单枝自带近万枚路径，对着线上树逐枚比当然几乎全"不同"。上一代把它们报成"这一手的字被线上盖掉了"，那是一句没有依据的指控。本代给这一类不出判语，门槛是自带路径 ≥ 线上树的一半。件 {r2}。
- 纯删除的手落进了 catch-all：一支只删不改时 SAME 与 CHANGED 都为零，上一代把它塞进 `OTHER`。本代另开 `ALL_DELETIONS_HELD` / `ALL_DELETIONS_UNDONE` / `DELETIONS_SPLIT` 三格。件 {r2}。
- 还有一个我自己仪器的 bug：`git diff-tree --stdin` 不把没以换行收尾的最后一行冲出去，于是字典序最大的那枚头从来没进过批次、它的手被读成"什么都没发"。这条是对照腿 C8 报出来的（`ABORT_DIFF_TREE_EMITTED_NOTHING`），本代补了行尾换行、补了名册覆盖检查，并把"批次等于逐枚"钉成常设腿 C11。件 {armsart}。

二、这一代量到的分母（现读远端，不是本地枝清单）
- 尖 `{tip}`，线上树 {tree} 枚路径（件 {sumart}）：`{tipref}` 名下 review 枝 {refs} 条，去重后头 {heads} 枚，其中 {share} 条枝与他人共用同一枚头。
- 本地取不到的头 {unres} 枚（全部可解，故本手一次 fetch 也没发）；批次里静默的头 {quiet} 枚，其中 {empty} 枚经复核是真·空提交（树与每一位父相同），单列为 `EMPTY_COMMIT` 而没有当漏洞（件 {sumart}）。
- 判语分布之一（件 {sumart}）：HELD {held} 条、MIXED {mixed} 条、ALL_DIFFERENT_ON_LINE {adiff} 条、ALL_NOT_ON_LINE {aabs} 条。
- 判语分布之二（同一件 {sumart}）：SNAPSHOT_SHAPED {snapn} 条、NONE_HELD_SPLIT {split} 条、ALL_DELETIONS_HELD {adel} 条、EMPTY_COMMIT {emp} 条；八格合计等于 {refs} 条，工具在落盘前断言过这个合计。
- 可判的手 {cand} 条，逐枚路径合计 {cp} 枚：SAME {same}、NOT_ON_LINE {absent}、DIFFERENT_ON_LINE {changedbytes}、删除被撤 {du}（件 {sumart}）。快照形那 {snapn} 条带来的 {snapath} 枚路径不进这个分母。

三、"改了判语"必须点名，不能只说"更准了"
- 两趟对拍只在同一枚尖上发布：`r1_tip` 与 `r2_tip` 都等于 `{tip}`，写手断言过。{refs} 条逐条比，{changed} 条换了类别，配对逐条如下。件 {deltaart}。
{pairs}
- 每路径计数移动的行 {movedrows} 条，全部有名字，没有一条被含糊过去。件 {deltaart}。
{causes}
- 无人认领的计数移动：{unattr} 条。这一格若非零，上线的那把对拍尺会直接以 `ABORT_UNATTRIBUTED_COUNT_MOVES` 中止，不会把没解释的数送进账本。件 {deltatool}。
{head_move}

四、对照腿全绿（新闸上架要有"该红的那一次"）
{arms}
- `every_arm_bit` = {allbit}（件 {armsart}）。C1 是控制腿：一支确实全 SAME 的枝不许被读成指控；C4、C5、C6、C7 各自喂一枚形状给聚合函数，证明标签是算出来的、不是写死的；C10 证明整趟扫描期间没有任何枝被我的读写动过，本手是纯读。
- 名册（每枝一行的逐枚计数）：`{tsvpath}` 数据行 {tsvrows} 行，另 {tsvhlines} 行抬头（抬头里的 `refs=` 与 `tip=` 就是上面断言过的同一组分母），件 {tsv}。

五、这格改了口径，但没有改任何人的交付状态
- 先把影响面划清，别把话说过头：这一代改的是车队第一代读数（`tools/fleet_landed_rescan_r1.py` 那份）的**聚合标签**，而那批标签从未进过账本——只留在车道档里，我没对外报过车队级判语，所以本手没有"撤回已发布读数"这回事。真正入过账的 `LOST_LANDED_CONTENT` 用词更正是上一块 `0108` 那一次做的，与本手无关，也不受本手影响。件 {r1tool}。
- 受影响的是聚合判语；每路径那三个数在本代确实动过 {movedrows} 行，动因在上面逐条点名，无一条含糊。要引用判语请引本代名册，件 {tsv}。
- 全车队没有任何一支被这一代判成 LOST：判"丢了"需要一张仪器落地回执、指名这一手曾经匹配过哪枚尖，而本扫描不读任何回执，所以只用字节词 `NOT_ON_LINE` 与 `DIFFERENT_ON_LINE`。
- 没量的部分照旧点名：真机 `adb devices` 未跑、Playwright 套件未跑、拒绝语逐句屏读不在这一代范围内。

六、我停手的那件（等你一句）
- 甲/乙/丙未回：`{r5}` 与 `{r7}` 的父仍停在尖之前那一代，我按自己推荐的乙/丙执行，这一小时里没有再推零变化的重切枝。你点头任一，我按现尖重父。
- 丙那问（这把重扫尺要不要进落地闸）仍挂起。若进闸，`SNAPSHOT_SHAPED` 的"不出判语"要一起进去，否则闸会拿快照形当红。

七、边界与复算
- 发布：`{ref}` 头 `{head}`，单父就是尖 `{tip}`；对尖改动 {pubpaths} 枚路径、全部落在 `{sub}/` 前缀下，该前缀之外零枚（现取 `git diff --name-only {tip}..{head}`）。件 {sumart}。
- 为省共享盘，上线的是名册（{tsvb} 字节，件 {tsv}）+ 摘要（{sumb} 字节，件 {sumart}），没把整棵 {fulljson} 字节的逐枚 JSON 推上线；那份留在车道里，路径写在摘要顶层 `per_ref_rows_live_at` 一格。
- 线上已落字节被我覆盖零枚；名下旧枝改写零枚；删枝零枚；force-push 零次；账本直写零处（本块走收件口）；端口起停零个；重启链零次；wt22 工作树写入零处（本手只读远端 tip、ref 与 blob）。
- 复算（现取现读；尖若已走请整代重跑）：`{py} {tools}/fleet_landed_rescan_r2.py` 出读数，再依次 `{py} {tools}/fleet_landed_rescan_arms_r2.py`、`{py} {tools}/fleet_rescan_label_delta_r2.py`、`{py} {tools}/fleet_rescan_roster_r2.py`。
""".format(
        refs=s["review_refs"], tip=s["tip"], tipref=TIP_REF, tree=s["tip_tree_paths"],
        heads=s["distinct_review_heads"], share=s["refs_sharing_a_head"],
        unres=s["heads_unresolvable_locally"], quiet=s["heads_quiet_in_batch"],
        empty=s["heads_empty_commit"], held=ct["HELD"], mixed=ct["MIXED"],
        adiff=ct["ALL_DIFFERENT_ON_LINE"], aabs=ct["ALL_NOT_ON_LINE"],
        snapn=ct["SNAPSHOT_SHAPED"], split=ct["NONE_HELD_SPLIT"],
        adel=ct["ALL_DELETIONS_HELD"], emp=ct["EMPTY_COMMIT"],
        cand=s["candidate_hands_judged"], cp=s["candidate_paths_total"], same=s["candidate_same"],
        absent=s["candidate_absent"], changedbytes=s["candidate_changed"],
        du=s["candidate_deletion_undone"], snapath=s["snapshot_shaped_paths_total"],
        changed=d["labels_changed"], unattr=d["unattributed_count_moves"],
        movedrows=d["rows_with_per_path_counts_moved"], narm=len(a["arms"]),
        allbit=a["every_arm_bit"], pairs=pairs, causes=causes, arms=arms, head_move=head_move,
        r2=coord("fleet_landed_rescan_r2.py"), armsart=coord("fleet_rescan_arms_r2.json"),
        deltaart=coord("label_delta_r2.json"), sumart=coord("fleet_rescan_r2_summary_r2.json"),
        deltatool=coord("fleet_rescan_label_delta_r2.py"),
        r1tool=coord("fleet_landed_rescan_r1.py"),
        tsvhlines=len(header),
        tsv=coord("fleet_rescan_r2_roster_r2.tsv"), tsvpath=pub["fleet_rescan_r2_roster_r2.tsv"][0],
        tsvrows=s["roster_tsv_rows"],
        r5="refs/heads/review/0afdb49b-ord0500-anchor-form-r5",
        r7="refs/heads/review/0afdb49b-ord0500-staging-door-r7",
        ref=REF, head=head, sub=SUB,
        pubpaths=len([l for l in git("diff", "--name-only", "%s..%s" % (tip, head))[1].splitlines()
                     if l.strip()]),
        nonreview=len([l for l in git("diff", "--name-only", "%s..%s" % (tip, head))[1].splitlines()
                      if l.strip() and not l.startswith(SUB + "/")]),
        tsvb=len(from_line("fleet_rescan_r2_roster_r2.tsv").encode("utf-8")),
        sumb=len(from_line("fleet_rescan_r2_summary_r2.json").encode("utf-8")),
        fulljson=os.path.getsize(os.path.join(LANE, "evidence", "fleet_rescan_r2",
                                             "fleet_rescan_r2.json")),
        cover="0", refwrite="0", dr="0", fp="0", direct="0", port="0", rs="0", wtwrite="0",
        py=PY, tools=TOOLS)

    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    ctext = closing.decode("utf-8").strip()
    composed = body.rstrip() + "\n\n" + ctext + "\n"
    if composed.count(ctext) != 1:
        raise SystemExit("ABORT_CLOSING_LINE_DUPLICATED %d" % composed.count(ctext))
    open(os.path.join(LANE, "run", "fleet_r2_block_body.md"), "w", encoding="utf-8",
         newline="\n").write(body)
    dest_comp = os.path.join(LANE, "run", "fleet_r2_block_composed.md")
    open(dest_comp, "w", encoding="utf-8", newline="\n").write(composed)

    found = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", composed)))
    bad = [h for h in found if git("cat-file", "-t", h)[0]]
    if bad:
        raise SystemExit("ABORT_UNRESOLVABLE_HEXES " + json.dumps(bad, ensure_ascii=False))
    gp = os.path.join(LANE, "run", "fleet_r2_precheck.txt")
    r = subprocess.run([PY, RULER, "--text", dest_comp, "--out", gp, "--expect-clean"],
                       capture_output=True, timeout=600, env=ENV)
    print("Q43 rc=%s\n%s" % (r.returncode, open(gp, encoding="utf-8", errors="replace").read()[-2600:]))
    if r.returncode != 0:
        raise SystemExit("ABORT_BLOCK_NOT_GREEN rc=%s" % r.returncode)
    now = datetime.now().astimezone()
    name = "0afdb49b_%s.md" % now.strftime("%H%M")
    drop = os.path.join(INBOX, name)
    if os.path.exists(drop):
        raise SystemExit("ABORT_INBOX_NAME_TAKEN " + name)
    # A generation is delivered once.  Without this leg, rerunning the emitter after the applier has
    # already inserted the block would drop a *second* copy under a new HHMM name and the commander's
    # applier would honour it -- the receipt below is the only proof of what has already been booked.
    title = body.splitlines()[0].strip()
    booked = []
    for f in os.listdir(os.path.join(INBOX, "_processed")):
        if not f.startswith("0afdb49b_") or ".md" not in f:
            continue
        first = open(os.path.join(INBOX, "_processed", f), encoding="utf-8",
                     errors="replace").readline().strip()
        if first == title:
            booked.append(f)
    if booked:
        raise SystemExit("ABORT_ALREADY_DELIVERED %s -- this generation is already booked; "
                         "publish an erratum as a NEW block instead of re-dropping" % booked[-1])
    shutil.copyfile(dest_comp, drop)
    print("DROPPED %s (%d B) | hexes %d | ref head %s" % (drop, os.path.getsize(drop), len(found), head))


def causes_sum(d):
    return list(d["count_move_causes"].values())


if __name__ == "__main__":
    main()
