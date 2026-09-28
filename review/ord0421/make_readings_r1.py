"""ORD-0421 lane: turn census_r3.json into the committed readings.

0 product bytes: this writes only files under review/ord0421/.  The "what the user would see"
sentence is derived from the delta between what the rule sets and what the element computes — not
written by hand — so a reader can check every claim against the JSON.
"""
import io
import json
import os
import subprocess
import time

RUN = "D:/moodle/_qoder_r_ord0421/run"
WT = "D:/moodle/_qoder_r_ord0421/wt"
OUT = os.path.join(WT, "review/ord0421")
CENSUS = os.path.join(RUN, "_census/census_r3.json")

os.makedirs(OUT, exist_ok=True)
c = json.load(io.open(CENSUS, encoding="utf-8"))

PROP_WHAT = {
    "background": "底色", "background-color": "底色", "background-image": "底图", "color": "字色",
    "font-size": "字号", "font-weight": "字重", "padding": "内边距", "margin": "外边距",
    "border-radius": "圆角", "border": "描边", "display": "排版方式", "width": "宽度",
    "height": "高度", "gap": "间隙", "opacity": "透明度", "visibility": "可见性",
    "text-decoration": "文字装饰", "line-height": "行高", "box-shadow": "投影",
    "position": "定位", "transform": "变换", "cursor": "光标", "overflow": "溢出处理",
    "align-items": "对齐", "justify-content": "分布", "flex-direction": "轴向",
    "grid-template-columns": "栅格列", "z-index": "层序", "filter": "滤镜",
    "min-height": "最小高度", "max-height": "最大高度", "content": "伪元素内容",
    "letter-spacing": "字距", "text-align": "对齐方向", "flex": "伸缩",
}


def norm(v):
    """Compare a declared value with a computed one as coarsely as a human eye would."""
    v = (v or "").strip().lower()
    v = v.replace("none repeat scroll 0% 0% / auto padding-box border-box", "")
    v = v.replace("  ", " ").strip()
    return v


def sentence(row):
    computed = row.get("computed_of_target") or {}
    rule = row.get("rule_sets") or {}
    diffs = []
    for prop, want in rule.items():
        got = computed.get(prop)
        if got is None:
            continue
        if norm(want) and norm(want) not in norm(got) and norm(got) not in norm(want):
            diffs.append((prop, want, got))
    if not diffs:
        return "该规则要设的属性，元素实际算出来已经一样（{n} 项）⇒ 今天肉眼看不出差别，属死重量。".format(
            n=len(rule))
    parts = [f"{PROP_WHAT.get(p, p)}（{p}）现在实际是 {g}，规则写的是 {w}" for p, w, g in diffs[:3]]
    return "用户会看见的差别：" + "；".join(parts) + "。"


dead = c["dead_rules_target_present"]
no_consumer = [r for r in c["all_zero_rows"] if r["class"] == "DEAD_RULE_NO_CONSUMER"]
stateful = [r for r in c["all_zero_rows"] if r["class"] == "STATEFUL_NOT_DEAD"]
not_sure = [r for r in c["all_zero_rows"] if r["class"].startswith("NOT_SURE")]

lines = []
A = lines.append
A("# ORD-0421 CSS 死规则普查 · 读数（0 产品字节）")
A("")
A(f"- 生成时间 {time.strftime('%Y-%m-%dT%H:%M:%S%z')}，仪表 `cmdr_css_census_r3.js`（本目录）。")
A(f"- 被量产物：现尖 `{c['served_tip']}` 的 frontend 构建，浏览器实载 CSS = {json.dumps(c['css_assets_loaded'])}。")
A(f"- 场景：{json.dumps(c['scenarios'], ensure_ascii=False)}，扫过 sweep 次数 = {c['sweeps']}。")
A(f"- 规则总数 rules_parsed = {c['rules_parsed']}，去重后唯一选择器 unique_selectors = {c['unique_selectors']}。")
A(f"- 全场景 0 命中的选择器 zero_exact = {c['zero_exact']}，分类分布 class_counts = "
  + json.dumps(c["class_counts"], ensure_ascii=False) + "。")
A("")
A("## 一、判成真缺陷（上下文在屏上、叶子也在其内，完整选择器仍 0 命中）")
A("")
A("这一类的判据不是「没命中」，而是三条同时成立：祖先上下文 querySelectorAll 命中 > 0、"
  "在该上下文内部再查叶子命中 > 0、完整选择器命中 = 0。也就是选择器写的结构关系在 DOM 里不存在。")
