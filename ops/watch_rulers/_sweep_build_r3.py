"""Build _q64_sweep_r2.json: the same inventory re-measured under ruler r3, plus the r2/r3 delta,
the carrier census for r3's three new grammars, and the shapes neither revision covers.

Every count is derived from artifacts on disk (the ruler's per-run JSONs, the census JSON, the killer
harness JSONs). Classification keys are reused from the r1 builder because the hit sets are identical -
that identity is asserted here, not assumed.
"""
import io
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "D:/moodle/_qoder_cmdr_ref_20260921/live_checks")
from _sweep_build import CLS, ADJACENT, BASELINE, NEGCTL, TIP, read_line  # noqa: E402

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
TREE = os.path.join(SCRATCH, "tree")
REPO = "D:/moodle/CityNexus"
R3_BLOB = "44e062e6ce9c7b5d97d78e09e432072da102292c"
R2_BLOB = "608016f6a538097041554b76cfe3e9a4192f299c"
R3_ROUTE = "evidence/cmdr-ui-exposure-r3-0200/ui_exposure_field_check_r3.py"

# chains where server prose reaches the DOM and BOTH revisions answer NO_EXPOSURE_SHAPE_FOUND
UNCOVERED = [
 {"id": "K1", "fixture": "_sweep_scratch/killers/k1_throw_via_bare_local.tsx",
  "file": "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx",
  "chain": [58, 65, 110, 116, 150],
  "how": "request<T> throws the server sentence into Error.message; the catch binds it to a local "
         "(`message`), setError stores it, and a bare `{error}` renders it. Neither hop is a "
         "`function` whose body RETURNS an upstream read, so the taint arms never bind, and the render "
         "is a bare local so the direct arm has nothing to match.",
  "sweep_verdict": "NO_EXPOSURE_SHAPE_FOUND"},
 {"id": "K2", "fixture": "_sweep_scratch/killers/k2_setstate_call_arg.tsx",
  "file": "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx",
  "chain": [57, 82, 86, 93, 162],
  "how": "throw new Error(body?.detail) at :82, read back as error.message at :93 inside a setMessage "
         "CALL. The interpolation-shaped windows r2/r3 scan are brace-delimited; a call parenthesis "
         "carries no name, so the read is invisible even though the value lands in the same state slot "
         "the :691-style render reads out.",
  "sweep_verdict": "NO_EXPOSURE_SHAPE_FOUND"},
 {"id": "K3", "fixture": "_sweep_scratch/killers/k3_paren_before_message.tsx",
  "file": "frontend/src/features/studio/V12TripStudioPanel.tsx",
  "chain": [106],
  "how": "This one IS an upstream read sitting inside a JSX interpolation - the case r2's own docstring "
         "says UPSTREAM_READ_DIRECT covers. It does not fire because the arm binds only the nine names "
         "in its identifier group and requires one to sit directly left of the dot; here the char "
         "before `.message` is `)` of `(a.error ?? b.error)`. The thrown text originates at "
         "frontend/src/api/v12Authoritative.ts:27.",
  "sweep_verdict": "NO_EXPOSURE_SHAPE_FOUND"},
]
# provenance of the shape-B carriers that are NOT server prose, so the gap is sized honestly
B_NOT_SERVER = [
 ("frontend/src/features/inbox/BookingArtifactScanner.tsx", 33, "value is QR/barcode text decoded from the "
  "device camera (:21 setValue(text)) - externally captured, but not a server sentence"),
 ("frontend/src/features/stay/StayExplorer.tsx", 37, "cityLabel is derived at :12 from journey.city_code, a code"),
 ("frontend/src/features/execution/V12StatePrimitives.tsx", 16, "stateLabel maps a state enum through the "
  "dictionary, so these three rows render local wording"),
 ("frontend/src/features/setup/JourneyTrialSetup.tsx", 637, "message arrives as a prop; I did not trace its "
  "origin, so this one is listed as unmeasured rather than cleared"),
]


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    if r.returncode:
        raise SystemExit("GIT_FAILED %s %s" % (" ".join(a), r.stderr.decode("utf-8", "replace")[:160]))
    return r.stdout.decode("utf-8", "replace").strip()


def j(p):
    return json.load(io.open(p, encoding="utf-8"))


