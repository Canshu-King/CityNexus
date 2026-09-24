"""ORD-0289 分析：把"数 fetch 腿"这件事的每种口径都跑一遍，逐条归因差异（谁的数都不默认对）。

口径清单（都跑在同一份导出上，同一棵树）：
  MINE-AST       我自己的：AST 调用点（callee 是 `fetch` 或 `X.fetch`），method 只认字面量/同文件常量；
  CMD-REGEX-ALL  正则 `fetch(`（子串）——包工头申报的 40/33 这一层；
  CMD-REGEX-WR   正则 + 700 字符窗口里找 method ∈ 写动词 —— 他那 17 的来源；
  HJP-BARE       AST 但只认裸 `fetch(`（不含 `X.fetch`）——试 HJ-P3 的 33/13 是不是这个范围；
  HJP-NOADAPTER  AST 但排除 simulationAdapter（他们那单的门面在别处）——另一种候选解释。
每张表都逐条点名，不给"大概"。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUN = Path("D:/moodle/_qoder_f_run")
RCP = RUN / "o225_receipts"
GENS = {"landed_45b0a5e2": ("45b0a5e281cae9c37715173afd3ac5778f309ca7", "o289_landed_45b0a5e2"),
        "earlier_dcae1bc9": ("dcae1bc964125c3a975916f6bf667794cc19622a", "o289_earlier_dcae1bc9")}
WRITE = {"POST", "PUT", "PATCH", "DELETE"}
CMDR = {"landed_45b0a5e2": {"files": 71, "fetch": 40, "write": 17, "signal": 2, "timer": 0},
        "earlier_dcae1bc9": {"files": None, "fetch": 33, "write": 13, "signal": 2, "timer": 0}}


def ts_files(root: Path):
    return sorted((str(p.relative_to(root)).replace("\\", "/"), p) for p in root.rglob("*")
                  if p.is_file() and p.suffix in (".ts", ".tsx") and not p.name.endswith(".d.ts"))


def regex_all(root: Path):
    hits = []
    for rel, p in ts_files(root):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"fetch\(", text):
            line = text.count("\n", 0, m.start()) + 1
            ctx = text[max(0, m.start() - 60):m.start() + 12].splitlines()[-1]
            hits.append({"file": rel, "line": line, "callee": ctx.strip()[-40:]})
    return hits


def regex_window_writes(root: Path, window=700):
    out = []
    for rel, p in ts_files(root):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"fetch\(", text):
            ahead = text[m.start():m.start() + window]
            mm = re.search(r"method\s*[:=]\s*[\"'`]([A-Za-z]+)[\"'`]", ahead)
            verb = mm.group(1).upper() if mm else None
            if verb in WRITE:
                out.append({"file": rel, "line": text.count("\n", 0, m.start()) + 1, "method": verb,
                            "signal": bool(re.search(r"signal\s*:", ahead)),
                            "timer": bool(re.search(r"AbortSignal\.timeout|setTimeout\([^)]*\)[\s\S]{0,200}?\.abort\(", ahead))})
    return out


def load_ast(label):
    d = json.loads((RCP / f"ord0289_census_{label}.json").read_text(encoding="utf-8"))
    return d["sites"], d["summary"]


analysis = {"what": "ORD-0289：口径逐一复数与逐条归因（不改码，只交清单）",
            "method_declared_by_me": {"ast_callee": "Identifier fetch 或 PropertyAccess .fetch",
                                      "method": "字面量 / 同文件字符串常量；其余记 UNRESOLVED，不猜",
                                      "signal": "第二个实参是对象字面量且有 signal 属性（或同表达式文本里出现）",
                                      "timer": "同一调用表达式子树里 AbortSignal.timeout/abort，或 setTimeout(…, cb) 且 cb 调 .abort("},
            "gens": {}}
for label, (sha, dirname) in GENS.items():
    root = RUN / dirname / "frontend" / "src"
    sites, summ = load_ast("landed" if "landed" in label else "earlier")
    ra = regex_all(root)
    rw = regex_window_writes(root)
    bare = [s for s in sites if s["callee"] == "fetch"]
    no_adapter = [s for s in sites if "simulationAdapter" not in s["file"]]
    ast_writes = [s for s in sites if s["method"] in WRITE]
    w_summary = sum(1 for s in sites if s["second_arg"] == "absent")
    read_default = [s for s in sites if not s["method"] and s["second_arg"] != "absent"]
    entry = {
        "sha": sha, "export_dir": str(root),
        "files_scanned": summ["files_scanned"],
        "MINE_AST": {"fetch_sites": len(sites), "write": len(ast_writes),
                     "write_with_signal": sum(1 for s in ast_writes if s["signal"]),
                     "write_with_timer": sum(1 for s in ast_writes if s["timer"]),
                     "read_by_default_options_without_method": len(read_default),
                     "no_options_at_all": summ["method_absent_no_options"],
                     "method_unresolved": summ["method_unresolved_with_options"],
                     "options_with_spread": summ["sites_with_spread_options"],
                     "write_detail": [f"{s['file']}:{s['line']} {s['method']} signal={s['signal']} timer={s['timer']}"
                                      for s in ast_writes],
                     "bucket_sum_equals_total": len(ast_writes) + len(read_default)
                     + summ["method_absent_no_options"] == len(sites)},
        "CMD_REGEX_ALL_count": len(ra),
        "CMD_REGEX_WINDOW_WRITES": {"write": len(rw), "with_signal": sum(1 for x in rw if x["signal"]),
                                    "with_timer": sum(1 for x in rw if x["timer"]),
                                    "detail": [f"{x['file']}:{x['line']} {x['method']}" for x in rw]},
        "HJP3_BARE_FETCH_ONLY_sites": len(bare),
        "HJP3_NO_SIM_ADAPTER_sites": len(no_adapter),
        "HJP3_NO_SIM_ADAPTER_writes": sum(1 for s in no_adapter if s["method"] in WRITE),
        "regex_minus_ast_named": sorted({f"{x['file']}:{x['line']}" for x in ra}
                                        - {f"{s['file']}:{s['line']}" for s in sites})[:30],
        "regex_write_minus_ast_write_named": sorted({f"{x['file']}:{x['line']}" for x in rw}
                                                    - {f"{s['file']}:{s['line']}" for s in ast_writes}),
        "ast_write_not_in_regex_write_named": sorted({f"{s['file']}:{s['line']}" for s in ast_writes}
                                                     - {f"{x['file']}:{x['line']}" for x in rw}),
    }
    analysis["gens"][label] = entry
    print(f"[{label}] AST {entry['MINE_AST']['fetch_sites']} 处（写 {entry['MINE_AST']['write']}）｜"
          f"正则 fetch( {entry['CMD_REGEX_ALL_count']}｜正则窗口写 {entry['CMD_REGEX_WINDOW_WRITES']['write']}｜"
          f"裸 fetch {entry['HJP3_BARE_FETCH_ONLY_sites']}｜不含 adapter {entry['HJP3_NO_SIM_ADAPTER_sites']}")

# 两代之差：按文件逐处比
lg = {f"{s['file']}:{s['line']}" for s in load_ast("landed")[0]}
eg = {f"{s['file']}:{s['line']}" for s in load_ast("earlier")[0]}
analysis["across_generations"] = {
    "sites_only_in_landed": sorted(lg - eg), "sites_only_in_earlier": sorted(eg - lg),
    "note": "行号会随文件内改动平移，所以这两列只作线索，不当结论；文件级差异看下面两个清单",
}
# 文件级计数差 + 两代之间前端到底改了哪些文件（GitHub compare，不靠本地仓）
land_sites, _ = load_ast("landed")
ear_sites, _ = load_ast("earlier")


def by_file(sites):
    d: dict[str, list] = {}
    for s in sites:
        d.setdefault(s["file"], []).append(s)
    return d


lf, ef = by_file(land_sites), by_file(ear_sites)
diff_files = sorted({f for f in set(lf) | set(ef) if len(lf.get(f, [])) != len(ef.get(f, []))}
                    | ({f for f in lf if f not in ef} | {f for f in ef if f not in lf}))
analysis["per_file_diff"] = [{"file": f, "earlier": len(ef.get(f, [])), "landed": len(lf.get(f, [])),
                              "writes_earlier": sum(1 for s in ef.get(f, []) if s["method"] in WRITE),
                              "writes_landed": sum(1 for s in lf.get(f, []) if s["method"] in WRITE)}
                             for f in diff_files]
tok = Path(r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920").read_text(encoding="utf-8").strip()
import urllib.request
req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/compare/"
                             "dcae1bc964125c3a975916f6bf667794cc19622a...45b0a5e281cae9c37715173afd3ac5778f309ca7")
req.add_header("Authorization", "Bearer " + tok)
req.add_header("User-Agent", "citynexus-lane-f")
try:
    cmpd = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
    changed = [f["filename"] for f in cmpd.get("files", []) if f["filename"].startswith("frontend/")]
    analysis["github_compare_frontend_files"] = {
        "total_files_in_compare_page": len(cmpd.get("files", [])),
        "ahead_by": cmpd.get("ahead_by"), "behind_by": cmpd.get("behind_by"),
        "frontend_changed": changed,
        "frontend_src_changed": [f for f in changed if f.startswith("frontend/src/")]}
except Exception as exc:  # noqa: BLE001
    analysis["github_compare_frontend_files"] = {"FAIL": f"{type(exc).__name__}:{str(exc)[:120]}"}
print("两代前端改动文件（GitHub compare）：",
      json.dumps(analysis.get("github_compare_frontend_files", {}), ensure_ascii=False)[:400])
print("按文件计数有差的：", json.dumps(analysis["per_file_diff"], ensure_ascii=False)[:600])
out = RCP / "ord0289_census_analysis.json"
out.write_text(json.dumps(analysis, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("WROTE", out, out.stat().st_size, "B")
