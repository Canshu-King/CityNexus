"""Fold the counter-arm readings into one verdict table: which assertion bit, on which generation, and
what the screen painted instead.

Every line here is derived from the reading files the runs wrote -- the judgement "判据真咬" is only
printed when a target arm carries a failed check AND the control arm in the same generation is clean, so
a mutation that broke the whole screen would not be mistaken for a bite.
"""
import glob
import io
import json
import os
import time

EVID = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/checkin-words-mutants-day25")
OUT = "%s/receipts/day25_mutants_summary_r1.json" % EVID
GENERATIONS = ["base", "m1", "m1_revert", "m2"]
TARGETS = ["targetRequired", "targetAmbiguous"]
CONTROL = "journeyInBin"
LOCALES = ["zh-CN", "en"]


def read(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main():
    generations = {}
    for gen in GENERATIONS:
        rows = {}
        for name in sorted(glob.glob("%s/readings/%s/w-*.json" % (EVID, gen))):
            body = read(name)
            checks = body.get("checks") or {}
            rows["%s/%s" % (body["locale"], body["state"])] = {
                "file": os.path.basename(name),
                "painted": body.get("painted_notice"),
                "notices_count": body.get("notices_count"),
                "failed": sorted(k for k, v in checks.items() if v is False),
                "expected": body.get("expected_from_table"),
            }
        generations[gen] = rows

    per_gen = {}
    for gen, rows in generations.items():
        caught = {}
        for key, row in rows.items():
            for check in row["failed"]:
                caught.setdefault(check, []).append(key)
        per_gen[gen] = {
            "arms": len(rows),
            "arms_red": sorted(k for k, v in rows.items() if v["failed"]),
            "arms_green": sorted(k for k, v in rows.items() if not v["failed"]),
            "checks_that_bit": {k: sorted(v) for k, v in sorted(caught.items())},
            "control_green": all(not rows.get("%s/%s" % (loc, CONTROL), {}).get("failed", ["x"])
                                 for loc in LOCALES),
            "targets_red": all(rows.get("%s/%s" % (loc, t), {}).get("failed")
                               for loc in LOCALES for t in TARGETS),
        }

    mutations = read("%s/receipts/target_sentences_mutant_r1.json" % EVID)["events"]
    commits = read("%s/receipts/mutant_commits_r1.json" % EVID)["events"]
    ownership_path = "%s/receipts/mutant_stack_ownership_r1.json" % EVID
    ownership = read(ownership_path) if os.path.exists(ownership_path) else {"missing": ownership_path}

    m1_bits = [c for c in per_gen["m1"]["checks_that_bit"] if c == "painted_equals_the_tables_own_row"]
    m2_bits = [c for c in per_gen["m2"]["checks_that_bit"] if c == "exactly_one_notice_on_the_whole_screen"]
    verdict = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generations": generations,
        "per_generation": per_gen,
        "mutation_events": mutations,
        "mutant_commits": commits,
        "ownership": {k: ownership.get(k) for k in ("every_lane_proven", "entry_assets_all_distinct",
                                                    "lanes") if k in ownership},
        "judgement": {
            "M1_bites": bool(per_gen["m1"]["targets_red"] and per_gen["m1"]["control_green"]
                             and m1_bits),
            "M1_assertion": m1_bits,
            "M2_bites": bool(per_gen["m2"]["targets_red"] and per_gen["m2"]["control_green"]
                             and m2_bits),
            "M2_assertion": m2_bits,
            "revert_restores_green": bool(per_gen["m1_revert"]["arms_red"] == []
                                          and per_gen["m1_revert"]["arms"] == per_gen["base"]["arms"]),
            "base_was_clean": bool(per_gen["base"]["arms_red"] == []),
        },
        "what_the_screen_said_instead": {
            "m1_zh_targetRequired": generations["m1"].get("zh-CN/targetRequired", {}).get("painted"),
            "m2_zh_targetRequired": generations["m2"].get("zh-CN/targetRequired", {}).get("painted"),
        },
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(verdict, handle, indent=1, ensure_ascii=False)
    printable = json.dumps({"per_generation": per_gen, "judgement": verdict["judgement"],
                            "what_the_screen_said_instead": verdict["what_the_screen_said_instead"]},
                           ensure_ascii=False, indent=1)
    print(printable.encode("ascii", "replace").decode("ascii")[:2200])
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(verdict, ensure_ascii=False).encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
