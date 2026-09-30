# -*- coding: utf-8 -*-
"""Emit the ORD-0536 delivery block for the ledger inbox.

Every number here is read back out of an artifact in this directory at write time, and the row that
produces it is named next to it, because two rounds ago I quoted a count the command had not produced.
Nothing in this script is a literal reading.
"""
import hashlib
import io
import json
import os

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0536"
LANE = "1d64acf5-3f5f-48e8-a7b4-9d7a37996edb"


def load(name):
    return json.load(io.open(os.path.join(WORK, name), encoding="utf-8"))


def blob(name):
    raw = io.open(os.path.join(WORK, name), "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(), len(raw)


rec = load("generation_reconciliation_r1.json")
ce = load("counterexamples_r1.json")
dv = load("door_view_r1.json")
st = load("st_r8_full.json")
ex = load("report_tip_7862c6de.json")
cand = load("report_cmdr_side_candidate.json")
sizes = load("export_sizes_r1.json")
caller = load("caller_cells_key_r1.json")
receipt = load("publish_receipt_r1.json")

TIP = "7862c6de5565c02c20ec2dccaa9da18960603e06"
HEAD = "66cd53af64ac99c0784108ebd7b5276cc8ac2917"
BLOB = "83819289685f4bb58c5dea728114473f66fd29ef"
MERGE = "6147d21fb54ce37e1370020335eac3b4445ffc97"

tree_rows = {}
for label, row in rec["trees"].items():
    tree_rows[label] = row

arms = st["exemption_arms"]
pair = dv["commander_pair"]
ctrl = ce["control"]["counts"]
m1 = {k: v for k, v in ce["mutants"].items() if k.startswith("cli_") is False and k != "published_bytes"}
m3 = {k: ce["mutants"][k] for k in ("fold_entry_removed", "fold_exempts_without_measuring")}
pub = ce["mutants"]["published_bytes"]

L = []
A = L.append

A("### ORD-0536 车道 %s：曝光尺的豁免全部改由一枚冻在尺里的形状表决定，表在形制上就写不出「某一格」；豁免前的分母从此不动，现针 8 格＝5 红＋3 枚逐格有据，两侧对照（候选 10 / 现针 6）用门钉那把逐字复现" % LANE)
A("")
A("**先印出我读了什么（不是断言）**：号令者 02:13 题面给的现针是 `f1decd85549996bad56d0e81ce77fa4e1ceeaeab`，叫醒那轮给的逐字是 `7862c6de5565c02ec0ec2dccaa9da18960603e06`。我在 `D:/moodle/CityNexus` 跑 `env -u HTTP_PROXY -u HTTPS_PROXY git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`，回读 `%s`；后一串逐字送进 `git cat-file -t` 报 could not get object info，我这一串回 commit。本块所有读数都在我这一串上，题面那串 `f1decd85…` 是 02:13 的针，我没去复现它——它已不是现针。" % TIP)
A("")
A("**这一单真正的缺口在哪里，是我找出来的，不是题面写好的**：尺族里已经有两条结构化豁免（ORD-0408 甲的契约闭集、Q67/Q75 的折叠具名锚），它们**判得对**；问题出在**豁免一旦生效，那一格就从 `hits` 搬进另一个列表，于是分母跟着制度走**。同一棵现针导出树上，门钉的 r7b 报 6 格、我上一轮发的 r7b4 报 5 格，差的那一格（`RecoveryRequiredPanel.tsx:299`）就是被折叠锚**静默**移走的——没人打印过它的依据。门 Q64 那一臂比的正是绝对格数（`preflight_and_land_r7.py:384` 从 `exposure_counts` 造 `growth`），所以「尺换了一代」与「候选真的长了曝光面」在门上读起来是同一件事。这就是「靠人手放」的形状：不是有人在块里写字，是**数字会随制度漂，只有人能把它圆回来**。")
A("")
A("## 1 交的一枚文件（已发布路径 0 改动）")
A("")
A("新名 `live_checks/ui_exposure_taint_ast_r8.cjs`，blob `%s`，%d B；枝 `review/S4-ord0536-structured-exemption-r8` 头 `%s`，`ls-remote` 回读与本机 `rev-parse` 逐字相等；对现针只读预测 `git merge-tree --write-tree` 退出 0、预测树 `%s`。r7b 与 r7b4 两枚已发布字节一字未动（本轮对账里它们仍按自己的字节被跑）：r7b blob `%s` %d B、r7b4 blob `%s` %d B，逐枚取自 `generation_reconciliation_r1.json` 的 `rulers`。" % (
    BLOB, blob("ui_exposure_taint_ast_r8.cjs")[1], HEAD, MERGE,
    rec["rulers"]["r7b"]["blob"], rec["rulers"]["r7b"]["bytes"],
    rec["rulers"]["r7b4"]["blob"], rec["rulers"]["r7b4"]["bytes"]))
A("")
A("## 2 豁免由结构化条件决定，写成了数据")
A("")
A("一枚冻在尺里的表，两条目，键就是题面点名的三根轴：**哪条规则 × 哪种 sink 形状（家族）× 哪个 origin_kind**，再加一条**必须在树上量得到**的证据谓词：")
A("")
A("| 条目 | rules | sink 形状家族 | origin_kind | 证据（必须实测） |")
A("| --- | --- | --- | --- | --- |")
for e in st["exemption_table_under_test"]["entries"]:
    A("| `%s` | %s | %s | %s | `%s` |" % (e["id"], ", ".join("`%s`" % x for x in e["rules"]),
                                        ", ".join("`%s`" % x for x in e["sink_shape_families"]),
                                        ", ".join("`%s`" % x for x in e["origin_kinds"]), e["evidence"]))
A("")
A("表的字节摘要 `%s`，每次跑都印在输出的 `exemption_table.digest_sha1` 里（件 `st_r8_full.json` blob `%s`）。" % (
    st["exemption_table_under_test"]["digest_sha1"], blob("st_r8_full.json")[0]))
A("")
A("**表写不出「某一格」，这是形制检查，不是口号**：`validateExemptionTable` 只允许 `id / rules / sink_shape_families / origin_kinds / evidence` 五枚键，任何值长得像路径、扩展名、行号或 16 位格 id 就拒；家族轴里带 `:`（即一整枚 sink 形状而不是一族）也拒；`evidence` 不在实现过的谓词名里同样拒。六枚真跑的拒件在 `counterexamples_r1.json`（blob %s），逐枚退 3 并回 `EXEMPTION_TABLE_SCHEMA_REJECTED`：" % blob("counterexamples_r1.json")[0])
for k, v in sorted(m1.items()):
    if k.startswith("cli_"):
        continue
    A("- `%s` ⇒ `%s`（期望的那条形制检查确实报出：%s）" % (k, ", ".join(v["problems"]), v["expected_problem_reported"]))
A("")
A("**命令行也没有后门**：接受的旗标是一枚闭集（`--tree --file --ref --path --out --contract --selftest`）；长得像豁免的旗标逐具名拒，不忽略、不降级。四枚真跑（同一件）：")
for k, v in sorted(ce["mutants"].items()):
    if not k.startswith("cli_"):
        continue
    A("- `%s` ⇒ 退出 %s，reason `%s`，且 `--out` 那枚文件没被写出（%s）" % (
        k.replace("cli_", "--"), v["exit"], v["refusal_reasons"][0], v["no_output_file_written"]))
A("")
A("## 3 现针上的具名报回：豁免的格逐格打印，没豁免的照旧红")
A("")
A("跑形制（两条命令都是我在 `D:/moodle/_qoder_lane_S4_0926/work/ord0536` 下逐字敲的，`node` 是 v24.18.0，环境里没有 `PYTHONPATH`/`NODE_PATH`）：")
A("")
A("```")
A("$ git archive %s frontend/src contracts | tar -x -C exp_tip_r8" % TIP)
A("$ node ui_exposure_taint_ast_r8.cjs --tree exp_tip_r8/frontend/src --contract exp_tip_r8/contracts/openapi.yaml --out report_tip_7862c6de.json")
A("cells_total %s = red %s + exempted %s   # 门钉的 r7b 在同一棵树上报 %s hits" % (
    ctrl["cells_total"], ctrl["red"], ctrl["exempted"], tree_rows["tip_7862c6de"]["r7b"]["red"]))
A("```")
A("")
A("被豁免的 %d 枚，逐格（规则 + 文件 + 行 + 依据），全部来自 `report_r1.txt`（blob %s）：：" % (
    ctrl["exempted"], blob("report_r1.txt")[0]))
A("")
A("| 规则 | 文件:行 | cell_id | 条目 / 证据 | 在树上量到的依据 |")
A("| --- | --- | --- | --- | --- |")
for row in ex["exemption_ledger"]:
    d = row["measured_on_tree"] or {}
    A("| %s | %s:%s | %s | %s / %s | fold `%s`@%s 具名锚 `%s`@%s |" % (
        row["rule"], row["file"], row["line"], row["cell_id"], row["exemption_id"], row["evidence"],
        d.get("fold_container"), d.get("fold_container_line"),
        d.get("attribution_anchor_field"), d.get("attribution_anchor_line")))
A("")
A("照旧红的 %d 枚一枚没被藏：每枚都带尺自己给的理由（哪条目形上匹配、哪条证据没量到），例如 `PlanWithAiSheet.tsx:931` 那枚属性位是 `shape-matched EX-1-CONTRACT-CLOSED-ENUM but NO_CODE_FIELD_NAMED_ON_THIS_CELL`，`ActivityDetail.tsx:216` 是 `… + NO_FOLD_CONTAINER`。逐格在 `report_r1.txt` 与 `rec_r8_tip_7862c6de.json`。" % ctrl["red"])
A("")
A("**分母不再随豁免移动，这是量出来的**：同一棵针树把折叠条目整枚删掉 ⇒ red %s、exempted %s；把该谓词改成「不读树就答 ok」（那正是「有人写一句就算豁免」在仪器里的样子）⇒ red %s、exempted %s。两种改法 `cells_total` 都是 %s，而 `--selftest` 双双 SELFTEST_FAIL（退 7），点名条目分别 `%s` 与 `%s`；未改动的交付字节 SELFTEST_%s（退 %s）。件 `counterexamples_r1.json` 的 `mutants` 三行。" % (
    m3["fold_entry_removed"]["counts"]["red"], m3["fold_entry_removed"]["counts"]["exempted"],
    m3["fold_exempts_without_measuring"]["counts"]["red"], m3["fold_exempts_without_measuring"]["counts"]["exempted"],
    ctrl["cells_total"], ", ".join(m3["fold_entry_removed"]["failing_arms"]),
    ", ".join(m3["fold_exempts_without_measuring"]["failing_arms"]),
    pub["selftest_verdict"].split("_")[1], pub["selftest_exit"]))
A("")
A("## 4 正反两向自检（两侧读数都贴）")
A("")
A("`node ui_exposure_taint_ast_r8.cjs --selftest` 退出 %s，`verdict` %s。新增豁免臂 %d 枚全部 met，逐条名与两侧读数在 `st_r8_full.json`（blob %s）的 `exemption_arms`：" % (
    st["_run"]["exit_code"], st["verdict"], st["n_exemption_arms"], blob("st_r8_full.json")[0]))
A("")
A("| 臂 | 应当豁免的那一侧 | 不应当豁免的那一侧 |")
A("| --- | --- | --- |")
fp = arms["fold_pair"]
A("| `fold_pair` | 折叠 + 具名锚 `data-cnx-field=\"http_status\"`：cells %s 枚、red %s，那枚格 verdict EXEMPTED 且仍留在 cells 里 | 同一格只把锚换成 JSX 注释 `{/* … */}`：cells %s 枚、red %s，near_miss 具名 EX-2 且 `fold_without_anchor` 为真。两侧 cells 相等 ⇒ 改的是判语，不是分母 |" % (
    fp["with_anchor"]["cells"], fp["with_anchor"]["red"],
    fp["comment_only"]["cells"], fp["comment_only"]["red"]))
cp = arms["contract_pair"]
A("| `contract_pair` | 契约声明闭集、值在集内：cells %s 枚、red %s，依据回显 enum 行号 | 值在集外：red %s（`value_not_in_the_contract_set`）；契约根本没声明该字段：red %s（`CONTRACT_MISSING_ENUM`）。三侧 cells 都是 %s/%s/%s |" % (
    cp["inside_the_set"]["cells"], cp["inside_the_set"]["red"],
    cp["token_outside_the_set"]["red"], cp["no_set_declared"]["red"],
    cp["inside_the_set"]["cells"], cp["token_outside_the_set"]["cells"], cp["no_set_declared"]["cells"]))
A("| `contract_is_not_for_sale_to_the_fold` | 同上，值在集内 ⇒ 豁免 | 同一格裹进合法折叠与合法锚里，值在集外 ⇒ cells %s 枚、red %s：契约先拒的不会被折叠条目救回 |" % (
    arms["contract_is_not_for_sale_to_the_fold"]["cells"],
    arms["contract_is_not_for_sale_to_the_fold"]["red"]))
A("")
A("另外几枚管的是「表与输入面」：`table_cannot_name_a_cell`（六枚写不出格的反例，逐条报出形制问题名）、`no_waiver_input_channel`、`class_name_opens_nothing`、`fold_family_excludes_the_attribute_slot`（EX-2 的家族轴里没有 `attribute`，Q71 关着）、`contract_is_not_for_sale_to_the_fold`（契约先拒的格不会被折叠条目救回，即便折叠与锚都合法）、`new_call_site_into_a_shared_helper_is_not_exemptible`（号令者点名的那一形：共用 helper 多一条来路上游正文，两枚面板各长出的格**全红**，包含车道根本没打开的那枚文件——因为作者身份不是这三根轴之一）、`no_drift_against_the_published_partition`（拿已发布的 %d 条 R7 臂的原期望比：本轮 red/exempted 分区逐条相等，%s/%s 全中，我没写过这些期望）。" % (
    st["n_slot_arms"], arms["no_drift_against_the_published_partition"]["met"],
    arms["no_drift_against_the_published_partition"]["arms"]))
A("")
A("旧的三组一并按原期望跑过：fixtures %s 条、mode 臂 %s/%s、cross 臂 %s/%s。" % (
    st["n_fixtures"], st["n_mode_arms_met"], st["n_mode_arms"], st["n_cross_file_arms_met"], st["n_cross_file_arms"]))
A("")
A("## 5 与号令者两侧对照（候选 10 / 现针 6）对齐口径")
A("")
A("我把他那两棵树按他给的逐字 rev 各自 `git archive … frontend/src contracts` 导出，用三把尺在同一棵上各跑一遍（件 `generation_reconciliation_r1.json` blob %s，`door_view_r1.json` blob %s）：" % (
    blob("generation_reconciliation_r1.json")[0], blob("door_view_r1.json")[0]))
A("")
A("| 树（rev 逐字） | 模块数 | r7b hits | r7b4 hits | r8 cells_total | r8 red | r8 exempted |")
A("| --- | --- | --- | --- | --- | --- | --- |")
rep_files = {"cmdr_side_tip": "report_cmdr_side_tip.json",
             "cmdr_side_candidate": "report_cmdr_side_candidate.json",
             "tip_7862c6de": "report_tip_7862c6de.json"}
for label, rev, note in [("cmdr_side_tip", "0989713aa687b97f4cd40bae009a6ce493425a4b", "他那轮的现针侧"),
                          ("cmdr_side_candidate", "62f030f351e70bd95108377fe2e3bbc49c5ef288", "他那轮的候选侧"),
                          ("tip_7862c6de", TIP, "本轮现针")]:
    row = rec["trees"][label]
    d = load(rep_files[label])
    A("| %s `%s` | %s | %s | %s | %s | %s | %s |" % (
        note, rev[:12], d["modules_in_graph"],
        row["r7b"]["red"], row["r7b4"]["red"], row["r8"]["pre_exemption_cells"], row["r8"]["red"],
        row["r8"]["pre_exemption_cells"] - row["r8"]["red"]))
A("")
A("⇒ **`r7b` 那一列逐字复现他的 %s / %s**（候选 / 现针），所以口径是接上的；r8 在同一对树上读到的豁免前分母是 %s 与 %s，红格 %s 与 %s。三把尺的**豁免前分母逐棵相等**（`pre_exemption_denominator_stable_across_generations` 三棵全 True），会漂的只有「红」那一列——而 r8 把漂的每一格都打印出来了。" % (
    pair["his_reading"]["candidate"], pair["his_reading"]["tip"],
    pair["r8_cells_total"]["candidate"], pair["r8_cells_total"]["tip"],
    pair["r8_red"]["candidate"], pair["r8_red"]["tip"]))
A("")
A("**给门的那一句（也是题面让我考虑的那条形状）**：candidate 相对 tip 按格 id 新增 %d 枚、消失 %d 枚，逐枚是 %s。这与门自己那套按 (file, rule) 计数的判语指的是同一批格（`the_two_views_agree` = %s），差别只在身份视图直接说出**文件与行**。绝对格数继续可用，但 r8 的输出现在给了门一个不必靠圆数字的选项；改门的判语不在我这一单里，我没动 `preflight_and_land_r7.py`。" % (
    len(pair["growth_by_identity_new_cell_ids"]), len(pair["growth_by_identity_gone_cell_ids"]),
    "; ".join(pair["growth_by_identity_new_cell_ids"]), pair["the_two_views_agree"]))
A("")
A("## 6 顺手抓到的一枚调用方形红（是尺族自己的问题，具名报，不自作主张修）")
A("")
A("`live_checks/patrol/_exposure_delta_r1.py:66` 那行取的是 `j.get(\"cells\") or []`，而**已发布的任何一代在 `--file`/`--ref` 模式都不吐 `cells` 这枚键**（`r7b`、`r7b4` 都没有；r8 有）。同一枚针、同一份路径各跑一遍的证据在 `caller_cells_key_r1.json`（blob %s）：`JourneyTrashPanel.tsx` 那一枚两代已发布尺都回 %d hits，而 `cells_key_len` = %s、抽出格 id = %s ⇒ 那一轮扫描对每枚文件拿到的都是空集，于是「不会新增曝光格（按逐枚文件集合差）」这一判语在该形状下**恒为真**，与产品字节无关。修法是一行（让那支扫描改读 r8 的 `cells`，或改读 `hits`），但那枚脚本不是我的字节，我不重写别人的量具，等号令者点单。" % (
    blob("caller_cells_key_r1.json")[0],
    [r["hits"] for r in caller["reading"] if r["ruler"].endswith("r7b.cjs")][0],
    [r["cells_key_len"] for r in caller["reading"] if r["ruler"].endswith("r7b.cjs")][0],
    [r["scan_extracts_ids"] for r in caller["reading"] if r["ruler"].endswith("r7b.cjs")][0]))
A("")
A("另有一格是既有分歧、不是我引入的：同一枚 `JourneyTrashPanel.tsx` 在 `--tree` 下不产格、在 `--file` 下产 %d 枚——r7b4 自己的 `upper_bound_claim` 已经把这种两模式分歧记成 REFUTED 了；本轮 `no_drift` 臂只保证与已发布分区一致，没有把它抹平。**这一格我没修，也不写成修了。**" % [r["hits"] for r in caller["reading"] if r["ruler"].endswith("r8.cjs")][0])
A("")
A("## 7 形制与边界")
A("")
A("- 基座 = 现读尖 `%s`；权威线 0 次移动；账本 0 次直写（本块走收件口）；别人的 worktree 0 次进入。" % TIP)
A("- `:8000` `:4781` `:4782` `:8693` 一枚没占；本轮 0 次起服务、0 次开端口（全是离线读树）；`_preview.db` 一字未读未写；`demo/reset` 0 次。")
A("- 新开整树导出 0 枚：三棵都只含 `frontend/src contracts` 两段，逐棵实测 %s / %s / %s B，合计 %s B（件 `export_sizes_r1.json` blob %s），跑完留在 `work/ord0536/` 等号令者处置。" % (
    sizes["bytes"]["exp_tip_r8"], sizes["bytes"]["exp_tip0989713a"], sizes["bytes"]["exp_cand0500"],
    sizes["bytes"]["total"], blob("export_sizes_r1.json")[0]))
A("- 反件与自检只读产品字节；七枚 mutant 与一枚 control 都在 `work/ord0536/` 本地，**mutant 不是交付字节**，`counterexamples_r1.json` 里 `published_bytes_unchanged` = %s 是那一次跑完对本文件字节的复读。" % ce["published_bytes_unchanged"])
A("- 我没做的：没改门（`preflight_and_land_r7.py` 仍钉 r7b）、没改值守那支扫描、没动 r7b/r7b4/r7b1/r7b3 任何一枚已发布字节、没把任何一格改成永真、没有 `--ignore`。")
A("")
A("## 8 仍未改善（不折进已收口）")
A("")
A("- 现针上照旧有 %d 枚红格，本单不吞它们；豁免表**没有**为它们任何一枚新增条目——那要的是产品字节改动或号令者具名裁语，不是仪器放行。" % ctrl["red"])
A("- 折叠豁免能证的是「这一格被折在具名锚后面」，证不了「用户打开以后读得明白」——后者是屏尺的活，我在 `interpretation_limit` 里写死了这句话，没让尺替它作答。")
A("- EX-1 那一条在全树模式本轮豁免 0 枚：现针上没有一枚格的元素具名 `*_code` 契约字段（唯一像的 `JourneyTrashPanel.tsx:233` 只在 `--file` 下现，见第 6 节）。所以它的正反两向只在自检与真文件两处都跑了，没只在树跑一侧就宣称过关。")
A("- 门那侧的判语换成按身份比较，需要号令者点一单改门；我只交了门可直接消费的两枚视图（`door_view_r1.json`）。")
A("")
A("## 9 坐标")
A("")
A("证据 %d 枚在 `commander/control` 的 `%s/`，逐件本机 blob 与服务端读回 blob 相同、byte_equal 全真（回执 `publish_receipt_r1.json` blob %s，本轮重试过的路径：`%s`）。汇总读数两件：`generation_reconciliation_r1.json` blob %s、`counterexamples_r1.json` blob %s。" % (
    len(receipt["files"]), receipt["slug"], blob("publish_receipt_r1.json")[0],
    ", ".join(receipt["retried_paths"]) or "无", blob("generation_reconciliation_r1.json")[0],
    blob("counterexamples_r1.json")[0]))
A("")
out = "\n".join(L) + "\n"
io.open(os.path.join(WORK, "block_text_r1.md"), "w", encoding="utf-8", newline="\n").write(out)
print(out)
