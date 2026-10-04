"""车道 8ac89982 · 具名控件普查的收法器：把 30 份逐屏读数合成一张可派单名单。

三件事一起算，都不靠我读代码猜：

  1. 每一屏的分母与无名数（`total_controls` / `unnamed`），并核这一屏**真的落到了这一屏**：
     `landed_href` 的路径段若不含所请求的键，就是被外壳弹回了 Today，清单里具名标出，
     绝不让「其实是别的屏」被读成「这一屏干净」。
  2. 无名控件去重成一行一个：同一路由族内按 (标签名, data-testid, 前三枚 class) 归并，
     再记下它出现在哪几枚臂与哪几屏 —— 修法归 1ba48dbf，名单归我，去重规则写在这里可复核。
  3. 把「只有装饰性子节点」那一族单独点出来（`icon_child` 且 `decorative_only`）：
     这一族是读屏用户拿到空白的那一批，也正是无障碍名那一单要修的形。

usage: python cdp_census_merge_r1.py
"""
import json
import os
import pathlib
import re
import sys

# The gate runner owns `CITYNEXUS_EVIDENCE_DIR` and points it at <evidence>/<run-id>, so the
# artifacts land there rather than where a hand-set variable would put them. Read it back from the
# runner's own report instead of guessing a second location.
DEFAULT = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/e2e")
FALLBACK = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/cdp_census_r1")
EV = pathlib.Path(os.environ.get("CDP_CENSUS_DIR") or (DEFAULT if any(DEFAULT.glob("census_*_*.json")) else FALLBACK))
# The summary is a new artefact of this lane, so it is written into this lane's own directory
# rather than beside the shared gate artifacts it read.
OUT = pathlib.Path(os.environ.get("CDP_CENSUS_OUT_DIR") or FALLBACK)
ROUTES = ["hub", "live", "map", "studio", "stay", "discover", "import", "bookings",
          "footprints", "agent", "authoritative", "intelligence", "twin", "trash", "access"]
ARMS = ["zh", "en"]


