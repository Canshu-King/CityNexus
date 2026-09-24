"""Derive the ORD-0269-4 verdict from the four measured artifacts - no verdict is typed.

Every judgement below is computed from (a) the DB read-back of a second connection,
(b) the backend's own access log, (c) my origin's per-request decision log, and (d) the
rendered leaf text the person actually saw.  The sentence the product tells the traveller
is taken from the product source AT THE MEASURED SHA by regex, never hand-typed, so a
wording change in the product makes this script stop matching instead of agreeing silently.
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
REPO = r"D:\moodle\_qoder_integration_20260919"
GEN = {"c79e2b4": {"sha": "c79e2b4f4efe414dba22a071a7136ae10b5c84aa", "bundle": "index-ChOTTCvB.js"},
       "1f44408": {"sha": "1f4440819a9d773da6e18f12a31412f73c6d0f55", "bundle": "index-Cpy_jhEg.js"}}
READ_DEADLINE_MS = 12_000


def source_literals(sha):
    src = subprocess.run(["git", "-C", REPO, "show", "%s:frontend/src/app/V8Experience.tsx" % sha],
                         capture_output=True, text=True, encoding="utf-8").stdout
    claims = {"claims_absent": None, "claims_present": None}
    for line in src.split("\n"):
        if "还没有创建" in line:
            claims["claims_absent"] = re.search(r'"([^"]*还没有创建[^"]*)"', line).group(1)
        if "行程已经创建" in line:
            claims["claims_present"] = re.search(r'"([^"]*行程已经创建[^"]*)"', line).group(1)
    dl = subprocess.run(["git", "-C", REPO, "show", "%s:frontend/src/lib/readDeadline.ts" % sha],
                        capture_output=True, text=True, encoding="utf-8").stdout
    m = re.search(r"READ_DEADLINE_MS\s*=\s*([\d_]+)", dl)
    return claims, (int(m.group(1).replace("_", "")) if m else None), src.count("tripWritten = true;")


def load(tag):
    r = json.load(io.open(os.path.join(LANE, "o269_arm_%s.json" % tag), encoding="utf-8"))
    w = json.load(io.open(os.path.join(LANE, "o269_walk_%s.json" % tag), encoding="utf-8"))
    return r, w


rows = []
for gen_key, arms in (("c79e2b4", ("swallow_journeys__c79e2b4", "never__c79e2b4")),
                      ("1f44408", ("swallow_journeys", "never", "answer"))):
    sha = GEN[gen_key]["sha"]
    claims, deadline_ms, tripwritten_sites = source_literals(sha)
    for tag in arms:
        arm = tag.split("__")[0]
        r, w = load(tag)
        after = r["db_after_shutdown"]["counts"]
        live = r["db_after_live"]["counts"]
        jkeys = r["db_after_shutdown"]["detail"]["journeys"]["keys"]
        tkeys = r["db_after_shutdown"]["detail"]["travelers"]["keys"]
        origin_swallow = [e for e in r["origin_events_summary"]["trip_write_decisions"]
                          if e.get("kind") == "swallow"]
        origin_never = [e for e in r["origin_events_summary"]["trip_write_decisions"]
                        if e.get("kind") == "hold"]
        log_201 = [ln for ln in r["backend_access_log_write_lines"]
                   if re.search(r'"POST /api/v1/journeys HTTP/1\.1" 201', ln)]
        rendered = [l["txt"] for l in w["terminal"]["leaves"]]
        samples_after_deadline = [s for s in w["samples"] if s["atMs"] > deadline_ms]
        rows.append({
            "gen": gen_key, "served_bundle_proved": r["origin"]["served_entry"] == GEN[gen_key]["bundle"],
            "arm": arm,
            "source_sha": sha[:12],
            "trip_written_assignments_in_source": tripwritten_sites,
            "journeys_rows_after": after.get("journeys"),
            "journeys_rows_live_second_connection": live.get("journeys"),
            "journey_pks": [k["id"] for k in jkeys],
            "traveler_pks": [k["id"] for k in tkeys],
            "tables_measured": r["db_after_shutdown"]["tables_measured"],
            "trip_write_withheld_from_traveller": bool(origin_swallow),
            "trip_write_never_reached_server": bool(origin_never),
            "backend_logged_201_for_journeys": bool(log_201),
            "server_answer_bytes": origin_swallow[0]["upstream_bytes"] if origin_swallow else None,
            "terminal_rendered_text_present": [t for t in rendered if t in (claims["claims_absent"],
                                                                            claims["claims_present"])],
            "sentence_claims_no_journey_exists": claims["claims_absent"] in rendered,
            "sentence_claims_journey_exists": claims["claims_present"] in rendered,
            "waiting_copy_still_on_screen_past_deadline": bool([
                s for s in samples_after_deadline
                if any("正在创建行程" in x["txt"] for x in s["waitCopies"])]),
            "named_attribution_view_appeared": bool([
                s for s in samples_after_deadline
                if any(("没有回音" in x["txt"] or "网络不可用" in x["txt"] or "failure-reason" in (x.get("testid") or ""))
                       for x in s["waitCopies"])]),
            "localStorage_journey_id": w["localStorageJourneyId"],
            "isolation": {"tempdir_deleted": r["tempdir_deleted"],
                          "db_leftovers": r["db_files_present_after_delete"],
                          "ports_released": not any(r["ports_final"].values())},
            "read_deadline_ms_in_source": deadline_ms,
            "wall_s": r["walk"]["wall_s"]})

for row in rows:
    row["screen_matches_store"] = (row["journeys_rows_after"] == 0) == row["sentence_claims_no_journey_exists"]

false_claim = [r for r in rows if r["trip_write_withheld_from_traveller"] and r["journeys_rows_after"]
               and r["sentence_claims_no_journey_exists"]]
truthful_control = [r for r in rows if r["trip_write_never_reached_server"] and not r["journeys_rows_after"]
                    and r["sentence_claims_no_journey_exists"]]
per_gen = {}
for g in ("c79e2b4", "1f44408"):
    sel = [r for r in rows if r["gen"] == g]
    per_gen[g] = {
        "arms": [r["arm"] for r in sel],
        "false_claim_arms": [r["arm"] for r in sel if r["arm"] in [f["arm"] for f in false_claim]],
        "truthful_control_arms": [r["arm"] for r in sel if r["arm"] in [f["arm"] for f in truthful_control]],
        "terminal_sentences_distinct_across_arms":
            len({tuple(r["terminal_rendered_text_present"]) for r in sel}),
        "deadline_named_state_reached_by_any_arm": any(r["named_attribution_view_appeared"] for r in sel)}

verdict = {
    "cell": "ORD-0269 第四格 (A3 write leg silent) - runtime, HJ-P1 代任",
    "why_red": bool(false_claim) and per_gen["c79e2b4"]["false_claim_arms"]
               and per_gen["1f44408"]["false_claim_arms"],
    "false_claim_count": len(false_claim),
    "truthful_control_count": len(truthful_control),
    "control_answer_arm_present": any(r["arm"] == "answer" for r in rows),
    "write_leg_deadline_covered": any(r["named_attribution_view_appeared"] for r in rows),
    "per_generation": per_gen}
verdict["verdict"] = "RED" if verdict["why_red"] else "NOT_RED_AS_SPECIFIED"
out = {"derived_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
       "rows": rows, "verdict_block": verdict,
       "derived_from": ["o269_arm_*.json", "o269_walk_*.json",
                        "git show <sha>:frontend/src/app/V8Experience.tsx",
                        "git show <sha>:frontend/src/lib/readDeadline.ts"]}
io.open(os.path.join(LANE, "o269_verdict.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps(verdict, ensure_ascii=False, indent=1))
for r in rows:
    print("%-9s %-18s journeys=%s live2nd=%s withheld=%s backend201=%s saysNoJourney=%s screen_matches_store=%s waiting@>12s=%s named=%s iso=%s"
          % (r["gen"], r["arm"], r["journeys_rows_after"], r["journeys_rows_live_second_connection"],
             r["trip_write_withheld_from_traveller"], r["backend_logged_201_for_journeys"],
             r["sentence_claims_no_journey_exists"], r["screen_matches_store"],
             r["waiting_copy_still_on_screen_past_deadline"], r["named_attribution_view_appeared"],
             r["isolation"]["tempdir_deleted"] and r["isolation"]["ports_released"]))
