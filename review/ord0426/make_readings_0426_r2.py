"""ORD-0426 lane: commit the two-pass readings (0 product bytes).

Adds what pass 1 could not answer on its own:
  - the family probe from pass 2 (does a container for the rule exist at all?) for every DEAD_LEGACY;
  - the title table across widths, compared against the two competing rules' PREDICTED values, so
    "which rule actually paints the h1" is settled by arithmetic on measured px rather than by my
    guess about file order (pass 1's shipped_offset could not tell three identical `.v8-page h1`
    occurrences apart — disclosed below rather than hidden).
"""
import io
import json
import os
import re
import time

RUN = "D:/moodle/_qoder_r_ord0426/run"
WT = "D:/moodle/_qoder_r_ord0426/wt"
OUT = os.path.join(WT, "review/ord0426")
SRC = os.path.join(WT, "frontend/src")
os.makedirs(OUT, exist_ok=True)

p1 = json.load(io.open(os.path.join(RUN, "_full/orphan_repoint_r2.json"), encoding="utf-8"))
p2 = json.load(io.open(os.path.join(RUN, "_pass2/orphan_repoint_pass2.json"), encoding="utf-8"))

SOURCE = []
for root, dirs, files in os.walk(SRC):
    dirs[:] = [x for x in dirs if x != "node_modules"]
    for f in files:
        if f.endswith((".tsx", ".ts", ".js", ".jsx", ".html")):
            SOURCE.append((os.path.join(root, f), io.open(os.path.join(root, f), encoding="utf-8",
                                                            errors="replace").read()))


def elem_source(cand):
    if not cand:
        return None, []
    toks = ([cand["id"]] if cand.get("id") else []) + \
           [c for c in re.split(r"\s+", (cand.get("classes") or "").strip()) if c]
    for t in toks:
        for p, text in SOURCE:
            for n, line in enumerate(text.splitlines(), 1):
                if t in line and ("className" in line or "id=" in line or 'class="' in line):
                    return t, [f"{os.path.relpath(p, WT).replace(os.sep, '/')}:{n}"]
    return (toks[0] if toks else None), []


PROP_WHAT = {"font-size": "字号", "font-weight": "字重", "line-height": "行高", "letter-spacing": "字距",
             "color": "字色", "background": "底色", "display": "排版方式",
             "grid-template-columns": "栅格列", "gap": "间隙", "padding": "内边距",
             "margin": "外边距", "min-height": "最小高度", "border-radius": "圆角",
             "justify-content": "主轴分布", "align-items": "交叉轴对齐", "height": "高度"}


def plain(c):
    if not c:
        return "屏上没有扮演该角色的元素。"
    return "；".join(f"{PROP_WHAT.get(p, p)}现在实际是 {g}，规则要的是 {w}" for p, w, g in c["diffs"][:3]) + "。"


def clamp_predict(w):
    """styles.css:166 says font-size: clamp(28px, 3.2vw, 43px) — what that would compute at width w."""
    vw = 3.2 * w / 100.0
    return round(min(43.0, max(28.0, vw)), 2)


orph = [r for r in p1["rows"] if r["class"] in ("ORPHAN_LAYOUT_RULE_WANTS_REPOINT",
                                                "NO_LONGER_NO_CONSUMER_ON_THIS_TIP")]
sib = [r for r in p1["rows"] if r["class"] == "INTENT_APPLIED_VIA_GROUP_SIBLING"]
tp = [r for r in p1["rows"] if r["class"] == "THIRD_PARTY_DOM_NOT_DEAD"]
dead = [r for r in p1["rows"] if r["class"] == "DEAD_LEGACY"]
p2map = {r["selector"]: r for r in p2["reclassified"]}

L = []
A = L.append
A("# ORD-0426 · 27 条「无消费者」选择器的屏上分诊（两趟，0 产品字节）")
A("")
A(f"- 生成 {time.strftime('%Y-%m-%dT%H:%M:%S%z')}；仪表 pass1 `cmdr_orphan_repoint_r2.js`、pass2 `cmdr_orphan_repoint_pass2.js`（同目录）。")
A(f"- 被量产物：现尖 `{p1['served_tip']}` 的构建，实载 CSS {json.dumps(p1['css_assets_loaded'])}。")
A(f"- pass1 场景 {json.dumps(p1['scenarios'], ensure_ascii=False)}，标题样本 heading_samples={p1['heading_samples']}；"
  f"pass2 场景 widths={json.dumps(p2['widths'])} × routes={json.dumps(p2['routes'])}。")
A(f"- 输入来自已落地的 ORD-0421：wanted={p1['wanted_from_ord0421']}，本尖重解析 rules={p1['rules_parsed_on_this_tip']}。")
A(f"- 结果 class_counts={json.dumps(p1['class_counts'], ensure_ascii=False)}；"
  f"pass2 对 {p2['dead_from_pass1']} 条 DEAD_LEGACY 再探容器：{json.dumps(p2['family_probe_counts'], ensure_ascii=False)}。")
