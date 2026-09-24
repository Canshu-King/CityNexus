"""ORD-0274 B2b runtime readings: the half-filled trip across the product's own convergence.

One arm per client generation, each with a fresh profile.  The probe fills the wizard (step 1 with the city,
both anchors and both dates; step 2 with party size, budget and a special-requirement sentence), leaves it
open WITHOUT submitting, swaps the generation underneath that open document, and then reads BOTH sides:

  stored side   the localStorage draft ({step, draft}) the product wrote
  rendered side the input values and the step marker the traveller can actually see

Each named value is read on the step whose screen renders it, before and after, because the wizard mounts
only the current step's body - looking for `city` while the page sits on step 2 would report a preserved
value as absent and blame the product for my probe's own choice.  The step verdict is taken on the LANDED
screen, before the probe walks back to step 1 (that walk itself rewrites step:1 into the draft).

Arms:
  candidate            every named value and the step must come back, into the new generation's BYTES, with
                       the draft still standing (a convergence must not read as 创建成功).
  counter_step_only    only the step persists -> REQUIRED RED.
  counter_step_forced  values persist, step forced to 1 -> REQUIRED RED.

`CNX_B2B_REDERIVE=1` re-runs the judge over probe artifacts already on disk without touching a browser: my
first version of this file crashed inside `per_value` after the probes had written their readings, and
re-deriving the SAME bytes keeps those readings instead of paying for a second sweep.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
PORT = int(os.environ.get("CNX_B2B_PORT") or 8471)
BASE = f"http://127.0.0.1:{PORT}"
DETACHED = 0x00000008 | 0x00000200
FRONT = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend")
WINDOW = int(os.environ.get("CNX_B2B_WINDOW") or 60)
RUN_ID = os.environ.get("CNX_B2B_RUN_ID") or ""
SUFFIX = f"_{RUN_ID}" if RUN_ID else ""

# arm -> (client generation, target generation, the tag only the target's bytes advertise).
# B2b's restoring code is the INCOMING generation, so the mutants are swap targets; the candidate arm keeps
# the healthy stand-in target so its MET is not bought with a mutant that never ran.
ARMS = {
    "candidate": (FRONT / "dist_0274sw", FRONT / "dist_0274gen2b", "gen2-standin"),
    "counter_step_only": (FRONT / "dist_0274sw", FRONT / "dist_0274b2b_steponly_t", "b2b-steponly"),
    "counter_step_forced": (FRONT / "dist_0274sw", FRONT / "dist_0274b2b_stepforced_t", "b2b-stepforced"),
}
EXPECT = {"candidate": "MET", "counter_step_only": "RED", "counter_step_forced": "RED"}
# B2b's named values, each with the step whose screen actually renders it.  Values are deliberately unlike
# the product defaults (2 people / 3000 / "" / futureLocalAt), so a silent fallback cannot pass.
NAMED = {
    "city": ("trial-city", "cityName", 1),
    "startAt": ("trial-start", "startAt", 1),
    "endAt": ("trial-end", "endAt", 1),
    "partySize": ("trial-party", "partySize", 2),
    "budget": ("trial-budget", "budgetMajor", 2),
    "specialRequirements": ("trial-special", "specialRequirements", 2),
}
TYPED = {"city": "厦门", "startAt": "2026-10-05T08:30", "endAt": "2026-10-09T19:45",
         "partySize": "4", "budget": "4321", "specialRequirements": "需要无障碍通道 · B2b"}


def listeners(port):
    o = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace").stdout
    return sorted({m.group(1) for m in re.finditer(rf"TCP\s+127\.0\.0\.1:{port}\s+\S+\s+LISTENING\s+(\d+)", o)})


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def probe(profile, out_name, tag):
    out = WORK / out_name
    out.unlink(missing_ok=True)
    r = subprocess.run(["node", str(SPIKE / "q274_b2b_probe.js"), "--base", BASE,
                        "--profile", str(profile), "--out", str(out), "--window", str(WINDOW),
                        "--tag", tag],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=520)
    line = ((r.stdout or "").strip().splitlines() or [f"NO OUTPUT rc={r.returncode} {(r.stderr or '')[-260:]}"])[-1]
    print(f"      {line[:210]}")
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {
        "missing": True, "stderr": (r.stderr or "")[-400:]}


def current_step(state):
    """Which step the traveller is looking at, read off the screen two ways, plus the stored step.

    `trial-step-N` carries className "active" (current) / "done" (passed) / "" (ahead), and only the current
    step's `trial-stepN-body` is rendered - so the screen can be judged without trusting the storage key,
    which is exactly what a step_forced mutant keeps honest while the wizard lands somewhere else.
    """
    marks = state.get("step_marks") or []
    return {"active_marks": [m["id"] for m in marks if "active" in str(m.get("class_name") or "")],
            "done_marks": [m["id"] for m in marks if "done" in str(m.get("class_name") or "")],
            "visible_bodies": state.get("visible_bodies") or [],
            "from_storage": (state.get("draft") or {}).get("step"),
            "on_screen": (state.get("visible_bodies") or [None])[0]}


def norm(x):
    """Compare values, not formats.  A datetime-local answers "2026-10-05T08:30" for the same instant the
    draft stores; only separators are folded, never content, and both raw strings stay in the receipt.
    """
    return str(x).replace("/", "-").replace(" ", "T") if x is not None else None


def per_value(run):
    """One row per named value, read on its own step's screen on BOTH sides of the reload."""
    screens = {1: (run.get("before_step1") or {}, run.get("after_on_step1") or {}),
               2: (run.get("before_swap") or {}, run.get("after_on_landed_step") or {})}
    stored_before = ((run.get("before_swap") or {}).get("draft") or {}).get("draft") or {}
    stored_after = ((run.get("after_on_landed_step") or {}).get("draft") or {}).get("draft") or {}
    rows = {}
    for name, (testid, draft_key, step) in NAMED.items():
        before, after = screens[step]
        field_before = (before.get("fields") or {}).get(testid) or {}
        field_after = (after.get("fields") or {}).get(testid) or {}
        b_render, a_render = field_before.get("value"), field_after.get("value")
        b_store, a_store = stored_before.get(draft_key), stored_after.get(draft_key)
        typed = TYPED[name]
        rows[name] = {"typed": typed, "testid": testid, "draft_key": draft_key, "rendered_on_step": step,
                      "rendered_before": b_render, "rendered_after": a_render,
                      "present_before": field_before.get("present"), "present_after": field_after.get("present"),
                      "stored_before": b_store, "stored_after": a_store,
                      "typed_matches_before": norm(b_render) == norm(typed),
                      "rendered_equal": bool(a_render is not None and norm(a_render) == norm(b_render)),
                      "stored_equal": norm(a_store) == norm(b_store),
                      "rendered_equals_stored_after": norm(a_render) == norm(a_store),
                      "still_the_typed_value": norm(a_render) == norm(typed)}
    return rows


