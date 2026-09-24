"""凑一遍 HJ-P3 那 33/13 可能的范围口径（穷举假设，不猜）；顺手记 readDeadline.ts 那一处未决。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUN = Path("D:/moodle/_qoder_f_run")
RCP = RUN / "o225_receipts"
OUT = RCP / "ord0289_hypotheses.json"
WRITE = {"POST", "PUT", "PATCH", "DELETE"}
GENS = {"earlier_dcae1bc9": ("ord0289_census_earlier.json", "o289_earlier_dcae1bc9/frontend/src"),
        "landed_45b0a5e2": ("ord0289_census_landed.json", "o289_landed_45b0a5e2/frontend/src")}


def rel(p, root):
    return str(p.relative_to(root)).replace("\\", "/")


res = {}
for lbl, (census, rootrel) in GENS.items():
    root = RUN / rootrel
    per, tot = {}, 0
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in (".ts", ".tsx") or p.name.endswith(".d.ts"):
            continue
        n = len(re.findall(r"(?<![A-Za-z0-9_$])fetch\(", p.read_text(encoding="utf-8", errors="replace")))
        if n:
            per[rel(p, root)] = n
            tot += n
    sites = json.loads((RCP / census).read_text(encoding="utf-8"))["sites"]

    def bucket(sel):
        ss = [s for s in sites if sel(s)]
        w = [s for s in ss if s["method"] in WRITE]
        return {"sites": len(ss), "writes": len(w), "writes_signal": sum(1 for s in w if s["signal"]),
                "writes_timer": sum(1 for s in w if s["timer"])}

    is_test = lambda s: (".test." in s["file"]) or ("/__tests__/" in s["file"]) or ("mock" in s["file"].lower())  # noqa: E731
    hypotheses = {
        "all_ast": bucket(lambda s: True),
        "exclude_test_mock": bucket(lambda s: not is_test(s)),
        "only_features_dir": bucket(lambda s: s["file"].startswith("features/")),
        "exclude_app_and_i18n": bucket(lambda s: not s["file"].startswith(("app/", "i18n/"))),
        "only_with_options_object": bucket(lambda s: s["second_arg"] != "absent"),
        "only_bare_fetch_no_member": bucket(lambda s: s["callee"] == "fetch"),
        "exclude_components_dir": bucket(lambda s: not s["file"].startswith("components/")),
    }
    res[lbl] = {"bounded_regex_total": tot, "bounded_regex_per_file": per, "hypotheses": hypotheses,
                "targets_from_hjp3": {"sites": 33, "writes": 13, "signal": 2, "timer": 0}}
    print(f"[{lbl}] 有界正则 {tot}；假设桶：")
    for k, v in hypotheses.items():
        mark = "  ← 命中 33/13" if (v["sites"] == 33 and v["writes"] == 13) else ""
        print(f"   {k:28s} sites={v['sites']:3d} writes={v['writes']:3d} signal={v['writes_signal']} timer={v['writes_timer']}{mark}")
out = {"what": "ORD-0289：把 HJ-P3 的 33/13 可能对应的范围口径逐个试一遍（命中与否都记）",
       "gens": res,
       "reading": None}
hit = [(g, k) for g in res for k, v in res[g]["hypotheses"].items()
       if v["sites"] == 33 and v["writes"] == 13]
out["reading"] = ("有桶精确命中 33/13：" + json.dumps(hit, ensure_ascii=False)) if hit else \
    "没有任何一个候选口径凑出 33 且 13（最接近的见 hypotheses）⇒ 33/13 只能作为他们那棵树 + 他们那份口径的读数保留，" \
    "不外推、不指错；能对齐的是承重那两项：写腿带 signal=2、写腿带计时器=0（四种口径、两代、三方人数一致）。"
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("WROTE", OUT, OUT.stat().st_size, "B")
print(out["reading"])
