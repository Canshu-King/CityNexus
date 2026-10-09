"""Measure PUBLISHER_SECRET_SCAN_DEBT_1 against the arbiter's own examples, byte for byte.

Three groups, kept apart on purpose:
  R*  the ruling's counter-controls - these have an expected verdict and the script fails if they drift;
  I*  an INHERITED behaviour the measurement surfaced (same answer before and after my change) - recorded
      as a named note instead of being quietly folded into the ruling's expectations;
  X*  what the real file on this disk does, read from disk rather than from my memory of it.
"""
import importlib.util
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pe", os.path.join(HERE, "publish_evidence.py"))
pe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pe)

RULING = (
    ("R1 documentation mentions token/secret, no value at all",
     b"# the words token and secret appear in this documentation sentence only\n", "GREEN"),
    ("R2 placeholder marker inside the VALUE",
     b'API_KEY = "YOUR_TEST_ONLY_VALUE"\n', "GREEN"),
    ("R3 marker only in the NAME, value looks real  <- THE HOLE",
     b'SECRET_PLACEHOLDER_IN_NAME = "hunter2hunter2hunter2"\n', "RED"),
    ("R4 placeholder in a COMMENT, value looks real",
     b'# EXAMPLE SECRET\nAPI_TOKEN = "abcdefghijklmnopqrstuvwx"\n', "RED"),
    ("R5 SYNTHETIC_TEST_FIXTURE_VALUE with a placeholder-shaped value",
     b'SYNTHETIC_TEST_FIXTURE_VALUE="synthetic-safe-value"\n', "GREEN"),
)
INHERITED = (
    ("I1 Authorization line whose scheme is a placeholder",
     b"Authorization: Bearer YOUR_BEARER_TOKEN_HERE_PLACEHOLDER\n", "RED",
     "AUTH_HEADER captures only `Bearer` (its pattern ends at the first space), so there is no VALUE to "
     "launder and the header shape itself is refused.  Identical answer under the old code, so this is "
     "not a regression from the tightening - it is a named narrowness (PUBLISHER_SECRET_SCAN_NOTE_1)."),
)
INSTRUMENT = os.path.join(HERE, "test_ord0275_publisher_guard_r3.py")


def old_semantics(blob):
    """The pre-debt line-scope skip, recomputed here so 'before' is measured and not remembered."""
    for rule, pat in pe.SECRET_VALUE_PATTERNS:
        for m in pat.finditer(blob):
            line = m.group(0)
            if any(ph.lower() in line.lower() for ph in pe.PLACEHOLDER_MARKERS):
                continue
            return rule
    return None


def show(label, blob):
    before, after = old_semantics(blob), pe._content_refusal(blob)
    print(f"  {label:<58} before={('RED:' + before) if before else 'GREEN':<34} "
          f"after={('RED:' + after) if after else 'GREEN'}")
    return "RED" if after else "GREEN"


bad = 0
print("R* the ruling's counter-controls (expected verdict enforced):")
for label, blob, want in RULING:
    got = show(label, blob)
    ok = got == want
    bad += 0 if ok else 1
    print(f"     -> expected {want}, got {got}: {'ok' if ok else 'MISMATCH'}")

print("I* inherited narrowness (measured, named, NOT folded into the ruling):")
for label, blob, want, note in INHERITED:
    got = show(label, blob)
    print(f"     -> got {got} (same as before my change: {got == ('RED' if old_semantics(blob) else 'GREEN')})")
    print(f"     -> note: {note}")

print("X* the real instrument on this disk:")
if os.path.exists(INSTRUMENT):
    raw = io.open(INSTRUMENT, "rb").read()
    show(f"whole file {os.path.basename(INSTRUMENT)} ({len(raw)} B)", raw)
    for line in raw.splitlines():
        if b"SECRET_VALUE =" in line or b"SECRET_LINE =" in line:
            show("   line: " + line.decode("utf-8", "replace")[:52], line + b"\n")
    ex = pe.synthetic_fixture_exemption("live_checks/test_ord0275_publisher_guard_r3.py", raw)
    print(f"     Q23 exemption layer would say: {ex}")
    print("     guard_pre today still returns the refusal (the exemption is DISARMED by design):",
          bool(pe.guard_pre(INSTRUMENT, "live_checks/test_ord0275_publisher_guard_r3.py", raw)))
else:
    print("  instrument file missing - not measured")

print(f"\nruling_cases={len(RULING)} mismatch={bad}")
sys.exit(1 if bad else 0)