def derive(run, target_sha, target_tag):
    landed = run.get("after_on_landed_step") or {}
    rows = per_value(run)
    step_before = current_step(run.get("before_swap") or {})
    step_after = current_step(landed)
    # The commander's boundary, both halves: a restored draft over the wrong step is RED, and the right step
    # over an empty draft is RED.  So `step` is judged on the LANDED screen AND in storage, before the probe
    # walks back to step 1 - that walk writes step:1 into the draft itself, so it cannot be the read.
    step_preserved = bool(
        step_before["from_storage"] and step_after["from_storage"]
        and step_before["from_storage"] == step_after["from_storage"]
        and step_before["on_screen"] == step_after["on_screen"]
        and step_before["visible_bodies"] == step_after["visible_bodies"]
        and step_before["active_marks"] == step_after["active_marks"])
    eb = run.get("executed_bytes") or {}
    # convergence is read two ways, both from bytes: the statement that exists only in the target bundle
    # executed (so the running code IS the target), and the digest of the fetched module equals the target
    # generation's entry digest.  A tag alone could be stale; a digest alone does not prove it executed.
    converged = landed.get("gen_tag") == target_tag
    sha_match = bool(target_sha and eb.get("sha256") == target_sha)
    draft_after = landed.get("draft")
    return {
        "step_before": step_before, "step_after": step_after,
        "step_preserved": step_preserved,
        "values": rows,
        "all_named_values_equal": all(r["rendered_equal"] and r["stored_equal"] and r["still_the_typed_value"]
                                      and r["rendered_equals_stored_after"] for r in rows.values()),
        "values_read_on_the_right_screen": all(bool(r["present_before"] and r["present_after"])
                                               for r in rows.values()),
        "draft_still_present_after_convergence": draft_after is not None,
        "draft_cleared_as_created": draft_after is None,
        "converged_to_new_generation": converged,
        "bundle_move_by_bytes": bool(converged and sha_match),
        "executed_bytes": {"ref": eb.get("ref"), "sha256": eb.get("sha256"), "bytes": eb.get("bytes"),
                           "content_type": eb.get("content_type")},
        "document_loads": len(run.get("loads") or []),
        "loads_series_tail": [s.get("loads") for s in (run.get("samples") or [])][-6:],
        "reload_key_after": landed.get("reload_key"),
        "pending_key_after": landed.get("pending_key"),
        "samples_needed_for_convergence": next((i + 1 for i, s in enumerate(run.get("samples") or [])
                                                if s.get("gen_tag") == target_tag), None),
        "probe_navigations": 1,
        "back_press": run.get("back_press"),
        "console_errors": (run.get("console_errors") or [])[:3],
        "page_errors": (run.get("page_errors") or [])[:3],
    }


