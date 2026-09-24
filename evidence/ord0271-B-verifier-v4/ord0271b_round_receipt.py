"""ORD-0271-B: write one round's receipt out of the instruments' own files, and compute every verdict in it.

A round is the unit the commander's Q13口径 counts, and it is deliberately self-contained: this round's mutant
readings, this round's restore, this round's control readings. The receipt therefore carries the *shapes*
themselves (rendered text, what the origin answered, the measured snapshot rows) rather than only my verdicts,
so `ord0271b_streak.py` can re-judge them with the ruler and derive the streak without taking my word for
anything.

Nothing below is a literal `"PASS"`. Each boolean is computed from measured fields:

* `control_all_green` / `control_aggregate_green` - v4's own verdicts on this round's control readings;
* `mutant_all_red` and `mutant_extra_condition_is_only_the_new_clause` - v4 and v3 on the runtime mutant
  readings, comparing the two rulers' failed-condition sets;
* `dedicated_carrier_red_only_on_new_clause` - the one-token rewrite of each control reading, judged by both
  rulers;
* `restore_byte_exact` - the asset sha the face answered over HTTP after `git checkout --` and a rebuild,
  compared with the control identity recorded before the mutation;
* `q8b_fingerprints_complete` - every admitted reading executed the bundle its pass claims, re-hashed from its
  own URL, with the shell and the cached shell naming the same generation;
* `product_tree_clean_after_restore` - `git status --porcelain` over the clone, read back after the restore.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
REPO = BASE / "repo"
SRC_FILE = "frontend/src/lib/failureAttribution.ts"
CONTROL_SHA256 = "2d56a79632efc0c6b30396ebbddcd54bd84c0d2fa6a30d3f20d09f4655d419de"
CONTROL_ASSET = "assets/index-ChOTTCvB.js"
CONTROL_SOURCE_SHA256 = "3472430ee46810bdef0f5b3e53cca88cbfeb9a4a5385760c165032a9974d5c5d"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())


def blob40(d: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(d) + d).hexdigest()


def ruler(name: str):
    p = BASE / "tools" / name
    spec = importlib.util.spec_from_file_location(name.replace(".", "_"), str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def reason_of(shape: dict) -> str:
    m = re.search(r"attribution_reason=(\S+)", shape.get("rendered_text") or "")
    return m.group(1) if m else ""


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--capture", required=True)
    ap.add_argument("--mutant-gen", required=True)
    ap.add_argument("--control-gen", required=True)
    a = ap.parse_args(argv)
    v4 = ruler("ord0263_verifier_v4.py")
    v3 = ruler("ord0263_verifier_v3.py")

    cap = json.loads((BASE / a.capture).read_text(encoding="utf-8"))
    ctl = (cap.get("cells") or {}).get("S5_invalid_response", {}).get("shapes") or []
    mut = (cap.get("cells") or {}).get("S5_invalid_response_mutant", {}).get("shapes") or []

    def face(gen: str) -> dict:
        p = BASE / f"ord0271B_face_{gen}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"missing": p.name}

    fm, fc = face(a.mutant_gen), face(a.control_gen)

    def wire_sha(fr: dict) -> tuple:
        w = (fr.get("shell") or {}).get("answered_over_http") or {}
        named = ((fr.get("shell") or {}).get("names_asset") or [""])[0]
        return named, (w.get(named) or {}).get("sha256"), (w.get(named) or {}).get("equals_source_build_file")

    ctl_asset_on_wire, ctl_sha_on_wire, ctl_eq = wire_sha(fc)
    mut_asset_on_wire, mut_sha_on_wire, mut_eq = wire_sha(fm)

    git = lambda *args: subprocess.run(["git", "-C", str(REPO), *args], capture_output=True,
                                       text=True, encoding="utf-8", errors="replace").stdout.strip()
    head = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain")
    src_sha_now = hashlib.sha256((REPO / SRC_FILE).read_bytes()).hexdigest()

    ctl_rows, mut_rows, car_rows = [], [], []
    for s in ctl:
        j4, j3 = v4.judge_v5(s), v3.judge_v5(s)
        ctl_rows.append({"shape": s["shape"], "v4": j4["verdict"], "v3": j3["verdict"],
                         "v4_failed": j4.get("failed_conditions"), "v3_failed": j3.get("failed_conditions"),
                         "reason": reason_of(s),
                         "q8b": (s.get("q8b_fingerprints") or {})})
    for s in mut:
        j4, j3 = v4.judge_v5(s), v3.judge_v5(s)
        f4, f3 = set(j4.get("failed_conditions") or []), set(j3.get("failed_conditions") or [])
        mut_rows.append({"shape": s["shape"], "pass": s.get("pass_label"), "v4": j4["verdict"],
                         "v3": j3["verdict"], "v4_failed": sorted(f4), "v3_failed": sorted(f3),
                         "v4_only": sorted(f4 - f3), "v3_only": sorted(f3 - f4),
                         "reason": reason_of(s), "q8b": (s.get("q8b_fingerprints") or {})})
    # the dedicated carrier the order asked for: one token of one column of a *control* reading
    for s in ctl:
        c, changed = v4.one_token_reason_rewrite(s)
        jc4, jc3 = v4.judge_v5(c), v3.judge_v5(c)
        car_rows.append({"from_shape": s["shape"], "tokens_changed": changed, "v4": jc4["verdict"],
                         "v4_failed": jc4.get("failed_conditions"), "v3": jc3["verdict"],
                         "v3_failed": jc3.get("failed_conditions"), "reason_now": reason_of(c)})

    agg4, agg3 = v4.aggregate_v5(ctl), v3.aggregate_v5(ctl)
    checks = {
        "control_three_shapes_present": len(ctl) == 3,
        "control_all_green_under_v4": all(r["v4"] == "GREEN" for r in ctl_rows),
        "control_aggregate_green_under_v4": agg4["verdict"] == "GREEN",
        "control_still_green_under_v3": agg3["verdict"] == "GREEN",
        "mutant_three_shapes_present": len(mut) >= 3,
        "mutant_all_red_under_v4": bool(mut_rows) and all(r["v4"] == "RED" for r in mut_rows),
        "mutant_extra_condition_is_only_the_new_clause": bool(mut_rows) and all(
            r["v4_only"] == ["reason_collapsed"] for r in mut_rows),
        "mutant_reason_is_the_catch_all": bool(mut_rows) and all(
            r["reason"] == "UNKNOWN_FAILURE" for r in mut_rows),
        "dedicated_carrier_red_only_on_new_clause": len(car_rows) == 3 and all(
            r["tokens_changed"] == 1 and r["v4"] == "RED" and r["v4_failed"] == ["reason_collapsed"]
            and r["v3"] == "GREEN" for r in car_rows),
        "restore_byte_exact": ctl_asset_on_wire == CONTROL_ASSET and ctl_sha_on_wire == CONTROL_SHA256
        and bool(ctl_eq),
        "control_source_file_back_at_pre_mutation_sha": src_sha_now == CONTROL_SOURCE_SHA256,
        "product_tree_clean_after_restore": dirty == "",
        "both_faces_ownership_proven": (fc.get("surface") or {}).get("ownership_verdict") == "PROVEN"
        and (fm.get("surface") or {}).get("ownership_verdict") == "PROVEN",
        "q8b_fingerprints_complete": all(
            all([q.get("asset_matches_expected"), q.get("sha_matches_local_build"),
                 q.get("shell_same_generation") is not False])
            for q in [r["q8b"] for r in ctl_rows + mut_rows]),
    }
    green = [k for k, v in checks.items() if v]
    red = [k for k, v in checks.items() if not v]
    out = {"at": NOW, "order": "ORD-0271-B", "lane": "HARNESS d291c9dc", "round": a.round,
           "subject": "one Q13 round: runtime single-variable mutant readings, the restore, and control readings "
                      "on the same face and instrument",
           "commit_under_test": cap.get("commit_under_test"), "clone_head": head,
           "clone_dirty_lines": dirty.splitlines(),
           "instruments": {"v4": {"file": "tools/ord0263_verifier_v4.py",
                                  "blob40": blob40((BASE / "tools/ord0263_verifier_v4.py").read_bytes())},
                           "v3": {"file": "tools/ord0263_verifier_v3.py",
                                  "blob40": blob40((BASE / "tools/ord0263_verifier_v3.py").read_bytes()),
                                  "published_blob40": "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9",
                                  "unchanged": blob40((BASE / "tools/ord0263_verifier_v3.py").read_bytes())
                                  == "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"},
                           "readout_body_sha256": hashlib.sha256(
                               (BASE / "tools" / "q8b_readout.js").read_bytes()).hexdigest()},
           "capture": {"file": a.capture, "blob40": blob40((BASE / a.capture).read_bytes())},
           "faces": {"mutant": {"gen": a.mutant_gen, "asset_named": mut_asset_on_wire,
                                "sha256_answered_over_http": mut_sha_on_wire,
                                "equals_source_build": mut_eq,
                                "tree_sha256": (fm.get("served_root") or {}).get("tree_sha256"),
                                "receipt": f"ord0271B_face_{a.mutant_gen}.json"},
                     "control": {"gen": a.control_gen, "asset_named": ctl_asset_on_wire,
                                 "sha256_answered_over_http": ctl_sha_on_wire,
                                 "equals_source_build": ctl_eq,
                                 "tree_sha256": (fc.get("served_root") or {}).get("tree_sha256"),
                                 "receipt": f"ord0271B_face_{a.control_gen}.json",
                                 "expected_asset": CONTROL_ASSET, "expected_sha256": CONTROL_SHA256}},
           "control_shapes": ctl, "mutant_shapes": mut,
           "control_rows": ctl_rows, "mutant_rows": mut_rows, "carrier_rows": car_rows,
           "aggregate_control_v4": agg4["verdict"], "aggregate_control_v3": agg3["verdict"],
           "checks": checks, "checks_green": len(green), "checks_total": len(checks),
           "derived_result": "ROUND_GREEN" if not red else "ROUND_RED:" + ",".join(red)}
    p = BASE / f"ord0271b_round{a.round}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps({"round": a.round, "derived_result": out["derived_result"],
                      "checks_green": f"{len(green)}/{len(checks)}", "red_checks": red},
                     ensure_ascii=False, indent=1))
    print("->", p.name, f"{p.stat().st_size:,} B blob {blob40(p.read_bytes())[:16]}")
    return 0 if not red else 5


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
