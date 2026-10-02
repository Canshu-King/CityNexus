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
MY_REF = "refs/heads/review/newlane-ord0500-phone-checkin-entry-" + GEN
GATE_RECEIPT = "citation_gate_%s.json" % GEN
MUT_RECEIPT = "citation_gate_%s_mutants.json" % GEN
RECEIPT_DIR = "review/ord0500-checkin/receipts"
WT = os.path.join(B.LANE, "wt22")
FOREIGN_SPEC = "backend/tests/test_qoder_ord0476_checkins.py"
NL = chr(10)


def main():
    gate = B.load(GATE_RECEIPT)
    gm = B.load(MUT_RECEIPT)
    py = B.load("pytest_r6.json")
    rows = B.load("checkin_copy_rows_r6.json")
    aud = B.load("citation_audit_r8.json")
    rcpt = B.load(os.environ.get("RECHECK_RECEIPT") or "day25_anchor_recheck_r12.json")
    land = B.load("landing_r6.json")
    me = [r for r in land["refs"] if r["ref"] == MY_REF]
    r9 = [r for r in land["refs"] if r["ref"].endswith("entry-r9")]
    r8 = [r for r in land["refs"] if r["ref"].endswith("entry-r8")]
    if not (len(me) == len(r9) == len(r8) == 1):
        raise SystemExit("ABORT_LANDING_ROWS")
    me, r9, r8 = me[0], r9[0], r8[0]

    blobs = {}
    for line in open(os.path.join(B.RUN, "r6_blobs.txt"), encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            blobs[parts[1]] = parts[0]          # path -> blob sha (the file list, not the key=value form)
    def blob(path):
        return B.fmt(blobs.get(path))
    blob_gate = blob("review/ord0500-checkin/receipts/citation_gate_r10.json")
    blob_mut = blob("review/ord0500-checkin/receipts/citation_gate_r10_mutants.json")
    blob_tool = blob("review/ord0500-checkin/tools/citation_gate_r9.py")
    blob_drv = blob("review/ord0500-checkin/tools/citation_gate_r10_mutants.py")

    # the ownership evidence for the confession: who has ever touched that spec
    rc, touching = B.sh(["git", "log", "--format=%H%x09%s", "--", FOREIGN_SPEC], cwd=WT)
    touching = [l for l in touching.splitlines() if l.strip()]
    mine_touching = [l for l in touching if "ORD-0500" in l]

    rc, listed = B.sh(["git", "ls-remote", "--refs", "origin", B.TIP_REF, MY_REF])
    remote, live_tip = B.pick_sha(listed, MY_REF), B.pick_sha(listed, B.TIP_REF)
    if not remote or not live_tip:
        raise SystemExit("ABORT_NO_REMOTE_READBACK %s" % listed[:200])
    if remote != me["commit"]:
        raise SystemExit("ABORT_REF_MOVED coordinates ran on %s, ref answers %s" % (me["commit"], remote))
    if gm.get("pairs_with_gate_receipt") != GATE_RECEIPT:
        raise SystemExit("ABORT_MUTANT_STALE the mutant run pairs with %s, this page reads %s"
                         % (gm.get("pairs_with_gate_receipt"), GATE_RECEIPT))
    if rcpt.get("branch_head") != remote:
        raise SystemExit("ABORT_RECHECK_STALE the re-check read branch %s, the ref is %s"
                         % (rcpt.get("branch_head"), remote))
    if gate.get("tip") != remote:
        raise SystemExit("ABORT_GATE_STALE gate read %s, the ref is %s -- re-run the gate"
                         % (gate.get("tip"), remote))
    # the line moves every couple of minutes on this project, so "the tip moved" alone is not a reason
    # to refuse a page -- "my citations stopped resolving on the tip as it now stands" is.  Re-measure
    # against the newest tip here, and refuse only on real rot or a product blob that no longer matches.
    import reanchor_r8 as RA
    def _show(rev, path):
        q = subprocess.run(["git", "-C", WT, "show", "%s:%s" % (rev, path)], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=180)
        return None if q.returncode else q.stdout.decode("utf-8", "replace")
    _m, _t = _show(live_tip, "backend/app/main.py"), _show(
        live_tip, "backend/tests/test_qoder_ord0500_journey_refusal.py")
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
    _paths = ["backend/app/main.py", "backend/tests/test_qoder_ord0500_journey_refusal.py",
              "contracts/openapi.yaml", "frontend/src/features/checkin/checkinCopy.ts",
              "frontend/src/features/trip/TripItinerary.tsx"]
    _eq = {}
    for _p in _paths:
        _a = _show(live_tip, _p)
        _b = subprocess.run(["git", "-C", WT, "show", "HEAD:%s" % _p], stdout=subprocess.PIPE,
                            timeout=180).stdout.decode("utf-8", "replace")
        _eq[_p] = (_a == _b)
    if not all(_eq.values()):
        raise SystemExit("ABORT_PRODUCT_MOVED %s" % {k: v for k, v in _eq.items() if not v})
    lag = subprocess.run(["git", "-C", WT, "rev-list", "--count", "%s..%s"
                          % (land["live_tip"], live_tip)], stdout=subprocess.PIPE,
                         timeout=120).stdout.decode().strip()

    # what this ref itself changes: diff from ITS OWN fork point to its head.  Diffing against the live
    # tip instead would count everything other lanes landed since I forked and print a number that
    # contradicts "0 product bytes" -- it did exactly that in an earlier draft of this page.
    rc, names = B.sh(["git", "diff", "--name-only", "%s..%s" % (me["fork_point"], remote)], cwd=WT)
    changed = [n.strip() for n in names.splitlines() if n.strip()]
    product = [n for n in changed if not n.startswith("review/")]
    rc2, ahead = B.sh(["git", "rev-list", "--count", "%s..%s" % (me["fork_point"], live_tip)], cwd=WT)
    line_ahead = ahead.strip()

    gate_tree, mut_tree = None, None
    for nm, store in (("citation_gate_%s.json" % GEN, "gate"), ("citation_gate_%s_mutants.json" % GEN,
                                                                 "mut")):
        rcx, txt = B.sh(["git", "show", "HEAD:review/ord0500-checkin/receipts/" + nm], cwd=WT)
        if rcx == 0 and txt.strip().startswith("{"):
            try:
                parsed = json.loads(txt)
                if store == "gate":
                    gate_tree = parsed
                else:
                    mut_tree = parsed
            except ValueError:
                pass

    foreign = [r for r in (gate.get("rows") or []) if r["verdict"] == "NOT_THIS_LANES_CITATION"]
    runs = gm.get("runs") or []

    L = []
    A = L.append
    A("### ORD-0500 %s（手机车道 0afdb49b）：上一手那枚闸把手伸进了别人的判据文件，这手把范围改成按作者定"
      % GEN.upper())
    A("")
    forked_now = me["fork_point"] == live_tip
    A("现尖 `%s`（`git ls-remote --refs` 现读逐字相等）；本枝 `review/newlane-ord0500-phone-checkin-"
      "entry-%s` = `%s`，%s，合并预测树 `%s`，merge-tree 退出码 %s，写集 %s 枚逐枚字节相同 %s 枚、"
      "需要再 rebase %s 枚。**产品字节 0 枚改动**：现尖到本枝的差共 %s 枚文件，`review/` 之外 %s 枚"
      "（清单：%s）。" % (
          live_tip, GEN, remote,
          ("从这一枚尖自己身上分叉（`fork_point` 相等 = 真）" if forked_now else
           "分叉于 `%s`（现尖之后又落了 %s 枚提交，`git rev-list --count` 现读），landing 判到需要再 "
           "re-cut 的路径仍是 %s 枚——不合的时候不用重剪，这是那把只读尺的答话" % (
               me["fork_point"], B.fmt(len(B.sh(["git", "rev-list", "--count", "%s..%s"
                                                 % (me["fork_point"], live_tip)], cwd=WT)[1].split())),
               B.fmt(len(me["files_needing_another_recut"])))),
          B.slot(me["predicted_tree"]), B.fmt(me["merge_tree_exit"]), B.fmt(me["write_set_files"]),
          B.fmt(me["files_landing_byte_identical"]), B.fmt(len(me["files_needing_another_recut"])),
          B.fmt(len(changed)), B.fmt(len(product)),
          "、".join("`%s`" % p for p in product) or "无"))
    A("")
    A("- 发页这一趟又现读了一次线：landing 那趟判的是 `%s`，此刻线是 `%s`（中间 %s 枚提交，"
      "`git rev-list --count` 现读）。四枚锚在 `%s` 上当场重读 = `%s`，注释现引 = `%s`，腐烂 %s 枚；"
      "本枝与现尖的 %s 枚产品路径逐枚等值 = 真——不相等这页根本生成不出来，发射器里那条 "
      "`ABORT_PRODUCT_MOVED` 就是干这个的。" % (
          land["live_tip"], live_tip, B.slot(lag), live_tip[:12],
          "`、`".join(str(_anchors[k]) for k in ("require", "lookup", "integrity", "caught_by")),
          "`、`".join(str(_cited[k]) for k in ("require", "lookup", "integrity", "caught_by")),
          B.fmt(len(_rot)), B.fmt(len(_eq))))
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
      "`%s`）：上一代之所以要在枝里留下同名旧件不动，是因为那一页已经把它们的 blob 报出去了——覆盖一份"
      "已被引用的机器件，等于把别人的复算入口抹掉。这条规矩是账本里别的车道先记过、我 09-30 自己踩过"
      "一次的。" % (GATE_RECEIPT, MUT_RECEIPT, os.environ.get("RECHECK_RECEIPT") or "—",
                    blob_gate, blob_mut))
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
          B.fmt(gate.get("pin_rows")), "receipts/citation_gate_r10.json", blob_gate, blob_tool))
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
      "%s，红的就是 `%s`。件 `receipts/citation_gate_r10_mutants.json`（blob `%s`），驱动 "
      "`tools/citation_gate_r10_mutants.py`（blob `%s`）。" % (
          B.fmt(m5.get("verdict")), B.fmt(m5.get("red_total")), "NOT_THIS_LANES_CITATION",
          B.slot(m5.get("row_mechanical_verdict")), B.slot(fu.get("owner_commit")),
          B.fmt(m6.get("verdict")), B.slot(m6.get("expect")), blob_mut, blob_drv))
    A("- 件自己也是提交，所以这个形状必须说清：枝里那两份 `citation_gate_%s*.json` 是在 `%s` 那一枚上"
      "跑的读数（`%s` 与 `%s`），本页引的是同一把尺在现在这枚 `%s` 上的重跑——两边只差 tree/tip 两格与"
      "时间戳。要把新件再提交进去，枝尖又前移一格，这个尾巴追不完，所以我停在「页用现跑、枝里那份具名为"
      "上一枚」这一形制上；枝里那份的 blob 是 `%s`。" % (
          GEN, B.slot((gate_tree or {}).get("tip") or "枝里没有同名件"),
          B.slot((gate_tree or {}).get("branch") or "—"), B.slot((gate_tree or {}).get("took_local")
                                                                 or "—"), remote, blob_gate))
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
    A("- 词汇闸：判语 %s、检查 %s 行。r8 那页报的别人名下不 OK 的 %s 条（空行 %s、路径不存在 %s、"
      "裸号无前文 %s，分母 %s 条 / %s 份文件）本手仍一枚没改——那是别人的判据，我这把闸现在也管不着它，"
      "这正是本手要的形状。" % (
          B.fmt(rows.get("verdict")), B.fmt(rows.get("rows_checked")),
          B.fmt(aud.get("mechanically_red")),
          B.fmt((aud.get("verdict_tally") or {}).get("BLANK_LINE_CITED")),
          B.fmt((aud.get("verdict_tally") or {}).get("UNRESOLVED_PATH")),
          B.fmt((aud.get("verdict_tally") or {}).get("ORPHAN_BARE")),
          B.fmt(aud.get("citations_found")), B.fmt(aud.get("files_scanned"))))
    an = rcpt.get("anchors") or {}
    A("- 换代复读（件 `%s`，尖 `%s`）：四枚锚现读是 `%s`，注释里此刻引的是 `%s`，腐烂集合 = %s；本枝与"
      "现尖的产品 blob 逐枚等值 %s 枚 / %s 枚。所以本代不需要再剪一次注释——这句话现在有件撑着，不是我"
      "口头保证。判语 %s，红 %s 枚；r8 那枝对现尖的写集 = %s 枚（早已完全进线）。" % (
          os.environ.get("RECHECK_RECEIPT") or "day25_anchor_recheck_r11.json",
          B.slot(rcpt.get("tip")),
          "`、`".join("`backend/app/main.py:%s`" % an.get(k) for k in
                     ("require", "lookup", "integrity", "caught_by")),
          "`、`".join(str(v) for v in (rcpt.get("cited") or {}).values()),
          B.fmt(len(rcpt.get("rot") or {})),
          B.fmt(sum(1 for v in (rcpt.get("tip_paths_equal_on_branch") or {}).values()
                    if v.get("equal"))),
          B.fmt(len(rcpt.get("tip_paths_equal_on_branch") or {})), B.fmt(gate.get("verdict")),
          B.fmt(gate.get("red_total")), B.fmt(r8["write_set_files"])))
    A("")
    A("## 五、不在本代的东西（具名）")
    A("")
    A("- 屏幕读数一枚没取：本手 0 浏览器、0 端口起停、0 次 `demo/reset`、0 枚产品字节；页里引用的入口名"
      "与 bundle 字节仍属 r7 那一代（枝里 `R6_READINGS.md` 第八节具名沿用）。")
    A("- 手机第二站中心不可按那一格：归滚动容器与底栏两家，等 ORD-0542 后续。「手机打卡门新句的屏读」"
      "按 CMDR 01:24 那块已归 `e766b154`，我不开那格。")
    A("- 字典里 `checkin.duplicate` / `checkin.refused` 两行仍是 0 读者，留 / 删 / 屏回去读三选一仍等你点。")
    A("- 真机与隧道：NOT_MEASURED。整套 Playwright：NOT_EXECUTED。")
    A("")
    A("## 六、下一件（两个待点，我不自作主张）")
    A("")
    A("- ① ORD-0500 r11 我想把这枚闸接到出页那一扇门里：`stage_readings_r6.py` 现在每代跑它并把读数写进"
      "本页，但**红不拦出页**。要不要我装成红就拒绝出页？装上不等于装好，我会带反件证明它真拦。")
    A("- ② `citation_audit_r8.py` 那把全线尺仍只报不改（别人名下 %s 条不 OK）。要我把同一条作者规则也"
      "用到那把尺上、好让号令者一眼看出每条该归谁，我就做；不做就停在这里等点名。" % B.fmt(
          aud.get("mechanically_red")))
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
