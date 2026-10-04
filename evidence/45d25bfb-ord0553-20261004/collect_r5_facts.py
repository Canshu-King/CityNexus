"""ORD-0553 census r5 -- turn the two arm readings into the table the commander can turn into orders.

Classes are decided by measurement, not by reading code: a painted machine token is a *server word* when
that exact string was answered by the backend in a response this walk received (the path is printed), and a
*style word* when it appears in no response body at all.  Everything is computed from the two JSON files;
nothing here is typed from memory.
"""
import json
import os

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
EV = os.path.join(R1, "_evidence")
FILES = {"en": "r5_census_en_49861.json", "zh": "r5_census_zh_49861.json"}

out = {"files": {}, "arms": {}}
for arm, name in FILES.items():
    path = os.path.join(EV, name)
    if not os.path.isfile(path):
        out["files"][name] = "MISSING"
        continue
    d = json.load(open(path, encoding="utf-8"))
    out["files"][name] = os.path.getsize(path)
    server = {t: c for t, c in d["census"].items() if c["provenance"] == "server-answer"}
    style = {t: c for t, c in d["census"].items() if c["provenance"] != "server-answer"}
    rows = []
    for t, c in sorted(server.items(), key=lambda kv: -sum(kv[1]["routes"].values())):
        rows.append({"token": t, "kind": c["kind"], "hits": sum(c["routes"].values()),
                     "routes": c["routes"], "slots": sorted(c["slots"].keys()),
                     "fields": c["server_answer_fields"][:3]})
    out["arms"][arm] = {
        "entry": d["entryAssets"], "totals": d["totals"], "api_responses": d["apiResponses"],
        "page_errors": len(d["pageErrors"]),
        "server_word_tokens": sorted(server.keys()),
        "style_word_tokens": sorted(style.keys()),
        "server_word_rows": rows,
        "routes_with_hits": sorted([r for r, v in d["perRoute"].items() if v["hits"]]),
    }

io_path = os.path.join(R1, "_facts_r5.json")
with open(io_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
for arm, a in out["arms"].items():
    print("== %s entry=%s hits=%s distinct=%s server=%s style=%s pageErrors=%s" % (
        arm, a["entry"], a["totals"]["painted_hits"], a["totals"]["distinct_tokens"],
        a["totals"]["server_answer_tokens"], a["totals"]["style_only_tokens"], a["page_errors"]))
    for r in a["server_word_rows"][:10]:
        print("   %-22s x%d  %s  routes=%s  fields=%s" % (r["token"], r["hits"], ",".join(r["slots"])[:44],
                                                          list(r["routes"].keys())[:3], r["fields"][:1]))
print("facts bytes", os.path.getsize(io_path))