def main() -> int:
    per_screen = []
    missing = []
    unnamed_rows = []
    pointer_unnamed = []
    via_counts: dict[str, int] = {}
    for route in ROUTES:
        for arm in ARMS:
            path = EV / f"census_{route}_{arm}.json"
            if not path.exists():
                missing.append(path.name)
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            landed_key = ""
            match = re.search(r"/v8/([a-z-]+)", data.get("landed_href", ""))
            if match:
                landed_key = match.group(1)
            bounced = landed_key != route
            per_screen.append({
                "route": route, "arm": arm, "landed_href": data.get("landed_href"),
                "landed_key": landed_key, "bounced_off_requested_route": bounced,
                "screen_title": data.get("screen_title"),
                "total_controls": data.get("total_controls"), "unnamed": data.get("unnamed"),
                "file": path.name,
            })
            for row in data.get("pointer_rows", []):
                via_p = row.get("name_via", "?")
                via_counts["pointer:" + via_p] = via_counts.get("pointer:" + via_p, 0) + 1
                if not row.get("unnamed"):
                    continue
                pointer_unnamed.append({**row, "route": route, "arm": arm})
            for row in data.get("rows", []):
                via = row.get("name_via", "?")
                via_counts[via] = via_counts.get(via, 0) + 1
                if not row.get("unnamed"):
                    continue
                unnamed_rows.append({**row, "route": route, "arm": arm})

    merged = {}
    for row in unnamed_rows:
        key = (row["tag"], row["testid"] or "", row["classes"] or "")
        entry = merged.setdefault(key, {
            "tag": row["tag"], "testid": row["testid"], "classes": row["classes"],
            "role": row["role"], "icon_child": row["icon_child"],
            "decorative_only": row["decorative_only"], "aria_hidden_self": row["aria_hidden_self"],
            "html_head": row["html_head"], "arms": set(), "routes": set(), "boxes": [],
            "count": 0,
        })
        entry["arms"].add(row["arm"])
        entry["routes"].add(row["route"])
        entry["boxes"].append([row["route"], row["arm"], row["box"]])
        entry["count"] += 1
    for entry in merged.values():
        entry["arms"] = sorted(entry["arms"])
        entry["routes"] = sorted(entry["routes"])

    pointer_merged = {}
    for row in pointer_unnamed:
        key = (row["tag"], row["testid"] or "", row["classes"] or "")
        entry = pointer_merged.setdefault(key, {
            "tag": row["tag"], "testid": row["testid"], "classes": row["classes"],
            "arms": set(), "routes": set(), "count": 0, "html_head": row["html_head"],
        })
        entry["arms"].add(row["arm"])
        entry["routes"].add(row["route"])
        entry["count"] += 1
    for entry in pointer_merged.values():
        entry["arms"] = sorted(entry["arms"])
        entry["routes"] = sorted(entry["routes"])
    report_pointer = sorted(pointer_merged.values(), key=lambda e: -e["count"])
    ordered = sorted(merged.values(), key=lambda e: (-e["count"], e["tag"], e["classes"] or ""))
    report = {
        "schema": "CNX_CDP_NAMED_CONTROL_CENSUS_R1",
        "shape": "390x844",
        "arms": ARMS,
        "routes_requested": len(ROUTES),
        "screens_measured": len(per_screen),
        "screens_missing": missing,
        "total_controls_across_screens": sum(row["total_controls"] or 0 for row in per_screen),
        "unnamed_occurrences": len(unnamed_rows),
        "pointer_only_unnamed_occurrences": len(pointer_unnamed),
        "distinct_unnamed_controls": len(ordered),
        "icon_only_unnamed": sum(1 for entry in ordered if entry["icon_child"]),
        "decorative_only_unnamed": sum(1 for entry in ordered if entry["decorative_only"]),
        "bounced_screens": [row for row in per_screen if row["bounced_off_requested_route"]],
        "name_source_distribution": dict(sorted(via_counts.items(), key=lambda kv: -kv[1])),
        "per_screen": per_screen,
        "unnamed_list": ordered,
        "pointer_only_unnamed_list": report_pointer,
    }
    (OUT / "census_summary_r1.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                                                 encoding="utf-8", newline="\n")
    print("screens=%d missing=%d controls=%d unnamed_occurrences=%d distinct=%d icon_only=%d decorative_only=%d bounced=%d"
          % (report["screens_measured"], len(missing), report["total_controls_across_screens"],
             report["unnamed_occurrences"], report["distinct_unnamed_controls"],
             report["icon_only_unnamed"], report["decorative_only_unnamed"], len(report["bounced_screens"])))
    print("pointer_only_unnamed_occurrences=%d distinct=%d" % (report["pointer_only_unnamed_occurrences"], len(report_pointer)))
    for entry in report_pointer[:10]:
        print("POINTER_UNNAMED tag=%s testid=%s classes=%s count=%d routes=%s" % (entry["tag"], entry["testid"],
              entry["classes"], entry["count"], ",".join(entry["routes"])[:70]))
    print("name_sources=%s" % json.dumps(report["name_source_distribution"], ensure_ascii=False))
    for entry in ordered[:12]:
        print("UNNAMED tag=%s testid=%s classes=%s count=%d arms=%s routes=%s icon=%s decorative=%s"
              % (entry["tag"], entry["testid"], entry["classes"], entry["count"],
                 "/".join(entry["arms"]), ",".join(entry["routes"])[:70], entry["icon_child"],
                 entry["decorative_only"]))
    if missing:
        print("MISSING=%s" % missing[:6])
    print("READ_FROM=%s WROTE=%s" % (EV, OUT / "census_summary_r1.json"))
    return 0 if not missing else 4


if __name__ == "__main__":
    sys.exit(main())
