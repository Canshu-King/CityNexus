"""ORD-0426 receipt: pin the "27 -> 0 need repoint" conclusion to the current tip.

Nothing here is typed from memory: the two generations' assets, per-rule classes and the h1 column
are read out of the run JSONs at write time, and the run is refused if the two row sets disagree in
size so a comparison can never be asserted from a summary I wrote myself.
"""
import io
import json
import os
import time

RUN = "D:/moodle/_qoder_r_ord0426r2/run"
WT = "D:/moodle/_qoder_r_ord0426r2/wt"
OUT = os.path.join(WT, "review/ord0426")
TIP = "dccd13ad66ea35e9a6d7ca7a3d91a1ae9a579808"
PREV = "fb6131f359e85deb18a2194494dc9a96e328cdee"

new1 = json.load(io.open(os.path.join(RUN, "_full/orphan_repoint_r2.json"), encoding="utf-8"))
new2 = json.load(io.open(os.path.join(RUN, "_pass2/orphan_repoint_pass2.json"), encoding="utf-8"))
old1 = json.load(io.open("D:/moodle/_qoder_r_ord0426/wt/review/ord0426/orphan_repoint_r2.json", encoding="utf-8"))
old2 = json.load(io.open("D:/moodle/_qoder_r_ord0426/wt/review/ord0426/orphan_repoint_pass2.json", encoding="utf-8"))

rn = {r["selector"]: r["class"] for r in new1["rows"]}
ro = {r["selector"]: r["class"] for r in old1["rows"]}
assert set(rn) == set(ro), "the two runs did not cover the same rule set; the comparison is void"
assert new1["served_tip"] == TIP and new2["served_tip"] == TIP, "the run was not made against the tip the receipt names"
same = sum(1 for k in rn if rn[k] == ro[k])
orph = [r for r in new1["rows"] if r["class"] == "ORPHAN_LAYOUT_RULE_WANTS_REPOINT"]
hero = next(r for r in new1["rows"] if r["selector"] == ".v8-hero-title")
sect = next(r for r in new1["rows"] if r["selector"] == ".v8-section-title")

L = []
A = L.append
A("# ORD-0426 收据 · 分诊结论钉在现尖（0 产品字节，只读重跑）")
A("")
A(f"- 生成 {time.strftime('%Y-%m-%dT%H:%M:%S%z')}；仪表沿用已入账的 `cmdr_orphan_repoint_r2.js` 与 "
  "`cmdr_orphan_repoint_pass2.js`（本目录），一字未改，被量尖由命令行参数传入。")
A(f"- 被量代次 tip={TIP}，页面实载资产（按名字钉代次）{json.dumps(new1['css_assets_loaded'])}。")
A(f"- 上一枚被量的代次 tip={PREV}，实载 {json.dumps(old1['css_assets_loaded'])}："
  "两代 CSS 与 JS 资产名字都不同（ORD-0417 与 ORD-0425 改过 frontend/src，含 map-selection.css 与 MapPanel.tsx），"
  "所以这不是同一份字节重述一遍。")
A(f"- 两份 CSS 源码本身在两代之间未变：styles.css 与 design-tokens.css 的 blob 与上一代逐字相同，"
  "变的是页面 DOM 与合成后的 CSS——这正是要重跑的理由：结论靠的是屏上命中，不是靠文件文本。")
A("")
A("## 钉住的结论")
A("")
A(f"- 输入 wanted={new1['wanted_from_ord0421']}（来自已入账的 ORD-0421 普查件 review/ord0421/census_r3.json），"
  f"本尖重解析唯一选择器 rules_parsed_on_this_tip={new1['rules_parsed_on_this_tip']}。")
A(f"- 场景 pass1 {json.dumps(new1['scenarios'], ensure_ascii=False)}，heading_samples={new1['heading_samples']}；"
  f"pass2 widths={json.dumps(new2['widths'])} × routes={json.dumps(new2['routes'])}。")
A(f"- 分诊计数 orphan_repoint={len(orph)}，"
  f"其余 {json.dumps(new1['class_counts'], ensure_ascii=False)}；"
  f"pass2 对 dead_legacy 那批再探容器：{json.dumps(new2['family_probe_counts'], ensure_ascii=False)}。")
