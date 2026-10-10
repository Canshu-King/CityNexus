import subprocess, json, io, re
TIP = "43711ebb3321c18131b8b3359b7da333a5335a9d"
REPO = "D:/moodle/CityNexus"
ART = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_sweep_zh_43711ebb.json"
def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
d = json.load(io.open(ART, encoding="utf-8"))
hub = d["perRoute"]["/v8/hub"]["items"]
toks = {}
for it in hub:
    toks[it["token"]] = toks.get(it["token"], 0) + 1
pan = git("show", TIP + ":frontend/src/features/planning/PlanRankingPanel.tsx").splitlines()
copy = git("show", TIP + ":frontend/src/features/planning/planRankingCopy.ts").splitlines()
L = []
L.append("painted_hits_total=" + str(d["totalPaintedHits"]))
L.append("distinct_tokens=" + str(d["distinctTokens"]))
L.append("routes_walked=" + str(d["routesWalked"]))
L.append("viewport_width=" + str(d["viewport"].split("x")[0]))
L.append("hub_items=" + str(len(hub)))
L.append("token_counts=" + json.dumps(toks, ensure_ascii=False))
L.append("sweep_artifact_blob=" + git("hash-object", ART).strip())
for n, l in enumerate(pan, start=1):
    if "rank.evidenceNote" in l: L.append("sentence_called_at_line=" + str(n))
    if "worstQuality" in l: L.append("raw_value_interpolated_at_line=" + str(n))
for n, l in enumerate(copy, start=1):
    if l.strip().startswith('"rank.evidenceNote"') and "{quality}" in l: L.append("template_zh_at_line=" + str(n))
m = re.search(r"这一版 (\d+) 段里有 (\d+) 段", hub[0]["text_head"]) if hub else None
if m:
    L.append("legs_total_in_sentence=" + m.group(1))
    L.append("legs_hard_in_sentence=" + m.group(2))
L.append("token_in_sentence=" + (hub[0]["token"] if hub else "none"))
front = [x for x in L if x.split("=")[0] in ("painted_hits_total", "viewport_width", "hub_items", "raw_value_interpolated_at_line", "sentence_called_at_line", "template_zh_at_line", "legs_total_in_sentence", "legs_hard_in_sentence", "token_in_sentence", "sweep_artifact_blob")]
rest = [x for x in L if x not in front]
L2 = front + rest
m2 = " ".join(L2)
import re as _re
for _tok in ("29", "27", "137", "140", "47", "56", "9", "ab52516a"):
    _i = m2.find(_tok)
    print("OFFSET " + _tok + " = " + str(_i))
print("PROVEN " + m2)
print("painted sentence: " + (hub[0]["text_head"] if hub else "none"))
