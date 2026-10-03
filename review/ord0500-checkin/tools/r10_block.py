"""ORD-0500 r10: the ledger page for the ownership fix, filled only from artifacts this window wrote.

Same discipline as the r8 and r9 emitters (no typed numbers, a missing slot aborts by line, and the page
refuses to post if the authoritative line or my own ref moved after the readings were taken), because the
defect this page is confessing is exactly "a shipped sentence that outran its evidence".
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r9_block as B          # the helpers: load / fmt / slot / sh / pick_sha and the paths
GEN = os.environ.get("R10_GEN") or "r10"
# the ref number and the receipt names move on different clocks: a receipt is named for the generation
# that wrote it into the branch, the ref for the commit the commander reviews.  They are allowed to
# differ, and the page says which is which.
REF_GEN = os.environ.get("R10_REF_GEN") or GEN
MY_REF = "refs/heads/review/newlane-ord0500-phone-checkin-entry-" + REF_GEN
GATE_RECEIPT = "citation_gate_%s.json" % GEN
MUT_RECEIPT = "citation_gate_%s_mutants.json" % GEN
RECHECK_RECEIPT = os.environ.get("RECHECK_RECEIPT") or "day25_anchor_recheck_%s.json" % GEN
ARM_RECEIPT = os.environ.get("ARM_RECEIPT") or "branch_emit_arm_%s.json" % GEN
AUD_RECEIPT = os.environ.get("AUD_RECEIPT") or "citation_audit_%s.json" % GEN
FMT_RECEIPT = os.environ.get("FMT_RECEIPT") or "fmt_lint_%s.json" % GEN
# the exposure pair is NOT re-taken every hand (it needs two swapped builds of the whole face); the
# generation whose receipts this page is quoting is named, and defaults to the one that exists
EXPOSURE_GEN = os.environ.get("EXPOSURE_GEN") or "r14"
RECEIPT_DIR = "review/ord0500-checkin/receipts"
WT = os.path.join(B.LANE, "wt22")
FOREIGN_SPEC = "backend/tests/test_qoder_ord0476_checkins.py"
NL = chr(10)


def main():
    # the paths a readings commit is allowed to differ from the ref head by: this order's own artifacts,
    # all of them rendered from the receipts (R6_READINGS.md included -- the door caught it on the first
    # try, which is exactly the kind of thing that should not be decided by my memory of what is derived)
    ARTIFACT_PREFIXES = ("review/ord0500-checkin/receipts/", "review/ord0500-checkin/run/",
                         "review/ord0500-checkin/tools/", "review/ord0500-checkin/R6_READINGS.md")

    def readings_commit_is_clean(reading_rev, ref_rev):
        """Readings have to be taken on a commit that already carries the tools; the ref then advances by
        one more commit that adds exactly those readings.  That is honest only if the extra commit is
        forward, touches artifact paths and nothing else, and changes no product byte -- otherwise a
        page would quote numbers that belong to a different tree than the one under review.  Returns
        (ok, what broke)."""
        if not reading_rev:
            return False, ["NO_READING_REVISION"]
        if reading_rev == ref_rev:
            return True, []
        if not re.fullmatch(r"[0-9a-f]{40}", str(reading_rev)):
            return False, ["READING_REVISION_NOT_40_HEX"]
        rc = B.sh(["git", "merge-base", "--is-ancestor", reading_rev, ref_rev], cwd=WT)[0]
        if rc != 0:
            return False, ["READING_COMMIT_IS_NOT_AN_ANCESTOR"]
        rc2, out = B.sh(["git", "diff", "--name-only", "%s..%s" % (reading_rev, ref_rev)], cwd=WT)
        if rc2 != 0:
            return False, ["DIFF_UNREADABLE"]
        touched = [l.strip() for l in out.splitlines() if l.strip()]
        off = [p for p in touched if not p.startswith(ARTIFACT_PREFIXES)]
        return (not off), {"off_limits": off, "artifacts_added": len(touched)}

    gate = B.load(GATE_RECEIPT)
    gm = B.load(MUT_RECEIPT)
    py = B.load("pytest_r6.json")
    rows = B.load("checkin_copy_rows_r6.json")
    aud = B.load(AUD_RECEIPT)
    vocab = B.load("checkin_copy_rows_mutants_r6.json")
    rcpt = B.load(RECHECK_RECEIPT)
    fmt = B.load(FMT_RECEIPT)
    land = B.load("landing_r6.json")
    collect = B.load("pytest_collectonly_%s.json" % GEN)
    # `branch_emit_arm_r16.py` pulled the emitter copy out of EVERY already-published ref in this family
    # and ran it there: "the tool is in the branch" is only worth printing for a ref whose copy answers.
    # This ref is deliberately NOT in that receipt -- it would be this very program reading its own
    # output.  It is proven a different way, one level stronger: byte equality with the copy that ran.
    arm = B.load(ARM_RECEIPT)
    arm_rows = arm.get("refs") or []
    excluded = arm.get("ref_excluded_and_proven_by_bytes")
    my_short = MY_REF.split("/")[-1]
    # the arm names refs by their trailing generation, so compare that, not two spellings of one name
    my_tail = "r" + re.search(r"(\d+)$", my_short).group(1)
    if excluded != my_tail:
        raise SystemExit("ABORT_ARM_EXCLUSION_MISMATCH the arm receipt excludes %s, this page is for %s"
                         % (B.slot(excluded), my_tail))
    if [r for r in arm_rows if str(r.get("ref", "")).endswith("-" + my_tail)]:
        raise SystemExit("ABORT_SELF_MEASUREMENT the arm receipt carries a row for the ref it runs under")
    _rc, _in_ref = B.sh(["git", "show", "HEAD:review/ord0500-checkin/tools/r10_block.py"], cwd=WT)
    _lane = open(os.path.join(B.LANE, "tools", "r10_block.py"), "rb").read().replace(b"\r\n", b"\n")
    emitter_same = (_in_ref.replace("\r\n", "\n").encode("utf-8", "replace") == _lane)
    # the ref this hand supersedes is the newest one in the receipt -- read off the server, because "the
    # previous ref" is exactly the kind of thing I have been mis-remembering
    _others = [r for r in arm_rows if r.get("commit")]
    _others.sort(key=lambda r: int(re.search(r"(\d+)$", r["ref"]).group(1)))
    if not _others:
        raise SystemExit("ABORT_NO_PREDECESSOR_REF the arm receipt holds no published ref")
    prev_arm = _others[-1]
    r15_arm_last = "%s（`%s`）判语 `%s`，尾行 `%s`" % (
        prev_arm["ref"], prev_arm["commit"][:10], B.slot(prev_arm.get("verdict")),
        B.slot(prev_arm.get("last_line")))
    me = [r for r in land["refs"] if r["ref"] == MY_REF]
    r9 = [r for r in land["refs"] if r["ref"].endswith("entry-r9")]
    r8 = [r for r in land["refs"] if r["ref"].endswith("entry-r8")]
    if not (len(me) == len(r9) == len(r8) == 1):
        raise SystemExit("ABORT_LANDING_ROWS")
    me, r9, r8 = me[0], r9[0], r8[0]

    # the door the commander ruled in (裁①): a red reading may not produce a page at all, only the
    # named failure sheet.  R10_FORCE_RED=<name> is the arm that proves this bites, run by r15_chain.sh.
    # This one list is the door's inventory AND the sentence in section 七 that names it, so the page
    # cannot claim more checks than the door actually runs.
    # the readings were taken on the commit that carried the tools; the ref may be one commit ahead of
    # them because that commit is what adds the readings themselves.  Checked here (before the door) and
    # reported in the page, so the one honest case cannot be confused with a stale one.
    gate_ok, gate_rel = readings_commit_is_clean(gate.get("tip"), me["commit"])
    rcpt_ok, rcpt_rel = readings_commit_is_clean(rcpt.get("branch_head"), me["commit"])
    RED_CHECKS = [
        ("引文闸判语", gate.get("verdict") == "GREEN", gate.get("verdict_tally")),
        ("引文闸反件全咬", bool(gm.get("every_arm_bit")) and bool(gm.get("green")), gm.get("runs")
        and [(r.get("id"), r.get("bite")) for r in gm["runs"]]),
        ("换代复读无腐烂", not (rcpt.get("rot") or {}), rcpt.get("rot")),
        ("后端臂退出码", py.get("exit") == 0, py.get("summary_lines")[-1:]),
        ("词汇闸判语", rows.get("verdict") == "GREEN", rows.get("rows_checked")),
        ("词汇闸反件", bool(vocab.get("every_mutant_bit")), vocab.get("control_verdict")),
        ("全线尺只判自己名下", aud.get("mechanically_red") == 0,
         {"red": aud.get("mechanically_red"), "declined": aud.get("citations_declined")}),
        ("枝里那份发射器＝刚跑这页的这枚", emitter_same,
         {"ref": my_short, "bytes_in_ref": len(_in_ref.encode("utf-8", "replace")),
          "bytes_of_this_program": len(_lane)}),
        ("静态 arity 尺绿且自检咬下", fmt.get("verdict") == "GREEN"
        and (fmt.get("selftest") or {}).get("verdict") == "PASS",
         {"calls_checked": fmt.get("calls_checked"), "mismatched": len(fmt.get("mismatched") or []),
          "selftest": (fmt.get("selftest") or {}).get("verdict")}),
        ("读数提交到枝尖只多了件", gate_ok and rcpt_ok, {"gate": gate_rel, "recheck": rcpt_rel}),
    ]
    RED_CHECK_NAMES = [c[0] for c in RED_CHECKS]
    B.refuse_on_red(REF_GEN, RED_CHECKS)

    blobs = {}
    for line in open(os.path.join(B.RUN, "r6_blobs.txt"), encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            blobs[parts[1]] = parts[0]          # path -> blob sha (the file list, not the key=value form)
    def blob(path):
        """A cited artifact that the coordinate list does not carry is a defect in THIS page, not a gap
        in the tree, so it names itself instead of surfacing as an anonymous empty slot."""
        if path not in blobs:
            raise SystemExit("ABORT_NO_BLOB_FOR %s -- the coordinate list (%d paths) does not carry it; "
                             "add a glob to tools/r6_coordinates.py or stop citing it"
                             % (path, len(blobs)))
        return blobs[path]
    RC_DIR = "review/ord0500-checkin/"
    blob_gate = blob(RC_DIR + "receipts/" + GATE_RECEIPT)
    blob_mut = blob(RC_DIR + "receipts/" + MUT_RECEIPT)
    blob_audit = blob(RC_DIR + "receipts/" + AUD_RECEIPT)
    blob_rc = blob(RC_DIR + "receipts/" + RECHECK_RECEIPT)
    blob_tool = blob(RC_DIR + "tools/citation_gate_r9.py")
    blob_drv = blob(RC_DIR + "tools/citation_gate_r10_mutants.py")
    blob_door = blob(RC_DIR + "tools/r9_block.py")
    blob_emit = blob(RC_DIR + "tools/r10_block.py")
    chain_path, blob_chain = blob_by_fragment("/tools/%s_chain.sh" % REF_GEN)
    blob_arm = blob(RC_DIR + "receipts/" + ARM_RECEIPT)

    def blob_by_fragment(fragment):
        """Cite an instrument by what the ref actually carries, not by a name I assume it carries: the
        emitter-arm file is named for the hand that wrote it (r16) while the ref is named for the hand
        being reviewed (r17), and typing `% REF_GEN` for it produced an empty slot.  Match is on the
        path containing the fragment -- an endswith() against a fragment without its extension can only
        ever find nothing, which is how this helper first bit itself."""
        hits = sorted(p for p in blobs if fragment in p)
        if not hits:
            raise SystemExit("ABORT_NO_BLOB_FOR %r -- the coordinate list (%d paths) carries none"
                             % (fragment, len(blobs)))
        return hits[-1], blobs[hits[-1]]
    arm_tool_path, blob_armtool = blob_by_fragment("/tools/branch_emit_arm_")
    pair_tool_path, blob_pairtool = blob_by_fragment("/tools/exposure_pair_")
    blob_fmt = blob(RC_DIR + "receipts/" + FMT_RECEIPT)
    blob_coll = blob(RC_DIR + "receipts/pytest_collectonly_%s.json" % GEN)
    blob_sweep = blob(RC_DIR + "receipts/sweep_r6.json")
    blob_faces2 = blob(RC_DIR + "receipts/build_faces_r6.json")
    blob_exp_cand = blob(RC_DIR + "receipts/exposure_%s_cand.json" % EXPOSURE_GEN)
    blob_exp_base = blob(RC_DIR + "receipts/exposure_%s_base.json" % EXPOSURE_GEN)

    def blob_screen(tag):
        """The one artifact that holds this run's counts.  The coordinate gate refuses a count that no
        same-line artifact vouches for, and the honest answer is that each row has its own file."""
        return blob(RC_DIR + "receipts/checkin_%s_390x844_r3.json" % tag)

    # the ownership evidence for the confession: who has ever touched that spec
    rc, touching = B.sh(["git", "log", "--format=%H%x09%s", "--", FOREIGN_SPEC], cwd=WT)
    touching = [l for l in touching.splitlines() if l.strip()]
    mine_touching = [l for l in touching if "ORD-0500" in l]

    rc, listed = B.sh(["git", "ls-remote", "--refs", "origin", B.TIP_REF, MY_REF])
    remote, live_tip = B.pick_sha(listed, MY_REF), B.pick_sha(listed, B.TIP_REF)
    if not remote or not live_tip:
        raise SystemExit("ABORT_NO_REMOTE_READBACK %s" % listed[:200])
    # the ref this hand abandoned (see section 八): read it, do not remember it
    rc17, r17ls = B.sh(["git", "ls-remote", "--refs", "origin",
                        "refs/heads/review/newlane-ord0500-phone-checkin-entry-r17"])
    prev_r17_sha = B.pick_sha(r17ls, "refs/heads/review/newlane-ord0500-phone-checkin-entry-r17") \
        or "NOT_ON_REMOTE"
    if remote != me["commit"]:
        raise SystemExit("ABORT_REF_MOVED coordinates ran on %s, ref answers %s" % (me["commit"], remote))
    if gm.get("pairs_with_gate_receipt") != GATE_RECEIPT:
        raise SystemExit("ABORT_MUTANT_STALE the mutant run pairs with %s, this page reads %s"
                         % (gm.get("pairs_with_gate_receipt"), GATE_RECEIPT))
    ok_g, why_g = readings_commit_is_clean(gate.get("tip"), remote)
    if not ok_g:
        raise SystemExit("ABORT_GATE_STALE gate read %s, the ref is %s -- %s" % (gate.get("tip"),
                                                                                remote, why_g))
    ok_r, why_r = readings_commit_is_clean(rcpt.get("branch_head"), remote)
    if not ok_r:
        raise SystemExit("ABORT_RECHECK_STALE the re-check read branch %s, the ref is %s -- %s"
                         % (rcpt.get("branch_head"), remote, why_r))
    # the line moves every few minutes here, so the arm being a commit or two behind is not a reason to
    # refuse a page -- an arm that ran against a tip that is NOT behind this one (or ran against a branch
    # that has since been rewritten) is.  What must hold is: arm.tip is an ancestor of the live tip, and
    # my own citations still resolve on the live tip, which is re-measured below.
    arm_lag = "NOT_MEASURED"
    if arm.get("tip") != live_tip:
        rca, _ = B.sh(["git", "merge-base", "--is-ancestor", arm.get("tip") or "", live_tip])
        if rca != 0:
            raise SystemExit("ABORT_ARM_STALE the emitter-arm ran against tip %s which is not an "
                             "ancestor of the line (%s)" % (arm.get("tip"), live_tip))
        rcl, arm_lag = B.sh(["git", "rev-list", "--count", "%s..%s" % (arm.get("tip"), live_tip)])
        arm_lag = arm_lag.strip()
    if not emitter_same:
        raise SystemExit("ABORT_EMITTER_BYTES_DIFFER the emitter copy inside %s is not the program "
                         "writing this page (%d bytes in the ref, %d here) -- stage it and re-cut"
                         % (my_tail, len(_in_ref.encode("utf-8", "replace")), len(_lane)))
    # the line moves every couple of minutes on this project, so "the tip moved" alone is not a reason
    # to refuse a page -- "my citations stopped resolving on the tip as it now stands" is.  Re-measure
    # against the newest tip here, and refuse only on real rot or a product blob that no longer matches.
    import reanchor_r8 as RA
    def _show(rev, path):
        q = subprocess.run(["git", "-C", WT, "show", "%s:%s" % (rev, path)], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=180)
        return None if q.returncode else q.stdout.decode("utf-8", "replace")
    # the anchors are read from the line I am merging INTO; the citations are read from HEAD -- the copy
    # THIS ref ships.  Reading both from the tip compares the line's old comment with the line's new
    # anchors, which is permanently red until somebody else lands my fix: a ruler that can only fail
    # before the delivery it governs is the instrument defect, not the defect it was built to catch.
    _m, _t = _show(live_tip, "backend/app/main.py"), _show(
        "HEAD", "backend/tests/test_qoder_ord0500_journey_refusal.py")
    _t_tip = _show(live_tip, "backend/tests/test_qoder_ord0500_journey_refusal.py")
    if _m is None or _t is None:
        raise SystemExit("ABORT_TIP_UNREADABLE %s" % live_tip)
    _anchors, _span = RA.read_anchors(_m.splitlines())
    _cited = {}
    for _lab, _pat in RA.PATTERNS:
        _mm = re.search(_pat, _t)
        _cited[_lab] = int(_mm.group(1)) if _mm else None
    _rot = {k: [_cited[k], _anchors[k]] for k in _anchors if _cited[k] != _anchors[k]}
    if _rot:
        raise SystemExit("ABORT_ROT_DETECTED on %s: %s -- run the re-anchor before posting"
                         % (live_tip, _rot))
    _cited_tip = {}
    for _lab, _pat in RA.PATTERNS:
        _mm = re.search(_pat, _t_tip or "")
        _cited_tip[_lab] = int(_mm.group(1)) if _mm else None
    _tip_rot = {k: [_cited_tip[k], _anchors[k]] for k in _anchors if _cited_tip[k] != _anchors[k]}
    # the paths this order's product sentences speak about, taken from the re-check receipt rather
    # than remembered: r14 added `frontend/src/i18n/LocaleContext.tsx` when the dictionary rows went
    _paths = sorted((rcpt.get("tip_paths_equal_on_branch") or {}).keys()) or [
        "backend/app/main.py", "backend/tests/test_qoder_ord0500_journey_refusal.py",
        "contracts/openapi.yaml", "frontend/src/features/checkin/checkinCopy.ts",
        "frontend/src/features/trip/TripItinerary.tsx", "frontend/src/i18n/LocaleContext.tsx"]
    # my own write-set is allowed to differ from the tip -- that is the delivery.  Anything else that
    # differs means the line moved a product file under me after I read it, and then this page's
    # sentence about "the bytes are in the line" would be false, so the page stops here.
    rcw, ws = B.sh(["git", "diff", "--name-only", "%s..HEAD" % live_tip], cwd=WT)
    write_set = {l.strip() for l in ws.splitlines() if l.strip()}
    _eq, _moved, mine_changed = {}, [], []
    for _p in _paths:
        _a = _show(live_tip, _p)
        _b = subprocess.run(["git", "-C", WT, "show", "HEAD:%s" % _p], stdout=subprocess.PIPE,
                            timeout=180).stdout.decode("utf-8", "replace")
        same = (_a == _b)
        _eq[_p] = same
        if not same and _p in write_set:
            mine_changed.append(_p)
        if not same and _p not in write_set:
            _moved.append(_p)
    if _moved:
        raise SystemExit("ABORT_PRODUCT_MOVED %s -- the line changed these outside my write-set; "
                         "re-read them before writing a page about them" % _moved)
    lag = subprocess.run(["git", "-C", WT, "rev-list", "--count", "%s..%s"
                          % (land["live_tip"], live_tip)], stdout=subprocess.PIPE,
                         timeout=120).stdout.decode().strip()

    # what this ref itself changes: diff from ITS OWN fork point to its head.  Diffing against the live
    # tip instead would count everything other lanes landed since I forked and print a number that
    # contradicts "0 product bytes" -- it did exactly that in an earlier draft of this page.
    rc, names = B.sh(["git", "diff", "--name-only", "%s..%s" % (me["fork_point"], remote)], cwd=WT)
    changed = [n.strip() for n in names.splitlines() if n.strip()]
    product = [n for n in changed if not n.startswith("review/")]
    # the size of each product change, read off the same diff rather than remembered: this hand deleted
    # dictionary rows, so "0 product bytes" would be a lie, and "+4 lines somewhere" would be vague.
    rcn, numstat = B.sh(["git", "diff", "--numstat", "%s..%s" % (me["fork_point"], remote)], cwd=WT)
    prod_delta = {}
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2].strip() in product:
            prod_delta[parts[2].strip()] = (parts[0], parts[1])
    # "everything else is under this order's own folder" is a claim, so it is checked, not asserted
    outside = [n for n in changed if not n.startswith("review/ord0500-checkin/")]
    if sorted(outside) != sorted(product):
        raise SystemExit("ABORT_STRAY_PATHS this ref touches outside the order folder and outside "
                         "the ruled product change: %s" % sorted(set(outside) ^ set(product)))
    if sorted(prod_delta) != sorted(product):
        raise SystemExit("ABORT_NUMSTAT_ROWS numstat did not answer for every product path")
    rc2, ahead = B.sh(["git", "rev-list", "--count", "%s..%s" % (me["fork_point"], live_tip)], cwd=WT)
    line_ahead = ahead.strip()
    # how much of my own write-set the line also moved: this is what a merge conflict is made of, and the
    # page should carry the number instead of letting the commander discover it at merge time
    rcf, mine_files = B.sh(["git", "diff", "--name-only", "%s..HEAD" % me["fork_point"]], cwd=WT)
    rcg, line_files = B.sh(["git", "diff", "--name-only", "%s..%s" % (me["fork_point"], live_tip)], cwd=WT)
    _mine = {l.strip() for l in mine_files.splitlines() if l.strip()}
    _line = {l.strip() for l in line_files.splitlines() if l.strip()}
    overlap = sorted(_mine & _line)
    ov_review = [p for p in overlap if p.startswith("review/")]
    ov_other = [p for p in overlap if not p.startswith("review/")]

    foreign = [r for r in (gate.get("rows") or []) if r["verdict"] == "NOT_THIS_LANES_CITATION"]
    runs = gm.get("runs") or []

    L = []
    A = L.append
    A("### ORD-0500 %s（手机车道 0afdb49b）：你 04:26 的三件裁语都落了——闸按引文那一行的作者收窄、"
      "出页那道门真拦、字典那两行连钉住它的臂一起删（上一手错在把闸伸进了别人的判据文件）"
      % REF_GEN.upper())
    A("")
    forked_now = me["fork_point"] == live_tip
    A("现尖 `%s`（`git ls-remote --refs` 现读逐字相等）；本枝 `review/newlane-ord0500-phone-checkin-"
      "entry-%s` = `%s`，%s，合并预测树 `%s`，merge-tree 退出码 %s，写集 %s 枚逐枚字节相同 %s 枚、"
      "需要再 rebase %s 枚。**产品改动就 %s 枚文件**（`git diff --name-only` 现读，全是裁③那一笔删除与"
      "它自己的注释，逐枚 %s），本手其余 %s 枚改动全在 `review/ord0500-checkin/` 里（发射器对"
      "这一格有 `ABORT_STRAY_PATHS` 兜底，越界一枚就不生成页）。" % (
          live_tip, REF_GEN, remote,
          ("从这一枚尖自己身上分叉（`fork_point` 相等 = 真）" if forked_now else
           "分叉于 `%s`（现尖之后又落了 %s 枚提交，`git rev-list --count` 现读），landing 判到需要再 "
           "re-cut 的路径仍是 %s 枚——不合的时候不用重剪，这是那把只读尺的答话" % (
               me["fork_point"], B.fmt(len(B.sh(["git", "rev-list", "--count", "%s..%s"
                                                 % (me["fork_point"], live_tip)], cwd=WT)[1].split())),
               B.fmt(len(me["files_needing_another_recut"])))),
          B.slot(me["predicted_tree"]), B.fmt(me["merge_tree_exit"]), B.fmt(me["write_set_files"]),
          B.fmt(me["files_landing_byte_identical"]), B.fmt(len(me["files_needing_another_recut"])),
          B.fmt(len(product)),
          "、".join("`%s` +%s/−%s" % (p, B.slot(prod_delta.get(p, ("—", "—"))[0]),
                                      B.slot(prod_delta.get(p, ("—", "—"))[1])) for p in product),
          B.fmt(len(changed) - len(product))))
    A("")
    A("- 发页这一趟又现读了一次线：landing 那趟判的是 `%s`，此刻线是 `%s`（中间 %s 枚提交，"
      "`git rev-list --count` 现读）。四枚锚在 `%s` 上当场重读 = `%s`，注释现引 = `%s`，腐烂 %s 枚；"
      "本枝与现尖把 %s 枚产品路径逐枚比过字节：等值 %s 枚，不等 %s 枚（`%s`——就是 §五 那一笔删除和它的"
      "注释，都在本枝写集之内），**写集之外不等 %s 枚**；最后那一格若不为 0，这页根本生成不出来，发射器里"
      "那条 `ABORT_PRODUCT_MOVED` 就是干这个的。" % (
          land["live_tip"], live_tip, B.slot(lag), live_tip[:12],
          "`、`".join(str(_anchors[k]) for k in ("require", "lookup", "integrity", "caught_by")),
          "`、`".join(str(_cited[k]) for k in ("require", "lookup", "integrity", "caught_by")),
          B.fmt(len(_rot)), B.fmt(len(_eq)), B.fmt(sum(1 for v in _eq.values() if v is True)),
          B.fmt(len(mine_changed)), "`、`".join(mine_changed) or "无", B.fmt(len(_moved))))
    A("- 上面那句「注释现引」读的是**我这枚枝交上去的那份**（`HEAD`），不是线上的那份——这不是偷懒，是这"
      "把尺原来的读法有缺陷：它两头都从现尖读，于是拿线上那条旧注释去比线上那批新锚，只要我这一手还没被合，"
      "它就永远红，一条只能在被它管辖的交付之前失败的尺，本身就是仪器缺陷。现尖那份注释此刻仍写 `%s`，"
      "对着现尖的锚差 %s 枚；我这枚枝写的是 `%s`，差 %s 枚——所以「要合的那件事」正是把差的那 %s 枚抹平。" % (
          "`、`".join(str(v) for v in (_cited_tip.get(k) for k in ("require", "lookup", "integrity",
                                                              "caught_by"))),
          B.fmt(len(_tip_rot)),
          "`、`".join(str(_cited[k]) for k in ("require", "lookup", "integrity", "caught_by")),
          B.fmt(len(_rot)), B.fmt(len(_tip_rot))))
    A("- 号分两套不是笔误：**枝号 `%s` 是这一枚提交**（号令者要合的那枚），**件名里的 `%s` 是落件的那一代**"
      "（`receipts/%s` 等三件在 `%s` 这一代写进枝里）。两者的差别只有 `tip`/`branch`/"
      "时间戳三格，页里的数一律取我在 `%s` 上重跑的那一趟，枝里那份具名为上一枚。" % (
          REF_GEN, GEN, GATE_RECEIPT, GEN, remote))
    A("")
    A("## 一、我上一手错在哪（这就是那类「句子跑在证据前面」）")
    A("")
    A("- r9 那页写了「别人手上的判据文件一枚不闸」。当场被打脸：那枚闸的文件清单是我手敲的，里面含 "
      "`%s`——那是 ORD-0476 的规格。逐枚翻它的历史：碰过它的是 %s 枚 commit，其中带 ORD-0500 的 %s 枚；"
      "唯一那枚是 `%s`（%s）。所以那句在 r9 那一代是假的，闸也确实能因为邻座改自己注释而把我的构建弄红。" % (
          FOREIGN_SPEC, B.fmt(len(touching)), B.fmt(len(mine_touching)),
          touching[0].split(chr(9))[0], touching[0].split(chr(9))[1][:58]) if touching else
          "碰过它的 commit 数没读到，本行作废")
    A("- 根因不是我眼神差，是**范围写死成清单**：清单是我抄的，抄的那一秒就没人保证它还和作者一致。"
      "这手把范围改成按引文那一行的作者算：`git log --grep=ORD-0500 --name-only` 现读要扫的文件，"
      "`git blame --line-porcelain` 一枚文件一趟定作者，作者在本枚 `%s` 枚 commit 集合内才判。" % (
          B.fmt(gate.get("lane_commits_in_set"))))
    A("- 闸与件的名字按代分开写，本代这三件是 `receipts/%s`、`receipts/%s`、`receipts/%s`（blob 各 `%s`、"
      "`%s`、`%s`）：上一代之所以要在枝里留下同名旧件不动，是因为那一页已经把它们的 blob 报出去了——覆盖一份"
      "已被引用的机器件，等于把别人的复算入口抹掉。这条规矩是账本里别的车道先记过、我 09-30 自己踩过"
      "一次的。" % (GATE_RECEIPT, MUT_RECEIPT, RECHECK_RECEIPT, blob_gate, blob_mut, blob_rc))
    A("- 还有一枚本手抓到的自己的错，而且是当场抓的：我把 `r15` 那枝里那份页发射器原样抽出来直接跑"
      "（`git show <枝>:review/ord0500-checkin/tools/r10_block.py`，配上同一枚枝里的 `r9_block.py`，件与 "
      "`run/r6_blobs.txt` 取现场），它的答话是 %s。根因还是同一类——**清单是抄的**：页里要点名的 blob 与"
      "坐标工具实际枚举的集合，两枚清单从来没绑在一起（那一行找的是 `%s` 的 blob，而坐标工具从不列发射器"
      "自己的路径）。这手把两边都改成按名字现读（发射器、门、复读尺、链、失败件全进坐标清单），并且不再口头"
      "保证「工具在枝里」：枝里那枚 `%s`（blob `%s`）把**每一枚已发布枝里那份发射器**抽出来真跑一遍。" % (
          B.slot(arm_tool_path.split("/")[-1]), blob_armtool,
          B.slot(r15_arm_last), RC_DIR + "tools/r9_block.py"))
    A("")
    A("| 枝 | 那份发射器的答话 | 退出码 | 它被喂的那一代（现场认名，不记忆） | 它写的页面文件 |")
    A("|---|---|---|---|---|")
    def dash(v):
        """A row that never got as far as running has no exit code and no generation named -- that is a
        real answer, not a missing slot, so it prints as a dash instead of refusing the whole page."""
        return "—" if v is None else str(v)
    for r in arm_rows:
        A("| %s | %s | %s | %s | %s |" % (
            dash(r.get("ref")), dash(r.get("verdict")), dash(r.get("returncode")),
            dash(r.get("generation_named") or r.get("why")),
            B.fmt(bool(r.get("page_file_this_arm_wrote"))) + ("/已还原" if r.get(
                "previous_page_restored") else "")))
    A("")
    A("- %s 枚**已发布**枝里带发射器，当场跑起来 %s 枚、跑不起来 %s 枚（判语集合 %s）。本枝 `%s` 不在"
      "这张表里，也不是漏了：那张表要读的就是正在写这页的程序自己产出的件，让自己测自己是循环论证。本枝这"
      "一枚换一种证法，而且更硬——把 `HEAD:review/ord0500-checkin/tools/r10_block.py` 与刚跑完这页的这一枚"
      "逐字节比（LF 归一后 %s 字节 对 %s 字节，相等 = %s），不等就退 `ABORT_EMITTER_BYTES_DIFFER`。这一格"
      "同时进了 §七 那张清单。臂量于尖 `%s`，写这页此刻线是 `%s`（中间 %s 枚提交，"
      "`merge-base --is-ancestor` 判它仍在这条线的上游；不是祖先就退 `ABORT_ARM_STALE`）。"
      "件 `receipts/%s`。" % (
          B.fmt(sum(1 for r in arm_rows if r.get("commit"))),
          B.fmt(sum(1 for r in arm_rows if r.get("verdict") == "RUNS")),
          B.fmt(sum(1 for r in arm_rows if r.get("verdict") == "ABORTS")),
          "、".join("`%s` %s 枚" % kv for kv in sorted((arm.get("verdict_tally") or {}).items())),
          my_short, B.fmt(len(_in_ref.encode("utf-8", "replace"))), B.fmt(len(_lane)),
          B.fmt(emitter_same), B.slot(arm.get("tip")), B.slot(live_tip), B.slot(arm_lag),
          ARM_RECEIPT))
    A("")
    A("## 二、现在的闸判谁、不判谁")
    A("")
    A("- 本代：扫 %s 枚文件（写集现读），看到引文 %s 条，判 %s 条，不判 %s 条。判的 %s 条来自 %s 枚"
      "文件里我自己写的 %s 行引文，同一行被看两遍——一遍形状、一遍内容钉子，所以是 %s 条机械加 %s 条钉子。"
      "件 `%s`（blob `%s`），闸 `%s`。" % (
          B.fmt(gate.get("files_scanned")), B.fmt(gate.get("citations_seen")),
          B.fmt(gate.get("citations_judged")), B.fmt(gate.get("citations_declined")),
          B.fmt(gate.get("citations_judged")), B.fmt(gate.get("judged_files")),
          B.fmt(gate.get("citation_lines_judged")), B.fmt(gate.get("mechanical_rows")),
          B.fmt(gate.get("pin_rows")), "receipts/" + GATE_RECEIPT, blob_gate, blob_tool))
    if not foreign:
        raise SystemExit("ABORT_NO_DECLINED_ROWS this generation declined nothing, so the ownership "
                         "bullet would have nothing to name")
    declined_files = sorted({r["cited_by"].split(":")[0] for r in foreign})
    example = next((r for r in foreign if r.get("mechanical_verdict") == "OK"), foreign[0])
    A("- 不判的那 %s 条不是被忽略：逐条带着写它的那枚 commit 与「如果这行是我的会判成什么」的机械判语，"
      "都落在件里。这代不判的出自 %s 枚文件（`%s`），作者 commit 去重后 %s 枚。随手举一件被看见而不判的："
      "`%s` 那一行引的是 `%s:%s`，写下这行的是 commit `%s`，不是本枚枝上的任何一手——所以我改不到它，"
      "它也不该决定我的判语。" % (
          B.fmt(len(foreign)), B.fmt(len(declined_files)), "`、`".join(declined_files),
          B.fmt(len({r.get("owner_commit") for r in foreign})),
          B.slot(example.get("cited_by")), B.slot(example.get("target")),
          B.slot(example.get("line")), B.slot(example.get("owner_commit"))))
    A("- 内容钉子仍不许我手改：闸把这 %s 枚钉子与 r8 那把尺当场量到的原文逐字比，不符就直接红（"
      "`expectations_agree_with_r8_receipt` = %s，读的是枝里那份）。" % (
          B.fmt(gate.get("pinned_citations")), B.fmt(gate.get("expectations_agree_with_r8_receipt"))))
    A("")
    A("## 三、反件 %s 枚（M5/M6 是一对反方向的，专咬「范围」这格）" % B.fmt(
        sum(1 for r in runs if str(r.get("id")).startswith("M"))))
    A("")
    A("| 反件 | 动的那一行（改后，节选） | 期望 | 咬住了 | 判语 |")
    A("|---|---|---|---|---|")
    for r in runs:
        after = r.get("citation_after") or r.get("citation_written") or "—"
        A("| %s | %s | %s | %s | %s |" % (B.slot(r.get("id")), B.slot(str(after)[:74]),
                                         B.slot(r.get("expect")), B.fmt(r.get("bite")),
                                         B.fmt(r.get("verdict"))))
    A("")
    fu = gm.get("foreign_citation_used") or {}
    m5 = next((r for r in runs if r.get("id") == "M5_foreign_line_not_judged"), {})
    m6 = next((r for r in runs if r.get("id") == "M6_same_line_claimed_mine"), {})
    if not m5 or not m6:
        raise SystemExit("ABORT_NO_OWNERSHIP_ARMS the receipt does not carry the M5/M6 pair")
    A("- M5/M6 这一对是本手真正要的东西。改动落在 `%s`——那行不是本枚枝写的（作者是 commit `%s`）。"
      "改前那一行是 `%s`，把里面的行号挪成越界的一枚 `%s` 之后变成 `%s`。" % (
          B.slot(fu.get("cited_by")), B.slot(fu.get("owner_commit")), B.slot(fu.get("line_before")
          or m5.get("citation_before")), B.slot(m5.get("digits_moved")),
          B.slot(m5.get("citation_after"))))
    A("- 同一枚改动，两种作者身份，判语必须相反，这才叫闸：作者不算我的时候，判语 %s、红 %s 枚，那一行"
      "自己记成 `%s`（机械判语仍留着，是 `%s`——看见了、没被判）；把作者 `%s` 划进本名下同一趟跑，判语立刻 "
      "%s，红的就是 `%s`。件 `receipts/%s`（blob `%s`），驱动 "
      "`tools/citation_gate_r10_mutants.py`（blob `%s`）。" % (
          B.fmt(m5.get("verdict")), B.fmt(m5.get("red_total")), "NOT_THIS_LANES_CITATION",
          B.slot(m5.get("row_mechanical_verdict")), B.slot(fu.get("owner_commit")),
          B.fmt(m6.get("verdict")), B.slot(m6.get("expect")), MUT_RECEIPT, blob_mut, blob_drv))
    A("- 件自己也是提交，所以这个形状必须说清，而且这一手开始是量出来的：闸的读数取自 `%s`、复读的读数"
      "取自 `%s`，本枝尖是 `%s`；两枚之间 `git diff --name-only` 现读 %s 枚路径，全部落在本单的产物之下"
      "（`receipts/`、`run/`、`tools/` 与暂存工具自己渲染的读数单 `R6_READINGS.md`；产品与判据文件 0 枚），"
      "`merge-base --is-ancestor` 判读数提交确在枝尖上游。不等这一形制就退 `ABORT_GATE_STALE`/"
      "`ABORT_RECHECK_STALE`，这一格也在 §七 那张清单里（第 %s 项）。**这格门第一次跑就咬过我**：我原以为"
      "允许集合是 `{receipts,run,tools}` 三格，它把 `R6_READINGS.md` 报了出来——那枚也是暂存工具从件渲染的"
      "产物，不是我手写的句子，所以允许集合按实增补，不是我嫌红所以把它放行。上一手我只写过「枝里那份具名为"
      "上一枚、两边差时间戳」——那句没把两枚 sha 与差集摆出来，等于让号令者信我。件里那份同名复制的 blob："
      "闸 `%s`、反件 `%s`。" % (
          B.slot(gate.get("tip")), B.slot(rcpt.get("branch_head")), B.slot(remote),
          B.fmt(max([d.get("artifacts_added", 0) for d in (gate_rel, rcpt_rel) if isinstance(d, dict)]
                    or [0])),
          B.fmt(RED_CHECK_NAMES.index("读数提交到枝尖只多了件") + 1), blob_gate, blob_mut))
    A("- 全部在 `scratch_cit_r9/` 的副本上跑（%s 份），判它用的登记清单与 blame 都仍取真实工作树——临时"
      "目录不给自己当权威。副本字节全部回来 = %s，本次跑对 `wt22` 的改动 = %s（开工前后逐行相等；开工前"
      "它就带着我已提交的件，所以判据是「没被这趟改过」，不是「干净」）。" % (
          B.fmt(gm.get("files_copied")), B.fmt(gm.get("all_bytes_restored")),
          B.fmt(gm.get("wt22_worktree_unchanged_by_this_run"))))
    A("")
    A("## 四、门里的臂与词汇闸（这代重跑）")
    A("")
    b = py.get("main_py_blobs") or {}
    A("- 两套规格在私库 `%s` 上：退出码 %s，尾行逐字 `%s`，跑后库中 %s 行；共享库字节 %s 对 %s、"
      "mtime_ns %s 对 %s，未动 = %s。`backend/app/main.py` 三枚里候选 `%s` 与判读时现尖 `%s` 同一枚 = %s。" % (
          B.slot(py.get("private_db")), B.fmt(py.get("exit")), B.slot(py.get("summary_lines")[-1]),
          B.fmt(py.get("checkin_rows_after_the_arms")), B.slot(py["shared_before"]["bytes"]),
          B.slot(py["shared_after"]["bytes"]), B.slot(py["shared_before"]["mtime_ns"]),
          B.slot(py["shared_after"]["mtime_ns"]), B.fmt(py.get("shared_untouched")),
          B.slot(b.get("candidate_worktree")), B.slot(b.get("tip_at_run")),
          B.fmt(b.get("candidate_worktree") == b.get("tip_at_run"))))
    mech = {}
    for r in (aud.get("declined_detail") or []):
        mech[r.get("mechanical_verdict")] = mech.get(r.get("mechanical_verdict"), 0) + 1
    A("- 词汇闸：判语 %s、检查 %s 行。全线那把尺按裁语改成只判自己名下的：看到 %s 条，判 %s 条，"
      "不判 %s 条（出自 %s 位作者）。不判那些条若按形状算会是：%s——一件不修，只把归属列清楚，"
      "转不转单归你决定。件 `receipts/%s`。" % (
          B.fmt(rows.get("verdict")), B.fmt(rows.get("rows_checked")),
          B.fmt(aud.get("citations_found")), B.fmt(aud.get("citations_judged")),
          B.fmt(aud.get("citations_declined")), B.fmt(aud.get("declined_authors")),
          "、".join("%s %s 条" % kv for kv in sorted(mech.items())),
          AUD_RECEIPT))
    an = rcpt.get("anchors") or {}
    eqv = rcpt.get("tip_paths_equal_on_branch") or {}
    neq = sorted(k for k, v in eqv.items() if not v.get("branch_equal"))
    A("- 换代复读（件 `%s`，尖 `%s`）：四枚锚现读是 `%s`，注释里此刻引的是 `%s`，腐烂集合 = %s；本枝与"
      "现尖的产品 blob 逐枚等值 %s 枚 / %s 枚，不等那 %s 枚是 `%s`——正是 §五 删的那两枚文件，不是又有人"
      "在我脚下动了线。所以本代不需要再剪一次注释——这句话现在有件撑着，不是我口头保证。判语 %s，红 %s 枚；"
      "r8 那枝 `%s` 此刻就是现尖的祖先（landing 的 `fork_point` 与它自身相等 = %s，对现尖的写集 %s 枚）。" % (
          RECHECK_RECEIPT,
          B.slot(rcpt.get("tip")),
          "`、`".join("`backend/app/main.py:%s`" % an.get(k) for k in
                     ("require", "lookup", "integrity", "caught_by")),
          "`、`".join(str(v) for v in (rcpt.get("cited") or {}).values()),
          B.fmt(len(rcpt.get("rot") or {})),
          B.fmt(sum(1 for v in eqv.values() if v.get("branch_equal"))),
          B.fmt(len(eqv)), B.fmt(len(neq)), "`、`".join(neq) or "无",
          B.fmt(gate.get("verdict")), B.fmt(gate.get("red_total")),
          r8["commit"], B.fmt(r8["fork_point"] == r8["commit"]), B.fmt(r8["write_set_files"])))
    # the door's own artifact from the previous generation, read back out of the ref rather than
    # remembered: the page may only claim "it bites" if a sheet the branch carries proves it.
    rct, tr = B.sh(["git", "ls-tree", "-r", "--name-only", "HEAD", "review/ord0500-checkin/run/"], cwd=WT)
    prior_sheets = []
    for p in sorted(x.strip() for x in tr.splitlines() if "READINGS_RED" in x):
        rcx, txt = B.sh(["git", "show", "HEAD:" + p], cwd=WT)
        try:
            s = json.loads(txt)
        except ValueError:
            raise SystemExit("ABORT_SHEET_UNREADABLE " + p)
        prior_sheets.append({"path": p, "bytes": len(txt.encode("utf-8")),
                             "blob": B.sh(["git", "rev-parse", "HEAD:" + p], cwd=WT)[1].strip(),
                             "tool": s.get("tool"), "aborts": s.get("aborts"),
                             "failed": [c.get("check") for c in s.get("failed_checks") or []],
                             "forced": [bool(c.get("forced")) for c in s.get("failed_checks") or []]})
    if not prior_sheets:
        raise SystemExit("ABORT_NO_SHEET_IN_REF the door is claimed in section 七 but the ref carries "
                         "no failure sheet to point at")
    faces = B.load("build_faces_r6.json")
    # the screen readings in section 六 belong to THIS candidate only while the product bytes they
    # walked are still the product bytes on the ref.  A tools-only re-cut must not inherit them by
    # silence, so the blobs are compared here and the page refuses when they differ.
    _fc = B.slot(faces.get("candidate_commit"))
    faces_blob = {}
    for _p in product:
        def _blob(rev):
            r = subprocess.run(["git", "-C", WT, "rev-parse", "%s:%s" % (rev, _p)],
                               stdout=subprocess.PIPE, timeout=120)
            return r.stdout.decode().strip() if r.returncode == 0 else None
        faces_blob[_p] = (_blob(remote), _blob(_fc))
    _stale = [p for p, (a, b) in faces_blob.items() if a != b or a is None]
    if _stale:
        raise SystemExit("ABORT_FACES_STALE the candidate's product bytes moved since the faces were "
                         "built, so section 六's readings are not this ref's: %s" % _stale)
    sweep = B.load("sweep_r6.json")
    ff = {f["label"]: f for f in (faces.get("faces") or [])}
    sw = {r["tag"]: r for r in (sweep.get("runs") or [])}
    dict_rel = "frontend/src/i18n/LocaleContext.tsx"
    tip_rows = (_show(live_tip, dict_rel) or "").count("checkin.duplicate") +         (_show(live_tip, dict_rel) or "").count("checkin.refused")
    head_rows = subprocess.run(["git", "-C", WT, "show", "HEAD:%s" % dict_rel],
                               stdout=subprocess.PIPE, timeout=180).stdout.decode(
                                   "utf-8", "replace")
    head_rows = head_rows.count("checkin.duplicate") + head_rows.count("checkin.refused")
    A("")
    A("## 五、裁③：字典里那两行零读者的句子删掉了，连钉住它的那枚臂")
    A("")
    A("- 删的是什么：`%s` 里 `checkin.duplicate` 与 `checkin.refused` 两把键，两档各一行——现尖上这一枚"
      "文件里还能数到 %s 处，本枝同一枚文件里是 %s 处。这屏自 r5 起就不读它们了，读的是 "
      "`features/checkin/checkinCopy.ts` 那张表。" % (dict_rel, B.fmt(tip_rows), B.fmt(head_rows)))
    A("- 钉住它们的臂一并删：词汇闸的 C1（专门记录这两把键的行号与读者数）随裁语去掉，判语仍是 %s、"
      "检查 %s 行；它自己的两枚反件本代仍各自咬下（控制趟 %s）。**具名代价**：闸从此不会再说「有人把这两"
      "行加回来了」——那格观察跟着被删的对象一起走了。" % (
          B.fmt(rows.get("verdict")), B.fmt(rows.get("rows_checked")),
          B.fmt(vocab.get("control_verdict"))))
    A("- 后端那套规格一枚没改，删除之后重跑收集：`%s` 收集 %s 条、退出码 %s（件 `receipts/"
      "pytest_collectonly_%s.json`，blob `%s`，取于 %s）；本单两套臂在私库上跑出的尾行逐字 `%s`、跑后库中"
      "%s 行、共享库未动 = %s——`collect-only` 是上一手「一删就整套空转」那笔账留下的规矩。" % (
          B.slot(collect.get("cmd")), B.fmt(collect.get("collected")), B.fmt(collect.get("exit")),
          GEN, blob_coll, B.slot(collect.get("took_local")), B.slot(py.get("summary_lines")[-1]),
          B.fmt(py.get("checkin_rows_after_the_arms")), B.fmt(py.get("shared_untouched"))))
    A("")
    A("## 六、这枚删除到没到 bundle —— 两枚面各建一遍，四趟屏读各走一遍")
    A("")
    A("| 面 | 入口 JS | bundle 字节 | tsc（两枚配置）| build |")
    A("|---|---|---|---|---|")
    for lab in (faces.get("base_label"), faces.get("candidate_label")):
        f = ff.get(lab) or {}
        e = f.get("entry") or {}
        A("| %s | %s | %s | %s / %s | %s |" % (
            B.slot(lab), B.slot(e.get("entry_asset")),
            B.fmt((e.get("bundle") or {}).get("bytes"), " 字节"),
            B.fmt((f.get("tsconfig.check.json") or {}).get("exit")),
            B.fmt((f.get("tsconfig.typecheck.json") or {}).get("exit")),
            B.fmt((f.get("build") or {}).get("exit"))))
    A("")
    A("- 两枚面的 bundle 字节不同 = %s，入口名不同 = %s：那四行字符串确实从出货的那一枚文件里走了；"
      "建完换回候选字节后逐枚核对 `every_path_matches_the_commit` = %s、`worktree_clean_after_restore` "
      "= %s。这 %s 趟屏读与两枚面取于候选 `%s`，本页把它们挂在枝 `%s` 下面，凭的是逐枚产品 blob 相等："
      "%s——不等发射器就退 `ABORT_FACES_STALE`（本手只往枝里加工具与件，产品字节一枚没再动，所以这句仍"
      "成立；这不是我口头保证）。**范围要说清**：对照的基座是 `%s`（那一次构建时的现尖），不是此刻的 `%s`，"
      "所以这句讲的是「删除让候选相对它自己的基座少了什么」，不是「相对此刻现尖少了什么」——后者要重 build，"
      "本手没做（§八 具名）。件 `receipts/build_faces_r6.json`。" % (
          B.fmt((ff.get(faces.get("base_label")) or {}).get("entry", {}).get("bundle", {}).get(
              "bytes") != (ff.get(faces.get("candidate_label")) or {}).get("entry", {}).get(
              "bundle", {}).get("bytes")),
          B.fmt((ff.get(faces.get("base_label")) or {}).get("entry", {}).get("entry_asset")
                != (ff.get(faces.get("candidate_label")) or {}).get("entry", {}).get("entry_asset")),
          B.fmt((faces.get("restore") or {}).get("every_path_matches_the_commit")),
          B.fmt((faces.get("restore") or {}).get("worktree_clean_after_restore")),
          B.fmt(len(sweep.get("runs") or [])), _fc, remote,
          "、".join("`%s` 枝上 `%s` = 候选上 `%s`" % (p, a[:12], b[:12])
                    for p, (a, b) in sorted(faces_blob.items())),
          B.slot(faces.get("base_label")), B.slot(live_tip)))
    A("| 屏读 | locale | 面身份 | 控件 | 中心可按 | 拒绝句枚数 | 屏上 CJK | 这一行的原件（blob，`git cat-file -t` 可验） |")
    A("|---|---|---|---|---|---|---|---|")
    for tag in sorted(sw):
        r = sw[tag]
        c = (r.get("readings") or {}).get("census") or {}
        ad = (r.get("readings") or {}).get("after_duplicate") or {}
        A("| %s | %s | %s | %s | %s | %s | %s | `receipts/checkin_%s_390x844_r3.json` %s |" % (
            tag, B.slot(r.get("locale")), B.fmt((r.get("serve") or {}).get("identity_ok")),
            B.fmt(c.get("controls")), B.fmt(c.get("pressable_by_centre_hit")),
            B.fmt(ad.get("notice_count"), " 条"), B.fmt(ad.get("cjk_chars_on_screen"), " 字"),
            tag, blob_screen(tag)))
    en = (sw.get("%s_en" % faces.get("candidate_label"), {}) or {}).get("readings", {})         .get("after_duplicate", {}) or {}
    zh = (sw.get("%s_zh" % faces.get("candidate_label"), {}) or {}).get("readings", {})         .get("after_duplicate", {}) or {}
    A("")
    A("- 删除之后两档屏幕上那句拒绝话仍是这屏自己的词汇：英文档逐字 `%s`；中文档逐字 `%s`。"
      "四趟的面身份四证齐（入口名取自被服务的 index.html、服务字节与磁盘字节 html/bundle 都相等，"
      "收工只停自己 spawn 的进程；四趟逐枚原件在上面那张表的最后一列）。第二站中心可按那一格本代仍然量到 "
      "%s 对 %s（zh 少一枚，件 `receipts/sweep_r6.json`，blob `%s`，字段 `runs[].readings.census."
      "pressable_by_centre_hit`），仍归滚动容器与底栏两家。" % (
          B.slot((en.get("notices") or ["未读到"])[0]), B.slot((zh.get("notices") or ["未读到"])[0]),
          B.fmt((sw.get("%s_zh" % faces.get("candidate_label"), {}) or {}).get("readings", {})
                .get("census", {}).get("pressable_by_centre_hit")),
          B.fmt((sw.get("%s_en" % faces.get("candidate_label"), {}) or {}).get("readings", {})
                .get("census", {}).get("pressable_by_centre_hit")), blob_sweep))
    pair = B.load("exposure_pair_%s.json" % EXPOSURE_GEN)
    # the pair compared my product paths against the tip AS IT WAS when it ran; the line moves every few
    # minutes, so "still valid" has to be re-measured here rather than assumed: same blobs on the current
    # tip for exactly the paths that were swapped, or the pair's number is about a base that no longer exists
    pair_still = {}
    for _p in (pair.get("swapped_paths") or []):
        pair_still[_p] = (_show(pair.get("base_tip"), _p) == _show(live_tip, _p))
    if not pair_still or not all(pair_still.values()):
        raise SystemExit("ABORT_PAIR_STALE the exposure pair's base %s no longer matches the live tip %s "
                         "for %s -- re-run tools/exposure_pair_r17.py"
                         % ((pair.get("base_tip") or "")[:12], live_tip[:12],
                            [p for p, v in pair_still.items() if not v]))
    cx, cb = B.load("exposure_%s_cand.json" % EXPOSURE_GEN), B.load("exposure_%s_base.json" % EXPOSURE_GEN)
    pr, pc, pb = pair.get("parity") or {}, pair.get("sides") or {}, pair.get("restore") or {}
    A("- Q64 曝光尺两边相等，而且这一对是**本手重取的**：枝里那枚 `%s`（blob `%s`）把 `%s` 换到基座 `%s` "
      "的字节、跑一枚尺、再换回候选 `%s`、逐枚验回（`every_path_matches_the_commit` = %s、"
      "`worktree_clean_after_restore` = %s、`checkout_rc` %s）。格总数 %s 对 %s、命中集合相同 = %s、"
      "未解析 import %s 对 %s、解析诊断 %s 对 %s——删死掉的字典行没有把任何正文值送进共用 helper。"
      "**这一回尺的版次记进件了**：`%s`（本机字节 %s，本机 sha1 `%s`，原件 blob `%s` 与 `%s`）——上一代那两份件"
      "的 `tool`/`version` 两格都是空的，所以那句「两边相等」我当时无法说清是哪一版答的；r7b4 自己写着「按文件"
      "的格数既不是 `--tree` 的上界也不是下界」，版次不记就等于我在替它担保。件 `receipts/exposure_pair_%s.json`。" % (
          B.slot(pair_tool_path.split("/")[-1]), blob_pairtool,
          B.slot(pair.get("candidate_head")), B.slot(pair.get("base_tip")),
          B.slot(pair.get("candidate_head")),
          B.fmt(pc.get("every_path_matches_the_commit")), B.fmt(pc.get("worktree_clean_after_restore")),
          B.fmt(pc.get("checkout_rc")),
          B.fmt((pc.get("candidate") or {}).get("cells_total")),
          B.fmt((pc.get("base") or {}).get("cells_total")),
          B.fmt(pr.get("hit_set_equal")),
          B.fmt((pc.get("candidate") or {}).get("unresolved_import_count")),
          B.fmt((pc.get("base") or {}).get("unresolved_import_count")),
          B.fmt((pc.get("candidate") or {}).get("parse_diagnostics_total")),
          B.fmt((pc.get("base") or {}).get("parse_diagnostics_total")),
          B.slot(pair.get("ruler")), B.fmt(cx.get("_lane_meta", {}).get("ruler_bytes"), " 字节"),
          # twelve characters, on purpose: this is a sha1 of bytes on my disk, not a git object, and a
          # full 40-hex here would read as a coordinate the commander could not cat-file
          "%s…（本机字节摘要，不是 git 对象）" % str(
              cx.get("_lane_meta", {}).get("ruler_sha1_of_local_bytes"))[:12],
          blob_exp_cand, blob_exp_base, EXPOSURE_GEN))
    A("- 这一对与 §六 上面那两枚面**不是同一次量的**：面与屏读取自候选 `%s`、其基座标签是 `%s`；曝光对的基座"
      "是它自己那次运行的现尖 `%s`，而我与它的分叉点是 `%s`（`git merge-base` 现读）——换进去比对的只有从这枚分叉"
      "到我这一手之间我动过的 %s 枚产品路径，别的车道落进线里的东西我一枚不碰。**这枚基座现在还在不在**也不靠"
      "记：发这页之前又在此刻的现尖 `%s` 上逐枚重读那几枚文件，与那次比对的基座等值 = %s，一枚不等就退 "
      "`ABORT_PAIR_STALE`。所以「bundle 少了什么」那句仍按上一代的基座说，「正文没被送进共用 helper」这句按"
      "它那次的基座说，两句各管各的范围，我不把它们并成一句好看的话。" % (
          B.slot(_fc), B.slot(faces.get("base_label")), B.slot(pair.get("base_tip")),
          B.slot(pair.get("merge_base")), B.fmt(len(pair.get("swapped_paths") or [])),
          B.slot(live_tip), B.fmt(all(pair_still.values()) and bool(pair_still))))
    A("")
    A("## 七、出页那扇门现在真的拦（裁①）")
    A("")
    A("- 装在哪：`tools/r9_block.py` 的 `refuse_on_red()`，页发射器在读完所有件之后、写页之前调用它。"
      "判红的清单是 %s 项：%s。任一项红 → 只落一张 `run/%s_READINGS_RED.json`（具名失败件），页面根本"
      "不生成；上一手那种「页里带一句红、照样投递」的形状没了。" % (
          B.fmt(len(RED_CHECK_NAMES)), "、".join(RED_CHECK_NAMES), REF_GEN))
    A("- 它真咬的证据有两层。本趟：生成这页之前先跑了一遍 `R10_FORCE_RED=引文闸判语`——那一格不动任何件，"
      "只把「判语」这一项按假塞进去，发射器立刻退 `ABORT_READINGS_RED`，只落一张失败件（`run/%s_READINGS_RED."
      "json`，%s），页面文件当时并不存在。枝里：同一扇门咬下来的那些张已经随本手进枝，逐枚现读是 %s。"
      "链里那条 `test ! -f run/%s_block_page.md` 就是钉「红的时候页面不存在」这一格的；它原先查的是**枝号**"
      "那一枚文件名、发射器写的却是**件号**那一枚，两者从来不是同一枚，那条守门条等于没有——本手改成查实际"
      "落点，并在跑拒绝趟之前先 `rm -f` 它，否则重跑会假报。本页是真跑过拒绝之后才生成的。" % (
          REF_GEN, B.fmt(os.path.getsize(os.path.join(B.RUN, "%s_READINGS_RED.json" % REF_GEN)), " 字节"),
          "；".join("`%s`（%s 字节，blob `%s`，`%s`，红的项 %s，其中演练塞的 %s）" % (
              s["path"].split("/")[-1], B.fmt(s["bytes"]), B.slot(s["blob"]), B.slot(s["aborts"]),
              "、".join("`%s`" % c for c in s["failed"]) or "无",
              B.fmt(sum(1 for f in s["forced"] if f))) for s in prior_sheets), GEN))
    A("- 同一趟门里还挂着另一把静态尺：`tools/fmt_lint_r16.py`（原件 `receipts/%s`，blob `%s`）用 AST "
      "把发射器和它的邻居共 %s 枚文件里 %s 处 `模板 %% (参数...)` 当场点数（槽位数 对 参数枚数），"
      "另有 %s 处右侧是单枚表达式、静态点不了数，具名不判而不是当作通过；判语 %s、自检 %s（自检是当场写"
      "一枚故意错的样本、要求它按行号报红，不是嘴上说说）。它排在上面那张清单的第 %s 项。"
      "它拦的就是这一路真踩过三次的形制：句子加了一格、参数没跟上，页要念到那一行才炸——而炸的时候枝已经"
      "推出去了。今天 r15 到 r16 之间就炸过两回：一枚 `not enough arguments for format string`、一枚 "
      "`NameError`（我把一个变量删了却还剩一处引用）。" % (
          FMT_RECEIPT, blob_fmt,
          B.fmt(fmt.get("files_scanned")), B.fmt(fmt.get("calls_checked")),
          B.fmt(fmt.get("single_expression_args")), B.slot(fmt.get("verdict")),
          B.slot((fmt.get("selftest") or {}).get("verdict")),
          B.fmt(RED_CHECK_NAMES.index("静态 arity 尺绿且自检咬下") + 1)))
    A("")
    A("## 八、不在本代的东西（具名）")
    A("")
    A("- 取了的先说清，免得你以为又是空口：**本手新取的**是引文闸、它的反件、全线尺、换代复读、词汇闸与它的"
      "反件、后端臂、收集尺、臂尺、静态 arity 尺、坐标与落地铁（§二到§五、§七）；**沿用上一代的**是两枚面"
      "（`%s` 与 `%s`，件 `receipts/build_faces_r6.json`，blob `%s`）与 %s 趟 390x844 屏读（件 "
      "`receipts/sweep_r6.json`，blob `%s`）与两枚 Q64 曝光尺——它们取于候选 `%s`，本手 0 浏览器、0 构建、"
      "0 端口起停，为什么敢沿用见 §六 那句逐枚产品 blob。" % (
          B.slot(faces.get("base_label")), B.slot(faces.get("candidate_label")), blob_faces2,
          B.fmt(len(sweep.get("runs") or [])), blob_sweep, _fc))
    A("- 手机第二站中心不可按那一格：归滚动容器与底栏两家，等 ORD-0542 后续。「手机打卡门新句的屏读」"
      "按 CMDR 01:24 那块已归 `e766b154`，我不开那格。")
    A("- 那把全线尺看到的别人名下引文一枚没改、也没转单：不判的 %s 条只把归属与机械判语列在件里"
      "（`receipts/%s`，blob `%s`），改不改、转不转由你点（§九 ② 问的就是这一格）。" % (
          B.fmt(aud.get("citations_declined")), AUD_RECEIPT, blob_audit))
    A("- 真机与隧道：NOT_MEASURED。整套 Playwright：NOT_EXECUTED。候选没上 `:4783` 预览站（未部署）。")
    A("- 枝号从 r17 换成 `%s` 不是笔误，也不是贪新：`r17` 已经把**没按现尖重切**的那批提交发出去了"
      "（服务端现读 `%s`），这一手要把那批提交整体重放到现尖 `%s` 之上、再加一枚重锚——那就等于改写已发布的"
      "提交。我唯一的合法动作是另开一枚枝号，不是 `--force`；`r17` 原样留着当证据，两份的差别就是 §〇 那条"
      "重放与 §一 那枚重锚（push 被拒那一次我记在件里，不是事后编的）。" % (
          my_tail, B.slot(prev_r17_sha), B.slot(live_tip)))
    A("")
    A("## 九、下一件（三个待点，我不自作主张）")
    A("")
    A("- ① 出页那扇门按裁①装好了，但它装在**页发射器**这一道。上游 `stage_readings_r6.py` 那一趟没有门："
      "它把件写进 `review/.../receipts/` 就退 0，红不红要等发射器读它时才知道。要不要我把 §七 那张清单"
      "搬到 stage 那道口，让一件红就落不进枝？装上不等于装好，我会带反件证明它真拦（同 §七 的形制）。")
    A("- ② 全线尺按裁②改成按作者判了，于是现出一件我判不了的事：本代不判的 %s 条若按形状算，"
      "是 %s（一件一件连作者 commit 都在 `receipts/%s`，blob `%s`）。这是别人的句子、别人的枝，我一枚不动。"
      "要我把这份归属清单按天发一枚 `note` 到总线（幂等键按天，不会刷屏）好让号令者不必翻件，"
      "还是就让它停在件里等你翻？" % (
          B.fmt(aud.get("citations_declined")),
          "、".join("%s %s 条" % kv for kv in sorted(mech.items())), AUD_RECEIPT, blob_audit))
    A("- ③ 沿用件的名字这一格不再是「规矩洞」这种抽象说法，本手把它量出来了：我与现尖的分叉是 `%s`，"
      "从我这枚枝分叉点到枝尖我动了 %s 枚路径，线在那段里动了 %s 枚，**交集 %s 枚**——其中 `review/` 之下 "
      "%s 枚、之外 %s 枚（`%s`），而**线动了、我没动的 %s 枚**。这最后一格才是重点：这一手的冲突面一枚都不是"
      "跟别的车道抢文件，全部是我自己早期落进线里的那批件被我这一手同名重写。"
      "成因就是我一直在**同名覆盖已经进线的件与量具**：`build_faces_r6.json`、`sweep_r6.json`、`pytest_r6.json`、"
      "`checkin_copy_rows_r6.json`、`reanchor_r8.json` 这几枚固定名每代 blob 变、路径不变；"
      "`citation_gate_*`、`citation_audit_*`、`day*_anchor_recheck_*`、`branch_emit_arm_*`、`fmt_lint_*`、"
      "`pytest_collectonly_*` 这批从 r14 起改成按代命名就不撞。CMDR-0925-2128 对量具代码路径是明令禁重写的，"
      "对件没有明文。`merge-tree` 对现尖与本枝退的是 %s，其中 landing 逐枚判到「要再剪」的 %s 枚是 %s"
      "（每枚在件里带候选 blob、合并 blob、现尖 blob 三格）。请点一个：甲=我把剩下那几枚也改按代名"
      "（下一份叫 `sweep_r19.json`，代价是每代件名都在动、复算入口要跟着改）；乙=接受同名覆盖，但每代把"
      "**旧 blob 与新 blob 都**写进页里；丙=我把 `review/` 里这批一次性挪进 `review/ord0500-checkin/g%s/`，"
      "此后不回头写。我这一手一枚没动它们（除了为裁③重跑的两趟同名件与本手那枚重锚注释）。" % (
          B.slot(me["fork_point"]), B.fmt(len(_mine)), B.fmt(len(_line)), B.fmt(len(overlap)),
          B.fmt(len(ov_review)), B.fmt(len(ov_other)),
          "、".join("`%s`" % p for p in ov_other) or "无", B.fmt(len(_line - _mine)),
          B.fmt(me["merge_tree_exit"]),
          B.fmt(len(me["files_needing_another_recut"])),
          "、".join("`%s`" % c["path"] for c in me["files_needing_another_recut"]) or "无", REF_GEN))
    A("")
    A("复算入口：`git -C D:/moodle/CityNexus ls-remote --refs origin %s %s`；"
      "`git -C D:/moodle/_qoder_phone_ord0485_20260930/wt22 cat-file -t %s`；"
      "作者那两条尺：`git -C .../wt22 log --grep=ORD-0500 --name-only --format= HEAD` 与 "
      "`git -C .../wt22 blame --line-porcelain -- backend/tests/test_qoder_ord0500_journey_refusal.py`；"
      "闸与反件的跑法逐枚写在枝里文件头（反件只写 `scratch_cit_r9/`）。" % (B.TIP_REF, MY_REF, blob_gate))
    A("")
    A("本页生成于 %s，全部数取自本窗口 instrument 写的件；页里没有一枚数是手打的。"
      % datetime.now().astimezone().isoformat(timespec="seconds"))
    block = NL.join(L) + NL

    closing = open(B.CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    out = block + closing.decode("utf-8").rstrip() + NL
    # the page quotes guard names on purpose, so only the leak shapes that cannot be prose are refused;
    # "MISSING" is checked as the sentinel the loaders write, never as a substring of a verdict word
    for bad in ("None", "%s", "MISSING_ARTIFACT", "MISSING_anchor"):
        if bad in out:
            raise SystemExit("ABORT_LEAKED_SLOT %s" % bad)
    dest = os.path.join(B.RUN, "%s_block_page.md" % GEN)
    open(dest, "w", encoding="utf-8", newline=NL).write(out)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("WROTE %s bytes=%d lines=%d product_changed=%d" % (
        dest, len(out.encode("utf-8")), out.count(NL), len(product)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
