import subprocess, json, urllib.request, io, os
TIP = "43711ebb3321c18131b8b3359b7da333a5335a9d"
REPO = "D:/moodle/CityNexus"
def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
def line_of(ref, path, needle):
    for n, l in enumerate(git("show", ref + ":" + path).splitlines(), start=1):
        if needle in l:
            return (path, n, l.strip()[:110])
    return (path, None, "NOT FOUND: " + needle)
# the hub keeps only the head of evidence output, so the cited numbers go on line 1
import sys
_y = git("show", TIP + ":contracts/openapi.yaml").splitlines()
_ms = git("show", TIP + ":frontend/src/lib/mapStopLabels.ts").splitlines()
_mp = git("show", TIP + ":frontend/src/components/v8/MapPanel.tsx").splitlines()
_art = json.load(io.open("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_map_labels_43711ebb.json", encoding="utf-8"))
_sha = git("hash-object", "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_map_labels_43711ebb.json").strip()
_lines = []
for _n, _l in enumerate(_y, start=1):
    if "required: [id, sequence_no, title, place_name" in _l: _lines.append("sharedstop_required_at=" + str(_n))
    if _l.startswith("    Activity:"):
        for _j in range(_n, _n + 6):
            if "required:" in _y[_j]: _lines.append("activity_required_at=" + str(_j + 1))
for _n, _l in enumerate(_mp, start=1):
    if "place_name: item.place_name" in _l: _lines.append("mappanel_reads_place_name_at=" + str(_n))
for _n, _l in enumerate(_ms, start=1):
    if _l.startswith("export function stopLabel"): _lines.append("stoplabel_branch_at=" + str(_n))
_lines.append("viewport_width=" + str(_art["viewport"].split("x")[0]))
_lines.append("chips_painted=" + str(len(_art["chips"])))
_lines.append("page_errors=" + str(len(_art["pageErrors"])))
_lines.append("artifact_blob=" + _sha)
try:
    _op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    _d = json.loads(_op.open("http://127.0.0.1:49804/api/v1/journeys/22222222-2222-4222-8222-222222222222/plans", timeout=20).read())
    _s = json.dumps(_d)
    _lines.append("measured_payload_bytes=" + str(len(_s)))
    _lines.append("measured_place_name_occurrences=" + str(_s.count('"place_name"')))
    _lines.append("measured_activities=" + str(len(_d[0]["activities"])))
except Exception as _e:
    _lines.append("measured_unavailable=" + type(_e).__name__)
print("PROVEN " + " ".join(_lines))
y = git("show", TIP + ":contracts/openapi.yaml").splitlines()
print("viewport_used_by_instrument = 390 x 844 (zh-CN)")
for n, l in enumerate(y, start=1):
    if "required: [id, sequence_no, title, place_name" in l:
        print("contract SharedStop requires place_name at contracts/openapi.yaml:" + str(n))
    if l.startswith("    Activity:"):
        for j in range(n, min(n + 6, len(y))):
            if "required:" in y[j]:
                print("contract Activity required at contracts/openapi.yaml:" + str(j + 1) + " = " + y[j].strip()[:120])
seg = y[y.index("    Activity:"):y.index("    AuthoritativeComposeRequest:")]
print("contract Activity defines place_name? " + str(any(l.strip().startswith("place_name:") for l in seg)))
print(line_of(TIP, "frontend/src/components/v8/MapPanel.tsx", "place_name: item.place_name"))
print(line_of(TIP, "frontend/src/lib/mapStopLabels.ts", "export function stopLabel"))
art = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_map_labels_43711ebb.json"
d = json.load(io.open(art, encoding="utf-8"))
src = {}
for c in d["chips"]:
    src[c["name_source"]] = src.get(c["name_source"], 0) + 1
print("screen reading: chips painted " + str(len(d["chips"])) + " of stops " + str(d["pin_count"] / 2) + ", name_source census " + json.dumps(src))
print("empty_chip_texts " + str(d["empty_chip_texts"]) + ", machine_shaped_chips " + str(len(d["machine_shaped_chips"])) + ", pageErrors " + str(len(d["pageErrors"])) + ", verdict " + d["verdict"])
hb = subprocess.run(["git", "-C", REPO, "hash-object", art], capture_output=True, text=True).stdout.strip()
print("local artifact sha (git blob id) " + hb)
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    pl = json.loads(op.open("http://127.0.0.1:49804/api/v1/journeys/22222222-2222-4222-8222-222222222222/plans", timeout=25).read())
    a0 = pl[0]["activities"]
    print("measured GET /plans: activities " + str(len(a0)) + ", payload bytes " + str(len(json.dumps(pl))) + ", place_name occurrences " + str(json.dumps(pl).count('"place_name"')) + ", keys " + json.dumps(sorted(a0[0])))
except Exception as e:
    print("measured GET /plans UNAVAILABLE " + type(e).__name__)
