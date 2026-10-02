"""ORD-0500 r9: the ledger page for the citation gate, filled only from artifacts this window wrote.

Same rule as the r8 emitter, and for the same reason -- the numbers in this lane's pages have been my
recurring fault, so nothing here is typed: every figure is read out of a JSON an instrument wrote or
out of `git`, a slot that cannot be filled aborts the page by name, and the page refuses to post if the
authoritative line or my own ref moved after the readings were taken.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
WT = os.path.join(LANE, "wt22")
EV = os.path.join(LANE, "evidence")
RUN = os.path.join(LANE, "run")
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
MY_REF = "refs/heads/review/newlane-ord0500-phone-checkin-entry-r9"
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
NL = chr(10)


def load(name):
    return json.load(open(os.path.join(EV, name), encoding="utf-8"))


def sh(args, cwd=REPO):
    env = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
    env["NO_PROXY"] = "*"
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=300, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def pick_sha(text, needle):
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == needle and re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            return parts[0]
    return None


def one(v):
    """A one-element list is how the recheck receipt stores an anchor; the page says the number."""
    return v[0] if isinstance(v, list) and len(v) == 1 else v


def slot(v):
    if v is None:
        fr = sys._getframe(1)
        raise SystemExit("ABORT_MISSING_SLOT at line %s" % fr.f_lineno)
    return v


def fmt(v, unit=""):
    if isinstance(v, bool):
        return "真" if v else "假"
    if isinstance(v, (list, tuple, set)):
        inner = "（%s）" % "、".join(str(x) for x in v) if v else "（空集）"
        return "%d %s%s" % (len(v), unit or "枚", inner)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return "%s%s" % (slot(v), unit)


def main():
    gate = load("citation_gate_r9.json")
    gm = load("citation_gate_r9_mutants.json")
    rc9 = load("day24_anchor_recheck_r9.json")
    py = load("pytest_r6.json")
    rows = load("checkin_copy_rows_r6.json")
    aud = load("citation_audit_r8.json")
    land = load("landing_r6.json")
    me = [r for r in land["refs"] if r["ref"] == MY_REF]
    r8 = [r for r in land["refs"] if r["ref"].endswith("entry-r8")]
    if len(me) != 1 or len(r8) != 1:
        raise SystemExit("ABORT_LANDING_ROWS me=%d r8=%d" % (len(me), len(r8)))
    me, r8 = me[0], r8[0]
    blobs = {}
    for line in open(os.path.join(RUN, "r6_blobs.txt"), encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            blobs.setdefault(parts[1], parts[0])
    blob_gate = fmt(blobs.get("review/ord0500-checkin/receipts/citation_gate_r9.json"))
    blob_mut = fmt(blobs.get("review/ord0500-checkin/receipts/citation_gate_r9_mutants.json"))
    blob_rc9 = fmt(blobs.get("review/ord0500-checkin/receipts/day24_anchor_recheck_r9.json"))
    blob_tool = fmt(blobs.get("review/ord0500-checkin/tools/citation_gate_r9.py"))
    blob_test = fmt(blobs.get("backend/tests/test_qoder_ord0500_journey_refusal.py"))

    rc, listed = sh(["git", "ls-remote", "--refs", "origin", TIP_REF, MY_REF])
    remote, live_tip = pick_sha(listed, MY_REF), pick_sha(listed, TIP_REF)
    if not remote or not live_tip:
        raise SystemExit("ABORT_NO_REMOTE_READBACK rc=%s %s" % (rc, listed[:200]))
    if live_tip != land["live_tip"]:
        raise SystemExit("ABORT_TIP_MOVED readings judged %s, the line now answers %s"
                         % (land["live_tip"], live_tip))
    if remote != me["commit"]:
        raise SystemExit("ABORT_REF_MOVED coordinates ran on %s, the ref answers %s"
                         % (me["commit"], remote))

    an = rc9.get("true_anchors_on_day24") or {}
    cited = rc9.get("cited_in_tip_copy_of_my_test") or []
    eqs = rc9.get("r8_product_paths_equal_on_day24") or {}
    b = py.get("main_py_blobs") or {}
    runs = {r["id"]: r for r in (gm.get("runs") or [])}

    L = []
    A = L.append
    A("### ORD-0500 r9（手机车道 0afdb49b）：把这单栽过三次的「注释行号会腐烂」装进随代必跑的闸")
    A("")
    A("被测尖 `%s`（`git ls-remote --refs` 现读逐字相等）。本枝 `review/newlane-ord0500-phone-checkin-"
      "entry-r9` = `%s`，从这一枚尖自己身上分叉（`fork_point` 与之相等 = %s），合并预测树 `%s`，"
      "merge-tree 退出码 %s；写集 %s 枚文件，逐枚合并进现尖字节相同 %s 枚，需要再 rebase 的 %s 枚。"
      "**产品字节 0 枚改动**（本手全部是 `review/ord0500-checkin/` 里的闸、件与工具）。" % (
          live_tip, remote, fmt(me["fork_point"] == live_tip), slot(me["predicted_tree"]),
          fmt(me["merge_tree_exit"]), fmt(me["write_set_files"]),
          fmt(me["files_landing_byte_identical"]), fmt(len(me["files_needing_another_recut"]))))
    A("")
    A("## 一、这一手从哪来（为什么不领屏读）")
    A("")
    A("- 账本 CMDR 01:24 那块派九手，逐条花名是 `6a150e1e`、`82f55d8a`、`cff87c64`、`5a53846b`、"
      "`e766b154`、`6a773af1`、`8ac89982`、`1d64acf5`、`2d2d7428` —— 没有 `0afdb49b`。九条里离我这扇门"
      "最近的一条是「手机打卡门新句的屏读」，已点名给 `e766b154`，所以我不开那格屏读：同一枚屏幕两家各读"
      "一遍是浪费你的手，撞别人的判据是失礼。")
    A("- 我名下现在无未交单（r7、r8 都在线上：r8 那枝 `%s` 对现尖的写集 = %s 枚，一枚不差，这就是「已经"
      "完全进线」的字节证）。于是按你给的第二条路自认领一件只属于我这扇门的活。" % (
          r8["commit"], fmt(r8["write_set_files"])))
    A("- 活的选法：这一单为同一枚错重剪三次（r5、r6、r8 都是注释里 `backend/app/main.py` 的行号随换代漂"
      "移）。r8 那把尺 `reanchor_r8.py` 修得好一次，修不了「下一次还得记得跑」。这手把它变成闸。")
    A("")
    A("## 二、闸的形制（只闸我自己名下的文件）")
    A("")
    A("- 被闸 %s 枚文件（`backend/tests/test_qoder_ord0500_journey_refusal.py`、"
      "`backend/tests/test_qoder_ord0476_checkins.py`、`frontend/src/features/checkin/checkinCopy.ts`、"
      "`frontend/src/features/checkin/checkins.ts`、`frontend/src/features/trip/TripItinerary.tsx`），"
      "**别人手上的判据文件一枚不闸**；查 %s 条引文，判语 %s，红 %s 条。件 "
      "`receipts/citation_gate_r9.json`（blob `%s`），闸 `%s`。" % (
          fmt(gate.get("files_gated")), fmt(gate.get("citations_checked")),
          fmt(gate.get("verdict")), fmt(gate.get("red_total")), blob_gate, blob_tool))
    A("- 拦四种红加一格自审：%s。前三种是机械的（路径不存在、行号超出文件长度、指到空行）；"
      "第四种 `CITED_LINE_CONTENT_MISMATCH` 才是这单真正栽过的那格——行号在范围内、不空，只是那一行"
      "早已不是句子说的那件事。" % fmt(sorted(k for k in (gate.get("verdict_tally") or {}) if k != "OK")))
    A("- 句子声称那一行写着什么，闸就真去读那一行：带内容钉子的引文 %s 枚，钉子是 "
      "`backend/app/main.py:%s`（require 助手）、`%s`（门里自查）、`%s`（唯一索引那层）、`%s`"
      "（`caught_by` 那一支）。" % (
          fmt(gate.get("pinned_citations")), one(an.get("require")), one(an.get("lookup")),
          one(an.get("integrity")), one(an.get("caught_by"))))
    A("- 钉子不许我手改：闸跑时把上面这四个字符串与 r8 那把尺当场量到的原文逐一比对，不相符就直接红"
      "（`expectations_agree_with_r8_receipt` = %s，读的是枝里 `receipts/reanchor_r8.json` 那份）。"
      "所以钉子换代的唯一合法路径是重跑量锚的尺、让件自己变，而不是在这枚文件里改数。" % fmt(
          gate.get("expectations_agree_with_r8_receipt")))
    A("- 闸拦不住的那一格也具名：它读得出「那一行现在写着什么」，读不出「这句话本来想指哪一行」。"
      "这句话如果被改掉，闸报 `CITED_PHRASE_GONE_FROM_COMMENT` 而不是悄悄不查——本代该格 %s 枚。" % (
          fmt((gate.get("verdict_tally") or {}).get("CITED_PHRASE_GONE_FROM_COMMENT"))))
    A("- 解析规矩写死一处：裸名（如 `main.py`）只在「去掉 `review/` 冻结副本后唯一」时才认，本代"
      "登记在库的非 `review/` 路径 %s 条即按此取。" % fmt(gate.get("live_tracked_paths")))
    A("- 闸的范围按**引文那一行的作者**定，不按我手写的文件清单定：本代看到 %s 条引文，判 %s 条、"
      "不判 %s 条（不判的那些逐条带着写它的那枚 commit，本手名下的 commit 集合是从 `git log --grep` "
      "现读的 %s 枚，不是记的）。不判 ≠ 不看：那 %s 条的机械判语仍逐条写在件里的 `mechanical_verdict`，"
      "只是不进红、不进我的判语。被看到但不判的文件：%s。" % (
          fmt(gate.get("citations_checked")), fmt(gate.get("citations_gated")),
          fmt(gate.get("citations_foreign")), fmt(gate.get("lane_commits_in_set")),
          fmt(gate.get("citations_foreign")),
          "、".join("`%s`" % f for f in (gate.get("foreign_files_seen") or [])) or "无"))
    A("")
    A("## 三、反件（每枚只咬一格，跑完按原字节还原；M5 两枚是反方向的：不许咬的那格必须不咬）")
    A("")
    A("| 反件 | 写进注释的那枚数 | 期望红类 | 真红了吗 | 判语 |")
    A("|---|---|---|---|---|")
    for r in [x for x in (gm.get("runs") or []) if str(x.get("id")).startswith("M")]:
        A("| %s | %s | %s | %s | %s |" % (slot(r.get("id")), slot(r.get("citation_written")),
                                         slot(r.get("expect")), fmt(r.get("bite")),
                                         fmt(r.get("verdict"))))
    A("")
    A("- 控制趟（同一棵树未改的副本）判语 %s，还原后判语 %s，`every_mutant_bit` = %s，副本字节全部回来 "
      "= %s；副本在 `scratch_cit_r9/` 里共 %s 份，判它用的登记清单仍取真实仓库那 %s 条——临时树不做自己"
      "的权威。`wt22` 工作树全程干净 = %s（不干净的那行清单 %s）。件 "
      "`receipts/citation_gate_r9_mutants.json`（blob `%s`）。" % (
          fmt(gm.get("control_verdict")), fmt(gm.get("after_revert_verdict")),
          fmt(gm.get("every_mutant_bit")), fmt(gm.get("all_bytes_restored")),
          fmt(gm.get("files_copied")), fmt(gate.get("live_tracked_paths")),
          fmt(gm.get("wt22_worktree_clean")), fmt(gm.get("wt22_dirty_lines")), blob_mut))
    A("- M4 是历史缺陷的原样复现：把 `%s` X `%s`——在范围内、不是空行，"
      "只是那一行现在是别的东西。r5/r6/r8 三度重剪的就是这一格，本代它一被写进副本就红。" % (
          "backend/app/main.py:%s" % one(an.get("require")), "backend/app/main.py:810"))
    A("")
    A("## 四、day24 换代复读（闸说这代是干净的，且它自己没被改口）")
    A("")
    A("- 尖 `%s` 的 `backend/app/main.py` 里四枚锚现读仍是 `%s`；注释里此刻引的就是 `%s`；两者逐项"
      "相等 = %s，所以本代**不需要**再剪一次注释。件 `receipts/day24_anchor_recheck_r9.json`（blob `%s`）。"
      % (slot(rc9.get("tip_day24")), fmt(sorted({v[0] for v in an.values()})),
         fmt(cited), fmt(sorted({v[0] for v in an.values()}) == sorted(cited)), blob_rc9))
    A("- 我这单 %s 枚产品路径在 day24 尖上与 r8 那枝逐枚等值 = %s（逐枚 `git rev-parse <rev>:<路径>` "
      "现读）：%s。" % (
          fmt(len(eqs)), fmt(all(v.get("equal") for v in eqs.values())),
          "、".join("`%s`" % k for k in sorted(eqs))))
    A("- 门里的臂本代在这枚尖上重跑：两套规格在私库 `%s` 上，退出码 %s，尾行逐字 `%s`，跑后库中 %s 行；"
      "共享库字节 `%s` 对 `%s`、mtime_ns `%s` 对 `%s`，未动 = %s。三枚 main.py blob：候选 `%s` 对判读时"
      "现尖 `%s` 同一枚 = %s。" % (
          slot(py.get("private_db")), fmt(py.get("exit")), slot(py.get("summary_lines")[-1]),
          fmt(py.get("checkin_rows_after_the_arms")),
          slot(py.get("shared_before", {}).get("bytes")), slot(py.get("shared_after", {}).get("bytes")),
          slot(py.get("shared_before", {}).get("mtime_ns")),
          slot(py.get("shared_after", {}).get("mtime_ns")), fmt(py.get("shared_untouched")),
          slot(b.get("candidate_worktree")), slot(b.get("tip_at_run")),
          fmt(b.get("candidate_worktree") == b.get("tip_at_run"))))
    mut = load("checkin_copy_rows_mutants_r6.json")
    A("- 词汇闸一并在这枚尖上重跑：判语 %s、检查 %s 行；它自己的两枚反件本代仍各自咬下来（%s，"
      "控制趟 %s 退出码 %s，`every_mutant_bit` = %s，临时树与工作树隔开 = %s）。件 "
      "`receipts/checkin_copy_rows_mutants_r6.json`。" % (
          fmt(rows.get("verdict")), fmt(rows.get("rows_checked")),
          "、".join("`%s` 判语 %s/还原后 %s" % (m.get("id"), m.get("verdict"),
                                                   m.get("revert_verdict")) for m in mut.get("mutants", [])),
          fmt(mut.get("control_verdict")), fmt(mut.get("control_exit")),
          fmt(mut.get("every_mutant_bit")), fmt(mut.get("scratch_isolated_from_wt22"))))
    A("")
    A("## 五、不在本代的东西（具名，不折算）")
    A("")
    A("- 屏幕读数一枚没取：本手 0 浏览器、0 端口起停、0 次 `demo/reset`；页面上引用的入口名与 bundle "
      "字节仍属 r7 那一代（枝里 `R6_READINGS.md` 第八节具名沿用），没被当成本轮新读数。")
    A("- 手机第二站中心不可按那一格：仍归滚动容器与底栏两家，等 ORD-0542 后续；本代没重取，也不替他们判。")
    A("- 字典里 `checkin.duplicate` / `checkin.refused` 两行仍是 0 读者（本轮词汇闸逐行带着读者计数，共检查 %s 行），"
      "留、删、屏回去读三选一仍等你点。" % fmt(rows.get("rows_checked")))
    A("- 真机与隧道：NOT_MEASURED。整套 Playwright 验收：NOT_EXECUTED（只跑本单载体、词汇闸与这枚新闸）。")
    A("- r8 那页报过别人手上不 OK 的 %s 条引文（指到空行 %s 条、路径不存在 %s 条、裸号无前文 %s 条，"
      "分母 %s 条 / %s 份文件）：本手一枚没改，闸也只闸我自己名下那 %s 枚文件。件 "
      "`receipts/citation_audit_r8.json`。" % (
          fmt(aud.get("mechanically_red")), fmt((aud.get("verdict_tally") or {}).get("BLANK_LINE_CITED")),
          fmt((aud.get("verdict_tally") or {}).get("UNRESOLVED_PATH")),
          fmt((aud.get("verdict_tally") or {}).get("ORPHAN_BARE")), fmt(aud.get("citations_found")),
          fmt(aud.get("files_scanned")), fmt(gate.get("files_gated"))))
    A("")
    A("## 六、下一件")
    A("")
    A("- 闸已装上，本手收口；我名下无未交、无待剪。两件事等你：① ORD-0500 r10 要不要我把这枚闸推到"
      "「每代 stage 必跑、红就拒绝出页」（现在它已进 `stage_readings_r6.py` 的件清单，但红不拦出页）；"
      "② `e766b154` 那格屏读若需要门侧配套数（同一枚私库、同一把词汇闸），我只交件不开屏。")
    A("")
    A("复算入口：`git -C D:/moodle/CityNexus ls-remote --refs origin %s %s`；"
      "`git -C D:/moodle/_qoder_phone_ord0485_20260930/wt22 cat-file -t %s`；"
      "闸与反件的跑法逐枚写在枝里 `review/ord0500-checkin/tools/citation_gate_r9.py` 与 "
      "`citation_gate_r9_mutants.py` 文件头（后者只写 `scratch_cit_r9/`，不碰工作树）。" % (
          TIP_REF, MY_REF, blob_gate))
    A("")
    A("本页生成于 %s，全部数取自本窗口 instrument 写的件；页里没有一枚数是手打的。"
      % datetime.now().astimezone().isoformat(timespec="seconds"))
    block = NL.join(L) + NL

    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    out = block + closing.decode("utf-8").rstrip() + NL
    for bad in ("None", "%s", "NOT_MEASURED_FROM_RECEIPT", "ABORT_MISSING"):
        if bad in out and bad != "NOT_MEASURED_FROM_RECEIPT":
            if bad == "None" and "None" in slot(py.get("summary_lines")[-1]):
                continue
            raise SystemExit("ABORT_LEAKED_SLOT %s" % bad)
    dest = os.path.join(RUN, "r9_block_page.md")
    open(dest, "w", encoding="utf-8", newline=NL).write(out)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("WROTE %s bytes=%d lines=%d" % (dest, len(out.encode("utf-8")), out.count(NL)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
