"""ORD-0553 r3 -- recompute every number the delivery block will quote, straight out of the artifacts.

Nothing in this file is typed by hand from memory: each figure is read from the JSON the instrument wrote
(this session), from `git` on the lane's own worktree, or from the publisher's receipt lines. The block
renderer then places those computed values; a number that is not in the artifacts is not in the block.

Writes only one file: _facts_r3.json.
"""
import json
import os
import re
import subprocess

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
R2 = r"D:/moodle/_qoder_cmdra_ord0553_r2_20261003"
WT = os.path.join(R2, "wt")
TIP = "0413e55634e9c6953ea88a4b01a17b8afd7ac88a"
R2HEAD = "1abc280a3d4b4bbb0bf6d9197322a5f4afc2697c"
ROUT = "/v8/authoritative"
ROUT_PANEL = "v12-authoritative-panel"
DIRTY = ("ARRIVED", "COMPLETED", "ACTIVE", "PLANNED", "ROUTE", "PROGRESS", "SKIPPED", "EN_ROUTE")


def git(*args):
    return subprocess.run(("git", "-C", WT) + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ctx(path):
    d = load(path)
    hits = d["hits"]
    return {
        "file": os.path.basename(path), "base": d["base"], "locale": d["locale"],
        "entry": d["entryAssets"], "doc_chars": d["docChars"],
        "painted_nodes": len(hits), "tokens": d["paintedTokens"],
        "dirty_nodes": sum(1 for h in hits if h["token"] in DIRTY),
        "dirty": {t: sum(1 for h in hits if h["token"] == t) for t in d["paintedTokens"] if t in DIRTY},
        "dirty_slots": sorted({h["cls"] or h["tag"] for h in hits if h["token"] in DIRTY}),
        "dirty_standalone": sum(1 for h in hits if h["token"] in DIRTY and h["standalone_line"]),
        "server_paths": {t: v["server_field_paths"] for t, v in
                         [(x["token"], x) for x in d["traced"] if x["token"] in DIRTY]},
        "panel_chars": len(d["panels"].get(ROUT_PANEL) or ""),
        "panel_present": bool(d["panels"].get(ROUT_PANEL)),
        "panel_text_head": (d["panels"].get(ROUT_PANEL) or "")[:120],
        "page_errors": len(d["pageErrors"]),
    }


def sweep(path):
    d = load(path)
    a = d["perRoute"][ROUT]
    return {
        "file": os.path.basename(path), "base": d["base"], "locale": d["locale"],
        "entry": d["entryAssets"], "screen_nodes": a["totalTextNodesScanned"],
        "screen_tokens": [i["token"] for i in a["items"]],
        "total": d["totalPaintedHits"], "distinct": d["distinctTokens"],
        "screen_chars": a["documentChars"],
        "routes_with_hits": d["routes_with_paints"] if "routes_with_paints" in d else d["routesWithPaintedMachineText"],
        "page_errors": len(d["pageErrors"]),
    }


def ruler(path):
    d = load(path)
    if "suites" not in d:
        return {"file": os.path.basename(path), "not_a_playwright_report": True,
                "keys": sorted(d.keys())[:12], "bytes": os.path.getsize(path)}
    arms = []
    for suite in d.get("suites", []):
        for spec in suite.get("specs", []):
            arms.append((spec["title"], spec["tests"][0]["results"][0]["status"]))
    return {"file": os.path.basename(path), "arms": arms, "stats": d["stats"]}


facts = {"tip": TIP, "tip_readback": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD")}

facts["blob_equality"] = {f: {"tip": git("rev-parse", "%s:%s" % (TIP, f)),
                              "r2": git("rev-parse", "%s:%s" % (R2HEAD, f))}
                          for f in ("frontend/src/i18n/LocaleContext.tsx",
                                    "frontend/src/lib/displayVocabulary.ts",
                                    "frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx",
                                    "frontend/e2e/qoder-45d25bfb-authoritative-status-vocabulary-r1.spec.ts")}
facts["r2_parent"] = git("rev-parse", "%s^" % R2HEAD)
facts["r2_numstat"] = [l.split("\t") for l in git("diff", "--numstat", facts["r2_parent"], R2HEAD).splitlines()
                       if l.split("\t") and l.split("\t")[2].startswith("frontend/src")]
facts["build_info"] = load(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_cmdra_0553_r2_info.json")

facts["ctx"] = {k: ctx(os.path.join(R1, "_evidence", k)) for k in (
    "r3_ctx_en_asis_49851.json", "r3_ctx_en_asis_49852.json",
    "r3_ctx_en_arrived_49851.json", "r3_ctx_en_arrived_49852.json",
    "r3_ctx_zh_arrived_49851.json")}
facts["sweep"] = {}
for k in sorted(os.listdir(os.path.join(R1, "_evidence"))):
    if not (k.startswith("r3_sweep_") and k.endswith(".json")):
        continue
    p = os.path.join(R1, "_evidence", k)
    if os.path.getsize(p) > 500:
        try:
            facts["sweep"][k] = sweep(p)
        except Exception as e:
            facts["sweep"][k] = {"error": type(e).__name__, "bytes": os.path.getsize(p)}
facts["store_state"] = load(os.path.join(R1, "_evidence", "r3_store_state_after_drive.json"))
facts["slots"] = {}
for k in ("r3_slots_en_49851.json", "r3_slots_en_49852.json", "r3_slots_zh_49851.json"):
    p = os.path.join(R1, "_evidence", k)
    if os.path.isfile(p):
        d = load(p)
        facts["slots"][k] = {"file": os.path.basename(p), "base": d["base"], "locale": d["locale"],
                             "entry": d["entryAssets"], "panel_present": d["read"]["panelPresent"],
                             "button": d["read"]["footerButton"], "values": d["read"]["stateValues"],
                             "rows": ["%s=%s" % (r["title"], r["status"]) for r in d["read"]["rows"]],
                             "page_errors": len(d["pageErrors"])}
facts["ruler_at_tip"] = ruler(os.path.join(R1, "_evidence", "r3_ruler_at_tip_0413e556.json"))

facts["r2_sweeps"] = {k: sweep(os.path.join(R2, "_evidence", k)) for k in
                      ("r2base_sweep_en.json", "r2_sweep_en.json", "r2base_sweep_zh.json", "r2_sweep_zh.json")}
facts["r2_label"] = load(os.path.join(R2, "_evidence", "r2_label_en.json"))["arms"]
facts["r2_rulers"] = {k: ruler(os.path.join(R2, "_evidence", k)) for k in
                      ("statusq_r2_prefix_red.json", "statusq_r2_green.json",
                       "statusq_r2_mC.json", "statusq_r2_mD.json")}
facts["r2_verbatim"] = {}
for k in ("statusq_r2_prefix_red_verbatim.txt", "statusq_r2_green_verbatim.txt",
          "statusq_r2_mC_verbatim.txt", "statusq_r2_mD_verbatim.txt"):
    txt = open(os.path.join(R2, "_evidence", k), encoding="utf-8", errors="replace").read()
    fails = len(re.findall(r"^\s*x\s+\d+", txt, re.M))
    oks = len(re.findall(r"^\s*ok\s+\d+", txt, re.M))
    dur = re.findall(r"\d+ passed \((\d+)ms\)|(\d+) failed", txt)
    facts["r2_verbatim"][k] = {"arms_failed": fails, "arms_passed": oks,
                               "tail_lines": [l for l in txt.splitlines() if "failed" in l or "passed (" in l][-2:]}

rows = [json.loads(l) for l in open(os.path.join(R2, "_publish_manifest.jsonl"), encoding="utf-8")]
facts["r2_publish"] = {"rows": len(rows), "created": sum(1 for r in rows if r["decision"] == "CREATED"),
                       "skip": sum(1 for r in rows if r["decision"] == "SKIP_IDENTICAL"),
                       "blobs": {r["remote_path"].split("/")[-1]: r["blob"] for r in rows},
                       "manifest_bytes": os.path.getsize(os.path.join(R2, "_publish_manifest.jsonl"))}
facts["inventory_bytes"] = os.path.getsize(os.path.join(R1, "_evidence", "r3_import_and_assertion_inventory.txt"))
facts["db_sizes"] = {p: os.path.getsize(os.path.join(R1, p)) for p in ("_cmdra_0553.db", "_cmdra_0553p.db")}
facts["seed_bytes"] = os.path.getsize(r"D:/moodle/_qoder_cmdr_priv_0437seed.db")

out = os.path.join(R1, "_facts_r3.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(facts, f, ensure_ascii=False, indent=1)
print(json.dumps({k: (len(json.dumps(v)) if not isinstance(v, (str, int)) else v) for k, v in facts.items()},
                 ensure_ascii=False, indent=1))
print("facts bytes", os.path.getsize(out))
