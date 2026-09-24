"""ORD-0277 / SW_REGISTRATION_GENERATION_CONTRACT offline proof (arbiter Q20 ruling, 2026-09-24T15:2x+08).

The defect this order exists for, measured rather than described: while demonstrating DEBT-3 live I added one
61-byte chunk to a build export and named it in `index.html`.  `I_pre` demanded that EVERY index-named .js
carry a `serviceWorker.register()` call, so the silent chunk read RED and `union_readiness` went BLOCKED -
a permanent red for any multi-entry frontend, and on the POST_UNION deploy path it would refuse a healthy
generation swap.  The arbiter kept it out of 0271-A on purpose: 0271-A owns predicate correctness and phase
separation, 0277 owns registration TOPOLOGY ("otherwise one gauge manages everything and nobody dares touch
it").

Offline by construction: the judge is pulled out of `deploy_bundle_v2_draft.py` by AST, and the positive
control is fed REAL bundle bytes read off disk (`sw_register_verdict` too is extracted, not imported).  No
server, no deployment, and the in-service gauge is asserted byte-unchanged in cell S2.
"""
import ast
import hashlib
import io
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "deploy_bundle_v2_draft.py")
IN_SERVICE_GAUGE = os.path.join(HERE, "deploy_bundle.py")
IN_SERVICE_GAUGE_BLOB = "149e9c6dbe6debcac92041bb192761c1cf1aa2a7"
SERVE = r"D:\moodle\_qoder_preview_20260920\dist"
OUT = os.path.join(HERE, "receipts", "ord0277_generation_contract_selftest.json")
GREEN, RED = "GREEN", "RED"
WANT_ARGS = ["rows"]


def blob_sha(raw):
    return hashlib.sha1(b"blob %d" % len(raw) + bytes(1) + raw).hexdigest()


def src():
    return io.open(DRAFT, encoding="utf-8").read()


def tree():
    return ast.parse(src())


def extract(names):
    """Compile the named top-level functions AND the named module constants into one namespace."""
    want = set(names)
    body = [n for n in tree().body
            if (isinstance(n, ast.FunctionDef) and n.name in want)
            or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in want
                                                  for t in n.targets))]
    found = set()
    for n in body:
        if isinstance(n, ast.FunctionDef):
            found.add(n.name)
        else:
            found |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    if want - found:
        raise SystemExit("ORD-0277 test cannot find in the draft: %s" % sorted(want - found))
    import re
    ns = {"re": re, "os": os, "pathlib": __import__("pathlib")}
    exec(compile(ast.Module(body=body, type_ignores=[]), DRAFT, "exec"), ns)
    return ns


