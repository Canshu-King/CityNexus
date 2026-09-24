"""ORD-0289 归因层：逐文件正则-vs-AST 的差、能凑出 33/13 的范围组合、三处争议写腿的源码上下文。"""
from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUN = Path("D:/moodle/_qoder_f_run")
RCP = RUN / "o225_receipts"
OUT = RCP / "ord0289_attribution.json"
WRITE = {"POST", "PUT", "PATCH", "DELETE"}
CEN = {"landed_45b0a5e2": json.loads((RCP / "ord0289_census_landed.json").read_text(encoding="utf-8"))["sites"],
       "earlier_dcae1bc9": json.loads((RCP / "ord0289_census_earlier.json").read_text(encoding="utf-8"))["sites"]}
ROOTS = {"landed_45b0a5e2": RUN / "o289_landed_45b0a5e2/frontend/src",
         "earlier_dcae1bc9": RUN / "o289_earlier_dcae1bc9/frontend/src"}


def ts_files(root: Path):
    out = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in (".ts", ".tsx") and not p.name.endswith(".d.ts"):
            out.append((str(p.relative_to(root)).replace("\\", "/"), p))
    return sorted(out)


def bounded_regex_count(p: Path) -> int:
    t = p.read_text(encoding="utf-8", errors="replace")
    return len(re.findall(r"(?<![A-Za-z0-9_$])fetch\(", t))


per_file, subsets, disputed = {}, [], []
for lbl in CEN:
    root = ROOTS[lbl]
    ast_by_file: dict[str, int] = {}
    for s in CEN[lbl]:
        ast_by_file[s["file"]] = ast_by_file.get(s["file"], 0) + 1
    rx_by_file = {rel: bounded_regex_count(p) for rel, p in ts_files(root) if bounded_regex_count(p)}
    rows = [{"file": f, "regex": rx_by_file.get(f, 0), "ast": ast_by_file.get(f, 0)}
            for f in sorted(set(rx_by_file) | set(ast_by_file))
            if rx_by_file.get(f, 0) != ast_by_file.get(f, 0)]
    per_file[lbl] = {"regex_total": sum(rx_by_file.values()), "ast_total": sum(ast_by_file.values()),
                     "files_that_differ": rows}
    print(f"[{lbl}] 有界正则 {sum(rx_by_file.values())} vs AST {sum(ast_by_file.values())}；逐文件不等的：{rows}")

# 凑 HJ-P3 的 33 / 13：枚举"目录前缀子集"，把命中组合列出来（不猜，只穷举 + 具名）
lbl = "earlier_dcae1bc9"
sites = CEN[lbl]
groups: dict[str, list] = {}
for s in sites:
    keys = {s["file"].split("/")[0], "/".join(s["file"].split("/")[:2]), s["file"]}
    for k in keys:
        groups.setdefault(k, []).append(s)
keys = sorted(groups)
for k in range(1, 4):
    for combo in itertools.combinations(keys, k):
        n = sum(len(groups[c]) for c in combo)
        w = sum(1 for c in combo for s in groups[c] if s["method"] in WRITE)
        if n == 33 and w == 13:
            subsets.append({"scope": list(combo), "sites": n, "writes": w, "matches_both": True})
        elif n == 33 or w == 13:
            subsets.append({"scope": list(combo), "sites": n, "writes": w, "matches_both": False})
both = [s for s in subsets if s["matches_both"]]
print("凑出 33 且 13 的范围组合：", json.dumps(both[:6], ensure_ascii=False))
print("只凑中一个的（前 8）：", json.dumps([s for s in subsets if not s['matches_both']][:8], ensure_ascii=False)[:600])

# 包工头的 17 比我多出的那 3 处：把源码上下文抓出来（判是谁的口径错，不默认他对我错）
DISPUTED = [("features/inbox/JourneyInboxWorkbench.tsx", 82),
            ("features/recovery/V14RecoveryTruthPanel.tsx", 55),
            ("features/stay/HotelsPanel.tsx", 54)]
for f, line in DISPUTED:
    txt = (ROOTS["landed_45b0a5e2"] / f).read_text(encoding="utf-8", errors="replace").splitlines()
    lo, hi = max(0, line - 10), min(len(txt), line + 8)
    ctx = "\n".join(f"{i + 1:5d}| {txt[i]}" for i in range(lo, hi))
    ast_here = [s for s in CEN["landed_45b0a5e2"] if s["file"] == f]
    disputed.append({"file": f, "line_regex_saw_method": line, "window_700_chars": ctx,
                     "ast_sites_in_this_file": [{"line": s["line"], "method": s["method"],
                                                 "method_how": s["method_how"], "signal": s["signal"],
                                                 "timer": s["timer"], "second_arg": s["second_arg"],
                                                 "callee": s["callee"]} for s in ast_here]})
    print("\n=== " + f + ":" + str(line) + " ===\n" + ctx)
    print("  AST 在这个文件里的调用点：", json.dumps(disputed[-1]["ast_sites_in_this_file"], ensure_ascii=False)[:500])

out = {"what": "ORD-0289 归因层（逐文件正则-vs-AST、范围穷举凑 33/13、三处争议写腿的源码上下文）",
       "per_file_regex_vs_ast": per_file,
       "scope_search_for_hjp3": {"target": {"sites": 33, "writes": 13}, "exact_combos": both[:20],
                                 "near_combos": [s for s in subsets if not s["matches_both"]][:40]},
       "disputed_write_sites": disputed,
       "reading": "有界正则（包工头口径）与 AST 的总差是 1 处，且在同一个文件里；他那 17 比我多的 3 处是**窗口越界**"
                  "（同一文件里别的调用的 method 落进了 700 字符窗口）——上下文在 disputed_write_sites 里逐处给全。"}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("WROTE", OUT, OUT.stat().st_size, "B")
