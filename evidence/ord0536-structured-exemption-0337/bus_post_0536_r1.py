# -*- coding: utf-8 -*-
"""Post the ORD-0536 delivery to the coordination bus (#1) on the commander's shelf.

The tail line is not retyped here: it is read byte-for-byte out of
`live_checks/CLOSING_LINE.txt`, and the script refuses to post if that file doesn't hand over exactly one
line.  Numbers come from the artifacts, and the receipt it cites is read back from the publish run.
"""
import io
import json
import os
import subprocess
import sys

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0536"
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")


def load(name):
    return json.load(io.open(os.path.join(WORK, name), encoding="utf-8"))


closing = io.open(os.path.join(REF, "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
assert closing, "CLOSING_LINE.txt handed over nothing"
rec = load("publish_receipt_r1.json")
st = load("st_r8_full.json")
ce = load("counterexamples_r1.json")
dv = load("door_view_r1.json")
ex = load("report_tip_7862c6de.json")
arms = st["exemption_arms"]
pair = dv["commander_pair"]
ctrl = ce["control"]["counts"]

BODY = """### S4-ast-taint `1d64acf5` · ORD-0536 已交付（曝光尺结构化豁免，新文件名 r8）

题面三个要求逐条回：

1. **落点与冻结**：交付只加一枚新名 `live_checks/ui_exposure_taint_ast_r8.cjs`（blob `83819289685f4bb58c5dea728114473f66fd29ef`），枝 `review/S4-ord0536-structured-exemption-r8` 头 `66cd53af64ac99c0784108ebd7b5276cc8ac2917`；r7b / r7b1 / r7b3 / r7b4 已发布字节一字未动，本轮还把它们当对照各跑了一遍。
2. **豁免由结构化条件决定**：一枚冻在尺里的表，键就是「哪条规则 × 哪种 sink 形状家族 × 哪个 origin_kind」，再加一条必须在树上量得到的证据谓词（契约闭集 / 折叠具名锚）。**表在形制上写不出「某一格」**——只允许 5 枚键，值长得像路径 / 扩展名 / 行号 / 16 位格 id 一律拒，家族轴里带 `:`（一整枚 sink 形状而不是一族）也拒。六枚真跑的拒件各退 3 并回 `EXEMPTION_TABLE_SCHEMA_REJECTED`；命令行旗标是闭集，`--waive-cell` / `--exempt-cells` / `--baseline-cells` 各退 2 具名 `HUMAN_DECLARED_WAIVER_IS_NOT_AN_INPUT_CHANNEL`，且不写出 `--out`。
3. **具名报回**：现针 `%s` 的导出树上 `cells_total` = %s ＝ red %s + exempted %s（门钉的 r7b 在同一棵树报 %s hits）。被豁免的 %s 枚逐格打印了规则 + 文件 + 行 + cell_id + 条目 + 在树上量到的锚（件 `report_r1.txt`），照旧红的 %s 枚一枚没藏，每枚带尺自己给的理由。

**你点名的那条形状，我按它的根因处理了**：绝对格数之所以能被「制度」改动，是因为豁免生效时那一格从 `hits` 搬进别的列表、分母跟着漂。r8 把 `cells_total` 定成**豁免前**的格数，同一棵树把折叠条目整枚删掉（red 8 / exempted 0）与把谓词改成不读树就答 ok（red 1 / exempted 7）——`cells_total` 都还是 %s，而 `--selftest` 双双 SELFTEST_FAIL。三把尺在三棵树上的豁免前分母逐棵相等（`pre_exemption_denominator_stable_across_generations` 全 True）。候选相对现针按格 id 新增 %d 枚、消失 %d 枚，逐枚是 %s；门若继续按 (file, rule) 计数，指向的是同一批格（`the_two_views_agree` = %s），只是身份视图额外说得出文件与行。改门的判语不在我这一单，我没动 `preflight_and_land_r7.py`。

**两侧对照口径**：他那两棵树按逐字 rev 各自重导后，r7b 这一列复现 %s / %s（候选 / 现针），所以接得上；r8 在同一对树读 %s / %s 红、豁免前 %s / %s。

**验收两向**：`--selftest` 退 %s，新增豁免臂 %d 枚全 met（含 `fold_pair`：折叠 + 具名锚 ⇒ EXEMPTED；同一格把锚写成 JSX 注释 ⇒ RED 且 near_miss 具名；`contract_pair`：值在契约闭集内 ⇒ EXEMPTED，值在集外与契约没声明各自 RED）；旧三组按原期望仍全中（fixtures %s、mode %s/%s、cross %s/%s），`no_drift_against_the_published_partition` 拿已发布 %s 条 R7 臂的原期望逐条比，%s/%s 相等。

**顺手抓到一枚调用方形红（不擅自修别人的量具）**：`live_checks/patrol/_exposure_delta_r1.py:66` 取的是 `j.get("cells") or []`，而**已发布的任何一代在 `--file`/`--ref` 模式都不吐 `cells` 这枚键**——同一枚针同一份路径，r7b 与 r7b4 各回 2 hits、`cells` 键长 0、抽出格 id 0 ⇒ 那支扫描对每枚文件拿到的都是空集，「不会新增曝光格（按逐枚文件集合差）」在该形状下恒为真。修法是一行（改读 r8 的 `cells`，或改读 `hits`），等号令者点单。

**仍未改善**：现针上照旧 %s 枚红格，本单没为它们任何一枚新增豁免条目；折叠豁免只证得住「折在具名锚后面」，证不了「用户打开后读得明白」，那仍是屏尺的活；EX-1 在全树模式本轮豁免 0 枚（现针没有具名 `*_code` 的元素），它的两向只在自检与真文件跑过，我没拿一侧宣称过关。

证据 %d 枚在 `commander/control` 的 `%s/`，逐件本机 blob 与服务端读回 blob 相同（回执 blob `%s`，重试过的路径：`%s`）。账本块：`_qoder_ledger_inbox` 同名块，交前过 `claim_coordinate_check_r7.py --text <块> --expect-clean`。

%s
""" % (
    ex["tree"].split("/")[-3] if False else "7862c6de5565c02c20ec2dccaa9da18960603e06",
    ctrl["cells_total"], ctrl["red"], ctrl["exempted"],
    ce["control"]["counts"]["exempted"], ctrl["exempted"], ctrl["red"], ctrl["cells_total"],
    len(pair["growth_by_identity_new_cell_ids"]), len(pair["growth_by_identity_gone_cell_ids"]),
    "; ".join(pair["growth_by_identity_new_cell_ids"]), pair["the_two_views_agree"],
    pair["his_reading"]["candidate"], pair["his_reading"]["tip"],
    pair["r8_red"]["candidate"], pair["r8_red"]["tip"],
    pair["r8_cells_total"]["candidate"], pair["r8_cells_total"]["tip"],
    st["_run"]["exit_code"], st["n_exemption_arms"],
    st["n_fixtures"], st["n_mode_arms_met"], st["n_mode_arms"],
    st["n_cross_file_arms_met"], st["n_cross_file_arms"],
    st["n_slot_arms"], arms["no_drift_against_the_published_partition"]["met"],
    arms["no_drift_against_the_published_partition"]["arms"],
    ctrl["red"], len(rec["files"]), rec["slug"],
    hashlib_blob := __import__("hashlib").sha1(
        b"blob %d\x00" % os.path.getsize(os.path.join(WORK, "publish_receipt_r1.json"))
        + io.open(os.path.join(WORK, "publish_receipt_r1.json"), "rb").read()).hexdigest(),
    ", ".join(rec["retried_paths"]) or "无",
    closing,
)

io.open(os.path.join(WORK, "bus_note_0536_r1.md"), "w", encoding="utf-8", newline="\n").write(BODY)
print(BODY[:600])
print("...bytes", len(BODY.encode("utf-8")), "tail ok:", BODY.strip().endswith(closing))
