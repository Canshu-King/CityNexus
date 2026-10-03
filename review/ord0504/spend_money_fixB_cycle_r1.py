"""ORD-0504 B -- grade four generations of the 花费 face on one store, one variable at a time.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/spend_money_fixB_cycle_r1.py

  tip    `spendFacts.ts` exactly as the authoritative tip holds it -> all three arms red (two passes)
  fix    both shipped fixes                                        -> all three green (two passes)
  MB1    only `moneyText` put back to dividing every currency by 100 -> the exponent arms red, fake-zero green
  MB2    only the commitment's unlearned price put back as a zero  -> the fake-zero arm red, exponent green

The ruler is `review/ord0504/one_ticket_two_faces_r1.js`: it reads the same JPY ticket on both faces of one
journey and the money column of the 花费 tab, and its expectation comes from its own exponent table, never
from the helper under test. Each generation is built into its own directory, served on this lane's own
front, and witnessed -- the entry JS the port answers is hashed and required to equal the bytes just built,
because a cycle that grades a stale bundle proves nothing. Every pass writes its own JSON.

Environment: `BOOK_B_PASSES` overrides how many passes the tip and fix generations take (default 2).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import book_screen_controls_r1 as ctl  # noqa: E402

TARGET = ctl.TREE / "frontend" / "src" / "features" / "trip" / "spendFacts.ts"
RULER = "review/ord0504/one_ticket_two_faces_r1.js"
TIP = "701b5e3868fa9bed6e7b6a377d1c4a38a5e0d06b"
OUT = ctl.TREE / "review" / "ord0504" / "spend_money_fixB_cycle_r1.txt"
PASSES = int(os.environ.get("BOOK_B_PASSES", "2"))

BODY_NEW = b"""  const digits = currencyExponent(currency);
  return `${currency} ${(amountMinor / currencyMinorFactor(currency)).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;"""

BODY_MB1 = b"""  const digits = 2;
  return `${currency} ${(amountMinor / 100).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;"""

GUARD_NEW = b"""    const learned = String(commitment.monetary_value_status ?? "") === "KNOWN";"""
GUARD_MB2 = b"""    const learned = true; // MB2: every stored digit is trusted, whatever the status word says"""

ARMS = {
    "exponent": "spend/a_zero_decimal_amount_keeps_its_own_exponent_on_the_face",
    "agreement": "spend/the_two_faces_of_one_journey_agree_on_one_ticket",
    "fake_zero": "spend/an_unlearned_commitment_price_is_not_a_zero_on_the_face",
}


def git_show(rev: str, path: str) -> bytes:
    done = subprocess.run(["git", "-C", str(ctl.TREE), "show", "%s:%s" % (rev, path)],
                          capture_output=True)
    if done.returncode:
        raise SystemExit("REFUSE: git show %s:%s failed (%s)" % (rev, path, done.stderr[-200:]))
    return done.stdout


def replace_once(data: bytes, find: bytes, replace: bytes, label: str) -> bytes:
    if data.count(find) != 1:
        raise SystemExit("REFUSE: %s found %d times in the shipped file; the mutant is not single-variable"
                         % (label, data.count(find)))
    return data.replace(find, replace, 1)


def grade(tag: str, data: bytes) -> dict:
    TARGET.write_bytes(data)
    dist = "dist_cycleB_%s" % tag
    ctl.rebuild(dist)
    ctl.restart_front(dist)
    served = ctl.served_entry()
    on_disk = ctl.sha1((ctl.LANE / dist / served["entry"].lstrip("/")).read_bytes())
    sink = "review/ord0504/spend_money_armsB_%s.json" % tag
    env = dict(os.environ, SPEND_OUT=sink)
    done = subprocess.run([ctl.NODE, RULER], cwd=str(ctl.TREE), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env)
    payload = json.loads((ctl.TREE / sink).read_text(encoding="utf-8"))
    reds = sorted(x["arm"] for x in payload.get("results", []) if not x.get("pass"))
    summary = [line for line in done.stdout.splitlines() if line.startswith("ARMS=")]
    return {"tag": tag, "summary": summary[-1] if summary else "no-summary", "reds": reds,
            "sink": sink, "entry": served["entry"], "served_sha1": served["sha1"],
            "served_equals_built": on_disk == served["sha1"],
            "generated_at": payload.get("generated_at"),
            "driver_error": payload.get("driver_error") or "none", "exit": done.returncode}


def main() -> int:
    shipped = TARGET.read_bytes()
    tip_bytes = git_show(TIP, "frontend/src/features/trip/spendFacts.ts")
    # MB1: only the money helper's量纲 handling put back; the import line and the guard stay.
    mb1 = replace_once(shipped, BODY_NEW, BODY_MB1, "the shipped moneyText body")
    # MB2: only the commitment's learned-ness put back; the amount expression stays.
    mb2 = replace_once(shipped, GUARD_NEW, GUARD_MB2, "the shipped `learned` declaration")

    lines = ["ORD-0504 B cycle | the tip's own file bytes sha1 %s | shipped file sha1 %s"
             % (ctl.sha1(tip_bytes), ctl.sha1(shipped)), ""]
    runs = []
    for index in range(1, PASSES + 1):
        runs.append(("tip #%d" % index, grade("tip%d" % index, tip_bytes)))
    for index in range(1, PASSES + 1):
        runs.append(("fix #%d" % index, grade("fix%d" % index, shipped)))
    runs.append(("MB1", grade("mb1", mb1)))
    runs.append(("MB2", grade("mb2", mb2)))

    for name, res in runs:
        lines.append("=== %s  (generation %s)" % (name, res["tag"]))
        lines.append("    %s" % res["summary"])
        lines.append("    driver error: %s | exit %s | generated_at %s"
                     % (res["driver_error"], res["exit"], res["generated_at"]))
        lines.append("    red arms: %s" % (res["reds"] or "none"))
        lines.append("    served %s sha1 %s | equals the bundle this generation built: %s"
                     % (res["entry"], res["served_sha1"], res["served_equals_built"]))
        lines.append("    arms reading: %s" % res["sink"])
        lines.append("")

    tip_reds = runs[0][1]["reds"]
    fix_res = [r for n, r in runs if n.startswith("fix")]
    mb1_res = dict(runs)["MB1"]
    mb2_res = dict(runs)["MB2"]
    lines.append("verdict tip: red set = %s" % (tip_reds or "none"))
    lines.append("verdict tip: both passes same red set = %s"
                 % all(r["reds"] == tip_reds for _n, r in runs[:PASSES]))
    lines.append("verdict fix: every pass reports zero reds = %s"
                 % all(r["summary"].endswith("FAILED=0") for r in fix_res))
    lines.append("verdict MB1: exponent+agreement red = %s | fake-zero stays green = %s"
                 % (ARMS["exponent"] in mb1_res["reds"] and ARMS["agreement"] in mb1_res["reds"],
                    ARMS["fake_zero"] not in mb1_res["reds"]))
    lines.append("verdict MB2: fake-zero red = %s | exponent and agreement stay green = %s"
                 % (ARMS["fake_zero"] in mb2_res["reds"],
                    ARMS["exponent"] not in mb2_res["reds"] and ARMS["agreement"] not in mb2_res["reds"]))
    lines.append("verdict distinct evidence per pass: %s"
                 % (len({r["sink"] for _n, r in runs}) == len(runs)))

    TARGET.write_bytes(shipped)
    lines.append("")
    lines.append("restored: bytes_equal_to_shipped=%s sha1=%s"
                 % (TARGET.read_bytes() == shipped, ctl.sha1(TARGET.read_bytes())))
    lines.append("git status --porcelain -- frontend/src/features/trip/spendFacts.ts = %r"
                 % ctl.run(["git", "status", "--porcelain", "--",
                            "frontend/src/features/trip/spendFacts.ts"], cwd=ctl.TREE).stdout)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
