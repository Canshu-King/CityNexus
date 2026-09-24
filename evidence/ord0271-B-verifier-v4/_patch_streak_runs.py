"""One-shot patch: the streak must name the red rounds *and* report the consecutive green run it did get.

A single `STREAK_BROKEN` string hides two things a reader needs: which round broke it and why, and how long the
unbroken run actually is. The口径 the commander set is that rounds must be logically consecutive and each one
self-contained, so a broken middle ring is not a streak - but the run that did hold is still a measurement, and
reporting only "broken" would throw it away.
"""
import ast
import pathlib

p = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\ord0271b_streak.py")
t = p.read_text(encoding="utf-8")
before = t

old = '''    if missing:
        verdict = f"INCOMPLETE(missing receipts: {','.join(missing)})"
    elif gaps:
        verdict = "STREAK_BROKEN(rounds not consecutive)"
    elif drift_rounds:
        verdict = "STREAK_INVALID(receipt text does not match its own readings)"
    elif len(green_rounds) == len(rounds) and rounds:
        verdict = f"STREAK_MET({len(green_rounds)})"
    else:
        bad = [r["file"] + ":" + ",".join(r.get("red_checks") or []) for r in rounds
               if r.get("recomputed") != "ROUND_GREEN"]
        verdict = "STREAK_BROKEN(" + ";".join(bad) + ")"'''

new = '''    # longest run of consecutive green rounds, in the order the receipts were asked for
    runs, cur = [], []
    for r in rounds:
        if r.get("recomputed") == "ROUND_GREEN":
            cur.append(r.get("round"))
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    best = max(runs, key=len) if runs else []
    red_named = [f"round {r.get('round')}:{','.join(r.get('red_checks') or ['?'])}" for r in rounds
                 if r.get("recomputed") != "ROUND_GREEN"]
    if missing:
        verdict = f"INCOMPLETE(missing receipts: {','.join(missing)})"
    elif gaps:
        verdict = "STREAK_BROKEN(rounds not consecutive)"
    elif drift_rounds:
        verdict = "STREAK_INVALID(receipt text does not match its own readings)"
    elif len(green_rounds) == len(rounds) and rounds:
        verdict = f"STREAK_MET({len(green_rounds)})"
    else:
        verdict = ("STREAK_BROKEN(" + ";".join(red_named) + f"); longest_consecutive_green_run="
                   f"{len(best)}" + (f"(rounds {best[0]}..{best[-1]})" if best else ""))'''

assert t.count(old) == 1, "verdict block not found"
t = t.replace(old, new, 1)
t = t.replace('''                      "gaps": gaps, "stored_vs_recomputed_mismatches": lying,''',
              '''                      "longest_consecutive_green_run": {"length": len(best), "rounds": best},
                      "red_rounds": red_named,
                      "gaps": gaps, "stored_vs_recomputed_mismatches": lying,''', 1)
t = t.replace('''           "rounds_requested": len(paths), "rounds_green": len(green_rounds),''',
              '''           "rounds_requested": len(paths), "rounds_green": len(green_rounds),
           "longest_consecutive_green_run": {"length": len(best), "rounds": best},
           "red_rounds": red_named,''', 1)
assert "longest_consecutive_green_run" in t and t != before
ast.parse(t)
p.write_bytes(t.encode("utf-8"))
print("patched; bytes", len(t.encode("utf-8")))
