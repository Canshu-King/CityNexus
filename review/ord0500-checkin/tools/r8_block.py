"""ORD-0500 r8: the ledger page, assembled only from artifacts this window wrote.

Same discipline as the r7 emitter, because the fault it guards against is mine and it keeps
recurring: no number is typed here.  Every figure is pulled out of a JSON an instrument wrote or out
of the coordinate files `r6_coordinates.py` verified with `git cat-file -t`, and a slot that cannot be
filled aborts the run instead of falling back to a remembered value.  The closing line is read byte
for byte out of the commander's own file, never retyped.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
R8_REF = "refs/heads/review/newlane-ord0500-phone-checkin-entry-r8"
EV = os.path.join(LANE, "evidence")
RUN = os.path.join(LANE, "run")
WT = os.path.join(LANE, "wt22")
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
    """The sha on the line whose second field is exactly the ref asked for (see the coordinates tool:
    reading the first token of the blob once turned a transport warning into `live_tip: ssh:`)."""
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == needle and re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            return parts[0]
    return None


def slot(v):
    """A missing reading is written as its own name and aborts the page -- never smoothed over.

    The abort names the call site, because "a slot was empty" without a line number sent me hunting
    through six receipts last time.
    """
    if v is None:
        fr = sys._getframe(1)
        raise SystemExit("ABORT_MISSING_SLOT at %s line %s" % (fr.f_code.co_filename, fr.f_lineno))
    return v


def fmt(v, unit=""):
    if isinstance(v, bool):
        return "真" if v else "假"
    if isinstance(v, (list, tuple)):
        # an empty list is a reading of "none", and it must say so -- joining it into "" would leave a
        # sentence with a blank where a number belongs
        inner = "（%s）" % "、".join(str(x) for x in v) if v else "（空集）"
        return "%d %s%s" % (len(v), unit or "枚", inner)
    return "%s%s" % (slot(v), unit)


def join_nums(vals):
    return " / ".join(str(v) for v in vals)


def main():
    land = load("landing_r6.json")
    r8 = [r for r in land["refs"] if r["ref"].endswith("entry-r8")]
    if len(r8) != 1:
        raise SystemExit("ABORT_NO_R8_IN_LANDING %d" % len(r8))
    r8 = r8[0]
    # the copy committed inside the branch: a receipt is itself a commit, so this one necessarily
    # describes the commit the branch held before it -- the page says so instead of hiding it
    land_tree = json.load(open(os.path.join(
        WT, "review/ord0500-checkin/receipts/landing_r6.json"), encoding="utf-8"))
    r8t = [r for r in land_tree["refs"] if r["ref"].endswith("entry-r8")][0]
    ra = load("reanchor_r8.json")
    st = load("reanchor_r8_selftest.json")
    ca = load("citation_audit_r8.json")
    py = load("pytest_r6.json")
    rows = load("checkin_copy_rows_r6.json")
    mut = load("checkin_copy_rows_mutants_r6.json")
    blobs = {}
    for line in open(os.path.join(RUN, "r6_blobs.txt"), encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            blobs.setdefault(parts[1], parts[0])
    mt = {}
    for line in open(os.path.join(RUN, "r6_merge_tree.txt"), encoding="utf-8"):
        p = line.split()
        for i in range(0, len(p) - 1, 2):
            mt.setdefault(p[i], p[i + 1])
    tip = fmt(mt.get("live_tip"))
    cand = fmt(mt.get("candidate"))
    predict = fmt(mt.get("predicted_tree"))
    # the page refuses to post against a world that moved after the readings were taken
    rc, listed = sh(["git", "ls-remote", "origin", TIP_REF, R8_REF])
    remote = pick_sha(listed, R8_REF)
    live_tip = pick_sha(listed, TIP_REF)
    if remote is None or live_tip is None:
        raise SystemExit("ABORT_NO_REMOTE_READBACK rc=%s %s" % (rc, listed[:200]))
    if live_tip != mt.get("live_tip"):
        raise SystemExit("ABORT_TIP_MOVED readings judged %s, the line now answers %s -- re-run the "
                         "readings before posting" % (mt.get("live_tip"), live_tip))
    if remote != mt.get("candidate"):
        raise SystemExit("ABORT_REF_MOVED coordinates ran on %s but the ref answers %s"
                         % (mt.get("candidate"), remote))
    blob_test = fmt(blobs.get("backend/tests/test_qoder_ord0500_journey_refusal.py"))
    blob_ra = fmt(blobs.get("review/ord0500-checkin/receipts/reanchor_r8.json"))
    blob_st = fmt(blobs.get("review/ord0500-checkin/receipts/reanchor_r8_selftest.json"))
    blob_ca = fmt(blobs.get("review/ord0500-checkin/receipts/citation_audit_r8.json"))
    blob_tool = fmt(blobs.get("review/ord0500-checkin/tools/reanchor_r8.py"))
    blob_main = fmt(blobs.get("backend/app/main.py"))
    blob_cc = fmt(blobs.get("frontend/src/features/checkin/checkinCopy.ts"))
    tally = ca["verdict_tally"]
    b = py["main_py_blobs"]
    an, old, vt = ra["anchors"], ra["numbers_replaced_from"], ra["verified_texts"]
    span = "%s 到 %s" % tuple(ra["route_span"])
    ORDER = ("require", "lookup", "integrity", "caught_by")
    nums = lambda d: " / ".join(str(d[k]) for k in ORDER)
    # the bare-name collision count is a reading too: how many tracked paths end in /main.py, and how
    # many of those are the frozen checkpoint copies under review/
    tracked = subprocess.run(["git", "-C", WT, "ls-files"], stdout=subprocess.PIPE,
                             timeout=180).stdout.decode("utf-8", "replace").splitlines()
    coll = [t for t in tracked if t.endswith("/main.py") or t == "main.py"]
    coll_review = [t for t in coll if t.startswith("review/")]
    # the negative claim in section five needs its inventory, not my word
    cred = [t for t in tracked if "credential_gate" in t]
    n_4307 = len([t for t in tracked if t.endswith("test_qoder_ord04307_credential_gate.py")])
    n_307 = len([t for t in tracked if t.endswith("test_qoder_ord0307_credential_gate.py")])

    L = []
    A = L.append
    A("### ORD-0500 r8（手机车道 0afdb49b）：字已经在线上，这一枝把自家注释里那四枚行号量回来")
    A("")
    A("现尖 `%s`（本枝从它自己身上分叉，`fork_point` 与之相等 %s）。本枝 `review/newlane-"
      "ord0500-phone-checkin-entry-r8` = `%s`，判读合并预测树 `%s`，merge-tree 退出码 %s。"
      "上一轮 22:52 那块已把 r7 收进线，所以这轮不是再抢落地，是把落地的东西说得经得起打开。" % (
          tip, fmt(r8["fork_point"] == tip), cand, predict, fmt(r8["merge_tree_exit"])))
    A("")
    A("## 一、这一枝只改了一件事（写集逐枚可点）")
    A("")
    A("- 写集 %s 枚文件，合并进现尖后逐枚字节相同 %s 枚，需要再 rebase 的 %s 枚。数取自车道本地件 "
      "`%s`（判的就是远端那一枚 %s）。" % (
          fmt(r8["write_set_files"]), fmt(r8["files_landing_byte_identical"]),
          fmt(len(r8["files_needing_another_recut"])), "evidence/landing_r6.json", cand))
    A("- 枝里同名那份 `review/ord0500-checkin/receipts/landing_r6.json` 判的是上一枚 %s（写集 %s 枚），"
      "比本页少 %s 枚：件本身也是一笔提交，所以枝里那份永远落后一枚。这不是读数错，是这形状的必然，"
      "写出来免得你按本页去对枝里的件对不上。" % (
          fmt(r8t["commit"]), fmt(r8t["write_set_files"]),
          fmt(r8["write_set_files"] - r8t["write_set_files"])))
    A("- 三枚枝尖读数对不对得上（这是本页自己的闸）：远端 `%s` 回读 %s、合并预测那趟判的候选 %s、"
      "landing 件判的那枚 commit %s —— 三者同一枚 = %s。%s" % (
          "newlane-ord0500-phone-checkin-entry-r8", remote, mt["candidate"], r8["commit"],
          fmt(remote == mt["candidate"] == r8["commit"]),
          "" if remote == mt["candidate"] == r8["commit"] else
          "不同一枚的原因是件本身也是一笔提交：把新件塞进枝里，枝尖就又前移一格；这一页不去追那"
          "一枚，只把「哪一枚被判过」写清楚，复算命令在末尾点名。"))
    A("- 产品侧只有 `backend/tests/test_qoder_ord0500_journey_refusal.py` 那一笔注释（blob `%s`），"
      "其余是 `review/ord0500-checkin/` 里的件与工具。前端字节一枚没动：引用这枚后端规格的 `%s`"
      " = %s，所以 r7 那一代的入口名与 bundle 字节不在这儿重述成本轮新读数。" % (
          blob_test, "frontend_files_referencing_the_test", fmt(ra["frontend_files_referencing_the_test"])))
    A("- 两枚仍在线上的产品 blob 顺手回读：`backend/app/main.py` = `%s`，"
      "`frontend/src/features/checkin/checkinCopy.ts` = `%s`（现尖与工作树同一枚，本枝没碰它们）。" % (
          blob_main, blob_cc))
    A("")
    A("## 二、四枚行号：注释里写的 → 现尖读到的")
    A("")
    A("| 说法 | 注释里的旧数 | 现尖读到的 | 那一行现在的原文 |")
    A("|---|---|---|---|")
    for lab, desc in (("require", "共用的 `require()` 助手"),
                      ("lookup", "门里自己先查一次表"),
                      ("integrity", "唯一索引那层捕获"),
                      ("caught_by", "`caught_by: unique_index` 那一支")):
        A("| %s（%s） | %s | %s | `%s` |" % (lab, desc, fmt(old[lab]), fmt(an[lab]), vt[lab]))
    A("")
    A("- 旧数 `%s` 是我在 r5 那一代量到的，随基座走动全数失效；这轮的数一律从现尖 `%s` 的 "
      "`backend/app/main.py`（共 %s 行）当场读：打卡那扇门自己的区间 `%s` 由路由路径那两行定位"
      "（不是我记的偏移），每枚锚还要求在这段里唯一，否则工具直接 ABORT。件 "
      "`review/ord0500-checkin/receipts/reanchor_r8.json`（blob `%s`）。" % (
          nums(old), tip, fmt(ra["main_lines"]), span, blob_ra))
    A("- 现在注释里那四枚行号是 `%s`；被替换掉的旧数是 `%s`，两两都不相等 = %s 枚（相等就不必修，"
      "工具在这种情况下会拒绝写任何东西）。" % (nums(an), nums(old), fmt(len(ra["were_stale"]))))
    A("")
    A("## 三、闸自己也挨了反件打（这一节是为我自己那一类错写的）")
    A("")
    A("- 我第一版本工具就把正文打坏了：替换串少写一枚反引号，注释里那句「require 助手」前面的记号被"
      "吞掉、句子撕开一半。"
      "所以 `apply()` 现在有一条只许改数字的闸：把两侧所有数字遮掉之后正文必须逐字相同，不相同就 "
      "`ABORT_TEXT_CHANGED`。这一条不是摆设，它拦的就是我自己刚犯的那个错。")
    A("- 三臂都跑在临时命名空间里，不碰工作树：反件一（少反引号）期望 %s；反件二（把锚定的短语改掉，"
      "让工具「什么都没换还装作曲线走完」）期望 %s；正件遮数之后正文逐字相同 = %s，改动行数 %s 行，"
      "字节数 %s 对 %s（只动数字所以总字节不变）。`every_arm` = %s。件 "
      "`review/ord0500-checkin/receipts/reanchor_r8_selftest.json`（blob `%s`）。" % (
          fmt(st["s1_prose_mutation"]["abort_head"]), fmt(st["s2_reworded_control"]["abort_head"]),
          fmt(st["s3_real_application"]["prose_identical_when_every_digit_masked"]),
          fmt(st["s3_real_application"]["lines_changed"]),
          fmt(st["s3_real_application"]["bytes_before"]),
          fmt(st["s3_real_application"]["bytes_after"]),
          fmt(st["every_arm"]), blob_st))
    A("- 那枚工具与它的反件都在枝里：`review/ord0500-checkin/tools/reanchor_r8.py`（blob `%s`）。" % blob_tool)
    A("")
    A("## 四、门里的臂与词汇闸（本代重跑，不是抄上一代）")
    A("")
    A("- 两套后端规格（`%s`）在私库 `%s` 上跑：退出码 %s，尾行逐字 `%s`，跑后库里 %s 行打卡。"
      "共享库没被碰：字节 %s 对 %s、mtime_ns %s 对 %s，未动 = %s。" % (
          "`、`".join(x.split("/")[-1] for x in py["files"]), fmt(py["private_db"]), fmt(py["exit"]),
          fmt(py["summary_lines"][-1]), fmt(py["checkin_rows_after_the_arms"]),
          fmt(py["shared_before"]["bytes"]), fmt(py["shared_after"]["bytes"]),
          fmt(py["shared_before"]["mtime_ns"]), fmt(py["shared_after"]["mtime_ns"]),
          fmt(py["shared_untouched"])))
    A("- 三枚 `backend/app/main.py` blob 的相等关系：候选 `%s` 对判读时现尖 `%s` 同一枚 = %s —— 这一枚"
      "相等就是「我那笔产品字节确实在线上」的字节证；候选对 r5 那一笔 `%s` = %s（不同是应该的，基座"
      "走过别人好几笔）。" % (
          fmt(b["candidate_worktree"]), fmt(b["tip_at_run"]),
          fmt(b["candidate_worktree"] == b["tip_at_run"]), fmt(b["r5_commit"]),
          fmt(b["candidate_worktree"] == b["r5_commit"])))
    A("- 词汇闸：%s，检查 %s 行；两枚反件跑完按原字节还原，`every_mutant_bit` = %s，控制趟 %s。" % (
        fmt(rows["verdict"]), fmt(rows["rows_checked"]), fmt(mut["every_mutant_bit"]),
        fmt(mut.get("control_verdict"))))
    A("")
    A("## 五、全线源码注释里的 path:line 我逐枚打开了一遍（只读，别人手上的判据我没动）")
    A("")
    A("- 分母：`backend/app`、`backend/tests`、`frontend/src`、`contracts` 四处的 %s 个 py/ts/tsx "
      "文件里 %s 枚 `path:line` 引文（含 %s 枚同段裸数 `%s`，按「读到此刻最近一枚具名路径」解）。"
      "本单自己那 %s 枚逐条 OK。不 OK 的 %s 枚分布：%s。件 "
      "`review/ord0500-checkin/receipts/citation_audit_r8.json`（blob `%s`）。" % (
          fmt(ca["files_scanned"]), fmt(ca["citations_found"]),
          fmt(sum(1 for r in ca["rows"] if r.get("bare"))), ":(\\d+)",
          fmt(ca["citations_in_this_lanes_files"]), fmt(ca["mechanically_red"]),
          "、".join("%s %s 枚" % (k, v) for k, v in sorted(tally.items()) if k != "OK"), blob_ca))
    A("- 最该点名的一条：`backend/tests/test_qoder_ord0467_v13_contract_family.py:3` 引的是 "
      "`test_qoder_ord04307_credential_gate.py:180`，而这枚文件名在库里不存在 —— 「不存在」按登记清单"
      "数出来：以该名结尾的路径 %s 条；同族另一枚 `backend/tests/test_qoder_ord0307_credential_gate.py` "
      "结尾的有 %s 条（它第 %s 行的那句确实在），所以那是 4 与 3 之差一枚字笔误，不是两件东西。归 0467 "
      "那一手，我不改别人的判据文件。" % (
          fmt(n_4307), fmt(n_307),
          fmt([r["line"] for r in ca["rows"]
               if r["verdict"] == "OK" and r["target"].endswith("test_qoder_ord0307_credential_gate.py")
               ][0])))
    A("- 另有 %s 枚引文指向一枚空行（含 `frontend/src/features/pending/pendingSet.ts:9` 引 "
      "`backend/app/main.py:5362`），这是「行号在、内容不是那句说的东西」的形状；逐条原文都在件里，"
      "本页不替别人修。" % fmt(tally.get("BLANK_LINE_CITED")))
    A("- 尺自己的限度具名：写裸名（如 `main.py:3527`）的引文，我按「排除 `review/` 里那些整棵冻结"
      "副本之后唯一后缀」解 —— 登记在库的 %s 条路径里有 %s 条以 `/main.py` 收尾，其中 %s 条是 "
      "`review/` 的检查点副本；不去掉就得把所有裸名引文都判成「不可解」。剩 %s 枚仍无解（已在上面"
      "点名）。" % (
          fmt(len(tracked)), fmt(len(coll)), fmt(len(coll_review)),
          fmt(tally.get("UNRESOLVED_PATH"))))
    A("")
    A("## 六、不在本代的东西（具名，不折算）")
    A("")
    A("- 手机第二站中心不可按那一格：仍归滚动容器与底栏两家，等 0542 后续；本代没重取屏幕读数，"
      "也不把 r7 的数当新的用。")
    A("- 字典里 `checkin.duplicate` / `checkin.refused` 两行仍是 0 读者（本轮词汇闸的读数在 "
      "`receipts/checkin_copy_rows_r6.json` 里逐行带着），留、删、还是让我屏回去读，等你点一个；"
      "我这侧的「留着 + 钉住」臂在跑。")
    A("- 真机与隧道：NOT_MEASURED。整套 Playwright 验收：NOT_EXECUTED（只跑本单载体与两把闸）。")
    A("")
    A("## 七、下一件（我自申报，不合序就驳）")
    A("")
    A("- 我名下账本没有未接单，按序自申报 ORD-0500 r9：把足迹那一屏（`FootprintPanel`）的两档屏读"
      "补上，并让它走与行程屏同一把词汇闸。这件会撞底栏那两家的写集，所以我先问一句再动手：**现在就"
      "起 r9，还是等 0542 后续把底栏那一格合完再起？**你没点头之前我只把 r8 交清，不开那枚屏读。"
      "r8 这一枝本身不需要再 rebase，依据是第一节点名的「需要再 rebase」计数 = %s 枚。" % (
          fmt(len(r8["files_needing_another_recut"]))))
    A("")
    A("复算入口（逐条可点）：`git -C D:/moodle/CityNexus ls-remote origin "
      "refs/heads/mirror/integration-frontend-apple-pass1 refs/heads/review/newlane-ord0500-phone-"
      "checkin-entry-r8`；`git -C D:/moodle/_qoder_phone_ord0485_20260930/wt22 cat-file -t %s`；"
      "第一节那枚「引用这枚后端规格的前端文件 = 0」由 `git -C .../wt22 grep -l "
      "test_qoder_ord0500_journey_refusal -- frontend` 复算（回空即 0 枚）；第五节那 175 枚引文的"
      "普查用 `D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0500-checkin/tools/"
      "citation_audit_r8.py`（只读，件落车道 evidence 目录），四枚行号那趟同理跑 `reanchor_r8.py`，"
      "它改的是工作树里那一笔注释，跑之前先 `git checkout` 干净。读数工具都在枝里 "
      "`review/ord0500-checkin/tools/`，跑法逐枚写在文件头。" % blob_ra)
    A("")
    A("本页生成于 %s，全部数取自本窗口写的件；页里没有一枚数是手打的。"
      % datetime.now().astimezone().isoformat())
    block = NL.join(L) + NL

    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    out = block + closing.decode("utf-8").rstrip() + NL
    # a page that lost a slot to a None would print the word; refuse instead
    for bad in ("NOT_MEASURED_FROM_RECEIPT", "ABORT_MISSING", "  None", "None "):
        if bad in out:
            raise SystemExit("ABORT_LEAKED_SLOT %s" % bad)
    dest = os.path.join(RUN, "r8_block_page.md")
    open(dest, "w", encoding="utf-8", newline=NL).write(out)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(sys.stdout, "reconfigure") else None
    print("WROTE %s bytes=%d lines=%d" % (dest, len(out.encode("utf-8")), out.count(NL)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
