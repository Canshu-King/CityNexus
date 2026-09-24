"""ORD-0267 step 1, receipt fixed: my driver looked for the wrong file names.

`q267_probe.js` appends the phase to `--out` itself, so it wrote `probe_up_up.json` /
`probe_down_down.json` while my driver looked for `probe_up.json` and recorded `{"missing": true}`.
The readings exist and are good; the assembly was wrong. This rewrites the receipt from the files that
were actually produced, names the mistake inside the artifact, and changes no reading.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0267_20260923")
OUT = WORK / "genB_baseline"
up = json.loads((OUT / "probe_up_up.json").read_text(encoding="utf-8"))
down = json.loads((OUT / "probe_down_down.json").read_text(encoding="utf-8"))
old = json.loads((OUT / "ord0267b_baseline.json").read_text(encoding="utf-8"))


def summarise(doc):
    rows = []
    for s in doc.get("steps") or []:
        f = s.get("facts") or {}
        r = s.get("registrations") or {}
        c = s.get("cache_state") or {}
        rows.append({"case": s.get("case"), "path": s.get("path"), "navigation": s.get("navigation"),
                     "url_after": f.get("url"), "controlled": f.get("controlled"),
                     "controller_script": r.get("controller_script"), "app_mounted": f.get("app_mounted"),
                     "registrations": r.get("count"), "cache_names": c.get("cache_names"),
                     "precache_entries": c.get("precache_entries"),
                     "precache_has_index_html": c.get("precache_has_index_html"),
                     "precache_sample_paths": c.get("precache_sample_paths")})
    return rows


receipt = dict(old)
receipt["at"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
receipt["up_phase"] = {"at": up.get("at"), "phase": up.get("phase"), "cases": summarise(up)}
receipt["down_phase"] = {"at": down.get("at"), "phase": down.get("phase"), "cases": summarise(down)}
receipt["correction"] = {
    "what_was_wrong": "the driver looked for probe_up.json / probe_down.json and recorded "
                      '{\"missing\": true}; q267_probe.js appends the phase to --out itself, so the '
                      "real files were probe_up_up.json / probe_down_down.json",
    "what_changed": "assembly only - no reading was retaken, no number altered",
    "instrument_line": "q267b_baseline.py:probe() now receives the file the probe actually writes"}

b = [c for c in receipt["down_phase"]["cases"]]
installed = [c for c in b if str(c["case"]).startswith("B")]
cold = [c for c in b if str(c["case"]).startswith("C")]
receipt["finding"] = {
    "one_line": "On the current generation (tip c79e2b4f) the ORD-0267 symptom survives only for a client "
                "that never installed the worker; for a client that did, all three offline navigations are "
                "answered 200 by the workbox precache - so the shaping has to be re-cut, not re-argued.",
    "installed_client_offline": {
        "cases_measured": len(installed),
        "all_answered_200": all((c["navigation"] or {}).get("ok") and (c["navigation"] or {}).get("status") == 200
                                for c in installed),
        "all_controlled": all(c["controlled"] for c in installed),
        "all_mounted": all(c["app_mounted"] for c in installed),
        "precache_entries": sorted({c["precache_entries"] for c in installed}),
        "paths": [c["path"] for c in installed]},
    "cold_client_offline": {
        "cases_measured": len(cold),
        "all_chrome_error": all("chrome-error" in (c["url_after"] or "") for c in cold),
        "all_uncontrolled": all(c["controlled"] is False for c in cold),
        "errors": sorted({(c["navigation"] or {}).get("error") for c in cold}),
        "paths": [c["path"] for c in cold]},
    "superseded_reading": "my 2026-09-23 shaping (evidence/ord0267-laneB-shaping) recorded CacheStorage "
                          "== [] and chrome-error for the INSTALLED client; that was true on d2665e2 and "
                          "is no longer true here - ORD-0268 (removing the hand-written v10-shell "
                          "precache entry) is what changed it",
    "what_this_leaves_for_0267": "a cold client has no bytes to be served from, so 'render something' is "
                                 "not achievable by the product at that moment; the version of this that "
                                 "the product CAN be responsible for is a first visit whose precache "
                                 "install only partially succeeded - measured next (step 2)"}
p = OUT / "ord0267b_baseline_v2.json"
p.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print(json.dumps(receipt["finding"], ensure_ascii=False, indent=1)[:1500])
print("->", p.name)