def verdict_of(d):
    if not d["converged_to_new_generation"]:
        return "RED", "the open document never reached the new generation, so nothing was preserved by it"
    if not d["bundle_move_by_bytes"]:
        return "RED", f"the executed bytes are not the new generation's ({d['executed_bytes']})"
    if d["draft_cleared_as_created"]:
        return "RED", "the draft is gone - a convergence must not read as 创建成功"
    # Order matters and it cost me a wrong label: a field missing from the screen is the CONSEQUENCE of
    # landing on the wrong step, not an instrument fault.  So the step is judged first, and only a field that
    # is missing while the step DID come back is an untrustworthy read (INVALID_ARM).
    if not d["step_preserved"]:
        off = sorted(k for k, v in d["values"].items() if not v["present_after"])
        return "RED", (f"step did not come back: before={d['step_before']} after={d['step_after']}"
                       + (f"; the fields that therefore are not on any screen: {off}" if off else ""))
    if not d["values_read_on_the_right_screen"]:
        return "INVALID_ARM", "a named field was not on its own screen although the step came back, so the "                               "per-value read is not trustworthy"
    if not d["all_named_values_equal"]:
        bad = [k for k, v in d["values"].items()
               if not (v["rendered_equal"] and v["stored_equal"] and v["still_the_typed_value"]
                       and v["rendered_equals_stored_after"])]
        return "RED", "named values differ: " + ", ".join(bad)
    return "MET", ("step and every named value - city, both dates, partySize, budget, specialRequirements - "
                   "came back per value on their own screens and in storage, into the new generation's bytes, "
                   "with the draft still standing")


def report(d):
    print(f"    step {d['step_before'].get('from_storage')}/{d['step_before'].get('on_screen')} -> "
          f"{d['step_after'].get('from_storage')}/{d['step_after'].get('on_screen')} "
          f"preserved={d['step_preserved']} | values_equal={d['all_named_values_equal']} "
          f"bytes_moved={d['bundle_move_by_bytes']} | draft_present={d['draft_still_present_after_convergence']} "
          f"| loads={d['document_loads']} in {d['samples_needed_for_convergence']} sample(s)")
    for k, v in d["values"].items():
        print(f"      {k:20s} step{v['rendered_on_step']} typed={str(v['typed'])!r:26s} "
              f"before={str(v['rendered_before'])!r:26s} after={str(v['rendered_after'])!r:26s} "
              f"store={str(v['stored_after'])!r:26s} "
              f"ok={v['rendered_equal']}/{v['stored_equal']}/{v['still_the_typed_value']}"
              f"/{v['rendered_equals_stored_after']}")
    print(f"    verdict={d['verdict']} (expected {d['expected']})  {d['why'][:170]}")


