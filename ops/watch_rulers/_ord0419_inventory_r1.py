"""ORD-0419 inventory: every hardcoded English string in three named panels, computed from the bytes of the
authoritative tip, each one cross-checked against what a zh device actually rendered.

Why this file exists instead of a hand-written list: the order I am about to dispatch quotes counts.  A count
I type is a count I can get wrong, so every number here is derived by re-reading the exported source at the
named sha and by re-reading the rendered receipts, and the two sides are joined per string.  If a string I
claim is "on screen" is not in the receipt, this script says NOT_IN_RECEIPT rather than letting me ship the
claim.

Three origin shapes are separated, because the existing ORD-0370 face (`tools/cnx_copy_tiers_r1.py`,
HARDCODED_FALLBACK) only inspects `??` slots and therefore cannot see any of them:
  JSX_TEXT   `<h3>Capability needs</h3>`            - a text node, no literal at all
  TERNARY    `x.length ? a : "No learned signals"`  - a bare literal in a ternary arm
  DEFAULT    `useState("I prefer quiet ...")`       - a bare literal as an initial value

Output: a JSON receipt + a UTF-8 text table.  ASCII summary to stdout (this box's console is GBK).
Read-only.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHA = "8a7665be2061a2f38aa2227f81c57003ca4caacb"
SRC = r"D:\moodle\_qoder_cmdr_scan_8a7665be\frontend\src"
RECEIPTS = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_untranslated_r2_all"
TWIN_RECEIPT = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_untranslated_r2\untranslated_twin_r2.json"
OUT = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_ord0419_inventory_r1.json"

# (file, line, exact string, origin shape, screen route it is expected on, or None when branch-gated)
CLAIMS = [
    ("features/traveler-twin/TwinPanel.tsx", 13, "No explicit capability facts recorded.", "JSX_TEXT", "twin"),
    ("features/traveler-twin/TwinPanel.tsx", 14, "Confirmed by traveler", "TERNARY", None),
    ("features/traveler-twin/TwinPanel.tsx", 14, "Stated; confirmation needed", "TERNARY", None),
    ("features/traveler-twin/TwinPanel.tsx", 24, "No explicit preferences", "TERNARY", None),
    ("features/traveler-twin/TwinPanel.tsx", 24, "Capability needs", "JSX_TEXT", "twin"),
    ("features/traveler-twin/TwinPanel.tsx", 24, "No learned signals", "TERNARY", "twin"),
    ("features/traveler-twin/TwinPanel.tsx", 24, "Learned capability state", "JSX_TEXT", "twin"),
    ("features/traveler-twin/TwinPanel.tsx", 24, "hard need(s) remain explicit and are never learned.",
     "TERNARY_TEMPLATE", None),
    ("features/traveler-twin/TwinPanel.tsx", 24, "Hard accessibility needs are never inferred from behavior.",
     "TERNARY", "twin"),
    ("features/traveler-twin/TwinPanel.tsx", 24, "Unknown accessibility evidence is not accessible.",
     "JSX_TEXT", "twin"),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 120, "policy unavailable · confirmation required",
     "TERNARY", None),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 125, "V14 · REALITY CHANGED", "JSX_TEXT", "authoritative"),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 126, "Grounded adaptive recovery", "JSX_TEXT", "authoritative"),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 129, "Refresh recovery", "JSX_TEXT", "authoritative"),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 132, "No recovery proposal is waiting on this Journey.",
     "JSX_TEXT", "authoritative"),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 137, "CHANGED", "JSX_TEXT", None),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 144, "PROTECTED", "JSX_TEXT", None),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 153, "Baseline evidence", "JSX_TEXT", None),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 157, "Incident evidence", "JSX_TEXT", None),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 163, "Deterministic gate", "JSX_TEXT", None),
    ("features/recovery/V14RecoveryTruthPanel.tsx", 167, "Delegation policy", "JSX_TEXT", None),
    ("features/discovery/RealCityDiscoveryPanel.tsx", 110,
     "I prefer quiet indoor culture, low walking, and rain-friendly places near my protected Journey moments.",
     "DEFAULT", "discover"),
]

# machine vocabulary rendered where a human word belongs - same screens, different fix (a mapping/format
# layer, not a dictionary entry)
MACHINE_RENDERS = [
    ("features/traveler-twin/TwinPanel.tsx", 24, "explicit.join(\" · \") renders raw dimension codes",
     "culture · local_food · relaxed · walking_minutes_max · waterfront", "twin"),
    ("features/traveler-twin/TwinPanel.tsx", 9, "capabilityLabel returns item.code verbatim",
     "walking_minutes_max", "twin"),
    ("features/traveler-twin/TwinPanel.tsx", 14, "{item.severity} rendered verbatim", "HARD", None),
    ("features/inbox/JourneyInboxWorkbench.tsx", 764, "{item.at} rendered as a raw ISO-8601 string",
     "Nexus River Cruise Pier · 2026-10-10T15:30:00+08:00", "bookings"),
]


def rendered_texts(route):
    """Every string the zh arm actually rendered on `route`, per the r2 scroll-union receipts."""
    cands = [os.path.join(RECEIPTS, "untranslated_%s_r2.json" % route)]
    if route == "twin":
        cands.insert(0, TWIN_RECEIPT)
    for p in cands:
        if os.path.exists(p):
            d = json.load(io.open(p, encoding="utf-8"))
            return [x["text"] for x in d["zh"]["ascii_prose"]], p
    return None, None


bodies = {}
rows = []
missing = []
for rel, line, s, shape, route in CLAIMS:
    p = os.path.join(SRC, rel.replace("/", os.sep))
    if p not in bodies:
        bodies[p] = io.open(p, encoding="utf-8", errors="replace").read().split("\n")
    src_line = bodies[p][line - 1] if line - 1 < len(bodies[p]) else ""
    present = s in src_line
    if not present:
        missing.append({"file": rel, "line": line, "string": s, "line_head": src_line[:120]})
    on_screen = None
    receipt = None
    if route:
        texts, receipt = rendered_texts(route)
        on_screen = (None if texts is None else any(s in t for t in texts))
    rows.append({"file": rel, "line": line, "string": s, "origin_shape": shape,
                 "present_at_that_line": present, "expected_route": route,
                 "seen_in_zh_receipt": on_screen, "receipt": (os.path.basename(receipt) if receipt else None),
                 "branch_gated": route is None})

mach = []
for rel, line, how, example, route in MACHINE_RENDERS:
    p = os.path.join(SRC, rel.replace("/", os.sep))
    if p not in bodies:
        bodies[p] = io.open(p, encoding="utf-8", errors="replace").read().split("\n")
    src_line = bodies[p][line - 1] if line - 1 < len(bodies[p]) else ""
    texts, receipt = (rendered_texts(route) if route else (None, None))
    mach.append({"file": rel, "line": line, "mechanism": how, "example_rendered": example,
                 "line_contains_example_fragment": bool(re.search(r"join|item\.code|item\.severity|item\.at", src_line)),
                 "seen_in_zh_receipt": (None if texts is None else any(example in t or t in example for t in texts)),
                 "receipt": (os.path.basename(receipt) if receipt else None)})

t_calls = {}
for rel in sorted({c[0] for c in CLAIMS}):
    body = "\n".join(bodies[os.path.join(SRC, rel.replace("/", os.sep))])
    t_calls[rel] = len(re.findall(r'\bt\("', body))

on_screen_rows = [r for r in rows if r["seen_in_zh_receipt"] is True]
not_seen = [r for r in rows if r["expected_route"] and r["seen_in_zh_receipt"] is not True]
res = {
    "generated_by": "_ord0419_inventory_r1.py",
    "authoritative_sha": SHA,
    "source_tree": SRC,
    "hardcoded_prose_strings_claimed": len(CLAIMS),
    "hardcoded_prose_present_at_claimed_line": len([r for r in rows if r["present_at_that_line"]]),
    "claims_that_failed_the_line_check": len(missing),
    "failed_line_checks": missing,
    "proven_on_screen_in_zh": len(on_screen_rows),
    "branch_gated_not_observed": len([r for r in rows if r["branch_gated"]]),
    "expected_on_screen_but_not_seen": len(not_seen),
    "expected_on_screen_but_not_seen_rows": not_seen,
    "machine_vocabulary_renders": len(mach),
    "t_calls_per_file": t_calls,
    "rows": rows,
    "machine_rows": mach,
    "verdict": ("INVENTORY_CONSISTENT" if not missing and not not_seen else "INVENTORY_INCONSISTENT"),
}
with io.open(OUT, "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)

lines = ["ORD-0419 INVENTORY (computed from the bytes of %s)" % SHA, ""]
lines.append("hardcoded English prose strings claimed: %d" % res["hardcoded_prose_strings_claimed"])
lines.append("  present at the claimed file:line:      %d" % res["hardcoded_prose_present_at_claimed_line"])
lines.append("  failed the line check:                 %d" % res["claims_that_failed_the_line_check"])
lines.append("  proven rendered on a zh screen:        %d" % res["proven_on_screen_in_zh"])
lines.append("  branch-gated (in source, not reached):  %d" % res["branch_gated_not_observed"])
lines.append("  expected on screen but NOT seen:       %d" % res["expected_on_screen_but_not_seen"])
lines.append("machine-vocabulary renders (different fix): %d" % res["machine_vocabulary_renders"])
lines.append("")
lines.append("t() calls per file, against the hardcoded count in the same file:")
per_file_hard = {}
for r in rows:
    per_file_hard[r["file"]] = per_file_hard.get(r["file"], 0) + 1
for k in sorted(per_file_hard, key=lambda x: -per_file_hard[x]):
    lines.append("  %-52s t()=%-3d hardcoded=%d" % (k, t_calls.get(k, 0), per_file_hard[k]))
lines.append("")
for r in rows:
    flag = "ON_SCREEN " if r["seen_in_zh_receipt"] else ("branch-gated" if r["branch_gated"] else "NOT_SEEN!!")
    lines.append("  [%s] %-18s %s:%d" % (flag, r["origin_shape"], r["file"], r["line"]))
    lines.append("        %r" % r["string"])
lines.append("")
lines.append("machine vocabulary:")
for m in mach:
    lines.append("  %s:%d  %s" % (m["file"], m["line"], m["mechanism"]))
    lines.append("        rendered example: %r  (in zh receipt: %s)" % (m["example_rendered"], m["seen_in_zh_receipt"]))
lines.append("")
lines.append("VERDICT " + res["verdict"])
TXT = OUT.replace(".json", ".txt")
with io.open(TXT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print("claimed", res["hardcoded_prose_strings_claimed"], "| line-check passed",
      res["hardcoded_prose_present_at_claimed_line"], "| failed", res["claims_that_failed_the_line_check"])
print("on screen", res["proven_on_screen_in_zh"], "| branch-gated", res["branch_gated_not_observed"],
      "| expected-but-not-seen", res["expected_on_screen_but_not_seen"])
print("t() calls:", json.dumps(t_calls, ensure_ascii=False))
print("VERDICT", res["verdict"])
print("wrote", OUT, os.path.getsize(OUT), "B")
print("wrote", TXT, os.path.getsize(TXT), "B")