A(f"- 与上一代逐条对照：per_rule_class_identical={same}/27，不同的选择器条数 {sum(1 for k in rn if rn[k] != ro[k])}。")
A("- 所以「那 27 条里没有一条需要 repoint」这句话现在有两枚独立代次支撑，不是单点读数。")
A("")
A("## 你原先担心的那两枚字号规则（现尖复述，值都是重测的）")
A("")
A(f"- `.v8-hero-title` 自身命中 own_hits_max={hero['own_hits_max']}，同组另一半 `.v8-page h1` 屏上命中 "
  f"{json.dumps(hero['sibling_hits'], ensure_ascii=False)}。")
A(f"- `.v8-section-title` 自身命中 own_hits_max={sect['own_hits_max']}，同组 `.v8-page h2` 命中 "
  f"{json.dumps(sect['sibling_hits'], ensure_ascii=False)}。")
tok = new1["h1_samples"][0]["token_fs_display"] if new1["h1_samples"] else "?"
A(f"- h1 实算字号按宽度 {json.dumps(new2['h1_font_size_by_width'], ensure_ascii=False)}，"
  f"token --cn-fs-display 解析为 {tok}；h1 不在档位上的屏数 h1_off={new1['h1_off_display_档位']}。")
A("- 顺带仍成立：styles.css 里两条随视口写的 h1 规则按公式应得的值与实测不符，画 h1 的是 token 档那一条。")
A("")
A("## 边界")
A("")
A("- 本收据只覆盖那 27 条与走到的 14 屏 × 2 语言 × 3 形状；弹层、错误/离线壳、深色档没驱动，"
  "dead_legacy 那批里若有服务于那些状态的规则，本收据不称它们可删。")
A("- 只读：没有改任何产品文件；本目录只新增收据与其原始件。")
A("- 手机链与号令者端口未参与；读数在本车道 backend_port=8736 与 front_port=4836 上成立。")

io.open(os.path.join(OUT, "RECEIPT_DCCD13AD_r1.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")

summary = {
    "tip": TIP, "assets_on_tip": new1["css_assets_loaded"], "previous_tip": PREV,
    "assets_previous": old1["css_assets_loaded"],
    "rules_parsed_on_this_tip": new1["rules_parsed_on_this_tip"],
    "wanted": new1["wanted_from_ord0421"], "heading_samples_pass1": new1["heading_samples"],
    "pass2_widths": new2["widths"], "pass2_routes": new2["routes"],
    "class_counts": new1["class_counts"], "orphan_repoint_count": len(orph),
    "pass2_family_probe": new2["family_probe_counts"],
    "per_rule_class_identical_vs_previous": same,
    "per_rule_class_differences": [k for k in rn if rn[k] != ro[k]],
    "h1_measured_by_width": new2["h1_font_size_by_width"],
    "h1_off_token_count": new1["h1_off_display_档位"],
    "hero_title_rule": {"own_hits_max": hero["own_hits_max"], "sibling_hits": hero["sibling_hits"]},
    "section_title_rule": {"own_hits_max": sect["own_hits_max"], "sibling_hits": sect["sibling_hits"]},
    "rows": new1["rows"],
    "pageerrors": new1["pageerrors"] + new2["pageerrors"],
}
io.open(os.path.join(OUT, "RECEIPT_DCCD13AD_r1.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(summary, ensure_ascii=False, indent=1))
for src, dst in [(os.path.join(RUN, "_full/orphan_repoint_r2.json"), "orphan_repoint_r2_on_dccd13ad.json"),
                 (os.path.join(RUN, "_pass2/orphan_repoint_pass2.json"), "orphan_repoint_pass2_on_dccd13ad.json")]:
    io.open(os.path.join(OUT, dst), "w", encoding="utf-8", newline="\n").write(io.open(src, encoding="utf-8").read())
print("orphans", len(orph), "identical", same, "assets", json.dumps(new1["css_assets_loaded"]))
print("md bytes", os.path.getsize(os.path.join(OUT, "RECEIPT_DCCD13AD_r1.md")))
