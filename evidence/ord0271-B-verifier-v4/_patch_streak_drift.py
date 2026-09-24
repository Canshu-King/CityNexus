"""One-shot patch: drift means a contradiction, not a difference in check coverage.

The aggregator flagged every round as `STREAK_INVALID` because it computes one check the round-receipt builder
does not (`mutant_face_answered_the_mutant_bytes`), so the stored value was simply absent. Comparing a set against
a superset that way can only ever produce noise, and noise in a verdict field is worse than no field. Now only
keys both sides computed can contradict; keys the aggregator has alone are listed as extra coverage it verified,
and keys the receipt has alone are listed as unchecked-by-aggregator so the gap is visible rather than implied.
"""
import ast
import pathlib

p = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\ord0271b_streak.py")
t = p.read_text(encoding="utf-8")
before = t

old = '''    stored = rec.get("checks") or {}
    drift = {k: {"stored": stored.get(k), "recomputed": v} for k, v in checks.items()
             if stored.get(k) != v}
    return {"checks": checks, "green": sum(1 for v in checks.values() if v), "total": len(checks),'''
new = '''    stored = rec.get("checks") or {}
    # a contradiction is both sides computing the same key and disagreeing; a key one side does not have is a
    # coverage difference and belongs in its own field, never in a verdict
    drift = {k: {"stored": stored[k], "recomputed": v} for k, v in checks.items()
             if k in stored and stored[k] != v}
    only_aggregator = {k: v for k, v in checks.items() if k not in stored}
    only_receipt = sorted(set(stored) - set(checks))
    return {"checks": checks, "green": sum(1 for v in checks.values() if v), "total": len(checks),
            "checks_only_in_aggregator": only_aggregator, "checks_only_in_receipt": only_receipt,'''
assert t.count(old) == 1
t = t.replace(old, new, 1)

old2 = '''                       "capture_blob40": (rec.get("capture") or {}).get("blob40"),
                       "latest_reading_on_origin_clock": read_at})'''
new2 = '''                       "capture_blob40": (rec.get("capture") or {}).get("blob40"),
                       "checks_only_in_aggregator": sorted(rj["checks_only_in_aggregator"]),
                       "checks_only_in_receipt": rj["checks_only_in_receipt"],
                       "latest_reading_on_origin_clock": read_at})'''
assert t.count(old2) == 1
t = t.replace(old2, new2, 1)

assert t != before
ast.parse(t)
p.write_bytes(t.encode("utf-8"))
print("patched; bytes", len(t.encode("utf-8")))
