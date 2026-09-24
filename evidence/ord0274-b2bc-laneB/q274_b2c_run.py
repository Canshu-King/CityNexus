"""ORD-0274 B2c runtime readings: one arm per client generation, each with its own profile and origin.

What every arm does, in this order:
  install  first visit on the client generation -> the worker registers and controls the document
  b2c      the traveller's own wizard fills and presses 确认创建, the origin HOLDS that non-idempotent
           request open (POST_DELAY_S), the probe waits until the origin itself reports an open write,
           then swaps the generation underneath the open document and samples it for the window.
           The probe performs exactly ONE navigation per phase; every later load is the product's.

Arms:
  candidate      this lane's B2c code -> must show: no reload while a write is open, the write's answer
                 actually delivered, convergence with no extra user navigation.
  counter_eager  reload the instant the new worker takes over -> REQUIRED TO BE RED: the criterion's own
                 counter-control ("写请求在飞就立刻 reload 的形状必须 RED").
  counter_manual defers the handover but never converges on its own -> REQUIRED TO BE RED: the other half
                 of the same sentence ("仍然不能要求用户再做一次导航").
  idle_control   no write in flight -> guards against a fix that only ever defers (it must still converge).

Every verdict below is derived from the origin's own log lines and the page's samples; nothing is typed in.
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
PORT = int(os.environ.get("CNX_B2C_PORT") or 8461)
BASE = f"http://127.0.0.1:{PORT}"
DETACHED = 0x00000008 | 0x00000200
FRONT = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend")
NEW_GEN = FRONT / "dist_0274gen2b"
POST_DELAY_S = int(os.environ.get("CNX_B2C_POST_DELAY") or 12)
WINDOW = int(os.environ.get("CNX_B2C_WINDOW") or 70)
# A second sweep must not overwrite the first sweep's readings: published instrument paths are frozen,
# and two runs of a timing claim are the point, not a replacement.  Empty means the original names.
RUN_ID = os.environ.get("CNX_B2C_RUN_ID") or ""
SUFFIX = f"_{RUN_ID}" if RUN_ID else ""

ARMS = {
    "candidate": FRONT / "dist_0274sw",
    "counter_eager": FRONT / "dist_0274b2c_eager",
    "counter_manual": FRONT / "dist_0274b2c_manual",
    "idle_control": FRONT / "dist_0274sw",
}
EXPECT = {"candidate": "MET", "counter_eager": "RED", "counter_manual": "RED", "idle_control": "MET"}


def listeners(port):
    o = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace").stdout
    return sorted({m.group(1) for m in re.finditer(rf"TCP\s+127\.0\.0\.1:{port}\s+\S+\s+LISTENING\s+(\d+)", o)})


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def probe(phase, profile, out_name, window):
    out = WORK / out_name
    out.unlink(missing_ok=True)
    r = subprocess.run(["node", str(SPIKE / "q274_b2c_probe.js"), "--base", BASE,
                        "--profile", str(profile), "--out", str(out), "--phase", phase,
                        "--window", str(window)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=520)
    line = ((r.stdout or "").strip().splitlines() or [f"NO OUTPUT rc={r.returncode} {(r.stderr or '')[-260:]}"])[-1]
    print(f"      {line[:200]}")
    if not out.exists():
        return {"missing": True, "stderr": (r.stderr or "")[-400:]}
    return json.loads(out.read_text(encoding="utf-8"))


def log_records(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def derive(recs, b2c, new_gen_sha):
    started = [r for r in recs if r.get("event") == "write_started"]
    finished = [r for r in recs if r.get("event") == "write_finished"]
    swap = next((r for r in recs if r.get("event") == "swap"), None)
    samples = b2c.get("samples") or []
    loads_series = [s.get("loads") for s in samples if isinstance(s.get("loads"), int)]
    open_series = [s.get("writes_open") for s in samples]
    # a load that appears while the origin still holds a write is the 腰斩 shape, read off one timeline
    reload_with_open = [i for i, s in enumerate(samples)
                        if i > 0 and isinstance(s.get("loads"), int) and isinstance(samples[i - 1].get("loads"), int)
                        and s["loads"] > samples[i - 1]["loads"] and (s.get("writes_open") or 0) > 0]
    delivered = [f for f in finished if f.get("delivered") is True]
    undelivered = [f for f in finished if f.get("delivered") is not True]
    converged = bool(b2c.get("seen", {}).get("gen_tag") == "gen2-standin")
    sha_match = bool(new_gen_sha and (b2c.get("executed_bytes") or {}).get("sha256") == new_gen_sha)
    pending_seen = any(s.get("pending_key") == "pending" for s in samples) or \
        any(e.get("kind") == "handover-pending" for e in (b2c.get("seen", {}).get("probe_events") or []))
    # A sample whose evaluate failed is the page CHANGING UNDER THE PROBE - that is the product's reload,
    # not a navigation the probe took.  Reading it as "the probe navigated" once made a clean MET arm RED.
    dead_samples = len([s for s in samples if s.get("dead")])
    loads_end = max(loads_series) if loads_series else 0
    return {
        "writes_started": len(started),
        "writes_finished": len(finished),
        "write_delivered": len(delivered),
        "write_undelivered": len(undelivered),
        "open_write_ids": [s.get("write_id") for s in started],
        "swap_at_wall": (swap or {}).get("at"),
        "writes_open_at_swap": (swap or {}).get("writes_open_at_swap"),
        "loads_series_first_last": [loads_series[:1], loads_series[-1:]],
        "loads_max": max(loads_series) if loads_series else 0,
        "reload_while_write_open_samples": reload_with_open,
        "samples_with_open_write": sum(1 for o in open_series if (o or 0) > 0),
        "pending_handover_marker_seen": pending_seen,
        "gen_tag_at_end": b2c.get("seen", {}).get("gen_tag"),
        "executed_ref_at_end": (b2c.get("executed_bytes") or {}).get("ref"),
        "executed_sha_at_end": (b2c.get("executed_bytes") or {}).get("sha256"),
        "executed_content_type": (b2c.get("executed_bytes") or {}).get("content_type"),
        "html_at_js_url": (b2c.get("executed_bytes") or {}).get("html_at_js_url"),
        "executed_sha_equals_new_generation_bytes": sha_match,
        "converged_by_the_product_without_another_navigation": bool(converged and loads_end >= 2),
        "document_loads_seen": loads_end,
        "samples_taken_while_the_page_was_changing": dead_samples,
        "probe_navigations_in_b2c_phase": 1,
        "page_errors": (b2c.get("page_errors") or [])[:3],
        "console_errors": (b2c.get("console_errors") or [])[:3],
        "fill_errors": (b2c.get("fill_errors") or [])[:3],
    }


def verdict_of(arm, d):
    """B2c's sentence, as arithmetic on the readings above.

    `idle_control` is the one arm where NO write may be open: it exists to catch a fix that defers always.
    """
    if arm == "idle_control":
        if d["writes_started"] > 0:
            return "INVALID_ARM", f"a control arm must hold nothing open, saw {d['writes_started']} write(s)"
        if not d["converged_by_the_product_without_another_navigation"]:
            return "RED", ("with nothing in flight the still-open document did not converge on its own "
                           f"(gen_tag={d['gen_tag_at_end']!r}); the handover cannot be deferred forever")
        return "MET", "with no write outstanding the same handover converged by itself, so the deferral is " \
                      "conditional and not the only behaviour"
    if d["writes_started"] == 0:
        return "NOT_ARMED", "no non-idempotent request was ever held open, so the cell was not measured"
    blocked_midair = len(d["reload_while_write_open_samples"]) > 0 or d["write_undelivered"] > 0
    if blocked_midair:
        return "RED", "the document reloaded (or lost the answer) while the origin still held the write open"
    if not d["converged_by_the_product_without_another_navigation"]:
        return "RED", ("the open document never reached the new generation's bytes on its own "
                       f"(gen_tag={d['gen_tag_at_end']!r}, sha_match={d['executed_sha_equals_new_generation_bytes']})")
    if not d["executed_sha_equals_new_generation_bytes"]:
        return "RED", f"converged to bytes that are not the new generation ({d['executed_sha_at_end']})"
    return "MET", ("no reload while a write was open, the write's answer was delivered, and the still-open "
                   "document reached the new generation's bytes without another user navigation")


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    if listeners(PORT):
        print(f"ABORT: :{PORT} already answers {listeners(PORT)}")
        return 2
    sys.path.insert(0, str(SPIKE))
    import q274_gen_identity as ident
    g_new = ident.disk_identity("new-generation", NEW_GEN)
    ident.refuse_if_unusable(g_new, "swap target")
    new_sha = list(g_new["per_script"].values())[0]["sha256"]
    print(f"swap target new generation: entry sha256={new_sha[:16]} content={g_new['content_fingerprint'][:16]}")

    only = sys.argv[1:] or list(ARMS)
    results = {}
    for arm in only:
        old_dist = ARMS[arm]
        if not old_dist.is_dir():
            print(f"  {arm}: NO DIST {old_dist}")
            continue
        delay = 0 if arm == "idle_control" else POST_DELAY_S
        profile = WORK / f"profile_b2c_{arm}{SUFFIX}"
        shutil.rmtree(profile, ignore_errors=True)
        profile.mkdir(parents=True)
        log = WORK / f"b2c_origin_{arm}{SUFFIX}.log"
        log.unlink(missing_ok=True)
        print(f"\n=== arm {arm} (client={old_dist.name}, new={NEW_GEN.name}, POST_DELAY_S={delay}) ===")
        origin = subprocess.Popen([PY, str(SPIKE / "q274_gen_origin.py"), "--gen", "old", "--gen2", "new",
                                   "--port", str(PORT), "--log", str(log)],
                                  env=dict(os.environ) | {"CNX_GEN_OLD_DIR": str(old_dist),
                                                          "CNX_GEN_NEW_DIR": str(NEW_GEN),
                                                          "CNX_POST_DELAY_S": str(delay)},
                                  stdout=open(WORK / f"b2c_origin_{arm}{SUFFIX}.out", "a", encoding="utf-8"),
                                  stderr=subprocess.STDOUT, creationflags=DETACHED)
        try:
            for _ in range(30):
                if listeners(PORT):
                    break
                time.sleep(1)
            else:
                print("  ABORT: origin never listened")
                continue
            install = probe("install", profile, f"b2c_{arm}{SUFFIX}_install.json", 0)
            si = install.get("seen") or {}
            if not si.get("controller_now"):
                print(f"  ABORT: first visit is not controlled ({si.get('controller_now')})")
                continue
            print(f"      install: controller={si.get('controller_now')} bundle={si.get('executing_bundle')}")
            b2c = probe("idle" if arm == "idle_control" else "b2c", profile,
                        f"b2c_{arm}{SUFFIX}_run.json", WINDOW)
            recs = log_records(log)
            d = derive(recs, b2c, new_sha)
            v, why = verdict_of(arm, d)
            d["swap_response"] = (b2c.get("swap_request") or {})
            d["draft_before_submit"] = b2c.get("draft_before_submit")
            d["draft_at_end"] = (b2c.get("seen") or {}).get("draft")
            d["samples"] = b2c.get("samples")
            d["origin_write_records"] = [r for r in recs if str(r.get("event", "")).startswith("write")]
            d["verdict"] = v
            d["why"] = why
            d["expected"] = EXPECT[arm]
            d["agrees_with_expectation"] = v == EXPECT[arm]
            results[arm] = d
            print(f"    writes={d['writes_started']}/{d['writes_finished']} delivered={d['write_delivered']} "
                  f"undelivered={d['write_undelivered']} open_at_swap={d['writes_open_at_swap']} "
                  f"reload_with_open={d['reload_while_write_open_samples']}")
            print(f"    loads {d['loads_series_first_last']} pending={d['pending_handover_marker_seen']} "
                  f"gen_tag={d['gen_tag_at_end']!r} sha==new:{d['executed_sha_equals_new_generation_bytes']}")
            print(f"    verdict={v} (expected {EXPECT[arm]})  {why}")
        finally:
            kill(listeners(PORT) + [origin.pid])
    p = WORK / os.environ.get("CNX_B2C_OUT", "ord0274_b2c_runtime.json")
    p.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                             "order": "ORD-0274 B2c 运行时读数 + 两枚反控",
                             "lane": "B c01d72a3", "candidate": "review/0274-b2c-b 1de4c25", "run_id": RUN_ID or "first",
                             "base": "dcae1bc964125c3a975916f6bf667794cc19622a",
                             "post_delay_s": POST_DELAY_S, "window_s": WINDOW,
                             "generation_identity_is_a_byte_verdict": {
                                 "ruler": g_new["ruler"], "new_generation_entry_sha256": new_sha,
                                 "new_generation_content_fingerprint": g_new["content_fingerprint"],
                                 "new_generation_verdict": g_new["generation_verdict"]},
                             "arms": results},
                            ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(f"\n-> {p.name}")
    for arm, d in results.items():
        print(f"  {arm:16s} {d['verdict']:4s} expected={d['expected']:4s} agrees={d['agrees_with_expectation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