def judge_one(arm, run, g_old, g_tgt, run_blob):
    d = derive(run, list(g_tgt["per_script"].values())[0]["sha256"], ARMS[arm][2])
    d["target_generation"] = {"dir": ARMS[arm][1].name, "tag": ARMS[arm][2],
                              "content_fingerprint": g_tgt["content_fingerprint"],
                              "entry": list(g_tgt["per_script"]),
                              "entry_sha256": list(g_tgt["per_script"].values())[0]["sha256"]}
    d["client_generation"] = {"dir": ARMS[arm][0].name, "content_fingerprint": g_old["content_fingerprint"],
                              "entry": list(g_old["per_script"]),
                              "entry_sha256": list(g_old["per_script"].values())[0]["sha256"],
                              "generation_verdict": g_old["generation_verdict"]}
    d["swap_response"] = run.get("swap")
    d["probe_events"] = run.get("probe_events")
    d["artifact"] = {"run_blob": run_blob}
    d["expected"] = EXPECT[arm]
    d["verdict"], d["why"] = verdict_of(d)
    d["agrees_with_expectation"] = d["verdict"] == EXPECT[arm]
    return d


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(SPIKE))
    import q274_gen_identity as ident
    g_new = ident.disk_identity("candidate-target", FRONT / "dist_0274gen2b")
    ident.refuse_if_unusable(g_new, "candidate swap target")
    print(f"candidate target: entry sha256={list(g_new['per_script'].values())[0]['sha256'][:16]} "
          f"content={g_new['content_fingerprint'][:16]}")

    only = [a for a in (sys.argv[1:] or list(ARMS)) if a in ARMS]
    rederive = os.environ.get("CNX_B2B_REDERIVE") == "1"
    if not rederive and listeners(PORT):
        print(f"ABORT: :{PORT} already answers {listeners(PORT)}")
        return 2
    results = {}
    for arm in only:
        old_dist, tgt_dist, tag = ARMS[arm]
        if not old_dist.is_dir() or not tgt_dist.is_dir():
            print(f"  {arm}: NO DIST client={old_dist.is_dir()} target={tgt_dist.is_dir()}")
            continue
        g_old = ident.disk_identity(f"{arm}-client", old_dist)
        g_tgt = ident.disk_identity(f"{arm}-target", tgt_dist)
        ident.refuse_if_unusable(g_old, "client generation")
        ident.refuse_if_unusable(g_tgt, "swap target")
        if g_tgt["content_fingerprint"] == g_old["content_fingerprint"]:
            print(f"  {arm}: TARGET IS BYTE-IDENTICAL TO THE CLIENT - the arm would prove nothing")
            continue
        run_name = f"b2b_{arm}{SUFFIX}_run.json"
        print(f"\n=== arm {arm} (client={old_dist.name} content={g_old['content_fingerprint'][:12]} "
              f"entry={list(g_old['per_script'])}) ===")
        if rederive:
            rp = WORK / run_name
            if not rp.exists():
                print(f"    no artifact to re-derive: {rp.name}")
                continue
            run = json.loads(rp.read_text(encoding="utf-8"))
            run_blob = ident.blob_sha(rp)
        else:
            profile = WORK / f"profile_b2b_{arm}{SUFFIX}"
            shutil.rmtree(profile, ignore_errors=True)
            profile.mkdir(parents=True)
            log = WORK / f"b2b_origin_{arm}{SUFFIX}.log"
            log.unlink(missing_ok=True)
            origin = subprocess.Popen([PY, str(SPIKE / "q274_gen_origin.py"), "--gen", "old", "--gen2", "new",
                                       "--port", str(PORT), "--log", str(log)],
                                      env=dict(os.environ) | {"CNX_GEN_OLD_DIR": str(old_dist),
                                                              "CNX_GEN_NEW_DIR": str(tgt_dist),
                                                              "CNX_POST_DELAY_S": "0"},
                                      stdout=open(WORK / f"b2b_origin_{arm}{SUFFIX}.out", "a",
                                                  encoding="utf-8"),
                                      stderr=subprocess.STDOUT, creationflags=DETACHED)
            try:
                for _ in range(30):
                    if listeners(PORT):
                        break
                    time.sleep(1)
                run = probe(profile, run_name, tag)
            finally:
                kill(listeners(PORT) + [origin.pid])
            if run.get("missing"):
                print("    probe missing:", str(run.get("stderr"))[:200])
                continue
            run_blob = ident.blob_sha(WORK / run_name)
        d = judge_one(arm, run, g_old, g_tgt, run_blob)
        results[arm] = d
        report(d)

    p = WORK / os.environ.get("CNX_B2B_OUT", "ord0274_b2b_runtime.json")
    p.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                             "order": "ORD-0274 B2b 运行时读数 + 两枚反控",
                             "lane": "B c01d72a3", "candidate_branch": "review/0274-b2c-b",
                             "run_id": RUN_ID or "first",
                             "mode": "re-derived from stored probe artifacts" if rederive else "fresh browser arms",
                             "window_s": WINDOW,
                             "generation_identity_is_a_byte_verdict": {
                                 "ruler": g_new["ruler"],
                                 "rule": "each arm converges into ITS OWN target generation, judged by the "
                                         "target entry's sha256 plus the tag statement inside those bytes"},
                             "arms": results}, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(f"\n-> {p.name}")
    for arm, d in results.items():
        print(f"  {arm:22s} {d['verdict']:4s} expected={EXPECT[arm]:4s} agrees={d['agrees_with_expectation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
