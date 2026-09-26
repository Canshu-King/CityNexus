"""ORD-0345 前两格读数件：改前红/改后绿由同一把尺（r6）在两棵树上量，逐格点名。

分工说清楚：这一件的 `claimed_result` 只到"AST 污点面" —— 尺说哪一格从命中变不命中、有没有新增格。
渲染面上的两件事（旅客到底看到哪句话、异常原文有没有进 DOM 或 data-*）**这一件不宣称已量**，
它需要真浏览器臂；那半是 R2，缺它就不能说"屏面已验"。
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
WT = HERE / "wt"
SNAP = HERE / "snap"
RULER = "ui_exposure_taint_ast_r6.cjs"
RULER_BLOB = "6a251d3a6bea70329e06581384a81d5ef54c96a6"
TIP = "38277c4e9787b1ddf0bf69487060ba0e40c14146"
FILES = {
    "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx": "150",
    "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx": "162",
    "frontend/src/features/simulation/SimulationPanel.tsx": "934",
    "frontend/src/features/studio/V12TripStudioPanel.tsx": "106",
    "frontend/src/features/trip/ActivityDetail.tsx": "206",
}
NEW = ["frontend/src/components/CnxMeasuredFacts.tsx", "frontend/src/lib/rejectionFacts.ts"]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")


def ruler(tree: Path, out: str) -> dict:
    proc = run(["node", str(HERE / RULER), "--tree", str(tree), "--out", str(HERE / out)], HERE)
    data = json.loads((HERE / out).read_text("utf-8"))
    return {"exit": proc.returncode, "hits": [f"{h['file']}:{h['line']} {h['rule']}" for h in data["hits"]],
            "modules_in_graph": data.get("modules_in_graph"), "out": out}


def facts_of(path: str, at_tip: bool) -> dict:
    ref = subprocess.run(["git", "show", f"{TIP}:{path}"], cwd=str(WT), capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return {"exists": bool(ref), "lines": ref.count("\n") + 1 if ref else 0,
            "message_render_present": "error.message" in ref or "cause.message" in ref}


def main() -> int:
    before = json.loads((HERE / "census_tip_38277c4e.json").read_text("utf-8"))
    after = ruler(SNAP, "census_after_cells123.json")
    bset = {f"{h['file']}:{h['line']} {h['rule']}" for h in before["hits"]}
    aset = set(after["hits"])
    mine = {k: v for k, v in FILES.items()}
    cleared = sorted(bset - aset)
    added = sorted(aset - bset)
    per_cell = {}
    for path, line in mine.items():
        was = sorted(h for h in bset if h.startswith(f"{path}:{line} "))
        now = sorted(h for h in aset if h.split(":")[0] + ":" in path or path.split("/")[-1] in h)
        still = [h for h in aset if path.split("/")[-1] in h]
        per_cell[path] = {"hit_at_tip": was, "hits_now_in_file": still,
                          "state": "CLEARED" if was and not still else "STILL_HITTING" if still else "NO_HIT_EVER"}
    diff_files = run(["git", "status", "--porcelain"], WT).stdout.split("\n")
    out = {
        "order": "ORD-0345", "lane": "S2-hermes (d9e2c9ae)",
        "ruler": {"file": RULER, "blob": RULER_BLOB,
                  "blob_verified_before_use": run(["git", "hash-object", "--no-filters", str(HERE / RULER)],
                                                  HERE).stdout.strip() == RULER_BLOB,
                  "same_tool_as_the_ledger_census": "evidence/cmdr-q64-census-0749/r6_tree_tip_c740f45d.json"},
        "tip": TIP,
        "scope_done_this_block": [k for k in ("frontend/src/features/discovery/RealCityDiscoveryPanel.tsx",
                                              "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx")],
        "scope_left_with_reasons": {
            "frontend/src/features/studio/V12TripStudioPanel.tsx:106":
                "异常原文是在 api/v12Authoritative.ts 的抛点铸成的，面板这一行只是转述；修它要动那两枚 mutation 的抛点，"
                "而 V12/Recovery 面正被 ORD-0338 与 ORD-0339 的车道压着 —— 我不改别人在飞的字节。",
            "frontend/src/features/simulation/SimulationPanel.tsx:934":
                "上游文字是经过 helper 返回的 `{zh ? outcome.zh : outcome.en}` 进 DOM 的，消它就得换 outcome 文案的出处；"
                "而 SimulationPanel 是 lane F 的界面（它的会话名就是 Simulation 面板），先要归属。",
            "frontend/src/features/trip/ActivityDetail.tsx:206":
                "命中在 `{openingKnown && ...}` 的渲染点上 —— 若 openingKnown 是布尔，React 根本不落文字，那是量具的保守命中；"
                "判它要有真 DOM 读数（臂 R2），不能靠我读源码下结论。",
        },
        "censuses": {"before_tip": {"out": "census_tip_38277c4e.json", "hits": sorted(bset),
                                    "modules_in_graph": before.get("modules_in_graph")},
                     "after_candidate": after},
        "delta": {"cleared": cleared, "added": added, "total_before": len(bset), "total_after": len(aset)},
        "per_cell": per_cell,
        "new_files": [{"path": f, "lines": len((WT / "frontend" / "src" / f.split("frontend/src/")[-1]).read_text("utf-8").split("\n"))}
                      for f in NEW],
        "changed_files": [l.strip() for l in diff_files if l.strip()],
        "shared_files_untouched": {
            "src/i18n/LocaleContext.tsx": not run(["git", "status", "--porcelain", "--", "src/i18n/LocaleContext.tsx"], WT / "frontend").stdout.strip(),
            "src/lib/rawFacts.ts": not run(["git", "status", "--porcelain", "--", "src/lib/rawFacts.ts"], WT / "frontend").stdout.strip(),
            "src/lib/failureAttribution.ts": not run(["git", "status", "--porcelain", "--", "src/lib/failureAttribution.ts"], WT / "frontend").stdout.strip(),
            "src/lib/errorReceipt.ts": not run(["git", "status", "--porcelain", "--", "src/lib/errorReceipt.ts"], WT / "frontend").stdout.strip(),
            "src/components/RawFactsPanel.tsx": not run(["git", "status", "--porcelain", "--", "src/components/RawFactsPanel.tsx"], WT / "frontend").stdout.strip(),
        },
        "instrument_self_faults": {
            "first_attempt_widened_the_leak": ("我先用 `await response.text()` 再 JSON.parse 同一份文本，"
                                               "于是尺顺着这条 text 把**成功响应体**里每个渲染点都判成 RAW_BODY 上屏："
                                               "命中从 :150 搬到 :228，一格没少。改成只在 !response.ok 那一支读文本、"
                                               "成功支仍走 response.json() 之后才真的清掉。读数件 census_after_cell1*.json 两件都留。"),
        },
        "third_cell_shape_call_measured": {
            "cell": "frontend/src/features/trip/ActivityDetail.tsx:206",
            "what_it_renders": "`opening?.raw`（地点记录自己的 opening_hours.raw），不是拒绝信封的句子；`openingKnown` 是条件而非被渲染的布尔，所以 React 这里确实落了文字 —— 量具的保守命中这条不成立",
            "what_i_changed": "给这一行加了归属（zh「· 供应商原文」/ en \"· provider's own text\"）与 Q70 锚 data-cnx-field=\"opening_hours.raw\"，值一个字没删",
            "measured_effect": "尺的命中没消，只是从 :206 移到 :214（census_after_cell5.json）—— 也就是说锚点与归属不足以让 RAW_BODY_TO_DOM 翻绿，撤回与否则是要你按要件判的，我不自己改判",
        },
        "not_yet_measured": ["真浏览器渲染面上：旅客具体看到哪句话、异常原文有没有进 DOM 或 data-*/aria-*（臂 R2）"],
        "derived_result": None, "claimed_result": "OBSERVED_ON_AST_SURFACE_ONLY",
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    target = HERE / "ord0345_readings_r1.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("cleared:", cleared)
    print("added  :", added or "NONE")
    print("per cell:", {k.split('/')[-1]: v["state"] for k, v in per_cell.items()})
    mine_files = set(FILES)
    net_new = [a for a in added if a.split(":")[0] not in mine_files]
    moved = [a for a in added if a.split(":")[0] in mine_files]
    out["verdict"] = {"cells_cleared": len(cleared), "net_new_exposures_other_files": net_new,
                      "hits_that_only_moved_line_within_an_argued_cell": moved,
                      "both_target_cells_cleared": all(any(c.startswith(f) for c in cleared)
                                                       for f in out["scope_done_this_block"])}
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + chr(10), "utf-8")
    print("net new in other files:", net_new or "NONE", "| moved within argued cell:", moved)
    return 0 if net_new == [] else 1


if __name__ == "__main__":
    raise SystemExit(main())
