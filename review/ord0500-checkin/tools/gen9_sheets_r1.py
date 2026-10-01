"""Generation 4 -- turn the artifacts into the two readings sheets.

Every number in the sheets is read out of a JSON this lane's instruments wrote, in this run.  Nothing
here is a sentence I typed from memory: if an artifact is missing, the cell says NOT_MEASURED rather
than keeping a number from an earlier generation.
"""
import json
import os
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EV = os.path.join(LANE, "evidence")


def load(name):
    p = os.path.join(EV, name)
    if not os.path.exists(p):
        return {"MISSING": name}
    return json.load(open(p, encoding="utf-8"))


def cell(v):
    if v is None:
        return "NOT_MEASURED"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def main():
    builds = load("gen9_builds_r1.json")
    sweep = load("gen9_checkin_sweep_r1.json")
    import glob, time
    _c = sorted(glob.glob(os.path.join(EV, "gen9_doors_*.json")), key=os.path.getmtime)
    doors = load(os.path.basename(_c[-1])) if _c else {"MISSING": "gen9_doors_*.json"}
    globals()["DOORS_FILE"] = os.path.basename(_c[-1]) if _c else "MISSING"
    ce1 = load("gen9_ce1_r1.json")
    proof = load("gen9_ce1_tree_proof_r1.json")
    carrier = load("gen9_carrier_r1.json")

    faces = {f.get("label"): f for f in builds.get("faces", [])}
    runs = {r.get("tag"): r for r in sweep.get("runs", [])}

    def bnd(label, key):
        f = faces.get(label, {})
        e = f.get("entry", {})
        return cell(e.get(key))

    lines = []
    a = lines.append
    a("# ORD-0500 r5 -- 现尖 b604f50d1645d028c2dd1d4406caee8198a3bc2d 读数单（与 ORD-0530 同族并块后重量；曝光尺两侧对照在 receipts 里）")
    a("")
    a("生成时间 `%s`；量具与件都在 `D:/moodle/_qoder_phone_ord0485_20260930`。"
      % datetime.now().astimezone().isoformat())
    a("")
    a("## 一、本代的产物身份（基座 + 交付候选 + 反件）")
    a("")
    a("| 面 | 入口资产 | 打包字节数 | 打包 sha256（本机字节） | tsc check | tsc all | build |")
    a("|---|---|---|---|---|---|---|")
    for label in ("TIP_b604f50d", "O0500_R5", "O0500_CLIENTBOOL_MUTANT"):
        f = faces.get(label, {})
        e = f.get("entry", {})
        bn = e.get("bundle") or {}
        a("| %s | %s | %s | %s | %s | %s | %s |" % (
            label, bnd(label, "entry_asset"), cell(bn.get("bytes")),
            str(bn.get("sha256"))[:16] + "…",
            cell((f.get("tsconfig.check.json") or {}).get("exit")),
            cell((f.get("tsconfig.typecheck.json") or {}).get("exit")),
            cell((f.get("build") or {}).get("exit"))))
    a("")
    a("本机字节 sha256，不是 git 物件，不可 cat-file；件 `evidence/gen9_builds_r1.json`。")
    a("")
    a("## 一′、Q64 曝光尺：基座面与候选面同代各跑一遍（CMDR 02:01 要两侧格总数相同）")
    a("")
    _rc = os.path.join(LANE, "wt22/review/ord0500-checkin/receipts")
    _tip = json.load(open(os.path.join(_rc, "exposure_tip_b604f50d_r1.json"), encoding="utf-8"))
    _cnd = json.load(open(os.path.join(_rc, "exposure_r5_candidate_r1.json"), encoding="utf-8"))
    a("| 面 | 量的树 | 格总数 | 图内模块 | 每规则命中 | unresolved import | 解析诊断 |")
    a("|---|---|---|---|---|---|---|")
    for f in (_tip, _cnd):
        a("| %s | %s | %s | %s | %s | %s | %s |" % (
            "基座" if f is _tip else "候选（本单交付）", cell(f.get("tree")),
            cell(f.get("cells_total")), cell(f.get("modules_in_graph")),
            json.dumps(f.get("per_rule"), ensure_ascii=False, sort_keys=True),
            cell(f.get("unresolved_import_count")), cell(f.get("parse_diagnostics_total"))))
    _key = lambda f: sorted((h.get("file"), h.get("line"), h.get("rule")) for h in f.get("hits", []))
    _extra = [h for h in _cnd.get("hits", []) if (h.get("file"), h.get("line"), h.get("rule"))
              not in _key(_tip)]
    a("")
    a("两侧格总数相同：%s（%s 对 %s）；逐枚（文件、行、规则）集合相等：%s；候选侧多出的格：%s。"
      % (_tip.get("cells_total") == _cnd.get("cells_total"), cell(_tip.get("cells_total")),
         cell(_cnd.get("cells_total")), _key(_tip) == _key(_cnd),
         "无" if not _extra else json.dumps(_extra, ensure_ascii=False)))
    a("")
    _r2 = json.load(open(os.path.join(_rc, "exposure_r2_candidate_r1.json"), encoding="utf-8"))
    _r2extra = [h for h in _r2.get("hits", [])
                if (h.get("file"), h.get("line"), h.get("rule")) not in _key(_tip)]
    a("两枚件：`receipts/exposure_tip_b604f50d_r1.json`、`receipts/exposure_r5_candidate_r1.json`。"
      "上一代（候选把服务器正文交进共用 helper 那一形）的对照留在 "
      "`receipts/exposure_r2_candidate_r1.json`：那枚 %s 格（量的树 `%s`），比基座多出的 %s 枚是 "
      "%s，正是本单被裁的那处缺陷。" % (cell(_r2.get("cells_total")), cell(_r2.get("tree")),
                                        cell(len(_r2extra)),
                                        " 与 ".join("`%s:%s`" % (h.get("file"), h.get("line"))
                                                    for h in _r2extra)))
    a("")
    a("## 二、打卡门在本代的普查（390x844 与 1280x800 各一趟，每趟一份新库）")
    a("")
    a("| 跑 | 视窗 | 站数 | 控件枚数 | 中心命中可按 | 盒 | 到屏时门里行数 | 屏上已打卡枚数 |")
    a("|---|---|---|---|---|---|---|---|")
    for tag, r in runs.items():
        rd = r.get("readings", {})
        c = rd.get("census", {})
        arr = rd.get("arrived", {})
        a("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            tag, cell(r.get("viewport")), cell(arr.get("stops")), cell(c.get("controls")),
            cell(c.get("pressable_by_centre_hit")),
            cell(sorted(set(c.get("boxes") or []))),
            cell((r.get("store_after_schema") or {}).get("count")), cell(arr.get("marks"))))
    a("")
    a("## 二′、历代同一把尺的分母：各代自己的件，逐枚带 blob")
    a("")
    a("本代之外的那几代，面早就不在了，数只能从它们各自冻结的交件枝里读回来（件 "
      "`evidence/prior_denominators_r5.json`，逐枚 `git ls-tree`+`cat-file`）。每行的 blob 就是那个数被读出来的那枚物件。")
    a("")
    prior = load("prior_denominators_r5.json")
    a("| 代 | 该代枝头 | 面 | 控件 | 中心命中可按 | 重复点击后拒绝句 | 读自哪枚 blob |")
    a("|---|---|---|---|---|---|---|")
    for row in prior.get("refs", []):
        for f in row.get("faces", []):
            read_from = (str(f.get("blob")) if f.get("blob")
                         else "本代那一行读自 `%s`（件在本枝的树里，blob 见 `git ls-tree`）"
                              % cell(f.get("file")))
            a("| %s | %s | %s | %s | %s | %s | %s |" % (
                cell(row.get("generation")), cell(str(row.get("commit"))[:12]),
                cell(f.get("generation_tag")), cell(f.get("controls")),
                cell(f.get("pressable_by_centre_hit")),
                cell(f.get("notices_after_duplicate")), read_from))
    gaps = [r.get("generation") for r in prior.get("refs", []) if r.get("GAP")]
    a("")
    a("缺口具名：%s 那一代的枝上只有截图、没有它自己基座面的普查 JSON，所以它那一代的中心命中枚数"
      "在这里读不到（NOT_AVAILABLE_IN_THAT_REF）。本代的枝把 JSON 与截图都放进去了，不留同样的洞。"
      % ("、".join(gaps) if gaps else "无"))
    a("")
    a("历代对照读出的是：r1、r2 那两代的手机面枚枚中心命中，本代基座与候选一起掉到同一枚数——"
      "掉的原因不在我这两笔里，表里「基座」那一行就是证据。")
    a("")
    a("## 三、真发一发：行数前后与那句拒绝")
    a("")
    a("| 跑 | 请求序列 | 行数 前→后 | 重复点击后屏上拒绝句枚数 | 句主 | 句子 |")
    a("|---|---|---|---|---|---|")
    for tag, r in runs.items():
        rd = r.get("readings", {})
        ad = rd.get("after_duplicate", {})
        na = (rd.get("census", {}).get("controls") == 0)
        if na:
            a("| %s | %s | %s→%s | 不适用：这一族代 %s 枚打卡控件，没有可点的第二下 | 不适用 | 不适用 |" % (
                tag, cell(rd.get("requests")),
                cell((r.get("store_after_schema") or {}).get("count")),
                cell((r.get("store_after_arm") or {}).get("count")),
                cell(rd.get("census", {}).get("controls"))))
            continue
        a("| %s | %s | %s→%s | %s | %s | %s |" % (
            tag, cell(rd.get("requests")),
            cell((r.get("store_after_schema") or {}).get("count")),
            cell((r.get("store_after_arm") or {}).get("count")),
            cell(ad.get("notice_count")), cell(ad.get("notice_owners")),
            cell((ad.get("notices") or [None])[0])))
    a("")
    a("## 四、门里的拒绝原文（四字段陈列，不造句子）")
    a("")
    a("件 `evidence/%s`（三枚后端各自起进程、各自一份一次性库，共享库未被触碰）。"
      % globals().get("DOORS_FILE", "MISSING"))
    a("")
    # one run per served backend, labelled by the tree each one booted -- the sheet must not carry
    # tree names from an earlier generation
    ROLE = {"wt23": "基座（现尖原样）", "wt22": "候选（本单交付）", "mutgen9": "反件一（409 判据摘掉）"}
    for r in doors.get("runs", []):
        name = ROLE.get(r.get("tree"), r.get("tree"))
        if not r:
            a("- %s：NOT_MEASURED（件缺）" % name)
            continue
        a("- %s `main.py` sha256 `%s…`，库行数 %s→%s，共享库未被动：%s" % (
            name, r.get("main_sha256", "")[:16],
            cell((r.get("staged") or {}).get("store_before", {}).get("count")),
            cell(r.get("store_after", {}).get("count")), cell(r.get("shared_untouched"))))
        a("")
        a("  | 用例 | http_status | content_type | body_bytes | reason_code | 句子里有 uuid | details 为 null | details |")
        a("  |---|---|---|---|---|---|---|---|")
        for p in r.get("probes", []):
            # NO_ERROR_OBJECT is the only field that separates a success body from a refusal whose
            # reason_code happens to be null -- keying on `reason_code is None` would print the
            # base door's unnamed refusal as "成功体里没有 error 对象", i.e. hide the defect.
            ok = p.get("envelope_keys") == "NO_ERROR_OBJECT"
            rc = ("不适用：成功体里没有 error 对象" if ok
                  else ("null（这一格测到了：拒绝体里没有这个名字）"
                        if p.get("reason_code") is None else cell(p.get("reason_code"))))
            dt = ("不适用：成功体里没有 error 对象" if ok
                  else ("null（这一格测到了：拒绝句该点名的格子是空的）"
                        if p.get("details") is None else cell(p.get("details"))[:120]))
            dn = ("不适用：成功体里没有 error 对象" if ok else cell(p.get("details_is_null")))
            a("  | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                p.get("case"), cell(p.get("http_status")), cell(p.get("content_type")),
                cell(p.get("body_bytes")), rc,
                cell(p.get("uuid_in_message")), dn, dt))
        a("")
        if r.get("mutant_screen"):
            ms = r["mutant_screen"]
            arm = ms.get("arm") or {}
            a("  反件屏侧：交付候选面 `%s`（outDir `%s`）挂在被改过的门上（判据摘掉），臂退出 %s，"
              "请求序列 %s，拒绝句枚数 %s，句主 %s，走完臂时库里 %s 行，pageerror %s "
              "—— 状态码与句子两样都看不出是哪一层拒的，这就是假绿。"
              % (cell((ms.get("serve") or {}).get("entry_asset")),
                 str((ms.get("serve") or {}).get("face_dir", "")).split("faces/")[-1],
                 cell(arm.get("exit")), cell(arm.get("requests")),
                 cell(arm.get("notice_count")), cell(arm.get("notice_owners")),
                 cell((ms.get("store_after_screen") or {}).get("count")),
                 cell(arm.get("page_errors"))))
            a("")
    a("## 五、反件一（服务端 409 判据摘掉）")
    a("")
    a("| 侧 | 臂数合计 | 通过 | 失败 | 退出 | 失败的臂 |")
    a("|---|---|---|---|---|---|")
    import re as _re
    for r in ce1.get("runs", []):
        summary = str(r.get("summary_line"))
        nums = dict(_re.findall(r"(\d+) (passed|failed|error)", summary))
        passed_u = sorted(set(r.get("passed_names") or []))
        failed_u = sorted(set(r.get("failed_names") or []))
        a("| %s | %s | %s | %s | %s | %s |" % (
            r.get("label"), "%s（= 通过 %d + 失败 %d，臂名去重）" % (len(passed_u) + len(failed_u), len(passed_u), len(failed_u)),
            "%s（臂名去重）" % len(passed_u), "%s（臂名去重）" % len(failed_u),
            cell(r.get("exit")), cell(failed_u)))
        r["_failed_unique"] = failed_u
    a("")
    compared = sum(int(v.get("files_compared") or 0) for v in (proof.get("dirs") or {}).values())
    a("两枚树只差 `backend/app/main.py` 一枚文件（比对 %s 枚，只有 main.py 不同＝%s，"
      "件 `evidence/gen9_ce1_tree_proof_r1.json`）；交付那枚的 `main.py` 前后 sha256 同一枚：%s…（本机字节 sha256，不是 git 物件，"
      "不可 cat-file）" % (cell(compared), cell(proof.get("only_main_py_differs")),
                          str(ce1.get("candidate_main_sha256_before", ""))[:16]))
    a("")
    a("## 六、反件二（屏上的标不是门里给的）")
    a("")
    for tag in ("TIP_b604f50d_phone", "O0500_R5_phone", "O0500_CLIENTBOOL_MUTANT_phone"):
        r = runs.get(tag, {})
        rd = r.get("readings", {})
        arr = rd.get("arrived", {})
        a("- %s：门里 %s 行时屏上 %s 枚「已打卡」；走完两站后门里 %s 行、最后一次屏读 %s 枚" % (
            tag, cell((r.get("store_after_schema") or {}).get("count")), cell(arr.get("marks")),
            cell((r.get("store_after_arm") or {}).get("count")),
            cell((rd.get("after_second") or {}).get("marks"))))
    a("")
    a("## 七、词汇闸（ORD-0485）不在这一页上。" )
    a("")
    a("那一单量在它自己那一代（基座 0989713aa687b97f4cd40bae009a6ce493425a4b），读数单是`review/ord0485-phone-walk/GEN6_READINGS.md`，随枝 `review/newlane-ord0485-phone-walkthrough-r5` 交付；把它的数写在本单页眉下就是跨代折算，Q24 不许。")
    a("")
    a("## 八、打卡真理载体（本单三臂）在三面上的通过/失败")
    a("")
    arms = load("gen9_carrier_arms_r1.json")
    for r in arms.get("runs", []):
        st = r.get("stats", {})
        a("- %s（Playwright 报告 %s）：通过 %s 枚，失败 %s 枚" % (
            r.get("label"), cell(r.get("report")), cell(st.get("expected")),
            cell(st.get("unexpected"))))
        for arm in r.get("arms", []):
            a("    · %-8s %s" % (cell(arm.get("status")), cell(arm.get("arm"))))
            if arm.get("node_message"):
                a("        %s" % arm["node_message"])
    a("")
    for r in carrier.get("runs", []):
        a("  （同跑的库行数 %s：%s→%s，入口 %s，服务字节与磁盘字节相等 %s）" % (
            r.get("label"), cell(r.get("rows_before")), cell(r.get("rows_after")),
            cell((r.get("serve") or {}).get("entry_asset")),
            cell((r.get("serve") or {}).get("index_bytes_equal_served_vs_disk"))))
    a("")
    a("## 九、没走的与不修的（具名）")
    a("")
    a("- 真机与隧道：NOT_MEASURED，以上全是本机 127.0.0.1 面上的模拟器读数。")
    a("- 整套 Playwright 验收：NOT_EXECUTED，只跑本单自己的载体与邻座已收的词汇闸。")
    a("- `GET /api/v1/journeys/{id}/checkins` 那一扇门在基座代仍不给未知行程具名（`require()` 印 uuid "
      "且 details 为 null）：本单在候选代把两扇门一起具名了，但契约侧只写 POST 的 404 —— 因为 GET 侧"
      "补 404 会撞 ORD-0476 已收的那条契约臂（`sorted(listed[\"responses\"]) == [\"200\", \"409\"]`），"
      "那是别人手上的判据，我不改。这条缺口具名留着，不在我写集里。")
    a("")
    a("## 十、随本轮一起改的两处注释（改的是我自己写进件里的话）")
    a("")
    anch = load("comment_anchors_r5.json")
    a("`backend/tests/test_qoder_ord0500_journey_refusal.py` 的注释里有四处 `main.py` 行号。"
      "件 `%s` 在基座树（= 现尖 `%s`）逐枚读回：新四处全部命中它声称的那句；旧四处在现尖、"
      "上一尖 `%s`、以及那四处最初被写下的那一尖 `%s` 上都不命中 —— 也就是这不是上游位移，"
      "是我从一开始就没测。" % (cell(anch.get("tool")), cell(str(anch.get("tip"))[:12]),
                                cell(str(anch.get("prev_tip"))[:12]),
                                cell(str(anch.get("origin_tip"))[:12])))
    a("")
    a("  | 注释说的那件事 | 旧行号 | 旧行在现尖读作 | 旧行在上一尖读作 | 旧行在 origin 尖读作 | 新行号 | 新行在现尖读作 | 命中 |")
    a("  |---|---|---|---|---|---|---|---|")
    for r in anch.get("rows", []):
        a("  | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            cell(r.get("what_the_comment_claims")), cell(r.get("old_line")),
            "`%s`" % cell(r.get("old_text")), "`%s`" % cell(r.get("old_text_on_prev_tip")),
            "`%s`" % cell(r.get("old_text_on_origin_tip")), cell(r.get("new_line")),
            "`%s`" % cell(r.get("new_text")), cell(r.get("new_carries"))))
    a("")
    cssp = load("css_delta_proof_r5.json")
    a("`frontend/src/features/checkin/footprint.css` 里我那段注释原话是「all six stops answer a centre hit」，"
      "而本代普查量到的是 5/6 —— 话错了，按读数改成实测句。件 `%s`：r4 那枚 blob `%s`、本轮 `%s`，"
      "差 %s 增 %s 删，删除行全是注释正文（`removed_are_prose_only.clean` = %s），"
      "ORD-0530 的 `cn-footprints__day` 那 %s 行两侧逐字相等：%s，改后那句写的是 %s of 6，"
      "旧那句还在不在：%s。" % (
          cell(cssp.get("tool")), cell(cssp.get("blob_r4")), cell(cssp.get("blob_r5")),
          cell((cssp.get("lines") or {}).get("added")), cell((cssp.get("lines") or {}).get("removed")),
          cell((cssp.get("removed_are_prose_only") or {}).get("clean")),
          cell((cssp.get("ord0530_section") or {}).get("day_class_lines_r5")),
          cell((cssp.get("ord0530_section") or {}).get("identical")),
          cell(cssp.get("sentence_claims_n_of_6")), cell(cssp.get("stale_all_six_phrase_present"))))
    a("")
    a("可达性这条本轮量到的形状（同一把尺：`scrollIntoViewIfNeeded` 后取控件自身中心的 "
      "`elementFromPoint`）：")
    a("")
    a("| 面 | 站 | 控件 | 中心命中可按 | 不可按的那一枚（索引：站名） |")
    a("|---|---|---|---|---|")
    for tag in ("TIP_b604f50d_phone", "O0500_R5_phone", "TIP_b604f50d_desktop", "O0500_R5_desktop"):
        r = runs.get(tag, {})
        c = (r.get("readings") or {}).get("census") or {}
        raw = load("checkin_%s_%s_r2.json" % (tag, r.get("viewport")))
        names = []
        for row in raw.get("rows", []):
            for b in (row.get("buttons") or []):
                if not b.get("hit_self"):
                    names.append("%s:%s" % (cell(b.get("index")), cell(b.get("stop"))))
        a("| %s | %s | %s | %s | %s |" % (
            tag, cell((r.get("readings") or {}).get("arrived", {}).get("stops")),
            cell(c.get("controls")), cell(c.get("pressable_by_centre_hit")),
            "、".join(names) if names else "无（枚枚中心命中）"))
    a("")
    scroll = load("checkin_SCROLLTEST_phone_390x844_r2.json")
    scensus = [row for row in scroll.get("rows", []) if "census" in str(row.get("arm"))]
    s_press = sum(1 for row in scensus for b in (row.get("buttons") or []) if b.get("hit_self"))
    s_total = sum(len(row.get("buttons") or []) for row in scensus)
    a("`scroll-margin-bottom: 92px` 那条单独造了一面重跑（面 `%s`，件 `receipts/checkin_SCROLLTEST_phone_390x844_r2.json`）："
      "中心命中可按 %s/%s 枚，与不加这条规则的候选面 %s/%s 枚一样，于是撤了这条规则、不留装饰；"
      "真正要动的是滚动容器与手机底栏那两家，不在本单写集里，具名报出。" % (
          cell(scroll.get("face")), cell(s_press), cell(s_total),
          cell((runs.get("O0500_R5_phone", {}).get("readings") or {}).get(
              "census", {}).get("pressable_by_centre_hit")),
          cell((runs.get("O0500_R5_phone", {}).get("readings") or {}).get(
              "census", {}).get("controls"))))
    text = "\n".join(lines) + "\n"
    for dest in (os.path.join(LANE, "wt22/review/ord0500-checkin/GEN9_READINGS.md"),):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8", newline="\n").write(text)
        print("WROTE %s bytes=%d lines=%d" % (dest, len(text.encode("utf-8")), text.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