def fn_span(name):
    s = src()
    t = tree()
    fn = next(n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(s, fn)


def call_of(node):
    """Best-effort textual form of a register call, used only for the unresolved-mention cell."""
    return ast.unparse(node)


def main():
    ns = extract(["_ord0277_generation_verdict", "sw_register_verdict", "strip_js_comments",
                  "SW_REGISTER_RULE"])
    decide, swv = ns["_ord0277_generation_verdict"], ns["sw_register_verdict"]
    cells = []

    def check(name, ok, detail):
        cells.append({"cell": name, "verdict": GREEN if ok else RED, "detail": detail})

    # ---- the signature and the wiring must be what this test thinks they are
    args = [a.arg for a in next(n for n in tree().body if isinstance(n, ast.FunctionDef)
                                and n.name == "_ord0277_generation_verdict").args.args]
    check("S0_judge_signature", args == WANT_ARGS, {"argnames": args})
    per_fn = {}
    for fn in [n for n in tree().body if isinstance(n, ast.FunctionDef)]:
        hits = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_ord0277_generation_verdict"]
        if hits:
            per_fn[fn.name] = len(hits)
    total = sum(per_fn.values())
    # Both real arms must go through the judge; the selftest's three synthetic controls may too.
    check("S1_both_arms_use_the_generation_judge",
          per_fn.get("preflight_before_switch", 0) >= 1 and per_fn.get("main", 0) >= 1,
          {"calls_per_function": per_fn, "total_calls": total,
           "required": {"preflight_before_switch": ">=1 (arm I_pre)", "main": ">=1 (arm I post-switch)"}})
    s = src()
    # Q21 changed HOW the per-file reading is demoted (scope mark instead of renaming the key), so this cell
    # now asserts the invariant rather than the spelling: the per-file aggregate is gone AND both sites are
    # demoted by scope, and the gate itself is the generation verdict.
    check("S2_per_file_rule_gone_and_demoted_by_scope",
          'all(x["verdict"] == "GREEN" for x in i_arms)' not in s
          and s.count("_audit_pool.append(mark_audit(v))") == 1
          and "per_file_verdict" not in s
          and s.count('v["gate"] = "generation"') == 2
          and 'i_green = bool(i_arms) and i_gen["verdict"] == "GREEN"' in s,
          {"old_aggregate_present": 'all(x["verdict"] == "GREEN" for x in i_arms)' in s,
           "preflight_site_pooled": s.count("_audit_pool.append(mark_audit(v))"),
           "key_renaming_left_behind": "per_file_verdict" in s,
           "both_sites_tagged_gate_generation": s.count('v["gate"] = "generation"'),
           "generation_is_the_gate": 'i_green = bool(i_arms) and i_gen["verdict"] == "GREEN"' in s,
           "why": "if a per-file RED can still reach the red scan, ORD-0277 is only half closed"})
    in_service = io.open(IN_SERVICE_GAUGE, "rb").read()
    check("S3_in_service_gauge_untouched", blob_sha(in_service) == IN_SERVICE_GAUGE_BLOB,
          {"blob": blob_sha(in_service), "expected": IN_SERVICE_GAUGE_BLOB, "bytes": len(in_service)})

    # ---- REAL product bytes: the entry chunk the phone is running today
    entry = os.path.join(SERVE, "assets", "index-ChOTTCvB.js")
    raw = io.open(entry, "rb").read()
    real_row = swv(raw.decode("utf-8", "replace"), "disk " + os.path.basename(entry))
    check("P1_real_entry_bundle_has_one_valid_registration",
          real_row["register_calls_parsed"] >= 1 and
          all(c["scope_ok"] and c["update_via_cache_ok"] for c in real_row["calls"]) and
          real_row["unresolved_registrations"] == 0,
          {"calls": [{k: c[k] for k in ("sw_url", "scope", "updateViaCache", "scope_ok",
                                       "update_via_cache_ok")} for c in real_row["calls"]],
           "parsed": real_row["register_calls_parsed"], "mentions": real_row["register_mentions_in_code"],
           "bundle_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()[:16]})
    silent = {"ref": "/assets/lazy-chunk.example.js", "readable": True, "calls": [], "unresolved": 0}
    g1 = decide([{"ref": "disk " + os.path.basename(entry), "readable": True,
                  "calls": real_row["calls"], "unresolved": real_row["unresolved_registrations"]}, silent])
    check("G1_multi_entry_real_owner_plus_silent_chunk_is_GREEN", g1["verdict"] == GREEN,
          {"verdict": g1["verdict"], "owners": g1["owner_refs"], "reason": g1["reason"][:150],
           "rule": "arbiter M1: index-a registers, index-b does not => GREEN"})
    # what the shipped per-file rule did with the same two rows - computed, not asserted from memory
    per_file = [swv(raw.decode("utf-8", "replace"), "a"), swv("const x=1;", "silent-chunk")]
    check("G2_the_old_per_file_rule_would_have_blocked_this_generation",
          all(x["verdict"] == RED for x in per_file[1:]) and per_file[0]["verdict"] == GREEN,
          {"owner_per_file": per_file[0]["verdict"], "silent_per_file": per_file[1]["verdict"],
           "meaning": "the shape that produced union_readiness=BLOCKED on a healthy export at 12:3x"})

    bad = {"ref": "/assets/second-entry.example.js", "readable": True,
           "calls": [{"sw_url": "/sub/sw.js", "scope": "/app/", "updateViaCache": "all",
                      "scope_ok": False, "update_via_cache_ok": False}], "unresolved": 0}
    g3 = decide([{"ref": "owner", "readable": True, "calls": real_row["calls"], "unresolved": 0}, bad])
    check("G3_secondary_dangerous_registration_is_RED", g3["verdict"] == RED,
          {"reason": g3["reason"][:170], "rule": "arbiter M2: a second ownership claim must not be ignored"})
    g4 = decide([silent, {"ref": "/assets/other.js", "readable": True, "calls": [], "unresolved": 0}])
    check("G4_zero_registrations_still_RED", g4["verdict"] == RED and "NO_SERVICE_WORKER" in g4["reason"],
          {"reason": g4["reason"][:140], "rule": "the killer that made arm I exist stays armed"})
    unres = {"ref": "/assets/unresolved.example.js", "readable": True, "calls": [], "unresolved": 1}
    g5 = decide([{"ref": "owner", "readable": True, "calls": real_row["calls"], "unresolved": 0}, unres])
    check("G5_unresolved_mention_is_RED_not_a_pass", g5["verdict"] == RED and "UNRESOLVED" in g5["reason"],
          {"reason": g5["reason"][:150]})
    g6 = decide([{"ref": "owner", "readable": True, "calls": real_row["calls"], "unresolved": 0},
                 {"ref": "/assets/unreadable.example.js", "readable": False, "calls": [], "unresolved": 0}])
    check("G6_unreadable_bundle_is_RED", g6["verdict"] == RED and "UNREADABLE" in g6["reason"],
          {"reason": g6["reason"][:120]})
    g7 = decide([])
    check("G7_empty_script_set_is_RED", g7["verdict"] == RED,
          {"reason": g7["reason"][:120], "why": "an index that names no script is not evidence of a SW"})

    # ---- killers: one variable each, each owning exactly one cell above
    judge_src = fn_span("_ord0277_generation_verdict")
    cases = [
        ("K1_invalid_registration_washed_to_green",
         "if invalid:", "if False and invalid:",
         lambda j: j([{"ref": "owner", "readable": True, "calls": real_row["calls"], "unresolved": 0}, bad]),
         RED, GREEN, "G3_secondary_dangerous_registration_is_RED"),
        ("K2_no_owner_stops_being_red",
         'elif not valid:', 'elif False:',
         lambda j: j([silent, {"ref": "/assets/other.js", "readable": True, "calls": [], "unresolved": 0}]),
         RED, GREEN, "G4_zero_registrations_still_RED"),
        ("K3_unresolved_mention_ignored",
         "elif unresolved:", "elif False and unresolved:",
         lambda j: j([{"ref": "owner", "readable": True, "calls": real_row["calls"], "unresolved": 0}, unres]),
         RED, GREEN, "G5_unresolved_mention_is_RED_not_a_pass"),
        ("K4_unreadable_treated_as_silent",
         "elif unreadable:", "elif False and unreadable:",
         lambda j: j([{"ref": "owner", "readable": True, "calls": real_row["calls"], "unresolved": 0},
                      {"ref": "/assets/x.js", "readable": False, "calls": [], "unresolved": 0}]),
         RED, GREEN, "G6_unreadable_bundle_is_RED"),
    ]
    kills = []
    for name, old, new, call, want_clean, want_mut, owner in cases:
        if old not in judge_src:
            kills.append({"mutant": name, "verdict": RED, "why": "anchor not found - mutant would be a no-op"})
            continue
        mns = {}
        exec(compile(ast.parse(judge_src.replace(old, new, 1)), "<mutant:%s>" % name, "exec"), mns)
        j = mns["_ord0277_generation_verdict"]
        clean_state, mut_state = call(decide)["verdict"], None
        try:
            mut_state = call(j)["verdict"]
        except Exception as exc:                       # noqa: BLE001 - name whatever the mutant did
            mut_state = type(exc).__name__
        kills.append({"mutant": name, "owner_cell": owner, "clean_returned": clean_state,
                      "mutant_returned": mut_state,
                      "verdict": "KILLED" if (clean_state == want_clean and mut_state == want_mut)
                                 else "SURVIVED"})
    check("K5_every_mutant_flips_only_its_own_cell",
          len(kills) == len(cases) and all(k["verdict"] == "KILLED" for k in kills), {"kills": kills})

    # ---- the live selftest arms the gauge now carries (both directions, no deployment)
    check("L1_selftest_carries_the_two_approved_controls",
          "0277-M1:multi_entry_only_owner_registers_is_green" in s and
          "0277-M2:secondary_dangerous_registration_is_red" in s and
          "0277-M3:no_registration_anywhere_stays_red" in s,
          {"arms": ["0277-M1 GREEN", "0277-M2 RED", "0277-M3 RED"],
           "measured_live": "the 15:3x run matched all three; the same run's other 10 arms went RED because "
                            "the 14:51 reboot had taken the server down - see the chain-restoration note"})

    n_green = sum(1 for c in cells if c["verdict"] == GREEN)
    overall = GREEN if n_green == len(cells) else RED
    draft_bytes = io.open(DRAFT, "rb").read()
    receipt = {"what": "ORD-0277 SW_REGISTRATION_GENERATION_CONTRACT offline proof",
               "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "order": {"id": "ORD-0277", "name": "SW_REGISTRATION_GENERATION_CONTRACT",
                         "source": "arbiter Q20 ruling 2026-09-24 (bus, after my 0271-A DEBT-3 demo)",
                         "scope_rule": "0271-A keeps predicate/phase work; 0277 owns registration topology"},
               "real_input": {"bundle": entry.replace("\\", "/"), "bytes": len(raw),
                              "sha256": hashlib.sha256(raw).hexdigest(),
                              "registrations_parsed": real_row["register_calls_parsed"]},
               "draft_under_test": {"path": DRAFT.replace("\\", "/"), "bytes": len(draft_bytes),
                                    "blob": blob_sha(draft_bytes)},
               "in_service_gauge": {"blob": blob_sha(in_service), "expected": IN_SERVICE_GAUGE_BLOB},
               "cells": cells, "cells_total": len(cells), "cells_green": n_green, "overall": overall,
               "claimed_result": "offline_selftest_" + overall}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, indent=1, ensure_ascii=False))
    print("overall = %s (%d/%d)" % (overall, n_green, len(cells)))
    for c in cells:
        print("  %-52s %s" % (c["cell"], c["verdict"]))
    for k in kills:
        print("  kill %-44s %-8s clean=%s mutant=%s" % (k["mutant"], k["verdict"],
                                                        k.get("clean_returned"), k.get("mutant_returned")))
    print("wrote", OUT)
    return 0 if overall == GREEN else 1


if __name__ == "__main__":
    raise SystemExit(main())