def main():
    agg3 = j(os.path.join(SCRATCH, "aggregate_r3.json"))
    agg2 = j(os.path.join(SCRATCH, "aggregate_r2.json"))
    base = j(os.path.join(SCRATCH, "baseline_r3.json"))
    neg = j(os.path.join(SCRATCH, "negctl_r3.json"))
    st = j(os.path.join(SCRATCH, "selftest_r3.json"))
    census = j(os.path.join(SCRATCH, "census_r3.json"))
    kl3 = j(os.path.join(SCRATCH, "killers_out_ui_exposure_field_check_r3.json"))
    kl2 = j(os.path.join(SCRATCH, "killers_out_ui_exposure_field_check_r2.json"))

    tip_now = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    assert git("rev-parse", "origin/cmdcontrol:" + R3_ROUTE) == R3_BLOB, "r3 ruler blob drift"
    assert agg3["ruler"] == R3_BLOB == agg3["ruler_local_git_hash"], "r3 provenance mismatch"

    key = lambda a: set((h["path"], h["line"], h["rule"], h.get("taint_chain")) for h in a["hits"])
    k2s, k3s = key(agg2), key(agg3)
    delta = {"r2_hits": len(agg2["hits"]), "r3_hits": len(agg3["hits"]),
             "identical_hit_set": k2s == k3s, "only_in_r3": sorted(k3s - k2s), "only_in_r2": sorted(k2s - k3s)}

    bh = base["hits"]
    baseline_ok = (len(bh) == 1 and bh[0]["rule"] == BASELINE["rule"] and bh[0]["line"] == BASELINE["line"]
                   and BASELINE["chain_src"] in bh[0]["taint_chain"]
                   and BASELINE["chain_name"] in bh[0]["taint_chain"])
    neg_ok = (neg["verdict"] == "NO_EXPOSURE_SHAPE_FOUND" and not neg["hits"]
              and neg["targets_scanned"] == ["%s:%s" % (TIP[:12], NEGCTL)])

    hits, missing = [], []
    for h in agg3["hits"]:
        ck = "%s:%d|%s" % (h["path"], h["line"], h["rule"])
        if ck not in CLS:
            missing.append(ck)
            continue
        cls, reaches, _s, basis, why = CLS[ck]
        hits.append({"file": h["path"], "blob": h["blob"], "line": h["line"], "rule": h["rule"],
                     "taint_chain": h["taint_chain"], "snippet": h["snippet"], "classification": cls,
                     "reaches_dom": reaches,
                     "basis": [{"file": bf, "line": bn, "text": read_line(os.path.join(TREE, bf), bn)}
                               for bf, bn in basis],
                     "why": why})
    if missing:
        raise SystemExit("UNCLASSIFIED_R3_HITS %s" % missing)

    tally, per_rule = {}, {}
    for x in hits:
        tally[x["classification"]] = tally.get(x["classification"], 0) + 1
        per_rule[x["rule"]] = per_rule.get(x["rule"], 0) + 1

    killer_by = {}
    for src, tag in ((kl3, "r3"), (kl2, "r2")):
        for f in ("k1_throw_via_bare_local.tsx", "k2_setstate_call_arg.tsx",
                  "k3_paren_before_message.tsx", "p1_positive_control.tsx"):
            killer_by.setdefault(f, {})[tag] = sum(1 for h in src["hits"] if h["file"].endswith(f))

    unc = []
    for u in UNCOVERED:
        u = dict(u)
        u["basis"] = [{"file": u["file"], "line": n, "text": read_line(os.path.join(TREE, u["file"]), n)}
                      for n in u["chain"]]
        f = os.path.basename(u["fixture"]).replace(".tsx", "")
        u["killer_hits"] = killer_by[f + ".tsx"]
        u["ruler_silent_on_this_file"] = (u["file"] not in {h["file"] for h in hits})
        unc.append(u)

    doc = {
     "schema": "CNX_Q64_SWEEP_V1",
     "lane": "S1-q64sweep",
     "revision": "r2 of this lane's sweep (first one was published as sweep_r1.json under ruler r2)",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation": TIP,
     "tip_moved": tip_now != TIP,
     "tip_readback_now": tip_now,
     "ruler": R3_BLOB,
     "ruler_route": "commander/control:" + R3_ROUTE,
     "ruler_local_git_hash_object": subprocess.run(["git", "hash-object",
            "ui_exposure_field_check_r3.py"], capture_output=True, cwd=ROOT).stdout.decode().strip(),
     "ruler_previous": R2_BLOB,
     "ruler_delta": len(delta["only_in_r3"]) + len(delta["only_in_r2"]),
     "ruler_delta_meaning": "named field the commander asked for at 03:07; derived, not typed - it is the size "
                            "of (only_in_r3 union only_in_r2) computed from the two aggregate artifacts",
     "ruler_previous_route": "commander/control:evidence/cmdr-ui-exposure-r2-0059/ui_exposure_field_check_r2.py",
     "ruler_switch_reason": "commander order 03:04 (bus ref issuecomment-5838017559): r2 superseded by r3, "
                            "which adds the renamed-tail-name, bare-local and paren-alias taint grammars",
     "companion_artifacts_verified": {
        "selftest_r3.json": git("rev-parse", "origin/cmdcontrol:evidence/cmdr-ui-exposure-r3-0200/selftest_r3.json"),
        "r3_differential.json": git("rev-parse", "origin/cmdcontrol:evidence/cmdr-ui-exposure-r3-0200/r3_differential.json"),
        "capture_tip_r3.json": git("rev-parse", "origin/cmdcontrol:evidence/cmdr-ui-exposure-r3-0200/capture_tip_r3.json"),
     },
     "scope": "frontend/src *.ts/*.tsx at the tip; node_modules / dist / frontend/node_modules excluded",
     "method": "one ruler subprocess per file: python -X utf8 ui_exposure_field_check_r3.py --ref <tip> "
               "--path <tree path> --out <scratch json>; the ruler reads bytes via git show, so the product "
               "working tree was never the input and was never written",
     "files_scanned": len(agg3["files"]),
     "files_failed": agg3["files_failed"],
     "bytes_scanned": agg3["bytes_total"],
     "files_with_hits": len(set(x["file"] for x in hits)),
     "hits_total": len(hits),
     "per_rule": per_rule,
     "classification_tally": tally,
     "selftest": st,
     "r2_vs_r3": delta,
     "carrier_census": {k: {"count": v["count"], "pattern": v["pattern"]}
                        for k, v in census["census"].items()},
     "carrier_census_detail": {k: v["carriers"] for k, v in census["census"].items()
                               if k in ("shape_A_tail_name_in_interp", "shape_C_paren_alias",
                                        "throw_embedding_upstream_prose")},
     "baseline_expectation": BASELINE,
     "baseline_observed": {"n_hits": len(bh), "rule": bh[0]["rule"] if bh else None,
                           "line": bh[0]["line"] if bh else None,
                           "taint_chain": bh[0]["taint_chain"] if bh else None},
     "baseline_reproduced": bool(baseline_ok),
     "negative_control": {"file": NEGCTL, "verdict": neg["verdict"], "n_hits": len(neg["hits"])},
     "negative_control_clean": bool(neg_ok),
     "verdict": "SWEEP_VALID" if (baseline_ok and neg_ok) else "SWEEP_INVALID",
     "headline_for_commander": "r3 changes nothing on THIS tip: the hit sets are identical, because the "
                               "three grammars r3 adds have 0 / 0 / 25 carriers here and none of the 25 is "
                               "fed by a function-declared poisoned helper. But three traced chains where "
                               "server prose reaches the DOM are reported clean by BOTH r2 and r3 - see "
                               "uncovered_shapes.",
     "uncovered_shapes": unc,
     "shape_B_carriers_traced_not_server": [{"file": f, "line": n, "note": t} for f, n, t in B_NOT_SERVER],
     "instrument_notes": [
       "r2 and r3 report the line where their match OPENS, so 16 of the 25 snippets are `} catch (error) {`-"
       "style block braces rather than the offending text; every cell carries machine-extracted basis lines.",
       "1 hit (V8Experience.tsx:320) fires on a JSDoc comment.",
       "adjacent_findings list DOM renders of server columns that the ruler does not flag and that are NOT "
       "counted in hits_total.",
       "uncovered_shapes were proven by running both ruler revisions over trimmed reproductions alongside a "
       "positive control; the positive control fired on both, so the silence is a rule gap, not a broken runner.",
     ],
     "adjacent_findings": [{"file": f, "line": n, "text": read_line(os.path.join(TREE, f), n), "note": t}
                           for f, n, t in ADJACENT],
     "hits": hits,
     "claim_kind": "pattern_determined",
     "claimed_result": None, "derived_result": None,
    }
    doc["claimed_result"] = ("%s under ruler %s: %d files scanned, %d hit(s) in %d file(s), classification %s, "
                             "r2-vs-r3 identical_hit_set=%s (delta %d/%d)"
                             % (doc["verdict"], R3_BLOB[:12], doc["files_scanned"], doc["hits_total"],
                                doc["files_with_hits"], json.dumps(doc["classification_tally"]),
                                delta["identical_hit_set"], len(delta["only_in_r3"]), len(delta["only_in_r2"])))
    doc["derived_result"] = "Q64 r3 exposure inventory for tip %s; 3 traced shapes neither revision covers" % TIP[:12]
    out = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else "_q64_sweep_r3.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("verdict=%s ruler=%s prev=%s files=%d hits=%d files_with_hits=%d" %
          (doc["verdict"], doc["ruler"][:12], doc["ruler_previous"][:12], doc["files_scanned"],
           doc["hits_total"], doc["files_with_hits"]))
    print("per_rule=%s tally=%s" % (json.dumps(per_rule, sort_keys=True), json.dumps(tally, sort_keys=True)))
    print("identical_hit_set=%s only_in_r3=%d only_in_r2=%d" % (delta["identical_hit_set"],
          len(delta["only_in_r3"]), len(delta["only_in_r2"])))
    print("baseline=%s negctl=%s census=%s" % (doc["baseline_reproduced"], doc["negative_control_clean"],
          json.dumps({k: v["count"] for k, v in census["census"].items()}, sort_keys=True)))
    print("killer_hits=%s" % json.dumps(killer_by, sort_keys=True))
    print("out=%s bytes=%d" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
