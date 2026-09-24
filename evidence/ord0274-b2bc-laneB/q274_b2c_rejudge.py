"""Re-judge the B2c arms from the artifacts already on disk, without touching a browser.

I needed this because my first judge counted a sample whose `page.evaluate` failed as "the probe navigated
again".  That sample is the page CHANGING UNDER THE PROBE - it is evidence of the product's reload, not of a
user navigation, and it turned a clean MET arm RED.  The readings themselves did not change; only the
arithmetic over them did.  Re-judging the SAME bytes is how I show that the correction moved a verdict and
nothing else.

The fixed judge lives in `q274_b2c_run.py` and is imported here, so there is exactly one copy of the rule.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
sys.path.insert(0, str(SPIKE))
import q274_b2c_run as R  # noqa: E402
import q274_gen_identity as ident  # noqa: E402

arms = sys.argv[1:] or list(R.ARMS)
g_new = ident.disk_identity("new-generation", R.NEW_GEN)
ident.refuse_if_unusable(g_new, "swap target")
new_sha = list(g_new["per_script"].values())[0]["sha256"]

out = {}
for arm in arms:
    run_p = WORK / f"b2c_{arm}_run.json"
    log_p = WORK / f"b2c_origin_{arm}.log"
    if not run_p.exists() or not log_p.exists():
        print(f"  {arm:16s} NO ARTIFACT ({run_p.name}/{log_p.name})")
        continue
    b2c = json.loads(run_p.read_text(encoding="utf-8"))
    recs = R.log_records(log_p)
    d = R.derive(recs, b2c, new_sha)
    v, why = R.verdict_of(arm, d)
    d["verdict"], d["why"], d["expected"] = v, why, R.EXPECT[arm]
    d["agrees_with_expectation"] = v == R.EXPECT[arm]
    d["artifact"] = {"run": run_p.name, "log": log_p.name,
                     "run_blob": ident.blob_sha(run_p), "log_blob": ident.blob_sha(log_p),
                     "bytes": run_p.stat().st_size}
    d["samples"] = b2c.get("samples")
    d["origin_write_records"] = [r for r in recs if str(r.get("event", "")).startswith("write")]
    out[arm] = d
    print(f'  {arm:16s} {v:4s} expected={R.EXPECT[arm]:4s} agrees={d["agrees_with_expectation"]}  '
          f'writes={d["writes_started"]}/{d["writes_finished"]} delivered={d["write_delivered"]} '
          f'undelivered={d["write_undelivered"]} open_at_swap={d["writes_open_at_swap"]} '
          f'loads={d["document_loads_seen"]} pending={d["pending_handover_marker_seen"]} '
          f'tag={d["gen_tag_at_end"]!r} sha==new={d["executed_sha_equals_new_generation_bytes"]}')
    print(f'      {why}')

p = WORK / "ord0274_b2c_rejudged.json"
prev = WORK / "ord0274_b2c_runtime.json"
old = json.loads(prev.read_text(encoding="utf-8")) if prev.exists() else {"arms": {}}
flips = {a: {"was": (old["arms"].get(a) or {}).get("verdict"), "now": d["verdict"]}
         for a, d in out.items() if (old["arms"].get(a) or {}).get("verdict") not in (None, d["verdict"])}
p.write_text(json.dumps({"arms": out, "verdict_flips_vs_previous_receipt": flips,
                         "judge": "q274_b2c_run.verdict_of (single copy, imported here)",
                         "new_generation_entry_sha256": new_sha},
                        ensure_ascii=False, indent=1), "utf-8", newline="\n")
agree = sum(1 for d in out.values() if d["agrees_with_expectation"])
print(f"\n{agree}/{len(out)} arms agree with their expectation; verdict flips vs the earlier receipt: "
      f"{json.dumps(flips, ensure_ascii=False)}")
print("->", p.name)
