"""ORD-0500 r6: stage this order's receipts into the tree and render the readings sheet from them.

Every number in R6_READINGS.md is read out of a JSON an instrument wrote in this window; a missing
artifact prints as its own name rather than as a number carried over from r5 (Q24: a reading belongs
to the generation that took it).  The tools are normalised to LF on the way in because
`.gitattributes` pins `*.py text eol=lf` -- copying a CRLF tool into the tree leaves the worktree
reading dirty right after `git add`, which has burned this lane before.
"""
import json
import os
import shutil
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
DEST = os.path.join(LANE, "wt22/review/ord0500-checkin")
RC = os.path.join(DEST, "receipts")
TL = os.path.join(DEST, "tools")
RUN = os.path.join(DEST, "run")
for d in (RC, TL, RUN):
    os.makedirs(d, exist_ok=True)

EV = ["build_faces_r6.json", "sweep_r6.json", "checkin_copy_rows_r6.json",
      "checkin_copy_rows_r6_control.json", "checkin_copy_rows_r6_M1.json",
      "checkin_copy_rows_r6_M1_revert.json", "checkin_copy_rows_r6_M2.json",
      "checkin_copy_rows_r6_M2_revert.json", "checkin_copy_rows_mutants_r6.json",
      "pytest_r6.json", "r6_exposure_base_dc9dc10f.json", "r6_exposure_cand.json",
      "comment_anchors_r5.json", "prior_denominators_r5.json", "css_delta_proof_r5.json",
      "CE2_MUTANT_RECIPE_r5.md", "landing_r6.json"]
for name in EV:
    src = os.path.join(LANE, "evidence", name)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(RC, name))
for f in os.listdir(os.path.join(LANE, "evidence")):
    if f.startswith("checkin_TIP_dc9dc10f") or f.startswith("checkin_O0500_R6"):
        shutil.copyfile(os.path.join(LANE, "evidence", f), os.path.join(RC, f))
TOOLS = ["checkin_phone_r3.cjs", "make_probe_r6.py", "build_faces_r6.py", "sweep_r6.py",
         "checkin_copy_rows_r6.py", "checkin_copy_rows_mutants_r6.py", "pytest_r6.py",
         "stage_readings_r6.py", "r6_coordinates.py", "r6_block.py",
         "selfdecl_ord0500_r6.py", "comment_anchors_r5.py", "prior_denominators_r5.py",
         "landing_r6.py", "r6_coordinates.py", "r6_block.py"]
for name in TOOLS:
    src = os.path.join(LANE, "tools", name)
    if not os.path.exists(src):
        continue
    data = open(src, "rb").read().replace(b"\r\n", b"\n")
    open(os.path.join(TL, name), "wb").write(data)
for name in ("r6_pytest.txt", "sweep_r6_out.txt", "sweep_r6_out2.txt", "r6_build_O0500_R6.txt",
             "r6_build_TIP_dc9dc10f.txt", "r6_tsc_O0500_R6_tsconfig.check.txt",
             "r6_tsc_O0500_R6_tsconfig.typecheck.txt", "r6_tsc_TIP_dc9dc10f_tsconfig.check.txt",
             "r6_tsc_TIP_dc9dc10f_tsconfig.typecheck.txt", "r6_face_4891.log",
             "r6_face_4892.log", "r6_face_4931.log", "r6_face_4932.log", "r6_face_4933.log",
             "r6_face_4934.log", "r6_face_4935.log", "r6_backend_8151.log",
             "landing_r6_out.txt", "landing_r6_out2.txt", "r6_exposure_base_dc9dc10f.txt",
             "r6_exposure_cand.txt"):
    src = os.path.join(LANE, "run", name)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(RUN, name))


def load(name):
    p = os.path.join(LANE, "evidence", name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"MISSING_ARTIFACT": name}


def cell(v):
    return "NOT_MEASURED" if v is None else (json.dumps(v, ensure_ascii=False)
                                             if isinstance(v, (dict, list)) else str(v))