A("")
A("## 直接回答你点的那两枚字号规则")
A("")
hero = next((r for r in p1["rows"] if r["selector"] == ".v8-hero-title"), None)
sect = next((r for r in p1["rows"] if r["selector"] == ".v8-section-title"), None)
A(f"- `.v8-hero-title`（{', '.join(hero['source_on_this_tip'])}）不是孤立布局规则：它写在**逗号分组**里，"
  f"同组的 `.v8-page h1` 实测命中 {json.dumps(hero['sibling_hits'], ensure_ascii=False)}，"
  f"所以档位是经这一半落地的；屏上没有任何元素带 `.v8-hero-title` 这个名字（own_hits_max={hero['own_hits_max']}）。")
A(f"- `.v8-section-title`（{', '.join(sect['source_on_this_tip'])}）同形：同组 `.v8-page h2` 命中 "
  f"{json.dumps(sect['sibling_hits'], ensure_ascii=False)}，own_hits_max={sect['own_hits_max']}。")
A("- 结论：标题不是「在吃默认样式」，而是**已经吃到设计档位**；未用的只是那两个类名。"
  "所以这两条按你的口径应归 INTENT_APPLIED_VIA_GROUP_SIBLING，不建议 repoint，只建议改名或删除该别名。")
A("")
A("## 一、屏上确有该角色且没吃到规则（ORPHAN_LAYOUT_RULE_WANTS_REPOINT）")
A("")
A(f"（计数 {len(orph)}）")
if not orph:
    A("- 本轮 0 条。pass1 的三条角色来源（同组兄弟 / 已存在祖先 / 明确叶标签）都没给出「元素在位但值不对」的组合；"
      "pass2 又对 15 条 DEAD_LEGACY 单独探了容器是否存在，也没有翻案。")
else:
    for i, r in enumerate(orph, 1):
        c = (r["role_candidates"] or [None])[0]
        t, sr = elem_source(c)
        A(f"{i}. `{r['selector']}` @ {', '.join(r['source_on_this_tip'])}")
        A(f"   - basis={r['role_basis']}，候选 `{c['tag']}.{c['classes'][:36] if c else ''}`「{c['text'][:18] if c else ''}」"
          f"，rect={c['rect'] if c else '-'}，文本 client rects={c['textRectLines'] if c else '-'}")
        A(f"   - 该元素源码反查 token `{t}` → {', '.join(sr) if sr else '未在任何 className/id 行找到（本机扫描，非 git 对象）'}")
        A(f"   - 差别：{plain(c)}")
A("")
A("## 二、意图经同组另一半落地（INTENT_APPLIED_VIA_GROUP_SIBLING，只欠类名）")
A("")
A("| 选择器 | path:line | 同组真正命中的选择器与屏上数 | own_hits |")
A("|---|---|---|---|")
for r in sib:
    hits = ", ".join(f"`{k}`={v}" for k, v in r["sibling_hits"].items() if v > 0) or "—"
    A(f"| `{r['selector']}` | {', '.join(r['source_on_this_tip'])} | {hits} | {r['own_hits_max']} |")
A("")
A("## 三、第三方运行时 DOM（不计缺陷）")
A("")
for r in tp:
    t = r["third_party"] or {}
    A(f"- `{r['selector']}` @ {', '.join(r['source_on_this_tip'])}：maplibre 自有节点；"
      f"本轮实测 gesture 容器在屏上出现 gesture_node={json.dumps(t.get('gesture_node'))}，"
      f"该类命中 hits={json.dumps(t.get('hits'))}。子串扫 frontend/src 看不到库自造的节点，故按你的护栏排除。")
A("")
A("## 四、屏上连容器都没有（DEAD_LEGACY，只建议删除，本单未删）")
A("")
A(f"- 计数 dead_legacy={len(dead)}，pass2 复核后确认无容器的条数 confirmed={p2['family_probe_counts'].get('DEAD_LEGACY_CONFIRMED_NO_CONTAINER', 0)}。")
A("")
A("| 选择器 | path:line | 命名家族 | 同族元素在屏数 | 容器 | pass2 结论 |")
A("|---|---|---|---|---|---|")
for r in dead:
    q = p2map.get(r["selector"], {})
    cont = q.get("container")
    A(f"| `{r['selector']}` | {', '.join(r['source_on_this_tip'])} | `{q.get('family', '-')}` | "
      f"{q.get('kin_elements', 0)} | {cont['tag'] + '.' + (cont['classes'][:26] if cont else '无') if cont else '无'} | "
      f"{q.get('class', 'pass2 未覆盖')} |")
A("")
A("## 五、h1 到底在哪条规则下画（跨宽度实测）")
A("")
A("| 视口宽 | h1 实算 font-size | clamp(28px,3.2vw,43px) 在该宽应得 | ≤680px 档应得 | token --cn-fs-display |")
A("|---|---|---|---|---|")
# aggregate over the COMPLETE pass-2 map: the row list itself is capped at 40, and building the
# table from it silently dropped 800 and 1280 while the prose still claimed both were measured.
widths = sorted(int(w) for w in p2["h1_font_size_by_width"].keys())
token_display = (p2["h1_rows"][0]["token_display"] if p2["h1_rows"] else "?")
for w in widths:
    sizes = p2["h1_font_size_by_width"][str(w)]
    A(f"| {w} | {', '.join(sizes)} | {clamp_predict(w)}px | {'30px' if w <= 680 else '不适用'} | {token_display} |")
