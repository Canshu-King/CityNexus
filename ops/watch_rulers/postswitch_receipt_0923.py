"""Post-switch A-E + G + F + A-9 evidence for the 13:02 dist swap.

The deploy run crashed *after* installing index.html on a KeyError in my own F arm, so the switch itself
was never evidenced.  This recomputes it with the gauge's own predicates, taking the previous generation
from dist_bak_130203 (the real anchor the tool saved before switching).
"""
import importlib.util
import json
import pathlib
import time

spec = importlib.util.spec_from_file_location("db", pathlib.Path(__file__).with_name("deploy_bundle.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

DECLARED_NO_PRECACHE = {"sw.js": "hand-written service worker, no workbox precacheAndRoute array"}

SERVE = pathlib.Path("D:/moodle/_qoder_preview_20260920/dist")
BAK = pathlib.Path("D:/moodle/_qoder_preview_20260920/dist_bak_130203")
AUTH = r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt"
TUN = pathlib.Path(r"D:\moodle\_qoder_preview_20260920\run\tunnel_url.txt").read_text(encoding="utf-8").strip()


def rep(ref, base=None, af=None):
    return m.repeated_verdict(ref, m.expect_ct_for(ref), SERVE, base=base, auth_file=af, times=2)


def slim(v):
    return {"verdict": v["verdict"], "statuses": v["statuses"],
            "ct": [p.get("content_type") for p in v["probes"]],
            "cc": [p.get("cache_control") for p in v["probes"]],
            "bytes": [p.get("body_size") for p in v["probes"]],
            "disk": [p.get("disk_bytes") for p in v["probes"]],
            "sha_eq_disk": [p.get("sha256") == p.get("disk_sha256") for p in v["probes"]],
            "error": [p.get("error") for p in v["probes"]]}


new_refs = m.asset_refs((SERVE / "index.html").read_text(encoding="utf-8"))
old_refs = m.asset_refs((BAK / "index.html").read_text(encoding="utf-8"))
out = {"what": "POST-SWITCH A-E + G + F + A-9 for the 13:0x dist swap to index-CrAwWm5f.js",
       "why": "deploy_bundle.py crashed after installing index.html (KeyError in my own F arm), so the "
              "switch had no receipt; recomputed here with the gauge's own predicates",
       "previous_generation_anchor": str(BAK), "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
       "served_refs": new_refs, "previous_generation_refs": old_refs}

out["A_previous_generation"] = [{"ref": r, **slim(rep(r))} for r in old_refs]
idx = (SERVE / "index.html").read_text(encoding="utf-8")
out["B_index_claims_only_new"] = {"new_all_present": all(r in idx for r in new_refs),
                                  "old_js_still_named": [r for r in old_refs if r.endswith(".js") and r in idx]}
out["C_new_assets"] = [{"ref": r, **slim(rep(r))} for r in new_refs]
out["D_service_workers"] = []
for name in ("sw.js", "v10-sw.js"):
    v = slim(rep("/" + name))
    v["name"] = name
    v["disk_matches"] = [p.get("sha256") == p.get("disk_sha256") for p in rep("/" + name)["probes"]]
    out["D_service_workers"].append(v)
out["G_precache"] = []
for name in ("sw.js", "v10-sw.js"):
    urls = m.precache_urls((SERVE / name).read_text(encoding="utf-8", errors="replace"))
    rows = []
    for u in urls:
        ref = u if u.startswith("/") else "/" + u
        rows.append({"ref": ref, **slim(rep(ref))})
    # mirror the tool's rule exactly: a DECLARED hand-written sw with no precache array is neither a pass
    # nor a failure - g_green needs >=1 sw actually GREEN and none RED.
    declared = (not urls and name in DECLARED_NO_PRECACHE)
    out["G_precache"].append({"sw": name, "urls_found": len(urls),
                              "declared_no_precache_array": DECLARED_NO_PRECACHE.get(name) if declared else None,
                              "verdict": "DECLARED_NO_PRECACHE_ARRAY" if declared else (
                                  "GREEN" if urls and all(r["verdict"] == "GREEN" for r in rows) else "RED"),
                              "reds": [r["ref"] for r in rows if r["verdict"] != "GREEN"]})
out["H_previous_generation_full"] = [{"ref": r, **slim(rep(r))} for r in old_refs]
out["F_surfaces"] = {}
for label, base, af in (("local_4781", "http://127.0.0.1:4781", None),
                        ("proxy_4782", "http://127.0.0.1:4782", AUTH),
                        ("public_tunnel", TUN, AUTH)):
    rows = [{"ref": r, **slim(rep(r, base, af))} for r in new_refs + ["/"]]
    out["F_surfaces"][label] = {"all_green": all(r["verdict"] == "GREEN" for r in rows),
                                "reds": [r["ref"] for r in rows if r["verdict"] != "GREEN"], "rows": rows}

DECLARED_NO_PRECACHE = {"sw.js": "hand-written service worker, no workbox precacheAndRoute array"}

arms = {
    "A": all(r["verdict"] == "GREEN" for r in out["A_previous_generation"]),
    "B": out["B_index_claims_only_new"]["new_all_present"] and not out["B_index_claims_only_new"]["old_js_still_named"],
    "C": all(r["verdict"] == "GREEN" for r in out["C_new_assets"]),
    "D": all(r["verdict"] == "GREEN" and all(r["disk_matches"]) for r in out["D_service_workers"]),
    "G": any(p["verdict"] == "GREEN" for p in out["G_precache"])
       and not any(p["verdict"] == "RED" for p in out["G_precache"]),
    "H": all(r["verdict"] == "GREEN" for r in out["H_previous_generation_full"]),
    "F": all(v["all_green"] for v in out["F_surfaces"].values()),
}
out["arm_summary"] = arms
out["overall"] = "GREEN" if all(arms.values()) else "RED"
dest = pathlib.Path(__file__).with_name("receipts") / f"deploy_postswitch_{time.strftime('%m%d_%H%M%S')}.json"
dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
print("arms:", json.dumps(arms))
print("overall:", out["overall"])
for key in ("C", "D", "G", "F"):
    if not arms[key]:
        print("RED detail", key, json.dumps(out[key if key != 'D' else 'D_service_workers'] if key == 'D' else (out['G_precache'] if key == 'G' else out['F_surfaces']), ensure_ascii=False)[:900])
print("wrote", dest)
