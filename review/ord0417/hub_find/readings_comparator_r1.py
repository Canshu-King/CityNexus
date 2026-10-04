"""ORD-0417 hub 那格：把四趟闸读数收成一枚件，并成对比玻璃闸那两枚红是不是这手带来的。

只读已经落盘的日志，不重跑测试。红集合只从汇总块里取：`--reporter=line` 的进度行也长得像
"[chromium] › …"，把它当失败读会把跑过的绿读成红（这一族我自己踩过一次，形制沿用当时的修法：
先找到"N failed"那行，再往下数缩进四空的条目）。

usage: python hub_pins_readings_r1.py
"""
import argparse
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
RUN = LANE / "run"
TIP = "eaf4069e5d07a3dacc1ec33a0be515119208e16e"
REL = "frontend/src/components/v8/MapPanel.tsx"
FAIL_COUNT = re.compile(r"^\s*(\d+) failed", re.M)
PASS_COUNT = re.compile(r"^\s*(\d+) passed", re.M)
ARM = re.compile(r"^\s{4}\[[a-z-]+\] › (\S+?) › (\S.*)$", re.M)


def text(path: pathlib.Path) -> str:
    return io.open(path, encoding="utf-8", errors="replace").read() if path.exists() else ""


def reading(path: pathlib.Path) -> dict:
    body = text(path)
    fails = FAIL_COUNT.search(body)
    passes = PASS_COUNT.search(body)
    reds = []
    if fails:
        after = body[fails.end():]
        reds = sorted({"%s :: %s" % (m.group(1), m.group(2).strip()) for m in ARM.finditer(after)})
    return {"file": path.name, "failed": int(fails.group(1)) if fails else 0,
            "passed": int(passes.group(1)) if passes else None, "red_arms": reds,
            "present": path.exists()}


def git(*args):
    return subprocess.run(["git", "-C", r"D:/moodle/CityNexus", *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hub-fixed", default="_hub_fixed_day35.out")
    ap.add_argument("--glass-fixed", default="_glass_fixed_day35.out")
    ap.add_argument("--out", default="hub_pins_readings_r1.json")
    ap.add_argument("--variant", default="A_reserve_plus_safety_gap")
    args = ap.parse_args()
    hub_base = reading(RUN / "_hub_base_day35.out")
    hub_fixed = reading(RUN / args.hub_fixed)
    glass_base = reading(RUN / "_glass_base_day35.out")
    glass_fixed = reading(RUN / args.glass_fixed)
    tree_blob = hashlib.sha256((LANE / "hubcut" / REL).read_bytes()).hexdigest()
    tip_blob = hashlib.sha256(subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "show", f"{TIP}:{REL}"],
                                             capture_output=True, check=True).stdout).hexdigest()
    new_red = sorted(set(glass_fixed["red_arms"]) - set(glass_base["red_arms"]))
    recovered = sorted(set(glass_base["red_arms"]) - set(glass_fixed["red_arms"]))
    report = {
        "schema": "CNX_ORD0417_HUB_PINS_READINGS_R1",
        "variant": args.variant,
        "tip": TIP,
        "git_blob_ids": {
            "mappanel_on_tip": git("rev-parse", f"{TIP}:{REL}"),
            "mappanel_in_this_tree": git("hash-object", str(LANE / "hubcut" / REL)),
        },
        "sha256_of_the_patched_file": {"tree_now": tree_blob, "tip_bytes": tip_blob,
                                       "tree_equals_tip": tree_blob == tip_blob},
        "hub_gate": {"baseline_on_tip_bytes": hub_base, "after_this_hand": hub_fixed},
        "glass_gate": {"baseline_on_tip_bytes": glass_base, "after_this_hand": glass_fixed},
        "glass_red_set": {"new_red": new_red, "recovered": recovered,
                          "verdict": "NEW_RED_EMPTY" if not new_red else "NEW_RED_FOUND"},
        "commands": {
            "gate": "python run/ord0512_run_gate_r1.py <run-id> <spec> --reporter=line "
                    "with ORD0512_TREE=hubcut ORD0512_PORTS=<front>,<back>",
            "run_ids": ["ord0417hub_day35 (tip bytes)", "ord0417hub_day35fix (patched)",
                        "ord0512glass_day35base (tip bytes)", "ord0512glass_day35fix (variant A)", "ord0417hub_leanB (variant B)", "ord0512glass_leanB (variant B)"],
            "apply_revert": "python run/ord0417_top_reservation_r1.py <apply|revert> --tree hubcut",
        },
    }
    out = RUN / args.out
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + chr(10), encoding="utf-8", newline="\n")
    print("hub base failed=%s passed=%s | hub fixed failed=%s passed=%s"
          % (hub_base["failed"], hub_base["passed"], hub_fixed["failed"], hub_fixed["passed"]))
    print("glass base failed=%s passed=%s | glass fixed failed=%s passed=%s"
          % (glass_base["failed"], glass_base["passed"], glass_fixed["failed"], glass_fixed["passed"]))
    print("glass verdict=%s new_red=%d recovered=%d" % (report["glass_red_set"]["verdict"], len(new_red), len(recovered)))
    print("tree_equals_tip=%s (True means the patched bytes were NOT left in place)" % report["sha256_of_the_patched_file"]["tree_equals_tip"])
    print("WROTE=%s" % out)
    return 0 if all(x["present"] for x in (hub_base, hub_fixed, glass_base, glass_fixed)) else 4


if __name__ == "__main__":
    sys.exit(main())