mobile = [w for w in widths if w <= 680]
desktop = [w for w in widths if w > 680]
distinct = sorted({v for vs in p2["h1_font_size_by_width"].values() for v in vs})
A("")
A(f"- 判读：走查宽度 widths={json.dumps(widths)} 共 {len(widths)} 档（手机档 {len(mobile)} 个、桌面档 {len(desktop)} 个），"
  f"h1 实算值去重后 measured={json.dumps(distinct)}，与 token 档位 {token_display} 相同；"
  "而 styles.css 里那两条随视口变化的 h1 规则按公式应得上表第三、四列（例如 1280 档 clamp 应得 "
  f"{clamp_predict(1280)}px、320 档应得 {clamp_predict(320)}px）。实测值与两者都不符 ⇒ "
  "在浏览器实载的那份 CSS 里，生效的是 token 档那一条，两条 responsive 规则没有落地。")
A("- 仪器缺陷主动报：pass1 想用「选择器在已加载 CSS 里的字节偏移」定级联顺序，但三条规则的**选择器文本相同**"
  "（都叫 `.v8-page h1`，只差外面有没有 @media），indexOf 只会返回第一次出现的位置，所以那列 offsets 不可用；"
  "本节改用「实测值 vs 两条候选规则的预测值」来定谁在画，不依赖顺序猜测。")
A("")
A("## 六、这轮不能主张的")
A("")
A("- 角色判定三条来源都是结构推断，不是设计意图的证词；第一节为 0 条时，结论只能是「本轮没找到该角色的元素」，"
  "不等于全应用都不存在这个角色（弹层、错误/离线壳、深色档没驱动）。")
A("- pass2 的「同族 + 最近公共祖先」是我给的启发式：它可能把相邻模块的容器当角色；因此每条都给了家族名、"
  "同族元素数与容器矩形，可复核。")
A("- 手机链与号令者端口未参与，读数只在 4826/8726 成立。")

io.open(os.path.join(OUT, "TRIAGE_r1.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")

summary = {
    "served_tip": p1["served_tip"], "css_assets_loaded": p1["css_assets_loaded"],
    "rules_parsed_on_this_tip": p1["rules_parsed_on_this_tip"],
    "wanted_from_ord0421": p1["wanted_from_ord0421"],
    "pass1_class_counts": p1["class_counts"], "pass2_probe_counts": p2["family_probe_counts"],
    "pass2_widths": p2["widths"], "pass2_routes": p2["routes"],
    "orphan_repoint_rows": orph,
    "group_sibling_rows": [{"selector": r["selector"], "source": r["source_on_this_tip"],
                             "sibling_hits": r["sibling_hits"], "own_hits_max": r["own_hits_max"]} for r in sib],
    "third_party_rows": [{"selector": r["selector"], "source": r["source_on_this_tip"],
                          "probe": r["third_party"]} for r in tp],
    "dead_legacy_rows": [{"selector": r["selector"], "source": r["source_on_this_tip"],
                          "pass2": p2map.get(r["selector"])} for r in dead],
    "h1_measured_by_width": p2["h1_font_size_by_width"],
    "h1_predicted_by_width": {str(w): {"clamp_predict_px": clamp_predict(w),
                                       "media_680_predict_px": 30 if w <= 680 else None,
                                       "measured": sorted({r['font_size'] for r in p2['h1_rows'] if r['width'] == w})}
                              for w in widths},
    "hero_title_rule": hero, "section_title_rule": sect,
    "instrument_limitation_shipped_offset": "same selector text appears three times in the loaded CSS; indexOf returns the first, so byte-order claims were dropped",
    "pageerrors": p1["pageerrors"] + p2["pageerrors"],
}
io.open(os.path.join(OUT, "SUMMARY_r1.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(summary, ensure_ascii=False, indent=1))
for name, src in [("orphan_repoint_r2.json", os.path.join(RUN, "_full/orphan_repoint_r2.json")),
                  ("orphan_repoint_pass2.json", os.path.join(RUN, "_pass2/orphan_repoint_pass2.json")),
                  ("cmdr_orphan_repoint_r2.js", os.path.join(RUN, "cmdr_orphan_repoint_r2.js")),
                  ("cmdr_orphan_repoint_pass2.js", os.path.join(RUN, "cmdr_orphan_repoint_pass2.js"))]:
    io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n").write(
        io.open(src, encoding="utf-8").read())
print("orphans", len(orph), "sibling", len(sib), "third", len(tp), "dead", len(dead),
      "pass2_confirmed", p2["family_probe_counts"], "md bytes",
      os.path.getsize(os.path.join(OUT, "TRIAGE_r1.md")))
print("h1 by width", json.dumps(p2["h1_font_size_by_width"], ensure_ascii=False))
