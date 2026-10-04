"""ORD-0553 r5 -- build the fleet census: painted machine words vs the words the backend actually answers.

Why a second pass: reading every response body over CDP inside the browser walk is what stalled the earlier
runs (measured: 420 s and no file).  So the walk keeps only endpoint metadata, and this pass replays those
same endpoints against the same backend (:8752, the one my launcher owns) over plain HTTP, indexes every
machine-shaped string the server answered, and classifies each painted token by that index.

Outputs: _evidence/r5_census_{en,zh}_49861.json (one arm per file) and _facts_r5.json for the block.
"""
import io
import json
import os
import re
import urllib.error
import urllib.request

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
EV = os.path.join(R1, "_evidence")
BACKEND = "http://127.0.0.1:8752"
ARMS = {"en": "r5_walk_en_49861.json", "zh": "r5_walk_zh_49861.json"}
SHAPES = [
    ("UPPER_SNAKE", re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b")),
    ("ALLCAPS_WORD", re.compile(r"\b[A-Z]{4,}\b")),
    ("LOWER_SNAKE_KEY", re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b")),
    ("IANA_ZONE", re.compile(r"\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)/[A-Za-z_]+(?:/[A-Za-z_]+)?\b")),
]
ALLOW = {"UTC", "GMT", "PDF", "ID", "URL", "API", "AI", "GPS", "OSM", "OK", "FAQ", "COPILOT"}
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))

server_index = {}
endpoints = []


def shape_of(tok):
    for kind, rx in SHAPES:
        if rx.fullmatch(tok):
            if kind == "ALLCAPS_WORD" and (tok in ALLOW or "_" in tok):
                continue
            return kind
    return None


def index_strings(v, path):
    if isinstance(v, str):
        if 1 < len(v) <= 64:
            for m in re.findall(r"[A-Za-z][A-Za-z0-9_/.:-]{1,63}", v):
                tok = m if shape_of(m) else (m.split("/")[-1] if "/" in m and shape_of(m.split('/')[-1]) else None)
                if tok and shape_of(tok):
                    lst = server_index.setdefault(tok, [])
                    if len(lst) < 4 and path not in lst:
                        lst.append(path)
        return
    if isinstance(v, list):
        for i, x in enumerate(v[:40]):
            index_strings(x, "%s[%d]" % (path, i))
        return
    if isinstance(v, dict):
        for k, x in v.items():
            index_strings(x, "%s.%s" % (path, k))


def replay(path):
    url = BACKEND + path
    try:
        with op.open(url, timeout=25) as r:
            body = r.read()
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except Exception:
        return None, b""


seen_paths = set()
for arm, walk_name in ARMS.items():
    p = os.path.join(EV, walk_name)
    if not os.path.isfile(p):
        raise SystemExit("ABORT: missing walk %s" % p)
    seen_paths.update(x["url"].split("?")[0] for x in json.load(io.open(p, encoding="utf-8"))["apiResponseList"])

for path in sorted(seen_paths):
    status, body = replay(path)
    rec = {"path": path, "http_status": status, "bytes": len(body)}
    endpoints.append(rec)
    if status and 200 <= status < 300 and body:
        try:
            index_strings(json.loads(body.decode("utf-8", "replace")), path)
        except Exception as e:
            rec["parse"] = "not-json:" + type(e).__name__

facts = {"backend": BACKEND, "endpoints_replayed": len(endpoints),
         "endpoints_answered_2xx": sum(1 for e in endpoints if e["http_status"] and 200 <= e["http_status"] < 300),
         "indexed_tokens": len(server_index), "arms": {}, "endpoint_log": endpoints}
for arm, walk_name in ARMS.items():
    d = json.load(io.open(os.path.join(EV, walk_name), encoding="utf-8"))
    census = {}
    for route, r in d["perRoute"].items():
        for h in r["hits"]:
            c = census.setdefault(h["token"], {"token": h["token"], "kind": h["kind"], "routes": {},
                                               "slots": {}, "server_answer_fields": server_index.get(h["token"], []),
                                               "provenance": "server-answer" if h["token"] in server_index else "style-or-unindexed"})
            c["routes"][route] = c["routes"].get(route, 0) + 1
            c["slots"][h["cls"] or h["tag"]] = c["slots"].get(h["cls"] or h["tag"], 0) + 1
    rows = sorted(census.values(), key=lambda c: -sum(c["routes"].values()))
    server = [c for c in rows if c["provenance"] == "server-answer"]
    style = [c for c in rows if c["provenance"] != "server-answer"]
    out = {"instrument": "cmdra_0553_caps_context_r2 + _census_r5.py", "locale": arm, "base": d["base"],
           "entryAssets": d["entryAssets"], "routesWalked": d["routesWalked"],
           "totals": {"painted_hits": sum(len(r["hits"]) for r in d["perRoute"].values()),
                      "distinct_tokens": len(census), "routes_with_hits": sum(1 for r in d["perRoute"].values() if r["hits"]),
                      "server_answer_tokens": len(server), "style_only_tokens": len(style)},
           "pageErrors": d["pageErrors"], "apiResponses": d["apiResponses"],
           "census": census,
           "server_word_rows": [{"token": c["token"], "kind": c["kind"], "hits": sum(c["routes"].values()),
                                 "routes": c["routes"], "slots": sorted(c["slots"].keys()),
                                 "fields": c["server_answer_fields"][:3]} for c in server]}
    with io.open(os.path.join(EV, "r5_census_%s_49861.json" % arm), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    facts["arms"][arm] = dict(out, entry=out["entryAssets"], page_errors=len(out["pageErrors"]),
                              api_responses=out["apiResponses"],
                              server_word_tokens=sorted(c["token"] for c in server),
                              style_word_tokens=sorted(c["token"] for c in style),
                              server_word_rows=out["server_word_rows"])

with io.open(os.path.join(R1, "_facts_r5.json"), "w", encoding="utf-8") as f:
    json.dump(facts, f, ensure_ascii=False, indent=1)
print(json.dumps({k: facts[k] for k in ("endpoints_replayed", "endpoints_answered_2xx", "indexed_tokens")}, ensure_ascii=False))
for arm, a in facts["arms"].items():
    print("==", arm, a["totals"], "pageErrors", a["page_errors"])
    for r in a["server_word_rows"][:14]:
        print("   %-24s x%-3s %s | %s" % (r["token"], r["hits"], ",".join(sorted(r["routes"]))[:44], (r["fields"][:1] or ["-"])[0][:56]))
print("facts bytes", os.path.getsize(os.path.join(R1, "_facts_r5.json")))