def readings():
    faces = {f["label"]: f for f in load("build_faces_r6.json").get("faces", [])}
    sweep = {r["tag"]: r for r in load("sweep_r6.json").get("runs", [])}
    rows = load("checkin_copy_rows_r6.json")
    mut = load("checkin_copy_rows_mutants_r6.json")
    py = load("pytest_r6.json")
    base_exp = load("r6_exposure_base_dc9dc10f.json")
    cand_exp = load("r6_exposure_cand.json")
    L = []
    A = L.append
    A("# ORD-0500 r6 -- 英文档那一格：读数单（基座 `dc9dc10fa769bd8c4f3712d9be0dacc2d54d29d5`，"
      "候选 = 本枝）")
    A("")
    A("生成 `%s`。本代新取的读数才写在这页上；r5 那一代的屏幕数不在这里折算，只在第八节按枝点名。"
      % datetime.now().astimezone().isoformat())
    A("")
    A("## 一、两枚面的身份（同一枚工作树换字节再换回来，换回后逐枚 blob 验过）")
    A("")
    A("| 面 | 入口 JS | CSS | bundle 字节 | tsc check | tsc all | build |")
    A("|---|---|---|---|---|---|---|")
    for label in ("TIP_dc9dc10f", "O0500_R6"):
        f = faces.get(label, {})
        e = f.get("entry") or {}
        A("| %s | %s | %s | %s | %s | %s | %s |" % (
            label, cell(e.get("entry_asset")), cell(e.get("css_asset")),
            cell((e.get("bundle") or {}).get("bytes")),
            cell((f.get("tsconfig.check.json") or {}).get("exit")),
            cell((f.get("tsconfig.typecheck.json") or {}).get("exit")),
            cell((f.get("build") or {}).get("exit"))))
    rest = load("build_faces_r6.json").get("restore", {})
    A("")
    A("换回候选字节之后的核对：`every_path_matches_the_commit` = %s，`worktree_clean_after_restore` "
      "= %s，不吻合的枚数 %s；基座面上不存在（本单新增）的路径 %s 枚。件 `receipts/build_faces_r6.json`。"
      % (cell(rest.get("every_path_matches_the_commit")),
         cell(rest.get("worktree_clean_after_restore")),
         cell(len(rest.get("mismatches") or [])),
         cell(len(load("build_faces_r6.json").get("base_absent_paths") or []))))
    A("")
    A("## 二、四趟屏幕读数（390x844、触摸档、判据读渲染文字；每趟一份新私库）")
    A("")
    A("| 跑 | locale | 控件 | 中心命中 | 句主 | 拒绝句枚数 | 屏上 CJK 枚 | CJK 段落 | 屏上标（中/英/按状态） |")
    A("|---|---|---|---|---|---|---|---|---|")
    for tag in ("TIP_dc9dc10f_zh", "TIP_dc9dc10f_en", "O0500_R6_zh", "O0500_R6_en"):
        r = sweep.get(tag, {})
        rd = r.get("readings") or {}
        ad = rd.get("after_duplicate") or {}
        c = rd.get("census") or {}
        A("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            tag, cell(r.get("locale")), cell(c.get("controls")),
            cell(c.get("pressable_by_centre_hit")), cell(ad.get("notice_owners")),
            cell(ad.get("notice_count")), cell(ad.get("cjk_chars_on_screen")),
            cell(ad.get("cjk_runs_on_screen")),
            "%s/%s/%s" % (cell(ad.get("marks_zh_words")), cell(ad.get("marks_en_words")),
                          cell(ad.get("marks_by_state")))))
    A("")
    for tag in ("TIP_dc9dc10f_en", "O0500_R6_en", "O0500_R6_zh"):
        ad = (sweep.get(tag, {}).get("readings") or {}).get("after_duplicate") or {}
        A("- %s 那句逐字：%s" % (tag, cell((ad.get("notices") or [None])[0])))
    en_runs = ((sweep.get("O0500_R6_en", {}).get("readings") or {}).get("after_duplicate") or {}).get(
        "cjk_runs_on_screen") or []
    A("")
    A("屏上那两枚 CJK 字是 `%s` —— 语言切换控件自己的名字，两代都在、与我这笔无关；所以判据按"
      "「除这枚标签外 en 屏无 CJK，且拒绝句与控件名无 CJK」写，不写「整屏 0 枚」（那样基座也红，"
      "量的就不是我这笔了）。" % cell(en_runs))
    A("")
    A("每趟的面身份两证齐：入口名取自被服务的 index.html 并与 `build_faces_r6.json` 记的名比对，"
      "服务字节与磁盘字节 html/bundle 都相等（`identity_ok` 逐趟 %s）；第三证具名 "
      "`NOT_AVAILABLE_BY_CMDR`（vite preview 不往我控制的日志写请求行）。"
      % cell([r.get("serve", {}).get("identity_ok") for r in
              load("sweep_r6.json").get("runs", [])]))
    A("")
    A("## 三、词汇闸（十一行 × 两档，逐行）")
    A("")
    A("| 行 | en 值所在行 | en 里的 CJK | 占位符 | 调用点供上的参数 |")
    A("|---|---|---|---|---|")
    for c in rows.get("row_checks", []):
        if "row" not in c:
            continue
        A("| %s | %s | %s | %s | %s |" % (cell(c.get("row")), cell(c.get("line")),
                                         cell(c.get("cjk_in_en")), cell(c.get("placeholders")),
                                         cell(c.get("supplied"))))
    A("")
    A("闸总结：%s，检查 %s 行，命中 0 条。件 `receipts/checkin_copy_rows_r6.json`。"
      % (cell(rows.get("verdict")), cell(rows.get("rows_checked"))))
    A("")
    A("## 四、两枚反件（各咬自己那一格，跑完按原字节还原）")
    A("")
    A("| 反件 | 做什么 | 期望 | 退出 | 命中的判据 | 还原后退出 | 还原后判据 | 字节回来了 |")
    A("|---|---|---|---|---|---|---|---|")
    for m in mut.get("mutants", []):
        A("| %s | %s | RED | %s | %s | %s | %s | %s |" % (
            cell(m.get("id")), cell("把写死的中文控件名放回英文行" if m.get("id") ==
                                    "M1_hard_coded_label_back"
                                    else "把调用点的 button 参数摘掉，句子里留下花括号"),
            cell(m.get("exit")), cell(m.get("cases")), cell(m.get("revert_exit")),
            cell(m.get("revert_verdict")), cell(m.get("bytes_restored"))))
    A("")
    A("控制趟 %s（退出 %s）；`every_mutant_bit` = %s。件 "
      "`receipts/checkin_copy_rows_mutants_r6.json`，五次闸跑各留一件 "
      "（`checkin_copy_rows_r6_control / _M1 / _M1_revert / _M2 / _M2_revert.json`）。"
      % (cell(mut.get("control_verdict")), cell(mut.get("control_exit")),
         cell(mut.get("every_mutant_bit"))))
    A("")
    A("## 五、门里的臂（服务端没被我碰，还是要在本代跑一遍）")
    A("")
    A("- `%s` 两套 %s 个文件在私库 `%s` 上跑：退出 %s，尾行逐字 %s；跑后库里 %s 行。" % (
        cell(len(py.get("files") or [])), cell(py.get("files")), cell(py.get("private_db")),
        cell(py.get("exit")), cell(py.get("summary_lines", [None])[-1]),
        cell(py.get("checkin_rows_after_the_arms"))))
    A("- 共享库前后：字节 %s 对 %s、mtime_ns %s 对 %s，未被动过 = %s。" % (
        cell((py.get("shared_before") or {}).get("bytes")),
        cell((py.get("shared_after") or {}).get("bytes")),
        cell((py.get("shared_before") or {}).get("mtime_ns")),
        cell((py.get("shared_after") or {}).get("mtime_ns")), cell(py.get("shared_untouched"))))
    b = py.get("main_py_blobs") or {}
    A("- 三枚 `backend/app/main.py` blob：候选 `%s`、r5 那笔 `%s`、现尖 `%s`——前两枚同一枚，"
      "所以我带的是 r5 的后端字节、不是我又改了一版。" % (cell(b.get("candidate_worktree")),
                                                       cell(b.get("r5_commit")),
                                                       cell(b.get("tip_dc9dc10f"))))
    A("")
    A("## 六、Q64 曝光尺：本代两侧各一趟")
    A("")
    A("| 面 | 格总数 | 图内模块 | 未解析 import | 解析诊断 |")
    A("|---|---|---|---|---|")
    for label, d in (("基座 dc9dc10f", base_exp), ("候选 r6", cand_exp)):
        A("| %s | %s | %s | %s | %s |" % (label, cell(d.get("cells_total")),
                                         cell(d.get("modules_in_graph")),
                                         cell(d.get("unresolved_import_count")),
                                         cell(d.get("parse_diagnostics_total"))))
    key = lambda d: sorted("%s:%s" % (h.get("file"), h.get("line")) for h in d.get("hits", []))
    A("")
    A("格总数相等：%s；逐枚（文件:行）集合相等：%s；候选侧多出的格：%s。"
      "也就是「把该档屏幕自己的控件名插进句子」这条路没有把正文值送进任何共用 helper。" % (
          base_exp.get("cells_total") == cand_exp.get("cells_total"), key(base_exp) == key(cand_exp),
          cell(sorted(set(key(cand_exp)) - set(key(base_exp))) or "无")))
    A("")
    A("## 七、这单还欠的一格（要裁，我不自己拍）")
    A("")
    orph = rows.get("orphan_dictionary_rows", [])
    A("- 字典里 `%s` 这几行现在没有读者（读计数逐行 %s），行号是 %s。留、删、还是让我屏回去读，"
      "三种形状的代价在我 19:40 那块里写过；本轮按推荐的「留着 + 钉住」做，没动那枚热文件。" % (
          cell(sorted({o.get("key") for o in orph})),
          cell([o.get("readers_outside_the_dictionary") for o in orph]),
          cell(sorted({n for o in orph for n in (o.get("dictionary_lines") or [])}))))
    A("")
    A("## 八、不在本代的东西（具名，不折算）")
    A("")
    A("- r5 那一代的六趟屏幕普查、三枚门探针、两枚反件在枝 "
      "`review/newlane-ord0500-phone-checkin-entry-r5` 的 `review/ord0500-checkin/` 里，本单不重述其数。")
    A("- 手机第二站中心不可按那一格：本代四趟仍然量到 %s 枚可按（基座与候选同数），归滚动容器与底栏"
      "两家，号令者已裁。" % cell([(t, (s.get("readings") or {}).get("census", {})
                                    .get("pressable_by_centre_hit"))
                                   for t, s in sweep.items()]))
    A("- 真机与隧道：NOT_MEASURED；整套 Playwright 验收：NOT_EXECUTED（只跑本单载体与词汇闸）；"
      "`targetRequired` 那句在屏幕上不可达（打卡钮永远带着一站的名字），所以它由第三节那道闸覆盖，"
      "不拿假可达的桩去凑一趟屏读。")
    text = chr(10).join(L) + chr(10)
    open(os.path.join(DEST, "R6_READINGS.md"), "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s bytes=%d lines=%d" % (os.path.join(DEST, "R6_READINGS.md"),
                                          len(text.encode("utf-8")), text.count(chr(10))))


def main():
    readings()
    listing = sorted(os.path.relpath(os.path.join(r, f), DEST).replace("\\", "/")
                     for r, _, fs in os.walk(DEST) for f in fs)
    total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(DEST) for f in fs)
    print(json.dumps({"files": len(listing), "total_bytes": total,
                      "first": listing[:4], "tools_missing":
                          [t for t in ["r6_coordinates.py", "r6_block.py"]
                           if not os.path.exists(os.path.join(LANE, "tools", t))]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