A("")
A("| # | 选择器 | path:line | 上下文 | 上下文命中 | 叶在其内 | 其中非直接子级 | 屏上实际（摘） | 用户会看见什么差别 |")
A("|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(dead, 1):
    t = r.get("target_probe") or {}
    comp = r.get("computed_of_target") or {}
    brief = " ".join(f"{k}={v}" for k, v in list(comp.items())[:3])
    A(f"| {i} | `{r['selector']}` | {', '.join(r['source'])} | `{r['context']}` | "
      f"{r['context_hits_max']} | {r['leaf_under_context_max']} | {t.get('leaves_not_direct_child', '-')} | "
      f"{t.get('tag', '-')}.{t.get('classes', '')}「{t.get('text', '')[:12]}」 {brief} | {sentence(r)} |")
A("")
A("## 二、叶子类名/id 在 frontend/src 里一次都没出现（无消费者）")
A("")
A("判据是对 `frontend/src` 下所有 `.ts/.tsx/.js/.jsx/.html` 做一次子串扫描（CSS 自身排除）。"
  "子串匹配偏保守：只要该名字在任何一处出现就不算缺。运行时拼出来的类名仍可能被骗过去，所以这一类只作候选、不称铁证。")
A("")
A("| # | 选择器 | path:line | 缺的名字 | 规则要设 |")
A("|---|---|---|---|---|")
for i, r in enumerate(no_consumer, 1):
    A(f"| {i} | `{r['selector']}` | {', '.join(r['source'])} | {', '.join(r['leaf_tokens_absent_from_source'])} | "
      + ", ".join(f"{k}: {v}" for k, v in list((r['rule_sets'] or {}).items())[:4]) + " |")
A("")
A("## 三、STATEFUL_NOT_DEAD（不算死规则，仪表看不见状态）")
A("")
A("| 选择器 | path:line | 为什么不算 |")
A("|---|---|---|")
for r in stateful:
    why = ("伪元素：querySelectorAll 永远看不见 ::before/::after" if "::" in r["selector"]
           else "状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次")
    A(f"| `{r['selector']}` | {', '.join(r['source'])} | {why} |")
A("")
A("## 四、NOT_SURE（点名缺哪一个读数，不计数）")
A("")
buckets = {}
for r in not_sure:
    buckets.setdefault(r["class"], []).append(r)
for k, v in sorted(buckets.items(), key=lambda x: -len(x[1])):
    A(f"- `{k}`：{len(v)} 条。" + ("这些选择器不在浏览器实载的 CSS 字节里（被 tree-shake/未 import/写错文件），"
      "本单的 DOM 探针判不了它们。" if k == "NOT_SURE_NOT_IN_LOADED_CSS" else
      "它们要的上下文在走过的 14 屏 × 2 语言 × 3 形状里一次都没挂载，缺的是能挂载它的那个状态："
      "弹层/抽屉内特定分组/错误提示/离线壳/深色档。" if k == "NOT_SURE_CONTEXT_NOT_MOUNTED" else
      "去组合符后叶子也没在走过的屏幕里出现，同缺上面那个状态读数。" if k == "NOT_SURE_LEAF_NOT_FOUND" else
      "仪表把该选择器判为非法语法，需换可读法重测。"))
A("")
A("## 五、正对照（仪表必须能抓到已知的那三条，否则普查不可信）")
A("")
known = [r for r in dead if "v8-nav-drawer" in (r["context"] or "")]
A(f"- 号令者亲测的抽屉一族被本仪表抓到 {len(known)} 条："
  + "; ".join(f"`{r['selector']}` @ {', '.join(r['source'])}" for r in known) + "。")
for r in known:
    A(f"  - `{r['selector']}`：{sentence(r)}")
A("")
A("## 六、这轮不能主张的")
A("")
A("- 手机链（:4781 / :4782 / :8693）与号令者的 :4805 我都没连，也没重起；读数只在我自起的端口上成立。")
A("- 弹层、错误提示、离线壳、深色档这些状态本轮没有驱动，落在第四节里；把它们的挂载条件补进扫屏后，"
  "第三/四节里的一部分会挪进第一节或彻底消失，那不是本轮的结论。")
A("- 「用户会看见什么差别」是把规则值与元素计算值做差得到的句子，不是设计判断；"
  "值相同的那些我写成死重量，不等于可以删——删除是另一个单的事。")

with io.open(os.path.join(OUT, "DEAD_RULES_r1.md"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")

summary = {
    "served_tip": c["served_tip"], "css_assets_loaded": c["css_assets_loaded"],
    "rules_parsed": c["rules_parsed"], "unique_selectors": c["unique_selectors"],
    "zero_exact": c["zero_exact"], "class_counts": c["class_counts"],
    "sweeps": c["sweeps"], "scenarios": c["scenarios"],
    "pageerrors": c["pageerrors"],
    "known_drawer_family_detected": [r["selector"] for r in known],
    "first_section_rows": [
        {"selector": r["selector"], "source": r["source"], "context": r["context"],
         "context_hits_max": r["context_hits_max"], "leaf_under_context_max": r["leaf_under_context_max"],
         "leaves_not_direct_child": (r.get("target_probe") or {}).get("leaves_not_direct_child"),
         "target": (r.get("target_probe") or {}).get("tag"),
         "target_text": (r.get("target_probe") or {}).get("text"),
         "rule_sets": r["rule_sets"], "computed_of_target": r["computed_of_target"],
         "why": r["why"], "plain_difference": sentence(r)} for r in dead],
}
with io.open(os.path.join(OUT, "SUMMARY_r1.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=1)

for name, src in [("census_r3.json", CENSUS),
                  ("cmdr_css_census_r3.js", os.path.join(RUN, "cmdr_css_census_r3.js"))]:
    if os.path.isfile(src):
        with io.open(src, encoding="utf-8") as fh:
            data = fh.read()
        with io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(data)

print("dead", len(dead), "no_consumer", len(no_consumer), "stateful", len(stateful),
      "not_sure", len(not_sure), "known_detected", len(known))
print("rows written to", os.path.join(OUT, "DEAD_RULES_r1.md"),
      "bytes", os.path.getsize(os.path.join(OUT, "DEAD_RULES_r1.md")))
