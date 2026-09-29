"""ORD-0417 lane: answer "does the hub draw stop pins?" from the two runs, not from an opinion.

Built from the gate logs of two runs on the same tip (4037cb331ea00b83124316d40329762fa1131689):
  hub0417r10onlinedef  -- the gate as it stands on the line (v1, no viewport assertion);
  hub0417r11viewport2  -- the same file with the viewport assertion re-applied.
Everything here is read out of the pushed rows of those logs; the code facts carry their own
`path:line`, taken from the tip's own bytes.
"""
import io
import json
import re

G = r"D:/moodle/_qoder_b_ord0417_20260928/evidence/gate"
TIP = "4037cb331ea00b83124316d40329762fa1131689"

ARM_LINE = re.compile(r"^\s+(ok|x)\s+\d+\s+\[chromium\].*spec\.ts:\d+:\d+ › (\S+)")


def read(path):
    results, rows = {}, []
    for l in io.open(path, encoding="utf-8", errors="replace"):
        m = ARM_LINE.match(l.rstrip())
        if m:
            results[m.group(2)] = "passed" if m.group(1) == "ok" else "failed"
        i = l.find("spec.ts :: hub-")
        if i < 0:
            continue
        arm = l[i + 11:].split(" ")[0]
        j = l.find("{")
        try:
            rows.append((arm, json.loads(l[j:])))
        except Exception:
            pass
    return results, rows


out = {"tip_measured": TIP, "runs": {}}
for tag, path in (("v1_gate_as_landed", f"{G}/hub0417r10onlinedef.log"),
                  ("v2_gate_viewport_assertion_reapplied", f"{G}/hub0417r11viewport2.log")):
    results, rows = read(path)
    marks = [r for a, r in rows if a.startswith("hub-pressed") and "states" in r]
    tap = [r for a, r in rows if a.startswith("hub-tap-named") and "glass" in r]
    cell = [r for a, r in rows if a.startswith("hub-not-aria") and "cell" in r]
    geom = [r for a, r in rows if a.startswith("hub-geometry") and "band_box_idle" in r]
    out["runs"][tag] = {
        "arms": results,
        "tally": {"passed": sum(1 for v in results.values() if v == "passed"),
                  "failed": sum(1 for v in results.values() if v == "failed")},
        "hub_markers_observed": [len(r["states"]) for r in marks],
        "hub_markers_reporting_selected": [sum(1 for s in r["states"] if s.get("pressed") == "true")
                                           for r in marks],
        "name_painted_on_hub": [bool(r.get("glass", {}).get("present")) for r in tap],
        "sentences": [r.get("cell", {}).get("text") for r in cell],
        "naming_cell_box_px": [r.get("cell", {}).get("box") for r in cell],
        "viewport_height_px": [r.get("cell", {}).get("inner_h") for r in cell
                               if r.get("cell", {}).get("inner_h") is not None],
        "geometry": [{"arm_lost": r.get("lost"), "reachable_idle": r.get("reachable_idle"),
                      "reachable_with_selection": r.get("reachable_with_selection"),
                      "band_growth_px": r.get("band_growth_px"),
                      "cell_box": (r.get("cell") or {}).get("box"),
                      "fatal": r.get("fatal")} for r in geom],
    }

out["code_facts_on_this_tip"] = {
    "pins_are_emitted_by": "frontend/src/components/v8/MapPanel.tsx:416 (class v9-map-marker, role=button at :424)",
    "the_optional_call_that_ate_hub_taps_before_the_fix": "frontend/src/components/v8/MapPanel.tsx:427",
    "map_stops_and_map_stop_ids_belong_to_map_page_only":
        "frontend/src/app/V8Experience.tsx:3930 and :3947, inside `function MapPage` at :3806",
    "hub_map_panel_call_site": "frontend/src/app/V8Experience.tsx:3137",
    "the_only_path_to_zero_markers_on_any_map_panel":
        "MapPanel's points memo returns active-plan activities with coordinates, else falls back to "
        "data.offers.slice(0,1); with neither a located plan nor an offer it yields no markers",
}
out["reading_of_the_relayed_claim"] = (
    "The relayed observation was `no map-stops and no map-stop-* on /v8/hub`. Those two testids are "
    "emitted only inside MapPage's stop list (anchors above), so their absence on the hub is the "
    "expected shape of the code and says nothing about pins. Pins are `.v9-map-marker` nodes, and both "
    "runs below count them on the hub directly."
)
io.open(f"{G}/HUB_PIN_PRESENCE_{TIP[:8]}_R1.json", "w", encoding="utf-8",
        newline=chr(10)).write(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps({k: v["tally"] for k, v in out["runs"].items()}))
print("markers on hub:", [r["hub_markers_observed"] for r in out["runs"].values()])
